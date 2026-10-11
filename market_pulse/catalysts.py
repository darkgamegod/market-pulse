"""Real catalysts: economic calendar (FairEconomy/ForexFactory weekly JSON) + earnings (Nasdaq calendar API).
Falls back to the rule-based schedule (labelled) when a source is unavailable."""
import logging
from datetime import datetime, timedelta
import requests

from .clock import now_et, is_trading_day, fmt
from .calendar import upcoming as rule_based

log = logging.getLogger("catalysts")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
      "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"}
FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
NASDAQ_URL = "https://api.nasdaq.com/api/calendar/earnings?date={d}"


def econ_calendar(items):
    now = now_et()
    try:
        r = requests.get(FF_URL, headers=UA, timeout=15); r.raise_for_status()
        ev = []
        for x in r.json():
            if x.get("country") != "USD":
                continue
            ts = datetime.fromisoformat(x["date"])
            if ts < now - timedelta(hours=12):
                continue
            imp = {"High": "high", "Medium": "medium"}.get(x.get("impact"), "low")
            if x.get("impact") == "Holiday":
                imp = "medium"
            ev.append({"when_et": fmt(ts), "date": ts.date().isoformat(), "event": x["title"], "importance": imp,
                       "forecast": x.get("forecast") or "", "previous": x.get("previous") or ""})
        if not ev:
            raise RuntimeError("no USD events")
        return {"source": "FairEconomy / ForexFactory weekly calendar (nfs.faireconomy.media)", "fallback": False,
                "fetched_et": fmt(now), "fetched_at": now.isoformat(), "events": ev}
    except Exception as e:
        log.warning("econ calendar failed, using rule-based fallback: %s", e)
        rb = rule_based(now.date(), items)
        return {"source": "RULE-BASED FALLBACK (approximate; live calendar unavailable)", "fallback": True,
                "fetched_et": fmt(now), "fetched_at": now.isoformat(),
                "events": [dict(e, when_et=e["date"], forecast="", previous="") for e in rb["events"]], "error": str(e)[:150]}


def yf_fallback(symbols, errs):
    """Slow per-ticker fallback via yfinance .calendar (limited to a short list)."""
    import yfinance as yf
    now = now_et(); out = []
    for s in symbols[:40]:
        try:
            cal = yf.Ticker(s).calendar or {}
            ds = cal.get("Earnings Date") or []
            for d in ds[:1]:
                if now.date() <= d <= now.date() + timedelta(days=8):
                    out.append({"date": d.isoformat(), "symbol": s, "name": s, "time": "time n/a",
                                "eps_forecast": str(cal.get("Earnings Average") or "n/a"), "last_year_eps": None, "mcap": 0})
        except Exception:
            pass
    out.sort(key=lambda x: x["date"])
    return {"source": "FALLBACK: yfinance per-ticker calendar (Nasdaq API unavailable; limited to top names)",
            "fetched_et": fmt(now), "fetched_at": now.isoformat(), "ok": bool(out), "fallback": True, "errors": errs, "events": out}


def earnings_calendar(universe: set, days=5, fallback_symbols=None):
    now = now_et(); d = now.date(); out = []; got_any = False; errs = []
    checked = 0
    while checked < days:
        if is_trading_day(d):
            checked += 1
            try:
                r = requests.get(NASDAQ_URL.format(d=d.isoformat()), headers=UA, timeout=(5, 10)); r.raise_for_status()
                rows = ((r.json().get("data") or {}).get("rows")) or []
                got_any = True
                for row in rows:
                    sym = (row.get("symbol") or "").replace(".", "-")
                    if sym not in universe:
                        continue
                    try:
                        mcap = int(row.get("marketCap", "0").replace("$", "").replace(",", "") or 0)
                    except ValueError:
                        mcap = 0
                    t = row.get("time", "")
                    out.append({"date": d.isoformat(), "symbol": sym, "name": row.get("name"),
                                "time": "BMO (pre-market)" if "pre" in t else "AMC (after close)" if "after" in t else "time n/a",
                                "eps_forecast": row.get("epsForecast"), "last_year_eps": row.get("lastYearEPS"), "mcap": mcap})
            except Exception as e:
                errs.append(f"{d}: {e}"[:120])
        d += timedelta(days=1)
    out.sort(key=lambda x: (x["date"], -x["mcap"]))
    if not got_any:
        return yf_fallback(fallback_symbols or [], errs)
    return {"source": "Nasdaq earnings calendar API (api.nasdaq.com), filtered to S&P 500 + watchlist",
            "fetched_et": fmt(now), "fetched_at": now.isoformat(), "ok": got_any, "errors": errs, "events": out}
