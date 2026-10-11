# Market Pulse (MVP)

Daily pre-market research dashboard + always-on live news feed for day-trading trainees.
**Educational research only, not financial advice.**

## Quick start
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run.py            # build today's pre-market report + dashboard + archive
.venv/bin/python run.py --watch    # poll every 5 min (use --interval N), live feed + re-render
.venv/bin/python run.py --once     # one watcher cycle (what the cloud cron runs)
```
Open `docs/index.html` (it works straight from disk; the data is embedded).

Run it in the background:
```bash
nohup .venv/bin/python run.py --watch --interval 5 > logs/watcher.out 2>&1 & echo $! > watcher.pid
kill $(cat watcher.pid)   # stops cleanly (SIGTERM is handled)
```

## Layout
| Path | Purpose |
|---|---|
| `run.py` | Entry point: daily build, `--watch`, `--once` |
| `market_pulse/config.py` | Feeds, quote symbols, ticker/sector/impact keyword maps, theme rules |
| `market_pulse/collectors.py` | RSS feeds (requests + feedparser, with retry) and Yahoo Finance quotes (yfinance) |
| `market_pulse/processing.py` | Dedupe (exact + Jaccard near-duplicates), ticker/sector tags, VADER sentiment with finance lexicon tweaks, 0–10 impact score, theme clustering, sector heat, watchlist |
| `market_pulse/calendar.py` | Rule-based "what to watch" (FOMC 2026 dates, claims, EIA, NFP, CPI window) + forward-looking headlines |
| `market_pulse/report.py` | Renders `templates/dashboard.html` into `docs/`, writes the JSON, archives each day |
| `docs/` | GitHub Pages root: `index.html`, `data/latest.json`, `data/live.json`, `archive/` |
| `logs/market_pulse.log` | Rotating log (5 MB x 5) |
| `.github/workflows/market-pulse.yml` | Cloud cron every 15 min, commits `docs/` |

## How it works
- **Daily report**: built the first time a cycle runs on a new ET date (or whenever you run plain `python run.py`). It's archived to `docs/archive/YYYY-MM-DD.{html,json}`.
- **Live feed**: every cycle pulls all the feeds again. Items not seen before get scored and added to the top of `docs/data/live.json` (capped at 400). Items under 30 min old show a NEW badge. The page reloads itself every 5 min.
- **State** is just `docs/data/*.json`, so the cron job doesn't need a database. It carries state forward by committing.
- **Robustness**: per-feed retry with backoff, timeouts, one failing source doesn't stop the others, the watcher backs off after repeated failures, files are written atomically, and SIGTERM/SIGINT shut it down cleanly.

## Data sources (free, no keys)
CNBC (Top/Markets/Economy RSS), MarketWatch (Dow Jones RSS), Yahoo Finance headline RSS, BBC Business, Reuters and AP (through Google News RSS search, since they no longer publish public RSS), Federal Reserve press releases, and Yahoo Finance quotes through `yfinance` (index futures, SPY/QQQ/DIA/IWM, VIX, WTI, gold, DXY, 10Y, BTC, 11 SPDR sector ETFs + SMH). Nasdaq's RSS is set up but often times out. A failed source shows ✗ in "Data sources".

## Extending: X/Twitter
`collectors.collect_social()` is a stub. Return items with the same shape as the RSS items (`title, summary, link, source, feed, published`) and add them to `collect_news()`. Then they get deduped, tagged, scored and shown in the live feed. Sources to try: X API v2 recent search / trends (`GET /2/trends/by/woeid/{id}`, needs a bearer token stored as a GitHub Actions secret), cashtag searches for watchlist tickers, or StockTwits' public trending endpoint.

## Limitations
- Sentiment and impact are keyword heuristics. Treat them as rough sorting signals, not predictions.
- Quotes may be delayed. On weekends they show Friday's close.
- The economic calendar is rule-based. Check the exact dates on bls.gov and federalreserve.gov.
