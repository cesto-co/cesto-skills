#!/usr/bin/env python3
"""
Fetch all supported tokens from the Cesto backend and merge with
Jupiter price data. Returns a unified list with prices.

Usage:
  python3 fetch_tokens.py

Output:
  {"tokens": [{"mint": "...", "symbol": "SOL", "name": "Solana", "logoUrl": "...", "usdPrice": 82.89, "priceChange24h": -3.46}]}
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request

BACKEND_URL = "https://backend.cesto.co"
JUPITER_PRICE_URL = "https://lite-api.jup.ag/price/v3"


def _get(url, timeout=15):
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "CestoCreatorToolkit/1.0")
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode())
    except Exception as e:
        return None


def main():
    # Step 1: Fetch supported tokens
    tokens_data = _get(f"{BACKEND_URL}/tokens")
    if tokens_data is None:
        print(json.dumps({"error": True, "message": "Failed to fetch tokens from backend"}))
        sys.exit(1)

    # Step 2: Fetch prices from Jupiter
    mints = [t["mint"] for t in tokens_data]
    prices = {}
    # Jupiter accepts comma-separated mints (batch in chunks of 50)
    for i in range(0, len(mints), 50):
        chunk = mints[i:i + 50]
        ids_param = ",".join(chunk)
        price_data = _get(f"{JUPITER_PRICE_URL}?ids={ids_param}", timeout=20)
        if price_data:
            prices.update(price_data)

    # Step 3: Merge
    result = []
    for t in tokens_data:
        mint = t["mint"]
        price_info = prices.get(mint, {})
        result.append({
            "mint": mint,
            "symbol": t.get("symbol", ""),
            "name": t.get("name", ""),
            "logoUrl": t.get("logoUrl", ""),
            "usdPrice": price_info.get("usdPrice"),
            "priceChange24h": price_info.get("priceChange24h"),
        })

    # Sort by price descending (tokens with price first)
    result.sort(key=lambda x: x["usdPrice"] or 0, reverse=True)

    print(json.dumps({"tokens": result}))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
