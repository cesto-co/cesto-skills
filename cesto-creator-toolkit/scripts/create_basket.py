#!/usr/bin/env python3
"""
Create a product basket via POST /creator/products.

Passthrough: reads the full JSON payload from stdin and POSTs it as-is.
The server forces isActive=false and isPublished=false on create, so every
basket starts as an inactive DRAFT. This script then activates it (isActive=true)
with a follow-up PUT — for BOTH creators and admins (the backend now lets a
creator set isActive on their own basket). Publishing is a separate, ADMIN-only
step: run update_basket.py with `product.isPublished: true`. So a freshly created
basket is always isActive=true, isPublished=false.

Required server-side: either `product.logoUrl` (valid URL) or
`product.aiGenerateThumbnail: true`. The `version` block must include
`definition` (the bucket-model WorkflowDefinition) and `minimumInvestment`
(base units, string).

Fields NOT accepted by the create-version DTO (will 400 — forbidNonWhitelisted):
  version.label, version.riskLevel, version.estimatedApy, version.isStable,
  version.tradingSchedule
Set those after creation with update_version_metadata.py.

Usage:
  echo '<payload-json>' | python3 create_basket.py

Example payload (mixed open basket). The script auto-derives `product.slug`
from `product.name` if you omit it — the controller overwrites server-side
anyway, so you never need to compute the slug yourself.

  {
    "product": {
      "name": "Football Glory",
      "description": "European football meets crypto",
      "category": "prediction",
      "tags": ["football", "polymarket"],
      "logoUrl": "https://res.cloudinary.com/.../cover.png"
    },
    "version": {
      "changelog": "Initial version",
      "minimumInvestment": "10000000",
      "about": "Long-form strategy description, >= 20 chars.",
      "riskNotes": "**No Liquidation Risk** — ...",
      "resources": "**Thesis** — ...",
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

import re
import sys
sys.dont_write_bytecode = True
import json, urllib.request
from _store import read_session, ACCESS_KEY
from _common import coerce_minimum_investment

BASE_URL = "https://backend.cesto.co"
ENDPOINT = "/creator/products"


def _to_slug(name):
    """Mirror the backend's toSlug: lowercase, non-alphanumerics → hyphens,
    collapse runs, trim. Returns '' if name yields nothing usable."""
    if not isinstance(name, str):
        return ""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


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


def _extract_percentages_from_definition(definition):
    """Walk a bucket-model definition and return a list of percentage values."""
    if not isinstance(definition, dict):
        return []
    bucket = definition.get("bucket")
    if not isinstance(bucket, dict):
        return []
    nodes = bucket.get("nodes") or []
    percentages = []
    for node in nodes:
        if isinstance(node, dict):
            amount = node.get("amount")
            if isinstance(amount, dict) and "percentage" in amount:
                percentages.append(amount["percentage"])
    return percentages


def _validate_allocations(payload):
    """
    Inspect payload for version.definition and verify that node percentages
    sum to exactly 100. Returns None if valid, or a human-readable error string.
    """
    version = payload.get("version") if isinstance(payload.get("version"), dict) else None
    if version is None:
        return None  # No version block — nothing to validate here.
    definition = version.get("definition")
    if definition is None:
        return None  # No definition — skip (the API will reject it anyway).
    percentages = _extract_percentages_from_definition(definition)
    if not percentages:
        return None  # Can't parse percentages — let the API validate.
    total = sum(percentages)
    if total != 100:
        return (
            f"Allocations sum to {total}, must equal 100. "
            f"Adjust the node percentages before submitting. "
            f"(Found {len(percentages)} node(s): {percentages})"
        )
    return None


def main():
    # Read payload from stdin
    try:
        payload = json.loads(sys.stdin.read(), strict=False)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": True, "message": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)

    if not isinstance(payload, dict):
        print(json.dumps({"error": True, "message": "Payload must be a JSON object with product and version."}))
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

    # Auto-derive slug if missing. CreateProductDto.slug is required by class-
    # validator (non-empty string), but the controller overwrites it with
    # toSlug(name) before persisting. So whatever we send is replaced — we
    # just need SOMETHING non-empty to clear validation. Deriving here means
    # the agent never has to remember to include it.
    product = payload.get("product") if isinstance(payload.get("product"), dict) else None
    if product is not None and not product.get("slug"):
        product["slug"] = _to_slug(product.get("name", "")) or "basket"

    # New baskets are always created as drafts: the create endpoint forces
    # isPublished=false (and isActive=false) server-side. Strip isPublished from
    # the create body so publishing is never attempted at create time — it's an
    # ADMIN-only follow-up via update_basket.py. The basket is activated below.
    if isinstance(payload.get("product"), dict):
        payload["product"].pop("isPublished", None)

    # Fail fast: validate allocations sum to exactly 100 before hitting the API.
    # The backend does not enforce this — a malformed basket persists silently.
    _alloc_err = _validate_allocations(payload)
    if _alloc_err is not None:
        print(json.dumps({"error": True, "message": _alloc_err}))
        sys.exit(1)

    # Guard: minimumInvestment must be a string. A JSON number slips past DTO
    # validation and 500s with a raw Prisma error — coerce it to a string here.
    _mi_warning = coerce_minimum_investment(payload)

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
        if _mi_warning:
            normalized["minimumInvestmentWarning"] = _mi_warning

        # Activate the basket. The create endpoint forces isActive=false, so set
        # it true with a follow-up PUT. This now works for creators too (the
        # backend lets a creator set isActive on their own basket); admins could
        # always do it. isPublished is left false — publishing is a separate
        # ADMIN-only step via update_basket.py.
        normalized["isActive"] = False
        product_id_new = normalized.get("productId")
        if product_id_new:
            act_body = json.dumps({"product": {"isActive": True}}).encode()
            act_req = urllib.request.Request(
                f"{BASE_URL}{ENDPOINT}/{product_id_new}", data=act_body, method="PUT"
            )
            act_req.add_header("Authorization", f"Bearer {token}")
            act_req.add_header("Content-Type", "application/json")
            try:
                act_resp = urllib.request.urlopen(act_req, timeout=30)
                act_result = json.loads(act_resp.read().decode())
                # PUT wraps the product under a "product" key on some codepaths.
                act_product = act_result.get("product") if isinstance(act_result.get("product"), dict) else act_result
                normalized["isActive"] = bool(act_product.get("isActive", True))
                normalized["raw"]["activate"] = act_result
            except Exception as act_e:
                normalized["activateWarning"] = (
                    f"Basket created but the activation step (isActive=true) failed: {act_e}. "
                    f"Retry by re-running update_basket.py on this product."
                )

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
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
