#!/usr/bin/env python3
"""Market Pulse – one command.

  python run.py                 # rebuild today's pre-market report + everything, archive it
  python run.py --watch         # run forever: poll every N min, live feed + market data + re-render
  python run.py --once          # one watcher cycle (used by the GitHub Actions cron)
"""
import argparse, json, logging, logging.handlers, signal, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from market_pulse import collectors, processing, report, market, catalysts, validation
from market_pulse.clock import now_et, session, fmt, freshness

ROOT = Path(__file__).resolve().parent
DATA = report.DOCS / "data"
LIVE_PATH, DAILY_PATH, MKT_PATH, CAT_PATH = (DATA / "live.json", DATA / "latest.json", DATA / "market.json", DATA / "catalysts.json")
LIVE_MAX = 400
log = logging.getLogger("market-pulse")


def setup_logging(level="INFO"):
    (ROOT / "logs").mkdir(exist_ok=True)
    fmt_ = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = logging.handlers.RotatingFileHandler(ROOT / "logs" / "market_pulse.log", maxBytes=5_000_000, backupCount=5)
    sh = logging.StreamHandler(sys.stdout)
    for h in (fh, sh):
        h.setFormatter(fmt_)
    logging.basicConfig(level=level, handlers=[fh, sh])


def _load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _age_min(iso):
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(iso)).total_seconds() / 60
    except Exception:
        return 1e9


def build_daily(items, nstat, quotes, cat):
    now = now_et()
    return {
        "date": now.date().isoformat(),
        "generated_et": now.strftime("%a %b %d %Y, %I:%M %p ET"),
        "generated_at": now.isoformat(),
        "session_at_generation": session(now),
        "item_count": len(items),
        "quotes": quotes,
        "themes": processing.cluster_themes(items),
        "sectors": processing.sector_heat(items, quotes),
        "watchlist": processing.watchlist(items, quotes),
        "top_items": sorted(items, key=lambda x: x["impact"], reverse=True)[:60],
        "sources": nstat,
    }


def update_live(live, items):
    known = set(live.get("seen_ids", [])) | {i["id"] for i in live.get("items", [])}
    now = now_et(); seeding = not known; new = []
    for it in items:
        if it["id"] in known:
            continue
        known.add(it["id"])
        if seeding and it["age_hours"] > 12:
            continue
        it = dict(it, seen_at=datetime.now(timezone.utc).isoformat(), seen_et=fmt(now))
        it.pop("summary", None)
        new.append(it)
    new.sort(key=lambda x: (x["published"], x["impact"]), reverse=True)
    live["items"] = (new + live.get("items", []))[:LIVE_MAX]
    live["seen_ids"] = list(known)[-5000:]
    live["updated_et"] = fmt(now); live["updated_at"] = now.isoformat()
    return new


