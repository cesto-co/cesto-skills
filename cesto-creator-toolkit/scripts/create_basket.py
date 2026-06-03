#!/usr/bin/env python3
"""
Create a product basket via POST /creator/products.

Passthrough: reads the full JSON payload from stdin and POSTs it as-is.
The server forces isActive=false and isPublished=false for creator-role
callers, so the new basket is always saved as a DRAFT pending admin publish.

Required server-side: either `product.logoUrl` (valid URL) or
`product.aiGenerateThumbnail: true`. The `version` block must include
`minimumInvestment` (base units, string).

Fields NOT accepted by the create-version DTO (will 400 — forbidNonWhitelisted):
  version.label, version.riskLevel, version.estimatedApy, version.isStable,
  version.tradingSchedule
Set those after creation with update_version_metadata.py.

Usage:
  echo '<payload-json>' | python3 create_basket.py

Example payload (mixed open basket). Note: `product.slug` is required by the DTO;
the controller overwrites it with toSlug(name) but validation runs first.

  {
    "product": {
      "name": "Football Glory",
      "slug": "football-glory",
      "description": "European football meets crypto",
      "category": "prediction",
      "tags": ["football", "polymarket"],
      "logoUrl": "https://res.cloudinary.com/.../cover.png"
    },
    "workflow": {
      "name": "Football Glory",
      "description": "European football meets crypto",
      "category": "prediction",
      "definition": {
        "bucket": {
          "mode": "parallel",
          "nodes": [
            {
              "id": "swap-sol",
              "nodeType": "swap.token",
              "submitMethod": "jupiter",
              "amount": {"percentage": 40},
              "parameters": {
                "chain": "solana",
                "fromToken": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "toToken":   "So11111111111111111111111111111111111111112",
                "recipient": "$userAddress",
                "slippage": 50,
                "purpose": "buy",
                "protocol": "jupiter"
              }
            },
            {
              "id": "pred-btc150k-yes",
              "nodeType": "prediction.open",
              "submitMethod": "rpc",
              "amount": {"percentage": 60},
              "parameters": {
                "protocol": "polymarket",
                "marketTicker": "POLY-573656",
                "eventTicker":  "POLY-36173",
                "seriesTicker": "POLY-36173",
                "title": "Bitcoin $150k by Dec 2026",
                "side": "YES",
                "closeTime": 1798776000,
                "userWallet": "$userAddress",
                "slippageBps": 500
              }
            }
          ]
        }
      }
    },
    "version": {
      "changelog": "Initial version",
      "minimumInvestment": "10000000",
      "about": "Long-form strategy description, >= 20 chars.",
      "riskNotes": "**No Liquidation Risk** — ...",
      "resources": "**Thesis** — ..."
    }
  }

Output (normalized — stable keys regardless of what the backend names them):
  {
    "productId": "...",
    "productSlug": "...",
    "versionId":  "...",     // use this for update_version_metadata.py --version-id
    "version":    1,
    "raw":        { /* the full backend response, unmodified */ }
  }

The backend's field for the version row may be `version` or `productVersion`
depending on the codepath; the script extracts it for you under `versionId`.
Capture `productSlug` for the preview URL.
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request
from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"
ENDPOINT = "/creator/products"


def _check_creator(token):
    """Fetch user role from /users/me. Caller verifies CREATOR or ADMIN."""
    try:
        req = urllib.request.Request(f"{BASE_URL}/users/me")
        req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=15)
        user = json.loads(resp.read().decode())
        return user.get("role", "")
    except Exception:
        return None


def main():
    # Read payload from stdin
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"error": True, "message": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)

    # Get session
    _session = read_session()
    if _session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)

    token = _session[ACCESS_KEY]

    # Verify CREATOR or ADMIN role
    role = _check_creator(token)
    if role not in ("CREATOR", "ADMIN"):
        print(json.dumps({"error": True, "message": f"Access denied. Your role is {role}, but CREATOR or ADMIN is required."}))
        sys.exit(1)

    url = f"{BASE_URL}{ENDPOINT}"

    # POST
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read().decode())

        # Normalize: backend uses either `version` or `productVersion` depending
        # on the codepath. Surface a stable shape so the agent doesn't have to
        # branch on it.
        product_obj = result.get("product") or {}
        version_obj = result.get("productVersion") or result.get("version") or {}
        normalized = {
            "productId": product_obj.get("id"),
            "productSlug": product_obj.get("slug"),
            "versionId": version_obj.get("id"),
            "version": version_obj.get("version"),
            "raw": result,
        }
        print(json.dumps(normalized))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            err = json.loads(error_body)
        except Exception:
            err = {"message": error_body}
        print(json.dumps({"error": True, "status": e.code, **err}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
