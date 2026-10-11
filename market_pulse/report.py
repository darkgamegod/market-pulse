"""Outputs: docs/index.html (server-rendered + JS-enhanced), docs/data/*.json, docs/api/summary.json,
docs/report.txt, docs/archive/."""
import json, os
from html import escape as E
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
TEMPLATE = ROOT / "templates" / "dashboard.html"
DISCLAIMER = "Educational research only - not financial advice. Automated heuristics; may be wrong or delayed."


def _atomic(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp"); tmp.write_text(text, encoding="utf-8"); os.replace(tmp, path)


def write_json(path, obj, indent=None):
    _atomic(Path(path), json.dumps(obj, ensure_ascii=False, indent=indent))


def _pct(v):
    return "n/a" if v is None else f"{v:+.2f}%"


def _a(h):
    return f'<a href="{E(h.get("link") or "")}" rel="noopener">{E(h.get("title") or "")}</a> <span class="meta">— {E(h.get("source") or "")}</span>'


def _badge(f):
    f = f or {}
    return f'<span class="badge {E(f.get("badge", "unknown"))}">{E(f.get("label", ""))}</span>'


# ---------- server-side render (visible to non-JS fetchers; JS re-renders richer versions) ----------
def ssr(b):
    m, c, d, v = b["market"], b["catalysts"], b["daily"], b["validation"]
    out = {}
    q = [x for x in m.get("quotes", {}).values() if x["group"] != "Sectors"]
    out["snap"] = "".join(f'<div class="q"><div class="l">{E(x["label"])}</div><div class="p">{x["price"]:,}</div>'
                          f'<div>{_pct(x["pct"])}</div><div class="meta">as of {E(x.get("asof_et") or "")}</div>{_badge(x.get("fresh"))}</div>' for x in q)
    out["live"] = "".join(f'<div class="li"><div class="imp">{i["impact"]}</div><div>{_a(i)}<div class="meta">{E(", ".join(i["tickers"][:6]))} · {i["sentiment_label"]} · seen {E(i.get("seen_et") or "")}</div></div></div>'
                          for i in b["live"]["items"][:25])
    out["themes"] = "".join(f'<div class="theme"><h3>{E(t["name"])} <span class="meta">{t["count"]} items</span></h3><ul class="hl">' +
                            "".join(f"<li>{_a(h)}</li>" for h in t["headlines"][:3]) + "</ul></div>" for t in d["themes"])
    ec = c.get("econ", {}); er = c.get("earnings", {})
    out["econ"] = "".join(f'<div class="ev"><span class="d">{E(e["when_et"])}</span><span class="{e["importance"]}">{E(e["event"])}'
                          f'{(" · fcst " + E(e["forecast"])) if e.get("forecast") else ""}{(" · prev " + E(e["previous"])) if e.get("previous") else ""}</span></div>'
                          for e in ec.get("events", []) if e["importance"] != "low")
    out["earn"] = "".join(f'<div class="ev"><span class="d">{E(e["date"])}</span><span><b class="tk">{E(e["symbol"])}</b> {E(e["name"] or "")} · {E(e["time"])} · EPS est {E(e.get("eps_forecast") or "n/a")}</span></div>'
                          for e in er.get("events", [])[:30])
    mv = m.get("movers", {})
    row = lambda x: f'<tr><td class="tk">{E(x["symbol"])}</td><td>{_pct(x["gap_pct"])}</td><td>{x["rvol"]}</td><td>{E(x["sector"])}</td></tr>'
    out["gap"] = "".join(row(x) for x in mv.get("gappers", []))
    out["vol"] = "".join(row(x) for x in mv.get("volume_leaders", []))
    out["wl"] = "".join(f'<tr><td class="tk">{E(w["ticker"])}</td><td>{_pct(w.get("pct"))}</td><td>{w["mentions"]}</td><td>{w["sentiment"]}</td><td>{_a(w["why"]) if w.get("why") else ""}</td></tr>' for w in d["watchlist"])
    out["val"] = "".join(f'<div>{E(h["name"])}: <b>{E(h["status"])}</b> · n={h["n_directional"]} · hit-rate {h["hit_rate"]}% · corr {h["corr"]}</div>' for h in v["horizons"].values())
    out["src"] = "".join(f'<span class="pill">{"✓" if s.get("ok") else "✗"} {E(k)} ({s.get("count", "-")}) · {E(s.get("fetched_et") or "")}</span>' for k, s in b["sources"].items())
    return out


def summary(b):
    m, d, c = b["market"], b["daily"], b["catalysts"]
    return {
        "schema": "market-pulse/summary@1", "disclaimer": DISCLAIMER,
        "generated_et": b["generated_et"], "generated_at": b["generated_at"], "session": b["session"],
        "daily_report": {"date": d["date"], "generated_et": d["generated_et"]},
        "snapshot": [{k: q.get(k) for k in ("symbol", "label", "price", "pct", "asof_et")} | {"freshness": q.get("fresh", {}).get("badge")}
                     for q in m.get("quotes", {}).values()],
        "top_themes": [{"name": t["name"], "count": t["count"], "sentiment": t["sentiment"], "tickers": t["tickers"],
                        "top_headline": t["headlines"][0] if t["headlines"] else None} for t in d["themes"]],
        "breaking": [{k: i.get(k) for k in ("title", "link", "source", "impact", "tickers", "sentiment_label", "seen_et", "consumer")}
                     for i in b["live"]["items"][:20]],
        "high_impact": [{k: i.get(k) for k in ("title", "link", "impact", "tickers")} for i in b["live"]["items"][:100] if i["impact"] >= 7],
        "watchlist": [{k: w.get(k) for k in ("ticker", "pct", "mentions", "sentiment", "why")} for w in d["watchlist"]],
        "movers": {k: m.get("movers", {}).get(k) for k in ("mode", "basis", "fetched_et", "gappers", "volume_leaders")},
        "economic_calendar": {k: c.get("econ", {}).get(k) for k in ("source", "fallback", "fetched_et", "events")},
        "earnings": {k: c.get("earnings", {}).get(k) for k in ("source", "fetched_et", "events")},
        "sentiment_validation": b["validation"],
        "sources": b["sources"],
    }


def text_report(b):
    m, d, c, v = b["market"], b["daily"], b["catalysts"], b["validation"]
    L = [f"MARKET PULSE — pre-market research report for {d['date']}",
         f"Generated {b['generated_et']} (daily report built {d['generated_et']}; session: {b['session']})",
         DISCLAIMER, "=" * 78, "", "MARKET SNAPSHOT (source: Yahoo Finance, ~15 min delayed)"]
    for q in m.get("quotes", {}).values():
        if q["group"] != "Sectors":
            L.append(f"  {q['label']:<18}{q['price']:>12,.2f}  {_pct(q['pct']):>8}   as of {q.get('asof_et')}  [{q.get('fresh', {}).get('label', '')}]")
    L += ["", "SECTORS (ETF % change)"]
    for s in d["sectors"]:
        q = m.get("quotes", {}).get(s["etf"], {})
        L.append(f"  {s['etf']:<5}{s['name']:<22}{_pct(q.get('pct', s['pct'])):>8}   news {s['news']:>3}  sent {s['sentiment']:+.2f}")
    L += ["", "TOP THEMES"]
    for t in d["themes"]:
        L.append(f"  * {t['name']} ({t['count']} items, avg sentiment {t['sentiment']:+.2f}) tickers: {', '.join(t['tickers'])}")
        for h in t["headlines"][:3]:
            L.append(f"      - {h['title']} [{h['source']}] {h['link']}")
    mv = m.get("movers", {})
    if mv.get("ok"):
        L += ["", f"GAP LEADERS — {mv['mode']} ({mv['basis']}; as of {mv['fetched_et']})"]
        L += [f"  {x['symbol']:<6}{_pct(x['gap_pct']):>8}  RVOL {x['rvol']}  {x['sector']}" for x in mv["gappers"][:10]]
        L += ["", "RELATIVE VOLUME LEADERS"]
        L += [f"  {x['symbol']:<6}RVOL {x['rvol']:<6} gap {_pct(x['gap_pct'])}  {x['sector']}" for x in mv["volume_leaders"][:10]]
    ec = c.get("econ", {})
    L += ["", f"ECONOMIC CALENDAR — {ec.get('source')} (fetched {ec.get('fetched_et')})"]
    L += [f"  {e['when_et']:<20} [{e['importance'].upper():<6}] {e['event']}" + (f"  fcst {e['forecast']}" if e.get("forecast") else "") +
          (f"  prev {e['previous']}" if e.get("previous") else "") for e in ec.get("events", []) if e["importance"] != "low"]
    er = c.get("earnings", {})
    L += ["", f"EARNINGS (next 5 trading days) — {er.get('source')} (fetched {er.get('fetched_et')})"]
    L += [f"  {e['date']}  {e['symbol']:<6}{(e['name'] or '')[:30]:<32}{e['time']:<18} EPS est {e.get('eps_forecast') or 'n/a'}" for e in er.get("events", [])[:40]]
    L += ["", "WATCHLIST (most-mentioned / highest-impact tickers) — why it moved"]
    for w in d["watchlist"]:
        L.append(f"  {w['ticker']:<9}{_pct(w.get('pct')):>8}  mentions {w['mentions']:>2}  sent {w['sentiment']:+.2f}  -> {w['why']['title'] if w.get('why') else ''}")
    L += ["", "BREAKING / LIVE FEED (newest first)"]
    for i in b["live"]["items"][:25]:
        L.append(f"  [{i['impact']:>4}] {i['title']} ({', '.join(i['tickers'][:4])}) [{i['source']}, seen {i.get('seen_et')}] {i['link']}")
    L += ["", f"SENTIMENT VALIDATION — overall status: {v['status']} (need n>={v['min_sample']} directional samples per horizon)"]
    for h in v["horizons"].values():
        L.append(f"  {h['name']:<8} status {h['status']:<22} n={h['n_directional']:<5} hit-rate {h['hit_rate']}% (±{h['ci95']}) corr {h['corr']}")
    L += ["", "SOURCES"] + [f"  {'OK ' if s.get('ok') else 'ERR'} {k} ({s.get('count', '-')}) fetched {s.get('fetched_et')}" for k, s in b["sources"].items()]
    L += ["", DISCLAIMER, ""]
    return "\n".join(L)


def _html(b, archived=False):
    s = ssr(b)
    html = TEMPLATE.read_text(encoding="utf-8")
    for k, v in s.items():
        html = html.replace(f"<!--SSR:{k}-->", v)
    html = html.replace("<!--SSR:generated-->", E(b["generated_et"])).replace("<!--SSR:date-->", E(b["daily"]["date"]))
    data = dict(b, archived=archived)
    return html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))


