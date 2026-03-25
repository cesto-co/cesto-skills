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

import json, sys, urllib.request

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


def parse_sort_flag():
    for arg in sys.argv[1:]:
        if arg.startswith("--sort="):
            return arg.split("=", 1)[1]
    return "24h"


def main():
    sort_by = parse_sort_flag()

    products = fetch("/products")
    analytics = fetch("/products/analytics")

    if products is None:
        print(json.dumps({"error": True, "message": "Failed to fetch baskets"}))
        sys.exit(1)

    # Build analytics lookup by basket ID
    analytics_map = {}
    if analytics and isinstance(analytics, list):
        for item in analytics:
            bid = item.get("id") or item.get("basketId")
            if bid:
                analytics_map[bid] = item

    results = []
    for p in products:
        pid = p.get("id", "")
        a = analytics_map.get(pid, {})

        min_inv_raw = p.get("minimumInvestment", 0)
        min_inv_usdc = min_inv_raw / 1_000_000 if min_inv_raw else 0

        perf = {
            "change24h": a.get("change24h") or p.get("tokenPerformance24h"),
            "return7d": a.get("return7d") or p.get("tokenPerformance7d"),
            "return30d": a.get("return30d") or p.get("tokenPerformance30d"),
            "return1y": a.get("return1y"),
            "annualizedReturn": a.get("annualizedReturn"),
        }

        results.append({
            "id": pid,
            "slug": p.get("slug", ""),
            "name": p.get("name", ""),
            "category": p.get("category", ""),
            "riskLevel": p.get("riskLevel", ""),
            "activePositions": p.get("activePositions", 0),
            "minInvestmentUSDC": min_inv_usdc,
            "tokenCount": len(p.get("definition", {}).get("nodes", [])) if isinstance(p.get("definition"), dict) else 0,
            "performance": perf,
        })

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
    main()
