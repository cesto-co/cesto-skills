#!/usr/bin/env python3
"""
Patch metadata on a specific ProductVersion via
PUT /creator/products/versions/:versionId.

Use this after creating a basket (Flow A) or after rebalancing (Flow C) to set
fields the create-version DTO doesn't accept: `label`, `riskLevel`,
`estimatedApy`, `isStable`, `tradingSchedule`. Also lets you update
`changelog`, `minimumInvestment`, or flip `isDeprecated` on an older version.

The workflow definition is immutable per version — this endpoint never
changes it. To change allocations, use rebalance_basket.py (creates a new
version).

Ownership rule (skill-enforced):
  The backend lets admins patch any version. This skill refuses to do that —
  both creators and admins may only patch versions on baskets they themselves
  created. That's why `--product-id` is required alongside `--version-id`:
  the script fetches the parent product, verifies `createdBy` matches the
  caller's /users/me.id, and confirms the version belongs to that product.

Usage:
  echo '{"label": "v1.0.0", "riskLevel": "MEDIUM", "estimatedApy": null}' \
    | python3 update_version_metadata.py --product-id <productId> --version-id <productVersionId>

Accepted fields (all optional — only send what's changing):
  label            string (≤50 chars)
  changelog        string (≤1000 chars)
  estimatedApy     number | null
  riskLevel        "LOW" | "MEDIUM" | "HIGH"
  minimumInvestment string (base units)
  tradingSchedule  any | null
  isStable         boolean
  isDeprecated     boolean

Output:
  The updated ProductVersion object.
"""

import sys
sys.dont_write_bytecode = True
import json
import urllib.error
import urllib.request

from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"


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


def main():
    # Parse args
    args = sys.argv[1:]
    version_id = None
    product_id = None
    i = 0
    while i < len(args):
        if args[i] == "--version-id" and i + 1 < len(args):
            version_id = args[i + 1]; i += 2
        elif args[i] == "--product-id" and i + 1 < len(args):
            product_id = args[i + 1]; i += 2
        else:
            i += 1

    if not version_id:
        print(json.dumps({"error": True, "message": "Missing --version-id argument"}))
        sys.exit(1)
    if not product_id:
        print(json.dumps({
            "error": True,
            "message": "Missing --product-id argument. This is required for the ownership pre-flight; pass the productId you got from create_basket.py or rebalance_basket.py.",
        }))
        sys.exit(1)

    # Read payload from stdin
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"error": True, "message": f"Invalid JSON input: {e}"}))
        sys.exit(1)

    if not isinstance(payload, dict) or not payload:
        print(json.dumps({"error": True, "message": "Payload must be a non-empty JSON object."}))
        sys.exit(1)

    # Session + role
    session = read_session()
    if session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    me, err = _http("GET", "/users/me", token, timeout=15)
    if err:
        print(json.dumps({"error": True, **err}))
        sys.exit(1)
    role = me.get("role", "")
    if role not in ("CREATOR", "ADMIN"):
        print(json.dumps({"error": True, "message": f"Access denied. Your role is {role}, but CREATOR or ADMIN is required."}))
        sys.exit(1)

    # Ownership pre-flight. Backend lets admins patch any version; we forbid
    # that here. Also verify the version actually belongs to this product —
    # otherwise the caller could pass a stranger's versionId with their own
    # productId and slip through.
    product, err = _http("GET", f"/creator/products/{product_id}", token, timeout=15)
    if err:
        print(json.dumps({"error": True, **err}))
        sys.exit(1)
    if product.get("createdBy") != me.get("id"):
        print(json.dumps({
            "error": True,
            "status": 403,
            "message": "This skill only patches versions on baskets you created yourself. Use the admin UI for cross-creator changes.",
            "yourId": me.get("id"),
            "productCreatedBy": product.get("createdBy"),
        }))
        sys.exit(1)
    own_version_ids = {v.get("id") for v in (product.get("versions") or [])}
    if version_id not in own_version_ids:
        print(json.dumps({
            "error": True,
            "status": 403,
            "message": f"versionId {version_id} does not belong to product {product_id}. Double-check the IDs.",
            "ownVersionIds": sorted(own_version_ids),
        }))
        sys.exit(1)

    # PUT
    result, err = _http(
        "PUT",
        f"/creator/products/versions/{version_id}",
        token,
        body=payload,
    )
    if err:
        print(json.dumps({"error": True, **err}))
        sys.exit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
