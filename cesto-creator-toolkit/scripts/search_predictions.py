#!/usr/bin/env python3
"""
Search or browse prediction events and their markets.

Usage:
  python3 search_predictions.py --query "bitcoin"
  python3 search_predictions.py --category crypto --filter trending
  python3 search_predictions.py --category sports --filter live --provider polymarket

Output:
  {"events": [{"eventId": "...", "title": "...", "category": "...", "markets": [...]}]}
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request, urllib.parse

BACKEND_URL = "https://dev.backend.cesto.co"


def _get(url, timeout=15):
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": True, "status": e.code, "message": e.read().decode()}
    except Exception as e:
        return {"error": True, "message": str(e)}


def _format_market(m):
    """Format a market for clean output, converting micro-USD prices."""
    pricing = m.get("pricing", {})
    buy_yes = pricing.get("buyYesPriceUsd")
    buy_no = pricing.get("buyNoPriceUsd")
    return {
        "marketId": m.get("marketId", ""),
        "title": m.get("title", ""),
        "status": m.get("status", ""),
        "buyYesPrice": round(buy_yes / 1_000_000, 4) if buy_yes is not None else None,
        "buyNoPrice": round(buy_no / 1_000_000, 4) if buy_no is not None else None,
        "volume": pricing.get("volume", 0),
        "closeTime": m.get("closeTime"),
        "outcomes": m.get("outcomes", []),
        "outcomePrices": m.get("outcomePrices", []),
        "marketOptions": m.get("marketOptions", []),
    }


def _format_event(e):
    """Format an event for clean output."""
    meta = e.get("metadata", {})
    markets = [_format_market(m) for m in e.get("markets", [])]
    return {
        "eventId": e.get("eventId", ""),
        "title": meta.get("title", ""),
        "subtitle": meta.get("subtitle", ""),
        "category": e.get("category", ""),
        "subcategory": e.get("subcategory", ""),
        "isActive": e.get("isActive", False),
        "isLive": e.get("isLive", False),
        "closeTime": meta.get("closeTime", ""),
        "imageUrl": meta.get("imageUrl", ""),
        "volumeUsd": e.get("volumeUsd", "0"),
        "markets": markets,
    }


def main():
    args = sys.argv[1:]
    params = {}
    i = 0
    while i < len(args):
        if args[i] == "--query" and i + 1 < len(args):
            params["query"] = args[i + 1]
            i += 2
        elif args[i] == "--category" and i + 1 < len(args):
            params["category"] = args[i + 1]
            i += 2
        elif args[i] == "--filter" and i + 1 < len(args):
            params["filter"] = args[i + 1]
            i += 2
        elif args[i] == "--provider" and i + 1 < len(args):
            params["provider"] = args[i + 1]
            i += 2
        elif args[i] == "--limit" and i + 1 < len(args):
            params["limit"] = args[i + 1]
            i += 2
        else:
            i += 1

    if "query" in params:
        # Search endpoint
        query_params = {"query": params["query"], "includeMarkets": "true"}
        if "provider" in params:
            query_params["provider"] = params["provider"]
        if "limit" in params:
            query_params["limit"] = params["limit"]
        else:
            query_params["limit"] = "10"
        url = f"{BACKEND_URL}/prediction/events/search?{urllib.parse.urlencode(query_params)}"
    else:
        # Browse endpoint
        query_params = {"includeMarkets": "true"}
        if "category" in params:
            query_params["category"] = params["category"]
        if "filter" in params:
            query_params["filter"] = params["filter"]
        if "provider" in params:
            query_params["provider"] = params["provider"]
        url = f"{BACKEND_URL}/prediction/events?{urllib.parse.urlencode(query_params)}"

    data = _get(url)

    if isinstance(data, dict) and data.get("error"):
        print(json.dumps(data))
        sys.exit(1)

    events_raw = data.get("data", []) if isinstance(data, dict) else []
    events = [_format_event(e) for e in events_raw]

    print(json.dumps({"events": events, "total": len(events)}))


if __name__ == "__main__":
    main()
