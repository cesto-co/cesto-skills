#!/usr/bin/env python3
"""
Fetch all baskets with analytics in a single call.
Returns clean JSON with basket info + performance merged together.

Usage:
  python3 fetch_baskets.py [--sort=24h|7d|30d|1y]

Sort options:
  24h  - Sort by 24-hour change (default)
  7d   - Sort by 7-day return
  30d  - Sort by 30-day return
  1y   - Sort by 1-year return
"""

import json, os, sys, urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15


def fetch(path):
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return json.loads(resp.read().decode())
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        return None


def fetch_authed(path):
    """Fetch a path with bearer-token auth if a valid session exists. Returns None on any failure."""
    try:
        from _store import read_session, ACCESS_KEY
        session = read_session()
        if not session:
            return None
        token = session.get(ACCESS_KEY)
        if not token:
            return None
        req = urllib.request.Request(f"{BASE_URL}{path}")
        req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return json.loads(resp.read().decode())
    except Exception:
        return None


def safe_num(val, default=None):
    """Safely convert a value to float, handling strings and None."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def parse_sort_flag():
    for arg in sys.argv[1:]:
        if arg.startswith("--sort="):
            return arg.split("=", 1)[1]
    return "24h"


def main():
    sort_by = parse_sort_flag()

    all_products = fetch("/products")
    analytics = fetch("/products/analytics")

    if all_products is None:
        print(json.dumps({"error": True, "message": "Failed to fetch baskets"}))
        sys.exit(1)

    # Only show published+active baskets from the public list
    products = [p for p in all_products if p.get("isPublished") and p.get("isActive")]

    # Best-effort: include the caller's own drafts (tagged with isDraft=True)
    # This call is optional — browsing still works with no session.
    own_products = fetch_authed("/products?mine=true")
    if own_products and isinstance(own_products, list):
        published_ids = {p["id"] for p in products}
        for op in own_products:
            if op.get("id") not in published_ids:
                op["_isDraft"] = True
                products.append(op)

    # Analytics is a dict keyed by basket ID
    analytics_map = analytics if isinstance(analytics, dict) else {}

    results = []
    for p in products:
        pid = p.get("id", "")
        lv = p.get("latestVersion") or {}
        a = analytics_map.get(pid, {})

        min_inv_raw = safe_num(lv.get("minimumInvestment"), 0)
        min_inv_usdc = min_inv_raw / 1_000_000 if min_inv_raw else 0

        # Performance from analytics
        tp = a.get("tokenPerformance") or {}
        tp7 = a.get("tokenPerformance7d") or {}
        tp30 = a.get("tokenPerformance30d") or {}

        perf = {
            "change24h": safe_num(a.get("priceChange24h")),
            "return7d": safe_num(tp7.get("return", tp7.get("avgPercentChange"))),
            "return30d": safe_num(tp30.get("return", tp30.get("avgPercentChange"))),
            "return1y": safe_num(tp.get("netPnL", tp.get("annualizedReturn", tp.get("avgPercentChange")))),
            "annualizedReturn": safe_num(tp.get("annualizedReturn")),
        }

        row = {
            "id": pid,
            "slug": p.get("slug", ""),
            "name": p.get("name", ""),
            "category": p.get("category", ""),
            "riskLevel": lv.get("riskLevel", ""),
            "activePositions": lv.get("activePositionCount", 0),
            "minInvestmentUSDC": min_inv_usdc,
            "performance": perf,
        }
        if p.get("_isDraft"):
            row["isDraft"] = True
        results.append(row)

    # Sort by the chosen metric (nulls go last)
    sort_key_map = {
        "24h": "change24h",
        "7d": "return7d",
        "30d": "return30d",
        "1y": "return1y",
    }
    key = sort_key_map.get(sort_by, "change24h")
    results.sort(key=lambda x: (x["performance"].get(key) is None, -(x["performance"].get(key) or 0)))

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
