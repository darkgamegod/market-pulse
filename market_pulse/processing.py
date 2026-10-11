"""Dedupe, tag, sentiment, impact scoring, theme clustering."""
import re, hashlib, html
from datetime import datetime, timezone
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .config import TICKER_KEYWORDS, SECTOR_KEYWORDS, HIGH_IMPACT, THEME_RULES, CONSUMER_LENS

_sia = SentimentIntensityAnalyzer()
# finance-specific lexicon tweaks
_sia.lexicon.update({"plunge": -3, "plunges": -3, "tumble": -2.5, "tumbles": -2.5, "slump": -2.5,
    "soar": 2.5, "soars": 2.5, "surge": 2, "surges": 2, "rally": 2, "rallies": 2, "beat": 1.5,
    "beats": 1.5, "miss": -1.5, "misses": -1.5, "downgrade": -2, "upgrade": 2, "selloff": -2.5,
    "sell-off": -2.5, "recession": -2.5, "layoffs": -2, "bankruptcy": -3, "record": 1.2,
    "gains": 1.5, "falls": -1.5, "drops": -1.5, "rises": 1.2, "jumps": 2, "slides": -1.5})

TAG_RE = re.compile(r"<[^>]+>")
CASHTAG = re.compile(r"\$([A-Z]{1,5})\b")
PAREN_TICKER = re.compile(r"\((?:NYSE|NASDAQ|Nasdaq|NYSEARCA)?:?\s?([A-Z]{1,5})\)")
STOP = set("the a an of to in on for and or at by with from as is are be after amid over its it this that".split())


def clean(t):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", t or ""))).strip()


def norm_key(title):
    w = [x for x in re.findall(r"[a-z0-9]+", title.lower()) if x not in STOP]
    return w


def item_id(title):
    return hashlib.sha1(" ".join(norm_key(title)).encode()).hexdigest()[:12]


def dedupe(items):
    seen, out, sigs = set(), [], []
    for it in sorted(items, key=lambda x: x["published"], reverse=True):
        it["title"], it["summary"] = clean(it["title"]), clean(it["summary"])
        k = item_id(it["title"])
        if k in seen:
            continue
        ws = set(norm_key(it["title"]))
        # near-duplicate: Jaccard > 0.7 against kept items
        if any(len(ws & s) / max(1, len(ws | s)) > 0.7 for s in sigs):
            continue
        seen.add(k); sigs.append(ws)
        it["id"] = k
        out.append(it)
    return out


def tag(it):
    text = f" {it['title']} {it['summary']} ".lower()
    raw = f"{it['title']} {it['summary']}"
    tickers = set(CASHTAG.findall(raw)) | set(PAREN_TICKER.findall(raw))
    for kw, ts in TICKER_KEYWORDS.items():
        if re.search(r"(?<![a-z])" + re.escape(kw.strip()) + r"(?![a-z])", text):
            tickers.update(ts)
    sectors = [s for s, kws in SECTOR_KEYWORDS.items() if any(_kw(k, text) for k in kws)]
    themes = [n for n, kws in THEME_RULES if any(_kw(k, text) for k in kws)]
    it["consumer"] = bool(CONSUMER_LENS & set(sectors))
    it["tickers"], it["sectors"], it["themes"] = sorted(tickers), sectors, themes or ["Other Market News"]


def _kw(k, text):
    k = k.strip()
    if len(k) <= 4:  # short keywords need word boundaries ("ups" vs "groups")
        return re.search(r"(?<![a-z])" + re.escape(k), text) is not None and re.search(re.escape(k) + r"(?![a-z])", text) is not None \
            if " " in k else re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", text) is not None
    return k in text


def score(it, now=None):
    now = now or datetime.now(timezone.utc)
    s = _sia.polarity_scores(it["title"] + ". " + it["summary"][:200])["compound"]
    it["sentiment"] = round(s, 3)
    it["sentiment_label"] = "bullish" if s >= 0.25 else "bearish" if s <= -0.25 else "neutral"
    text = (it["title"] + " " + it["summary"]).lower()
    kw = sum(w for k, w in HIGH_IMPACT.items() if k in text)
    age_h = max(0, (now - datetime.fromisoformat(it["published"])).total_seconds() / 3600)
    recency = max(0.0, 1 - age_h / 36)  # fades over 36h
    raw = 1.5 * min(kw, 8) + 1.2 * min(len(it["tickers"]), 4) + 3 * abs(s) + 4 * recency
    if it["feed"].startswith("Fed"):
        raw += 4
    it["impact"] = round(min(10, raw * 10 / 26), 1)
    it["age_hours"] = round(age_h, 1)


def process(items):
    items = dedupe(items)
    now = datetime.now(timezone.utc)
    for it in items:
        tag(it); score(it, now)
    return items


def cluster_themes(items, top=8):
    themes = {}
    for it in items:
        for t in it["themes"]:
            themes.setdefault(t, []).append(it)
    out = []
    for name, its in themes.items():
        its.sort(key=lambda x: x["impact"], reverse=True)
        tick = {}
        for i in its:
            for t in i["tickers"]:
                tick[t] = tick.get(t, 0) + 1
        out.append({
            "name": name, "count": len(its),
            "score": round(sum(i["impact"] for i in its[:10]), 1),
            "sentiment": round(sum(i["sentiment"] for i in its) / len(its), 2),
            "tickers": sorted(tick, key=tick.get, reverse=True)[:6],
            "headlines": [{k: i[k] for k in ("title", "link", "source", "impact", "sentiment_label")} for i in its[:5]],
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:top]


def sector_heat(items, quotes):
    from .config import SECTOR_ETFS
    res = []
    for etf, name in SECTOR_ETFS.items():
        rel = [i for i in items if name in i["sectors"]]
        q = quotes.get(etf, {})
        res.append({"etf": etf, "name": name, "pct": q.get("pct"), "news": len(rel),
                    "sentiment": round(sum(i["sentiment"] for i in rel) / len(rel), 2) if rel else 0})
    return res


def why_moved(items):
    """ticker -> highest-impact headline mentioning it (used for 'why it moved' lines)."""
    best = {}
    for i in items:
        for t in i["tickers"]:
            if t not in best or i["impact"] > best[t]["impact"]:
                best[t] = {k: i.get(k) for k in ("title", "link", "source", "impact", "sentiment_label", "published")}
    return best


def watchlist(items, quotes, n=15):
    agg = {}
    for i in items:
        for t in i["tickers"]:
            a = agg.setdefault(t, {"ticker": t, "mentions": 0, "impact": 0.0, "sent": 0.0, "headlines": [], "why": None})
            if a["why"] is None or i["impact"] > a["why"]["impact"]:
                a["why"] = {k: i[k] for k in ("title", "link", "source", "impact", "sentiment_label")}
            a["mentions"] += 1; a["impact"] += i["impact"]; a["sent"] += i["sentiment"]
            if len(a["headlines"]) < 4:
                a["headlines"].append({k: i[k] for k in ("title", "link", "source")})
    out = []
    for a in agg.values():
        a["sentiment"] = round(a.pop("sent") / a["mentions"], 2)
        a["impact"] = round(a["impact"], 1)
        q = quotes.get(a["ticker"])
        a["pct"] = q["pct"] if q else None
        out.append(a)
    out.sort(key=lambda x: x["impact"], reverse=True)
    return out[:n]
