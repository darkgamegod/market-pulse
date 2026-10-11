"""Market session + freshness helpers (US equities, ET)."""
from datetime import datetime, date, time as dtime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
# NYSE full-day holidays 2026-2027 (Columbus Day is NOT an NYSE holiday)
HOLIDAYS = {"2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03",
            "2026-09-07", "2026-11-26", "2026-12-25", "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26",
            "2027-05-31", "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24"}


def now_et():
    return datetime.now(ET)


def is_trading_day(d: date):
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS


def session(ts=None):
    ts = (ts or now_et()).astimezone(ET)
    if not is_trading_day(ts.date()):
        return "closed"
    t = ts.time()
    if dtime(4) <= t < dtime(9, 30):
        return "pre-market"
    if dtime(9, 30) <= t < dtime(16):
        return "regular"
    if dtime(16) <= t < dtime(20):
        return "after-hours"
    return "closed"


def fmt(ts):
    if ts is None:
        return None
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    return ts.astimezone(ET).strftime("%b %d %I:%M %p ET")


def freshness(asof, kind="quote", now=None):
    """Return a badge dict: delayed (normal Yahoo lag), stale (older than threshold while market open),
    closed (market closed, last available value)."""
    now = now or now_et()
    if asof is None:
        return {"badge": "unknown", "label": "no timestamp"}
    if isinstance(asof, str):
        asof = datetime.fromisoformat(asof)
    age_min = (now - asof).total_seconds() / 60
    sess = session(now)
    if kind == "news":
        thr = 90
    elif kind == "futures":
        thr = 45  # futures trade ~23h/day Sun 6pm-Fri 5pm ET
    else:
        thr = 35
    if kind == "crypto":
        thr = 30
    if kind == "futures":
        wk = now.weekday()
        fut_open = not (wk == 5 or (wk == 4 and now.time() >= dtime(17)) or (wk == 6 and now.time() < dtime(18)))
        if not fut_open:
            return {"badge": "closed", "label": "futures closed · last trade", "age_min": round(age_min)}
    elif kind == "quote" and sess == "closed":
        return {"badge": "closed", "label": "market closed · last trade (incl. ext. hours)", "age_min": round(age_min)}
    if age_min > thr:
        return {"badge": "stale", "label": f"stale · {int(age_min)} min old", "age_min": round(age_min)}
    if kind == "news":
        return {"badge": "fresh", "label": "fresh", "age_min": round(age_min)}
    return {"badge": "delayed", "label": "~15 min delayed (Yahoo)", "age_min": round(age_min)}