def render(b):
    _atomic(DOCS / "index.html", _html(b))
    write_json(DOCS / "api" / "summary.json", summary(b), indent=1)
    _atomic(DOCS / "report.txt", text_report(b))
    _atomic(DOCS / ".nojekyll", "")


def archive(b):
    day = b["daily"]["date"]; ad = DOCS / "archive"
    write_json(ad / f"{day}.json", summary(b))
    _atomic(ad / f"{day}.txt", text_report(b))
    _atomic(ad / f"{day}.html", _html(b, archived=True).replace('href="archive/', 'href="').replace('href="data/', 'href="../data/')
            .replace('href="api/', 'href="../api/').replace('href="report.txt', 'href="' + day + '.txt'))
    days = sorted((p.stem for p in ad.glob("20*.html")), reverse=True)
    links = "\n".join(f'<li><a href="{d}.html">{d}</a> · <a href="{d}.txt">txt</a> · <a href="{d}.json">json</a></li>' for d in days)
    _atomic(ad / "index.html", f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Market Pulse archive</title><style>body{{font-family:system-ui;background:#0b1020;color:#e6e9f2;max-width:640px;margin:40px auto;padding:0 16px}}a{{color:#7aa2ff}}</style>
<h1>Market Pulse – Archive</h1><p><a href="../index.html">← Today</a></p><ul>{links}</ul><p>{DISCLAIMER}</p>""")
