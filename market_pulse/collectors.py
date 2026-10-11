"""Collectors: RSS news + Yahoo Finance quotes (no API keys)."""
import logging, time, calendar
from datetime import datetime, timezone
import feedparser, requests

from .config import FEEDS, QUOTES, SECTOR_ETFS

log = logging.getLogger("collectors")
UA = {"User-Agent": "Mozilla/5.0 (MarketPulse research bot; educational)"}


def _retry(fn, tries=2, delay=2.0):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa
            last = e
            time.sleep(delay * (2 ** i))
    raise last


def fetch_feed(name, url):
    def go():
        r = requests.get(url, headers=UA, timeout=(6, 12))
        r.raise_for_status()
        return feedparser.parse(r.content)
    parsed = _retry(go)
    items = []
    for e in parsed.entries[:60]:
        t = e.get("published_parsed") or e.get("updated_parsed")
        ts = datetime.fromtimestamp(calendar.timegm(t), timezone.utc) if t else datetime.now(timezone.utc)
        title = (e.get("title") or "").strip()
        if not title:
            continue
        src = name
        # Google News titles end with " - Publisher"
        if "news.google.com" in url and " - " in title:
            title, pub = title.rsplit(" - ", 1)
            src = pub.strip()
        items.append({
            "title": title,
            "summary": (e.get("summary") or "")[:600],
            "link": e.get("link", ""),
            "source": src,
            "feed": name,
            "published": ts.isoformat(),
        })
    if not items:
        raise RuntimeError("feed returned 0 entries")
    return items


def collect_news():
    all_items, status = [], {}
    for name, url in FEEDS.items():
        try:
            got = fetch_feed(name, url)
            all_items += got
            status[name] = {"ok": True, "count": len(got)}
        except Exception as e:
            log.warning("feed %s failed: %s", name, e)
            status[name] = {"ok": False, "error": str(e)[:200]}
    return all_items, status


def collect_quotes():
    import yfinance as yf
    symbols = list(QUOTES) + list(SECTOR_ETFS)
    out, status = {}, {}
    try:
        df = _retry(lambda: yf.download(symbols, period="5d", interval="1d", group_by="ticker",
                                        progress=False, threads=True, auto_adjust=False))
    except Exception as e:
        log.error("yfinance download failed: %s", e)
        return out, {"yfinance": {"ok": False, "error": str(e)[:200]}}
    for s in symbols:
        try:
            closes = df[s]["Close"].dropna()
            if len(closes) < 2:
                raise ValueError("insufficient data")
            last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
            label, group = QUOTES.get(s, (SECTOR_ETFS.get(s, s), "Sectors"))
            out[s] = {"symbol": s, "label": label, "group": group, "price": round(last, 2),
                      "change": round(last - prev, 2), "pct": round((last / prev - 1) * 100, 2),
                      "asof": str(closes.index[-1].date())}
        except Exception as e:
            status[s] = {"ok": False, "error": str(e)[:100]}
    status["yfinance"] = {"ok": bool(out), "count": len(out)}
    return out, status


# Placeholder: X/Twitter trends. See README "Extending: X/Twitter".
def collect_social():
    return []
