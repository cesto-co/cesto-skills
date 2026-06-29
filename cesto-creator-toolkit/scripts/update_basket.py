#!/usr/bin/env python3
"""
Update an existing product basket via PUT /creator/products/:id.

Reads a partial JSON payload from stdin and PUTs it. Only send fields you
want to change. To change allocations (the workflow definition), use
rebalance_basket.py instead — it creates a new version.

`isActive` / `isPublished` are role-aware:
  - ADMIN:   both pass through as provided — admins may activate, deactivate,
             publish, or unpublish a basket through this script.
  - CREATOR: `isActive` is honored (activate/deactivate your own basket), but
             `isPublished` is NOT applicable and is stripped — publishing is
             admin-only.
Any field you don't send is left unchanged (partial update), so a content-only
edit won't change the active/published state. Cover image and content fields
work the same for both roles.

Where each field belongs:
  product.*   — name, description, category, tags, logoUrl, aiGenerateThumbnail,
                pointsMultiplier, creatorFeeSharePercentage, metadata
  version.*   — changelog, minimumInvestment, isDeprecated, inputTokenMint,
                inputTokenDecimals, about, riskNotes, resources, definition
                (updates the LATEST version's metadata in place; sending
                `definition` here mutates the current version — to preserve
                history, publish a new version with rebalance_basket.py instead)

For setting `label`, `riskLevel`, `estimatedApy`, `isStable` on a specific
version, use update_version_metadata.py instead.

Ownership rule (skill-enforced):
  The backend lets admins edit any product via this endpoint. This skill
  refuses to do that — both creators and admins may only edit baskets they
  themselves created. The pre-flight fetches the product and refuses if
  `createdBy` doesn't match the caller's id.

Usage:
  echo '<partial payload>' | python3 update_basket.py --product-id <product-id>

Output:
  The updated product object.
"""

import sys
sys.dont_write_bytecode = True
import json
import urllib.error
import urllib.request

from _store import read_session, ACCESS_KEY
from _common import resolve_product_uuid

BASE_URL = "https://backend.cesto.co"
ENDPOINT = "/creator/products"


def _http(method, path, token, body=None, timeout=30):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            err = json.loads(body_text)
        except Exception:
            err = {"message": body_text}
        return None, {"status": e.code, **err}
    except Exception as e:
        return None, {"message": str(e)}


def _get_me(token):
    return _http("GET", "/users/me", token, timeout=15)


def main():
    # Parse args
    args = sys.argv[1:]
    product_id = None
    i = 0
    while i < len(args):
        if args[i] == "--product-id" and i + 1 < len(args):
            product_id = args[i + 1]
            i += 2
        else:
            i += 1

    if not product_id:
        print(json.dumps({"error": True, "message": "Missing --product-id argument"}))
        sys.exit(1)

    # Read payload from stdin
    try:
        payload = json.loads(sys.stdin.read(), strict=False)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": True, "message": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)

    if not isinstance(payload, dict):
        print(json.dumps({"error": True, "message": "Payload must be a JSON object (partial product/version)."}))
        sys.exit(1)

    # Get session
    session = read_session()
    if session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    # Accept a slug or a UUID for --product-id (resolve before any /creator call).
    product_id, rerr = resolve_product_uuid(BASE_URL, product_id, token)
    if rerr or not product_id:
        msg = (rerr or {}).get("message", "Could not resolve that basket id or slug.")
        print(json.dumps({"error": True, "message": msg, **({"status": rerr.get("status")} if rerr and rerr.get("status") else {})}))
        sys.exit(1)

    # Role check.
    me, err = _get_me(token)
    if err:
        print(json.dumps({"error": True, **err}))
        sys.exit(1)
    role = me.get("role", "")
    if role not in ("CREATOR", "ADMIN"):
        print(json.dumps({"error": True, "message": f"Access denied. Your role is {role}, but CREATOR or ADMIN is required."}))
        sys.exit(1)

    # Ownership backstop. The backend would let an admin edit anyone's
    # product through this endpoint; we explicitly forbid that here so the
    # skill behaves "exactly like creator" for admins.
    product, err = _http("GET", f"{ENDPOINT}/{product_id}", token, timeout=15)
    if err:
        print(json.dumps({"error": True, **err}))
        sys.exit(1)
    if product.get("createdBy") != me.get("id"):
        print(json.dumps({
            "error": True,
            "status": 403,
            "message": "This skill only edits baskets you created yourself. Use the admin UI for cross-creator changes.",
            "yourId": me.get("id"),
            "productCreatedBy": product.get("createdBy"),
        }))
        sys.exit(1)

    # Role-aware isActive / isPublished:
    #   - ADMIN: pass BOTH through exactly as provided (activate/deactivate/
    #     publish/unpublish all allowed). Nothing forced or stripped.
    #   - CREATOR: isActive is honored, but isPublished is NOT applicable — strip
    #     it so it's never sent. (The backend enforces this too; stripping here
    #     makes it an explicit no-op rather than a silently-ignored field.)
    # Partial update: any field not sent is left unchanged server-side, so a
    # content-only edit never needs to force isActive.
    product_block = payload.get("product")
    if isinstance(product_block, dict) and role != "ADMIN":
        product_block.pop("isPublished", None)

    # PUT
    result, err = _http("PUT", f"{ENDPOINT}/{product_id}", token, body=payload)
    if err:
        print(json.dumps({"error": True, **err}))
        sys.exit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
