#!/usr/bin/env python3
"""
Patch metadata on a specific ProductVersion via
PUT /creator/products/versions/:versionId.

Use this after creating a basket (Flow A) or after rebalancing (Flow C) to set
fields the create-version DTO doesn't accept: `tradingSchedule`. Also lets you
update `changelog`, `minimumInvestment`, or flip `isDeprecated` on any version.

IMPORTANT — supported fields only:
  The backend's updateProductVersion handler ONLY persists four fields:
    changelog, minimumInvestment, tradingSchedule, isDeprecated
  The DTO technically accepts `label`, `riskLevel`, `estimatedApy`, `isStable`
  but the service layer silently ignores them — they are never written to the
  database. This script strips those four unsupported fields client-side and
  warns the caller so they get honest feedback. Risk level, version label,
  estimated APY, and stable-flag are set by the Cesto team during review.

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
  echo '{"changelog": "...", "minimumInvestment": "10000000"}' \
    | python3 update_version_metadata.py --product-id <productId> --version-id <productVersionId>

Supported fields (all optional — only send what's changing):
  changelog         string (≤1000 chars)
  minimumInvestment string (base units)
  tradingSchedule   any | null
  isDeprecated      boolean

Unsupported fields (stripped with a warning — NOT persisted by the backend):
  label, riskLevel, estimatedApy, isStable

Output:
  The updated ProductVersion object, plus an optional "warning" key if
  unsupported fields were present and stripped.
"""

import sys
sys.dont_write_bytecode = True
import json
import urllib.error
import urllib.request

from _store import read_session, ACCESS_KEY
from _common import resolve_product_uuid

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
        payload = json.loads(sys.stdin.read(), strict=False)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": True, "message": f"Invalid JSON input: {e}"}))
        sys.exit(1)

    if not isinstance(payload, dict) or not payload:
        print(json.dumps({"error": True, "message": "Payload must be a non-empty JSON object."}))
        sys.exit(1)

    # Strip unsupported fields that the backend DTO accepts but silently ignores.
    # Patching them returns 200 but the values are never written to the database.
    UNSUPPORTED = ("riskLevel", "label", "estimatedApy", "isStable")
    stripped = [f for f in UNSUPPORTED if f in payload]
    for f in stripped:
        del payload[f]

    warning = None
    if stripped:
        warning = (
            "These fields are not settable via the skill and were ignored: "
            + ", ".join(stripped)
            + ". Risk level, version label, estimated APY, and stable-flag are "
            "managed by the Cesto team during review — they can't be set through this skill."
        )

    if not payload:
        out = {
            "error": True,
            "message": (
                "Nothing left to patch after removing unsupported fields. "
                "Only changelog, minimumInvestment, tradingSchedule, and isDeprecated "
                "are supported by this endpoint."
            ),
        }
        if warning:
            out["warning"] = warning
        print(json.dumps(out))
        sys.exit(1)

    # Session + role
    session = read_session()
    if session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    # Accept a slug or a UUID for --product-id.
    product_id, rerr = resolve_product_uuid(BASE_URL, product_id, token)
    if rerr or not product_id:
        msg = (rerr or {}).get("message", "Could not resolve that basket id or slug.")
        print(json.dumps({"error": True, "message": msg}))
        sys.exit(1)

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
    if warning and isinstance(result, dict):
        result["warning"] = warning
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
