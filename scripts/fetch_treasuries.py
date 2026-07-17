#!/usr/bin/env python3
"""
Daily fetch of Treasury yields from Yahoo Finance.
Writes data/treasuries.json for the markets dashboard.
"""
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TICKERS = [
    {"symbol": "^IRX", "name": "3-Month T-Bill",  "why": "Closely tracks Fed policy and cash yields."},
    {"symbol": "^FVX", "name": "5-Year Treasury", "why": "Sensitive to medium-term rate expectations."},
    {"symbol": "^TNX", "name": "10-Year Treasury","why": "Most important benchmark for mortgages, valuations, and the economy."},
    {"symbol": "^TYX", "name": "30-Year Treasury","why": "Long-term inflation and government debt expectations."},
]
LOOKBACK_DAYS = 180
UA = "Mozilla/5.0 (compatible; treasuries-dashboard/1.0)"


def fetch(symbol: str) -> dict:
    end = int(time.time())
    start = end - 60 * 60 * 24 * LOOKBACK_DAYS
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?period1={start}&period2={end}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read())
    result = d["chart"]["result"][0]
    meta = result["meta"]
    ts = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    history = [
        {"t": ts[i], "y": round(closes[i], 3)}
        for i in range(len(ts)) if closes[i] is not None
    ]
    last = history[-1]["y"] if history else None
    prev = history[-2]["y"] if len(history) >= 2 else None
    change_bp = round((last - prev) * 100, 1) if (last is not None and prev is not None) else None
    # 52-week high/low from what we have (~6 months)
    ys = [h["y"] for h in history]
    return {
        "symbol": symbol,
        "last": last,
        "prev_close": prev,
        "change_bp": change_bp,
        "range_low":  min(ys) if ys else None,
        "range_high": max(ys) if ys else None,
        "history": history,
        "regular_market_time": meta.get("regularMarketTime"),
        "currency": meta.get("currency"),
        "exchange": meta.get("exchangeName"),
    }


def main():
    root = Path(__file__).resolve().parent.parent
    out_path = root / "data" / "treasuries.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Yahoo Finance (query1.finance.yahoo.com)",
        "instruments": [],
    }
    for cfg in TICKERS:
        try:
            data = fetch(cfg["symbol"])
        except Exception as e:
            print(f"WARN: fetch {cfg['symbol']} failed: {e}")
            data = {"symbol": cfg["symbol"], "error": str(e)}
        entry = {**cfg, **data}
        payload["instruments"].append(entry)
        print(f"{cfg['symbol']:6s} last={data.get('last')} change_bp={data.get('change_bp')}")
        time.sleep(0.6)  # be polite

    with out_path.open("w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
