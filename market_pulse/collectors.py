"""Collectors: RSS news + Yahoo Finance quotes (no API keys)."""
import logging, time, calendar
from datetime import datetime, timezone
import feedparser, requests

from .config import FEEDS

log = logging.getLogger("collectors")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept": "application/rss+xml, application/xml, text/xml, */*", "Accept-Language": "en-US,en;q=0.9"}


BOT_UA = {"User-Agent": "Mozilla/5.0 (MarketPulse research bot; educational)"}


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
        hdr = BOT_UA if "yahoo.com" in url else UA  # Yahoo 429s browser-like UAs from scripts
        r = requests.get(url, headers=hdr, timeout=(6, 12))
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
            from .clock import fmt
            status[name] = {"ok": True, "count": len(got), "fetched_et": fmt(datetime.now(timezone.utc)),
                            "newest_et": fmt(max(i["published"] for i in got)), "newest": max(i["published"] for i in got)}
        except Exception as e:
            log.warning("feed %s failed: %s", name, e)
            from .clock import fmt
            status[name] = {"ok": False, "error": str(e)[:200], "fetched_et": fmt(datetime.now(timezone.utc))}
    return all_items, status


# Placeholder: X/Twitter trends. See README "Extending: X/Twitter".
def collect_social():
    return []
