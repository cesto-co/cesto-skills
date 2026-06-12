#!/usr/bin/env python3
"""
Get detail for a single prediction event or market so a user can confirm a
prediction leg before adding it to a community Labs basket.

Public proxy endpoints — work with no session.

Usage:
  python3 get_prediction_detail.py --event POLY-89502
  python3 get_prediction_detail.py --market POLY-573656

Output:
  Full event/market detail with markets, readable YES/NO prices ($), volume,
  and close time. Provider is derived from the id prefix.
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15

# Investability floor (USD). Event markets at or below this are hidden by default;
# override with --min-volume (0 = show all). A single --market lookup is always
# shown but tagged with `investable`.
MIN_VOLUME_USD = 100_000


def market_volume(m):
    """Market traded volume in USD. Lives in `volume` or `pricing.volume`."""
    v = m.get("volume")
    if not isinstance(v, (int, float)):
        v = (m.get("pricing") or {}).get("volume", 0)
    return v if isinstance(v, (int, float)) else 0


def _get(url):
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": True, "status": e.code, "message": e.read().decode()}
    except Exception as e:
        return {"error": True, "message": str(e)}


def derive_provider(_id):
    if not _id:
        return ""
    if _id.startswith("POLY-"):
        return "polymarket"
    if _id.startswith("KX"):
        return "kalshi"
    return ""


def format_market(m):
    pricing = m.get("pricing", {}) or {}
    buy_yes = pricing.get("buyYesPriceUsd")
    buy_no = pricing.get("buyNoPriceUsd")
    mid = m.get("marketId", "")
    return {
        "marketId": mid,
        "provider": m.get("provider") or derive_provider(mid),
        "title": m.get("title", ""),
        "status": m.get("status", ""),
        "result": m.get("result"),
        "buyYesPrice": round(buy_yes / 1_000_000, 4) if buy_yes is not None else None,
        "buyNoPrice": round(buy_no / 1_000_000, 4) if buy_no is not None else None,
        "volume": market_volume(m),
        "closeTime": m.get("closeTime"),
        "outcomes": m.get("outcomes", []),
        "outcomePrices": m.get("outcomePrices", []),
        "rulesPrimary": m.get("rulesPrimary", ""),
    }


def main():
    args = sys.argv[1:]
    event_id = None
    market_id = None
    min_volume = MIN_VOLUME_USD
    i = 0
    while i < len(args):
        if args[i] == "--event" and i + 1 < len(args):
            event_id = args[i + 1]
            i += 2
        elif args[i] == "--market" and i + 1 < len(args):
            market_id = args[i + 1]
            i += 2
        elif args[i] == "--min-volume" and i + 1 < len(args):
            try:
                min_volume = float(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1

    if not event_id and not market_id:
        print(json.dumps({"error": True, "message": "Provide --event <eventId> or --market <marketId>"}))
        sys.exit(1)

    if event_id:
        data = _get(f"{BASE_URL}/prediction/events/{event_id}")
        if isinstance(data, dict) and data.get("error"):
            print(json.dumps(data))
            sys.exit(1)
        # Event detail is NOT wrapped in a `data` envelope.
        ev = data.get("data", data) if isinstance(data, dict) else {}
        meta = ev.get("metadata", {}) or {}
        eid = ev.get("eventId", "")
        raw = ev.get("markets", [])
        kept = sorted(
            (m for m in raw if market_volume(m) > min_volume),
            key=market_volume,
            reverse=True,
        )
        result = {
            "type": "event",
            "eventId": eid,
            "provider": derive_provider(eid),
            "title": meta.get("title", ""),
            "category": ev.get("category", ""),
            "isLive": ev.get("isLive", False),
            "closeTime": meta.get("closeTime", ""),
            "imageUrl": meta.get("imageUrl", ""),
            "volumeUsd": ev.get("volumeUsd", "0"),
            "minVolumeUsd": min_volume,
            "marketsHidden": len(raw) - len(kept),
            "markets": [format_market(m) for m in kept],
        }
        print(json.dumps(result, indent=2))

    else:
        data = _get(f"{BASE_URL}/prediction/markets/{market_id}")
        if isinstance(data, dict) and data.get("error"):
            print(json.dumps(data))
            sys.exit(1)
        m = data.get("data", data) if isinstance(data, dict) else {}
        result = {"type": "market"}
        result.update(format_market(m))
        # A directly-requested market is always shown, but flagged for investability.
        result["investable"] = market_volume(m) > min_volume
        result["minVolumeUsd"] = min_volume
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
