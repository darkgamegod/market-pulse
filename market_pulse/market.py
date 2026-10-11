"""Yahoo Finance market data with freshness: quotes, pre-market gap/volume leaders, universe prices."""
import json, logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

from .config import QUOTES, SECTOR_ETFS
from .clock import now_et, session, freshness, fmt, ET

log = logging.getLogger("market")
ROOT = Path(__file__).resolve().parent.parent
FUT = {"ES=F", "NQ=F", "YM=F", "RTY=F", "CL=F", "GC=F", "DX-Y.NYB", "^TNX", "^VIX"}
CRYPTO = {"BTC-USD"}
YAHOO = "Yahoo Finance via yfinance (quotes ~15 min delayed for many venues)"


def _yf():
    import yfinance as yf
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    return yf


def universe():
    d = json.loads((ROOT / "data" / "sp500.json").read_text())
    return [{"ticker": c["ticker"].replace(".", "-"), "name": c["name"], "sector": c["sector"]} for c in d["constituents"]]


def _dl(symbols, **kw):
    yf = _yf()
    for attempt in range(2):
        try:
            df = yf.download(symbols, group_by="ticker", progress=False, threads=True, auto_adjust=False, **kw)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            log.warning("yfinance download attempt %d failed: %s", attempt + 1, e)
    return pd.DataFrame()


def _col(df, sym, field):
    try:
        return df[sym][field].dropna() if isinstance(df.columns, pd.MultiIndex) else df[field].dropna()
    except KeyError:
        return pd.Series(dtype=float)


def collect_quotes():
    """Snapshot quotes: last price from 5m extended-hours bars (timestamped), prev close from daily."""
    syms = list(QUOTES) + list(SECTOR_ETFS)
    daily = _dl(syms, period="10d", interval="1d")
    intra = _dl(syms, period="5d", interval="5m", prepost=True)
    now = now_et(); out = {}; failed = []
    for s in syms:
        try:
            dc = _col(daily, s, "Close")
            ic = _col(intra, s, "Close")
            if len(dc) < 2:
                raise ValueError("no daily data")
            if len(ic):
                last_ts = ic.index[-1].to_pydatetime().astimezone(ET); last = float(ic.iloc[-1])
            else:
                last_ts = datetime.combine(dc.index[-1].date(), datetime.min.time(), ET).replace(hour=16); last = float(dc.iloc[-1])
            # previous close = last completed daily bar strictly before the last trade's date
            prior = dc[[d.date() < last_ts.date() for d in dc.index]]
            prev = float(prior.iloc[-1]) if len(prior) else float(dc.iloc[-2])
            label, group = QUOTES.get(s, (SECTOR_ETFS.get(s, s), "Sectors"))
            out[s] = {"symbol": s, "label": label, "group": group, "price": round(last, 2),
                      "change": round(last - prev, 2), "pct": round((last / prev - 1) * 100, 2),
                      "asof": last_ts.isoformat(), "asof_et": fmt(last_ts), "source": "Yahoo Finance",
                      "fresh": freshness(last_ts, "crypto" if s in CRYPTO else "futures" if s in FUT else "quote", now)}
        except Exception as e:
            failed.append(s)
    return out, {"yfinance": {"ok": bool(out), "count": len(out), "failed": failed}}


def movers(top_intraday=150, n=15):
    """Gap & volume leaders across the S&P 500. During pre-market: live pre-market gap + pre-market volume
    as % of 20-day avg daily volume (RVOL proxy). Otherwise: last session's opening gap + full-day RVOL."""
    now = now_et(); sess = session(now)
    uni = universe(); syms = [u["ticker"] for u in uni]; meta = {u["ticker"]: u for u in uni}
    daily = _dl(syms, period="1mo", interval="1d")
    if daily.empty:
        return {"ok": False, "error": "daily download failed", "fetched_et": fmt(now)}, {}
    rows, prices = [], {}
    for s in syms:
        c, o, v = _col(daily, s, "Close"), _col(daily, s, "Open"), _col(daily, s, "Volume")
        if len(c) < 5 or len(v) < 5:
            continue
        adv = float(v.iloc[-21:-1].mean()) if len(v) > 21 else float(v.iloc[:-1].mean())
        prices[s] = {"price": round(float(c.iloc[-1]), 2), "pct": round((c.iloc[-1] / c.iloc[-2] - 1) * 100, 2),
                     "asof": c.index[-1].date().isoformat()}
        rows.append({"symbol": s, "name": meta[s]["name"], "sector": meta[s]["sector"],
                     "prev_close": float(c.iloc[-2]), "open": float(o.iloc[-1]) if len(o) else None,
                     "close": float(c.iloc[-1]), "vol": float(v.iloc[-1]), "adv": adv,
                     "dollar_vol": adv * float(c.iloc[-1]), "date": c.index[-1].date().isoformat()})
    mode = "pre-market (live)" if sess == "pre-market" else "last session (market not in pre-market)"
    if sess == "pre-market":
        liquid = sorted(rows, key=lambda r: r["dollar_vol"], reverse=True)[:top_intraday]
        intra = _dl([r["symbol"] for r in liquid], period="1d", interval="5m", prepost=True)
        res = []
        for r in liquid:
            ic, iv = _col(intra, r["symbol"], "Close"), _col(intra, r["symbol"], "Volume")
            today = [t for t in ic.index if t.astimezone(ET).date() == now.date()]
            if not today:
                continue
            last = float(ic.loc[today[-1]]); pm_vol = float(iv.loc[today].sum())
            prev = r["close"] if r["date"] < now.date().isoformat() else r["prev_close"]
            res.append({"symbol": r["symbol"], "name": r["name"], "sector": r["sector"], "price": round(last, 2),
                        "gap_pct": round((last / prev - 1) * 100, 2), "volume": int(pm_vol),
                        "rvol": round(pm_vol / r["adv"], 3) if r["adv"] else None, "asof_et": fmt(today[-1])})
        basis = "pre-market price vs prior close; RVOL = pre-market volume / 20-day avg daily volume"
    else:
        res = [{"symbol": r["symbol"], "name": r["name"], "sector": r["sector"], "price": round(r["close"], 2),
                "gap_pct": round((r["open"] / r["prev_close"] - 1) * 100, 2) if r["open"] else 0,
                "day_pct": round((r["close"] / r["prev_close"] - 1) * 100, 2), "volume": int(r["vol"]),
                "rvol": round(r["vol"] / r["adv"], 2) if r["adv"] else None, "asof_et": r["date"] + " close"}
               for r in rows]
        basis = "opening gap (open vs prior close) of the last session; RVOL = session volume / 20-day avg"
    gappers = sorted(res, key=lambda x: abs(x["gap_pct"]), reverse=True)[:n]
    volume = sorted([x for x in res if x["rvol"] is not None], key=lambda x: x["rvol"], reverse=True)[:n]
    return {"ok": True, "mode": mode, "basis": basis, "universe": f"S&P 500 ({len(rows)} names)" +
            (f", intraday scan of top {top_intraday} by $ volume" if sess == "pre-market" else ""),
            "source": YAHOO, "fetched_et": fmt(now), "fetched_at": now.isoformat(), "session": sess,
            "gappers": gappers, "volume_leaders": volume}, prices


def bars(symbols, period="5d"):
    """5-minute bars incl. extended hours for validation lookups."""
    return _dl(list(symbols), period=period, interval="5m", prepost=True)
