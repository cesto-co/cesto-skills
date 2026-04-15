#!/usr/bin/env python3
"""
Get detailed info for a single prediction event or market.

Usage:
  python3 get_prediction_detail.py --event POLY-36173
  python3 get_prediction_detail.py --market POLY-573656

Output:
  Full event/market detail with all outcomes, pricing, and rules.
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request

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
    """Format market with readable prices."""
    pricing = m.get("pricing", {})
    buy_yes = pricing.get("buyYesPriceUsd")
    buy_no = pricing.get("buyNoPriceUsd")
    sell_yes = pricing.get("sellYesPriceUsd")
    sell_no = pricing.get("sellNoPriceUsd")
    return {
        "marketId": m.get("marketId", ""),
        "title": m.get("title", ""),
        "status": m.get("status", ""),
        "result": m.get("result"),
        "buyYesPrice": round(buy_yes / 1_000_000, 4) if buy_yes is not None else None,
        "buyNoPrice": round(buy_no / 1_000_000, 4) if buy_no is not None else None,
        "sellYesPrice": round(sell_yes / 1_000_000, 4) if sell_yes is not None else None,
        "sellNoPrice": round(sell_no / 1_000_000, 4) if sell_no is not None else None,
        "volume": pricing.get("volume", 0),
        "closeTime": m.get("closeTime"),
        "outcomes": m.get("outcomes", []),
        "outcomePrices": m.get("outcomePrices", []),
        "marketOptions": m.get("marketOptions", []),
        "rulesPrimary": m.get("rulesPrimary", ""),
    }


def main():
    args = sys.argv[1:]

    event_id = None
    market_id = None
    i = 0
    while i < len(args):
        if args[i] == "--event" and i + 1 < len(args):
            event_id = args[i + 1]
            i += 2
        elif args[i] == "--market" and i + 1 < len(args):
            market_id = args[i + 1]
            i += 2
        else:
            i += 1

    if not event_id and not market_id:
        print(json.dumps({"error": True, "message": "Provide --event <eventId> or --market <marketId>"}))
        sys.exit(1)

    if event_id:
        data = _get(f"{BACKEND_URL}/prediction/events/{event_id}")
        if isinstance(data, dict) and data.get("error"):
            print(json.dumps(data))
            sys.exit(1)

        meta = data.get("metadata", {})
        markets = [_format_market(m) for m in data.get("markets", [])]
        result = {
            "type": "event",
            "eventId": data.get("eventId", ""),
            "title": meta.get("title", ""),
            "subtitle": meta.get("subtitle", ""),
            "category": data.get("category", ""),
            "isActive": data.get("isActive", False),
            "isLive": data.get("isLive", False),
            "closeTime": meta.get("closeTime", ""),
            "imageUrl": meta.get("imageUrl", ""),
            "markets": markets,
        }
        print(json.dumps(result))

    elif market_id:
        data = _get(f"{BACKEND_URL}/prediction/markets/{market_id}")
        if isinstance(data, dict) and data.get("error"):
            print(json.dumps(data))
            sys.exit(1)

        result = {"type": "market"}
        result.update(_format_market(data))
        print(json.dumps(result))


if __name__ == "__main__":
    main()
