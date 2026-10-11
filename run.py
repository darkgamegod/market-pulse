#!/usr/bin/env python3
"""Market Pulse – one command.

  python run.py                 # build today's pre-market report + dashboard (and archive it)
  python run.py --watch         # run forever: poll every N min, append live feed, re-render
  python run.py --once          # one watcher cycle (used by GitHub Actions cron)
"""
import argparse, json, logging, logging.handlers, signal, sys, time
from datetime import datetime, timezone
from pathlib import Path

from market_pulse import collectors, processing, report
from market_pulse.calendar import upcoming

ROOT = Path(__file__).resolve().parent
LIVE_PATH = report.DOCS / "data" / "live.json"
DAILY_PATH = report.DOCS / "data" / "latest.json"
LIVE_MAX = 400
log = logging.getLogger("market-pulse")


def setup_logging(level="INFO"):
    (ROOT / "logs").mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = logging.handlers.RotatingFileHandler(ROOT / "logs" / "market_pulse.log", maxBytes=5_000_000, backupCount=5)
    sh = logging.StreamHandler(sys.stdout)
    for h in (fh, sh):
        h.setFormatter(fmt)
    logging.basicConfig(level=level, handlers=[fh, sh])
    logging.getLogger("yfinance").setLevel(logging.WARNING)


def _load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def build_daily():
    t0 = time.time()
    news, nstat = collectors.collect_news()
    quotes, qstat = collectors.collect_quotes()
    items = processing.process(news)
    now = report.now_et()
    daily = {
        "date": now.date().isoformat(),
        "generated_et": now.strftime("%a %b %d %Y, %I:%M %p ET"),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "item_count": len(items),
        "quotes": quotes,
        "quotes_asof": max((q["asof"] for q in quotes.values()), default=None),
        "themes": processing.cluster_themes(items),
        "sectors": processing.sector_heat(items, quotes),
        "watchlist": processing.watchlist(items, quotes),
        "what_to_watch": upcoming(now.date(), items),
        "top_items": sorted(items, key=lambda x: x["impact"], reverse=True)[:60],
        "sources": {**nstat, **{k: v for k, v in qstat.items() if k == "yfinance"}},
        "failed_symbols": [k for k, v in qstat.items() if k != "yfinance" and not v.get("ok")],
    }
    log.info("daily report built: %d items, %d quotes, %.1fs", len(items), len(quotes), time.time() - t0)
    return daily, items


def update_live(live, items):
    known = set(live.get("seen_ids", [])) | {i["id"] for i in live.get("items", [])}
    now = report.now_et()
    seeding = not known
    new = []
    for it in items:
        if it["id"] in known:
            continue
        known.add(it["id"])
        if seeding and it["age_hours"] > 12:
            continue  # first run: remember old items but only show recent ones
        it = dict(it, seen_at=datetime.now(timezone.utc).isoformat(), seen_et=now.strftime("%b %d %I:%M %p ET"))
        it.pop("summary", None)
        new.append(it)
    new.sort(key=lambda x: (x["published"], x["impact"]), reverse=True)
    live["items"] = (new + live.get("items", []))[:LIVE_MAX]
    live["seen_ids"] = list(known)[-5000:]
    live["updated_et"] = now.strftime("%a %b %d, %I:%M %p ET")
    return new


def cycle(force_daily=False):
    """One poll: refresh news + quotes, append live items, rebuild daily if new ET day."""
    live = _load(LIVE_PATH, {"items": []})
    daily = _load(DAILY_PATH, None)
    today = report.now_et().date().isoformat()
    if force_daily or not daily or daily.get("date") != today:
        daily, items = build_daily()
        report.archive(daily)
    else:
        news, nstat = collectors.collect_news()
        items = processing.process(news)
        daily["sources"].update(nstat)
    new = update_live(live, items)
    for n in sorted(new, key=lambda x: x["impact"], reverse=True)[:5]:
        log.info("NEW [%s] %s (%s)", n["impact"], n["title"], ",".join(n["tickers"]))
    report.render(daily, live)
    log.info("cycle done: %d new live items (total %d)", len(new), len(live["items"]))
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
            fails += 1
            log.exception("cycle failed (%d consecutive)", fails)
        wait = a.interval * 60 * (min(2 ** (fails - 1), 6) if fails else 1)  # backoff on failure
        end = time.time() + wait
        while time.time() < end and not stop["v"]:
            time.sleep(1)
    log.info("watcher stopped")


if __name__ == "__main__":
    main()
