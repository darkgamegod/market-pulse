"""Writes JSON data + static dashboard (docs/ for GitHub Pages)."""
import json, os, shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
TEMPLATE = ROOT / "templates" / "dashboard.html"
ET = ZoneInfo("America/New_York")


def _atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def render(daily: dict, live: dict):
    """Render docs/index.html with daily report + live feed embedded (works from file:// too)."""
    payload = json.dumps({"daily": daily, "live": live}, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
    _atomic_write(DOCS / "index.html", html)
    _atomic_write(DOCS / "data" / "latest.json", json.dumps(daily, indent=1, ensure_ascii=False))
    _atomic_write(DOCS / "data" / "live.json", json.dumps(live, indent=1, ensure_ascii=False))
    _atomic_write(DOCS / ".nojekyll", "")


def archive(daily: dict):
    day = daily["date"]
    ad = DOCS / "archive"
    _atomic_write(ad / f"{day}.json", json.dumps(daily, ensure_ascii=False))
    payload = json.dumps({"daily": daily, "live": {"items": [], "updated_et": daily["generated_et"], "archived": True}},
                         ensure_ascii=False).replace("</", "<\\/")
    _atomic_write(ad / f"{day}.html", TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
                  .replace('href="archive/', 'href="'))
    days = sorted((p.stem for p in ad.glob("20*.json")), reverse=True)
    links = "\n".join(f'<li><a href="{d}.html">{d}</a> · <a href="{d}.json">json</a></li>' for d in days)
    _atomic_write(ad / "index.html", f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Market Pulse archive</title><style>body{{font-family:system-ui;background:#0b1020;color:#e6e9f2;max-width:640px;margin:40px auto;padding:0 16px}}a{{color:#7aa2ff}}</style>
<h1>Market Pulse – Archive</h1><p><a href="../index.html">← Today</a></p><ul>{links}</ul>""")


def now_et():
    return datetime.now(ET)
