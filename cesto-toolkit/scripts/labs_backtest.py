#!/usr/bin/env python3
"""
Run a 1-year backtest for a community Labs post.

Public endpoint — works with no session. Prediction legs are excluded from
the backtest; token legs without price history are skipped. If the post has
no backtestable tokens, the backtest is null (not an error).

Usage:
  python3 labs_backtest.py <slug> [--refresh]

Output (with data):
  {"backtest": {timeRange, metrics: {...}, startValue, endValue,
   portfolio: [...], sp500: [...], warnings: [...]}}
Output (none):
  {"backtest": null, "note": "No token backtest available (prediction-only
   or insufficient price history)."}
"""

import json, sys, urllib.request

sys.dont_write_bytecode = True

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 30

NO_BACKTEST_NOTE = "No token backtest available (prediction-only or insufficient price history)."


def safe_num(val, default=None):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def main():
    slug = None
    refresh = False
    for arg in sys.argv[1:]:
        if arg == "--refresh":
            refresh = True
        elif not slug:
            slug = arg

    if not slug:
        print(json.dumps({"error": True, "message": "Please provide a Labs post slug"}))
        sys.exit(1)

    path = f"/labs/posts/{slug}/backtest"
    if refresh:
        path += "?refresh=true"

    try:
        req = urllib.request.Request(f"{BASE_URL}{path}")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        raw = resp.read().decode()
        data = json.loads(raw, strict=False) if raw.strip() else None
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": True, "status": e.code, "message": e.read().decode()}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)

    # Backtest can legitimately be null (prediction-only / no price history).
    if data is None or (isinstance(data, dict) and not data.get("metrics") and not data.get("series")):
        print(json.dumps({"backtest": None, "note": NO_BACKTEST_NOTE}))
        return

    metrics = data.get("metrics") or {}
    series = data.get("series") or []
    benchmark = data.get("benchmark") or []

    portfolio = [{"t": s.get("t"), "v": safe_num(s.get("v"))} for s in series]
    sp500 = [{"t": s.get("t"), "v": safe_num(s.get("v"))} for s in benchmark]

    out = {
        "backtest": {
            "slug": data.get("slug", slug),
            "timeRange": data.get("timeRange"),
            "startDate": data.get("startDate"),
            "endDate": data.get("endDate"),
            "startValue": safe_num(data.get("initialValue")),
            "endValue": safe_num(data.get("finalValue")),
            "metrics": {
                "totalReturnPct": safe_num(metrics.get("totalReturnPct")),
                "cagr": safe_num(metrics.get("cagr")),
                "volatility": safe_num(metrics.get("volatility")),
                "maxDrawdown": safe_num(metrics.get("maxDrawdown")),
                "sharpe": safe_num(metrics.get("sharpe")),
            },
            "portfolio": portfolio,
            "sp500": sp500,
            "dataPoints": len(portfolio),
            "warnings": data.get("warnings", []),
        }
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
