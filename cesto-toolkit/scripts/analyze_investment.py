#!/usr/bin/env python3
"""
Full investment analysis — fetches all baskets, analytics, and token-level data
for the top N baskets. One script call replaces 8+ individual API calls.

Usage:
  python3 analyze_investment.py [--top=5] [--sort=24h|7d|30d|1y]

Options:
  --top=N    How many baskets to deep-dive into (default: 5)
  --sort=X   Primary sort metric for ranking (default: 24h)
"""

import json, sys, urllib.request
from datetime import datetime, timezone

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15


def fetch(path):
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return json.loads(resp.read().decode())
    except Exception:
        return None


def parse_args():
    top = 5
    sort_by = "24h"
    for arg in sys.argv[1:]:
        if arg.startswith("--top="):
            try:
                top = int(arg.split("=", 1)[1])
            except ValueError:
                pass
        elif arg.startswith("--sort="):
            sort_by = arg.split("=", 1)[1]
    return top, sort_by


def main():
    top_n, sort_by = parse_args()

    # Step 1: Fetch all baskets
    products = fetch("/products")
    if not products:
        print(json.dumps({"error": True, "message": "Failed to fetch baskets"}))
        sys.exit(1)

    # Step 2: Fetch cross-basket analytics
    analytics = fetch("/products/analytics")
    analytics_map = {}
    if analytics and isinstance(analytics, list):
        for item in analytics:
            bid = item.get("id") or item.get("basketId")
            if bid:
                analytics_map[bid] = item

    # Build basket list with performance
    baskets = []
    for p in products:
        # Skip prediction baskets (no meaningful performance data)
        if p.get("category") == "prediction":
            continue

        pid = p.get("id", "")
        a = analytics_map.get(pid, {})
        min_inv_raw = p.get("minimumInvestment", 0)

        perf = {
            "change24h": a.get("change24h") or p.get("tokenPerformance24h"),
            "return7d": a.get("return7d") or p.get("tokenPerformance7d"),
            "return30d": a.get("return30d") or p.get("tokenPerformance30d"),
            "return1y": a.get("return1y"),
            "annualizedReturn": a.get("annualizedReturn"),
        }

        baskets.append({
            "id": pid,
            "name": p.get("name", ""),
            "slug": p.get("slug", ""),
            "category": p.get("category", ""),
            "riskLevel": p.get("riskLevel", ""),
            "minInvestmentUSDC": min_inv_raw / 1_000_000 if min_inv_raw else 0,
            "performance": perf,
        })

    # Sort by chosen metric
    sort_key_map = {
        "24h": "change24h",
        "7d": "return7d",
        "30d": "return30d",
        "1y": "return1y",
    }
    key = sort_key_map.get(sort_by, "change24h")
    baskets.sort(key=lambda x: (x["performance"].get(key) is None, -(x["performance"].get(key) or 0)))

    # Step 3: Deep dive into top N baskets — fetch token-level data
    rankings = []
    for i, b in enumerate(baskets[:top_n]):
        basket_id = b["id"]
        tokens_data = fetch(f"/products/{basket_id}/analyze")

        tokens = []
        if tokens_data and isinstance(tokens_data, list):
            for t in tokens_data:
                tokens.append({
                    "symbol": t.get("symbol", ""),
                    "name": t.get("name", ""),
                    "allocationPercent": t.get("allocationPercent", t.get("percentage", 0)),
                    "currentPrice": t.get("currentPrice", t.get("price")),
                    "priceChange24h": t.get("priceChange24h", t.get("change24h")),
                    "priceChange7d": t.get("priceChange7d", t.get("change7d")),
                    "priceChange30d": t.get("priceChange30d", t.get("change30d")),
                })

        rankings.append({
            "rank": i + 1,
            "name": b["name"],
            "slug": b["slug"],
            "category": b["category"],
            "riskLevel": b["riskLevel"],
            "minInvestmentUSDC": b["minInvestmentUSDC"],
            "performance": b["performance"],
            "tokens": tokens,
        })

    result = {
        "summary": {
            "totalBaskets": len(baskets),
            "analyzedInDepth": len(rankings),
            "sortedBy": sort_by,
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
        },
        "rankings": rankings,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
