"""Rule-based 'what to watch' calendar (no API key). Approximate; verify against official calendars."""
import re
from datetime import date, timedelta

FOMC_2026 = [("2026-01-27", "2026-01-28"), ("2026-03-17", "2026-03-18"), ("2026-04-28", "2026-04-29"),
             ("2026-06-16", "2026-06-17"), ("2026-07-28", "2026-07-29"), ("2026-09-15", "2026-09-16"),
             ("2026-10-27", "2026-10-28"), ("2026-12-08", "2026-12-09")]


def upcoming(today: date, items, days=7):
    ev = []
    end = today + timedelta(days=days)
    for s, e in FOMC_2026:
        d = date.fromisoformat(e)
        if today <= d <= end + timedelta(days=14):
            ev.append({"date": e, "event": f"FOMC decision (meeting {s}–{e}), 2:00pm ET + Powell presser", "importance": "high"})
    d = today
    while d <= end:
        if d.weekday() == 3:
            ev.append({"date": d.isoformat(), "event": "Weekly initial jobless claims, 8:30am ET", "importance": "medium"})
        if d.weekday() == 4 and d.day <= 7:
            ev.append({"date": d.isoformat(), "event": "Monthly jobs report (NFP) – typical first-Friday release, 8:30am ET", "importance": "high"})
        if d.weekday() == 2:
            ev.append({"date": d.isoformat(), "event": "EIA crude oil inventories, 10:30am ET", "importance": "medium"})
        if 10 <= d.day <= 15 and d.weekday() < 5 and not any("CPI" in x["event"] for x in ev):
            ev.append({"date": d.isoformat(), "event": "CPI inflation report window (mid-month, check BLS schedule)", "importance": "high"})
        d += timedelta(days=1)
    # headlines that look forward-looking
    pat = re.compile(r"week ahead|what to watch|this week|earnings (?:due|preview|on deck)|ahead of|will report|set to report|later today|tomorrow", re.I)
    hints = [{"title": i["title"], "link": i["link"], "source": i["source"]} for i in items if pat.search(i["title"])][:8]
    ev.sort(key=lambda x: x["date"])
    return {"events": ev, "headline_hints": hints,
            "note": "Rule-based schedule; confirm exact dates on bls.gov, federalreserve.gov and earnings calendars."}
