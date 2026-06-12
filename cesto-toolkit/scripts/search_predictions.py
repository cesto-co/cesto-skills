#!/usr/bin/env python3
"""
Search or browse prediction-market events (and their markets) so a user can
pick prediction legs for a community Labs basket.

Public proxy endpoints — work with no session.

Usage:
  python3 search_predictions.py --query "bitcoin"
  python3 search_predictions.py --category crypto --filter trending
  python3 search_predictions.py --category sports --filter live --limit 5
  python3 search_predictions.py --category crypto --filter trending --min-volume 0   # show all

Categories: crypto, sports, politics, economics, finance, esports, weather
Filters:    new, live, trending

Investability filter: only markets with traded volume ABOVE $100,000 (USD) are
shown by default — illiquid markets are hidden when answering "which market can
I invest in". Each event reports `marketsHidden` (count filtered out). Override
the floor with `--min-volume <usd>`; `--min-volume 0` disables it.

Output:
  {"events": [{eventId, title, category, provider, closeTime, markets:[
     {marketId, title, side hints, buyYesPrice($), buyNoPrice($), volume, closeTime}
  ]}]}

Provider is derived from id prefix: POLY-* -> polymarket, KX* -> kalshi.
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request, urllib.parse

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15

# Investability floor: only surface markets with real liquidity. Markets with
# volume at or below this (USD) are hidden when answering "which market can I
# invest in". Override with --min-volume (use 0 to show everything).
MIN_VOLUME_USD = 100_000


def market_volume(m):
    """Market traded volume in USD. Lives in `volume` or `pricing.volume`."""
    v = m.get("volume")
    if not isinstance(v, (int, float)):
        v = (m.get("pricing") or {}).get("volume", 0)
    return v if isinstance(v, (int, float)) else 0


def _get(url):
    # The prediction proxy fans out to an upstream (Jupiter/Polymarket/Kalshi) and
    # can cold-time-out on the first hit. Retry once on a transient error; never
    # retry a real HTTPError (that's a genuine response, not a hiccup).
    last_err = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=TIMEOUT)
            return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": True, "status": e.code, "message": e.read().decode()}
        except Exception as e:
            last_err = e
    return {"error": True, "message": str(last_err)}


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
        "buyYesPrice": round(buy_yes / 1_000_000, 4) if buy_yes is not None else None,
        "buyNoPrice": round(buy_no / 1_000_000, 4) if buy_no is not None else None,
        "volume": market_volume(m),
        "closeTime": m.get("closeTime"),
        "outcomes": m.get("outcomes", []),
    }


def format_event(e, min_volume=MIN_VOLUME_USD):
    meta = e.get("metadata", {}) or {}
    eid = e.get("eventId", "")
    raw = e.get("markets", [])
    # Keep only investable markets (volume above the floor), highest volume first.
    kept = sorted(
        (m for m in raw if market_volume(m) > min_volume),
        key=market_volume,
        reverse=True,
    )
    return {
        "eventId": eid,
        "provider": derive_provider(eid),
        "title": meta.get("title", ""),
        "category": e.get("category", ""),
        "isLive": e.get("isLive", False),
        "closeTime": meta.get("closeTime", ""),
        "imageUrl": meta.get("imageUrl", ""),
        "volumeUsd": e.get("volumeUsd", "0"),
        "markets": [format_market(m) for m in kept],
        "marketsHidden": len(raw) - len(kept),
    }


def main():
    args = sys.argv[1:]
    params = {}
    i = 0
    while i < len(args):
        if args[i] in ("--query", "--category", "--filter", "--limit", "--min-volume") and i + 1 < len(args):
            params[args[i][2:]] = args[i + 1]
            i += 2
        else:
            i += 1

    min_volume = MIN_VOLUME_USD
    if "min-volume" in params:
        try:
            min_volume = float(params["min-volume"])
        except ValueError:
            pass

    if "query" in params:
        q = {"query": params["query"], "includeMarkets": "true", "limit": params.get("limit", "10")}
        url = f"{BASE_URL}/prediction/events/search?{urllib.parse.urlencode(q)}"
    else:
        q = {"includeMarkets": "true"}
        if "category" in params:
            q["category"] = params["category"]
        if "filter" in params:
            q["filter"] = params["filter"]
        url = f"{BASE_URL}/prediction/events?{urllib.parse.urlencode(q)}"

    data = _get(url)
    if isinstance(data, dict) and data.get("error"):
        print(json.dumps(data))
        sys.exit(1)

    events_raw = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    events = [format_event(e, min_volume) for e in events_raw]
    # Drop events left with no investable markets (unless the floor is disabled).
    if min_volume > 0:
        events = [ev for ev in events if ev["markets"]]
    print(json.dumps({
        "events": events,
        "total": len(events),
        "minVolumeUsd": min_volume,
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
