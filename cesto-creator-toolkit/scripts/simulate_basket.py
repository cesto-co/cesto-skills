#!/usr/bin/env python3
"""
Simulate a basket workflow definition via POST /positions/simulate.

Public endpoint — no auth required. The definition must be the new
bucket-model shape (see references/workflow-definition.md).

Usage:
  echo '{"definition": {...}, "amount": 100, "refresh": true}' | python3 simulate_basket.py

Input JSON shape:
  {
    "definition": {
      "bucket": {
        "mode": "parallel",
        "nodes": [
          {
            "id": "swap-sol",
            "nodeType": "swap.token",
            "submitMethod": "jupiter",
            "amount": {"percentage": 100},
            "parameters": {
              "chain": "solana",
              "fromToken": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
              "toToken":   "So11111111111111111111111111111111111111112",
              "recipient": "$userAddress",
              "slippage": 50,
              "purpose": "buy",
              "protocol": "jupiter"
            }
          }
        ]
      }
    },
    "amount": 100,
    "refresh": true,
    "timeRange": "1y"
  }

Output:
  Formatted analytics: aggregate netPnL/APY/return at 7d/30d/1y windows, plus
  per-node breakdown (current price, price changes), plus predictionPerformance
  for baskets that include prediction.open nodes.
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request

BASE_URL = "https://backend.cesto.co"


def main():
    # Read definition from stdin
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"error": True, "message": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)

    # Ensure required fields
    if "definition" not in input_data:
        print(json.dumps({"error": True, "message": "Missing 'definition' in input"}))
        sys.exit(1)

    payload = {
        "definition": input_data["definition"],
        "amount": input_data.get("amount", 100),
        "refresh": input_data.get("refresh", True),
    }

    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/positions/simulate",
        data=body,
        method="POST",
    )
    req.add_header("Content-Type", "application/json")

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": True, "status": e.code, "message": e.read().decode()}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)

    # Format the analytics response
    analytics = data.get("analytics", {})
    aggregates = analytics.get("aggregates", {})
    perf = aggregates.get("tokenPerformance", {})
    perf_7d = aggregates.get("tokenPerformance7d", {})
    perf_30d = aggregates.get("tokenPerformance30d", {})

    # Format node analyses
    node_analyses = []
    for na in analytics.get("nodeAnalyses", []):
        market_data = na.get("marketData", {})
        token_perf = market_data.get("tokenPerformance", {})
        node_analyses.append({
            "id": na.get("id", ""),
            "nodeType": na.get("nodeType", ""),
            "protocol": na.get("protocol", ""),
            "inputSymbol": na.get("inputSymbol", ""),
            "outputSymbol": na.get("outputSymbol", ""),
            "currentPrice": token_perf.get("currentPrice"),
            "priceChange24h": token_perf.get("priceChange24h"),
            "priceChange7d": token_perf.get("priceChange7d"),
            "priceChange30d": token_perf.get("priceChange30d"),
            "priceChange1y": token_perf.get("priceChange1y"),
            "marketCap": token_perf.get("marketCap"),
        })

    output = {
        "analytics": {
            "tokensInvolved": aggregates.get("tokensInvolved", []),
            "netPnL": perf.get("netPnL"),
            "priceAPY": perf.get("priceAPY"),
            "annualizedReturn": perf.get("annualizedReturn"),
            "daysAvailable": perf.get("daysAvailable"),
            "startDate": perf.get("startDate"),
            "endDate": perf.get("endDate"),
            "7d": {
                "return": perf_7d.get("return") or perf_7d.get("netPnL"),
                "priceAPY": perf_7d.get("priceAPY"),
            } if perf_7d else None,
            "30d": {
                "return": perf_30d.get("return") or perf_30d.get("netPnL"),
                "priceAPY": perf_30d.get("priceAPY"),
            } if perf_30d else None,
        },
        "nodes": node_analyses,
        "predictionPerformance": perf.get("predictionPerformance") if "predictionPerformance" in perf else None,
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