def cycle(force_daily=False):
    t0 = time.time(); now = now_et()
    live = _load(LIVE_PATH, {"items": []})
    daily = _load(DAILY_PATH, None)
    mkt = _load(MKT_PATH, {})
    cat = _load(CAT_PATH, {})
    vstate = validation.load()
    new_day = force_daily or not daily or daily.get("date") != now.date().isoformat()

    news, nstat = collectors.collect_news()
    items = processing.process(news)

    quotes, qstat = market.collect_quotes()
    if not quotes and mkt.get("quotes"):
        quotes = mkt["quotes"]; log.warning("quotes failed; reusing previous snapshot")
    mv = mkt.get("movers") or {}
    if new_day or session(now) == "pre-market" or not mv.get("ok") or _age_min(mv.get("fetched_at", "")) > 180:
        mv_new, prices = market.movers()
        if mv_new.get("ok"):
            mv = mv_new; mkt["prices"] = prices
    mkt.update(quotes=quotes, movers=mv, quotes_fetched_et=fmt(now), quotes_source=market.YAHOO, yf_status=qstat["yfinance"])

    if new_day or _age_min(cat.get("econ", {}).get("fetched_at", "")) > 60:
        cat["econ"] = catalysts.econ_calendar(items)
    if new_day or _age_min(cat.get("earnings", {}).get("fetched_at", "")) > 240:
        uni = {u["ticker"] for u in market.universe()} | set(k for k in quotes)
        top = [w["ticker"] for w in (daily or {}).get("watchlist", [])] + ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM", "UNH", "XOM", "UPS", "FDX"]
        e = catalysts.earnings_calendar(uni, fallback_symbols=[t for t in dict.fromkeys(top) if t in uni])
        if e["ok"] or not cat.get("earnings"):
            cat["earnings"] = e

    if new_day:
        daily = build_daily(items, nstat, quotes, cat)
    else:
        daily["sources"] = nstat  # source health is always current

    new = update_live(live, items)
    validation.log_new(vstate, new)
    try:
        filled = validation.fill(vstate, market.bars)
    except Exception:
        log.exception("validation fill failed"); filled = 0
    validation.save(vstate)
    vstats = validation.stats(vstate)

    bundle = {
        "generated_et": fmt(now), "generated_at": now.isoformat(), "session": session(now),
        "daily": daily, "live": {k: live[k] for k in ("items", "updated_et", "updated_at")},
        "market": mkt, "catalysts": cat, "validation": vstats,
        "why": processing.why_moved(sorted(items, key=lambda x: x["published"])),
        "sources": {**nstat, "Yahoo Finance quotes": {"ok": bool(quotes), "count": len(quotes),
                    "fetched_et": fmt(now)}, "Nasdaq earnings API": {"ok": cat.get("earnings", {}).get("ok", False),
                    "count": len(cat.get("earnings", {}).get("events", [])), "fetched_et": cat.get("earnings", {}).get("fetched_et")},
                    "Economic calendar": {"ok": not cat.get("econ", {}).get("fallback", True),
                    "count": len(cat.get("econ", {}).get("events", [])), "fetched_et": cat.get("econ", {}).get("fetched_et"),
                    "note": cat.get("econ", {}).get("source")}},
    }
    DATA.mkdir(parents=True, exist_ok=True)
    report.write_json(LIVE_PATH, live); report.write_json(DAILY_PATH, daily)
    report.write_json(MKT_PATH, mkt); report.write_json(CAT_PATH, cat)
    report.render(bundle)
    if new_day:
        report.archive(bundle)
    for n in sorted(new, key=lambda x: x["impact"], reverse=True)[:3]:
        log.info("NEW [%s] %s (%s)", n["impact"], n["title"], ",".join(n["tickers"]))
    log.info("cycle done in %.0fs: %d new live items (total %d), %d validation fills, new_day=%s",
             time.time() - t0, len(new), len(live["items"]), filled, new_day)
    return len(new)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--watch", action="store_true", help="poll continuously")
    ap.add_argument("--once", action="store_true", help="single watcher cycle")
    ap.add_argument("--interval", type=float, default=5, help="minutes between polls (default 5)")
    a = ap.parse_args()
    setup_logging()
    if not a.watch:
        cycle(force_daily=not a.once)
        return
    stop = {"v": False}
    def _sig(*_):
        stop["v"] = True; log.info("shutdown requested")
    signal.signal(signal.SIGTERM, _sig); signal.signal(signal.SIGINT, _sig)
    log.info("watcher started, interval %.1f min", a.interval)
    fails = 0
    while not stop["v"]:
        try:
            cycle(); fails = 0
        except Exception:
            fails += 1; log.exception("cycle failed (%d consecutive)", fails)
        end = time.time() + a.interval * 60 * (min(2 ** (fails - 1), 6) if fails else 1)
        while time.time() < end and not stop["v"]:
            time.sleep(1)
    log.info("watcher stopped")


if __name__ == "__main__":
    main()
