#!/usr/bin/env python3
"""
Deep dive into a single basket — fetches detail, token analysis, and graph data
in one call.

Usage:
  python3 fetch_basket_detail.py <slug-or-name> [--include=detail,tokens,graph]

Arguments:
  slug-or-name  Basket slug (e.g., "defense-mode") or partial name for fuzzy match
  --include     Comma-separated sections to fetch. Default: detail,tokens,graph (all)
                Options: detail, tokens, graph

Examples:
  python3 fetch_basket_detail.py defense-mode
  python3 fetch_basket_detail.py "defense" --include=tokens
  python3 fetch_basket_detail.py made-in-america --include=detail,graph
"""

import json, sys, urllib.request

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15


def fetch(path):
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return json.loads(resp.read().decode())
    except Exception:
        return None


def find_basket(query):
    """Find basket by slug or fuzzy name match."""
    products = fetch("/products")
    if not products:
        return None, None

    query_lower = query.lower().strip()

    # Try exact slug match first
    for p in products:
        if p.get("slug", "").lower() == query_lower:
            return p, products

    # Try partial name match
    for p in products:
        if query_lower in p.get("name", "").lower():
            return p, products

    # Try partial slug match
    for p in products:
        if query_lower in p.get("slug", "").lower():
            return p, products

    return None, products


def parse_args():
    slug_or_name = None
    include = {"detail", "tokens", "graph"}

    for arg in sys.argv[1:]:
        if arg.startswith("--include="):
            include = set(arg.split("=", 1)[1].split(","))
        elif not slug_or_name:
            slug_or_name = arg

    return slug_or_name, include


def main():
    slug_or_name, include = parse_args()

    if not slug_or_name:
        print(json.dumps({"error": True, "message": "Please provide a basket slug or name"}))
        sys.exit(1)

    basket_data, all_products = find_basket(slug_or_name)

    if not basket_data:
        # Return available baskets so the agent can suggest alternatives
        available = [{"name": p.get("name"), "slug": p.get("slug")} for p in (all_products or [])]
        print(json.dumps({
            "error": True,
            "message": f"No basket found matching '{slug_or_name}'",
            "availableBaskets": available
        }))
        sys.exit(1)

    slug = basket_data.get("slug", "")
    basket_id = basket_data.get("id", "")
    result = {}

    # Fetch detail
    if "detail" in include:
        detail = fetch(f"/products/{slug}")
        if detail:
            min_inv_raw = detail.get("minimumInvestment", 0)
            definition = detail.get("definition", {}) or {}
            nodes = definition.get("nodes", []) if isinstance(definition, dict) else []

            allocations = []
            for node in nodes:
                allocations.append({
                    "token": node.get("label", node.get("token", "")),
                    "nodeLabel": node.get("label", ""),
                    "percentage": node.get("percentage", node.get("weight", 0)),
                })

            result["basket"] = {
                "id": basket_id,
                "name": detail.get("name", ""),
                "slug": slug,
                "category": detail.get("category", ""),
                "description": detail.get("description", ""),
                "riskLevel": detail.get("riskLevel", ""),
                "minInvestmentUSDC": min_inv_raw / 1_000_000 if min_inv_raw else 0,
                "strategy": definition.get("about", "") if isinstance(definition, dict) else "",
                "allocations": allocations,
                "performance": {
                    "return1y": detail.get("tokenPerformance1y"),
                    "return7d": detail.get("tokenPerformance7d"),
                    "return30d": detail.get("tokenPerformance30d"),
                    "annualizedReturn": detail.get("annualizedReturn"),
                },
            }
        else:
            result["basket"] = None

    # Fetch token analysis
    if "tokens" in include and basket_id:
        tokens_data = fetch(f"/products/{basket_id}/analyze")
        if tokens_data and isinstance(tokens_data, list):
            result["tokens"] = []
            for t in tokens_data:
                result["tokens"].append({
                    "symbol": t.get("symbol", ""),
                    "name": t.get("name", ""),
                    "allocationPercent": t.get("allocationPercent", t.get("percentage", 0)),
                    "currentPrice": t.get("currentPrice", t.get("price")),
                    "priceChange24h": t.get("priceChange24h", t.get("change24h")),
                    "priceChange7d": t.get("priceChange7d", t.get("change7d")),
                    "priceChange30d": t.get("priceChange30d", t.get("change30d")),
                    "priceChange1y": t.get("priceChange1y", t.get("change1y")),
                    "marketCap": t.get("marketCap"),
                    "volume24h": t.get("volume24h"),
                })
        else:
            result["tokens"] = None

    # Fetch graph
    if "graph" in include and basket_id:
        graph_data = fetch(f"/products/{basket_id}/graph")
        if graph_data and isinstance(graph_data, dict):
            series = graph_data.get("timeSeries", [])
            if series:
                values = [(s.get("timestamp", ""), s.get("portfolioValue", 0)) for s in series if s.get("portfolioValue") is not None]
                sp500 = [s.get("sp500Value", 0) for s in series if s.get("sp500Value") is not None]

                start_val = values[0][1] if values else 0
                end_val = values[-1][1] if values else 0
                sp_start = sp500[0] if sp500 else 0
                sp_end = sp500[-1] if sp500 else 0

                best = max(values, key=lambda x: x[1]) if values else ("", 0)
                worst = min(values, key=lambda x: x[1]) if values else ("", 0)

                has_liquidations = any(s.get("isLiquidated", False) for s in series)

                result["graph"] = {
                    "startValue": start_val,
                    "endValue": end_val,
                    "totalReturn": round((end_val - start_val) / start_val * 100, 2) if start_val else 0,
                    "sp500Return": round((sp_end - sp_start) / sp_start * 100, 2) if sp_start else 0,
                    "bestDay": {"date": best[0], "value": best[1]},
                    "worstDay": {"date": worst[0], "value": worst[1]},
                    "hasLiquidations": has_liquidations,
                    "dataPoints": len(series),
                }
            else:
                result["graph"] = None
        else:
            result["graph"] = None

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
