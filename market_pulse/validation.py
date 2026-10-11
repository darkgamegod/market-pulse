"""Sentiment validation: log (headline, ticker, sentiment) and the subsequent price move at +1h / +1d.
Prices come from Yahoo 5-minute bars incl. extended hours, anchored at the first bar at/after the time the
headline was first seen (so overnight/weekend headlines are measured from the next tradable bar)."""
import json, logging, math, re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .clock import now_et, fmt

log = logging.getLogger("validation")
PATH = Path(__file__).resolve().parent.parent / "docs" / "data" / "sentiment_log.json"
MAX = 4000
MIN_SAMPLE = 100          # below this the panel says "UNPROVEN"
TRADABLE = re.compile(r"^[A-Z]{1,5}(-[A-Z])?$")


def load():
    try:
        return json.loads(PATH.read_text())
    except Exception:
        return {"entries": []}


def log_new(state, new_items):
    known = {(e["id"], e["ticker"]) for e in state["entries"]}
    added = 0
    for it in new_items:
        if abs(it["sentiment"]) < 0.05:
            continue
        for t in it["tickers"][:3]:
            if not TRADABLE.match(t) or (it["id"], t) in known:
                continue
            state["entries"].append({"id": it["id"], "ticker": t, "sentiment": it["sentiment"], "title": it["title"][:140],
                                     "t0": it["seen_at"], "p0": None, "r1h": None, "r1d": None, "done": False})
            added += 1
    state["entries"] = state["entries"][-MAX:]
    return added


def _price_at(series, t):
    s = series[series.index >= t]
    if not len(s) or (s.index[0] - t) > timedelta(days=4):
        return None, None
    return float(s.iloc[0]), s.index[0].to_pydatetime()


def fill(state, bars_fn):
    now = datetime.now(timezone.utc)
    pend = [e for e in state["entries"] if not e["done"]]
    for e in pend:  # expire entries we can no longer look up (5d bar window)
        if now - datetime.fromisoformat(e["t0"]) > timedelta(days=5):
            e["done"] = True; e["expired"] = e["r1d"] is None
    pend = [e for e in pend if not e["done"] and now - datetime.fromisoformat(e["t0"]) > timedelta(hours=1)]
    if not pend:
        return 0
    tick = sorted({e["ticker"] for e in pend})[:200]
    df = bars_fn(tick)
    if df.empty:
        return 0
    filled = 0
    for e in pend:
        try:
            s = df[e["ticker"]]["Close"].dropna() if len(tick) > 1 else df["Close"].dropna()
        except KeyError:
            continue
        if not len(s):
            continue
        t0 = datetime.fromisoformat(e["t0"])
        if e["p0"] is None:
            p0, b0 = _price_at(s, t0)
            if p0 is None:
                continue
            e["p0"], e["b0"] = p0, b0.isoformat()
        b0 = datetime.fromisoformat(e["b0"])
        for key, dt in (("r1h", timedelta(hours=1)), ("r1d", timedelta(days=1))):
            if e[key] is None and now > b0 + dt + timedelta(minutes=20):
                p, _ = _price_at(s, b0 + dt)
                if p is not None:
                    e[key] = round((p / e["p0"] - 1) * 100, 3); filled += 1
        if e["r1d"] is not None:
            e["done"] = True
    return filled


def _corr(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs)); sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy), 3) if sx and sy else None


def stats(state):
    out = {"logged": len(state["entries"]), "min_sample": MIN_SAMPLE, "generated_et": fmt(now_et()), "horizons": {}}
    for key, name in (("r1h", "+1 hour"), ("r1d", "+1 day")):
        ev = [e for e in state["entries"] if e.get(key) is not None]
        directional = [e for e in ev if abs(e["sentiment"]) >= 0.25 and e[key] != 0]
        hits = sum(1 for e in directional if (e["sentiment"] > 0) == (e[key] > 0))
        n = len(directional)
        hr = hits / n if n else None
        ci = round(1.96 * math.sqrt(hr * (1 - hr) / n) * 100, 1) if n else None
        status = "UNPROVEN" if n < MIN_SAMPLE else ("EDGE?" if hr - ci / 100 > 0.5 else "NO EDGE (≈ coin flip)")
        out["horizons"][key] = {"name": name, "n_scored": len(ev), "n_directional": n,
                                "hit_rate": round(hr * 100, 1) if hr is not None else None, "ci95": ci,
                                "corr": _corr([e["sentiment"] for e in ev], [e[key] for e in ev]), "status": status}
    out["status"] = "UNPROVEN" if any(h["status"] == "UNPROVEN" for h in out["horizons"].values()) else "MEASURED"
    out["recent"] = [{k: e.get(k) for k in ("ticker", "sentiment", "title", "r1h", "r1d")}
                     for e in state["entries"][::-1] if e.get("r1h") is not None][:10]
    return out


def save(state):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_suffix(".tmp"); tmp.write_text(json.dumps(state)); tmp.replace(PATH)
