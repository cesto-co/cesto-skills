#!/usr/bin/env python3
"""
Create a new ProductVersion (rebalance) for an existing basket.

Reads a {workflow, version} payload from stdin and POSTs to
/creator/products/:productId/versions. Automatically fetches all existing
versions via GET /creator/products/:id and computes nextVersion = max + 1
so the caller doesn't have to.

Usage:
  echo '{"workflow": {...}, "version": {...}}' \
    | python3 rebalance_basket.py --product-id <product-id-or-slug>

The payload's `version` block should NOT include `version` (auto-bumped),
`label`, `riskLevel`, `estimatedApy`, or `isStable` — those aren't accepted
by the create-version DTO and will 400 via forbidNonWhitelisted. Use
update_version_metadata.py after creation to set them.

Output:
  The new version response from the API: { version: { id, version, ... } }.
"""

import sys
sys.dont_write_bytecode = True
import json
import urllib.error
import urllib.request

from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"


def _http(method, path, token=None, body=None, timeout=30):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            err = json.loads(body_text)
        except Exception:
            err = {"message": body_text}
        return {"error": True, "status": e.code, **err}
    except Exception as e:
        return {"error": True, "message": str(e)}


def _get_me(token):
    user = _http("GET", "/users/me", token=token, timeout=15)
    if isinstance(user, dict) and user.get("error"):
        return None
    return user


def _resolve_product_uuid(identifier, token):
    """Accept either a UUID or a slug. Resolve to the canonical product UUID."""
    # UUIDs are 36 chars with dashes; slugs aren't. Cheap heuristic.
    if len(identifier) == 36 and identifier.count("-") == 4:
        return identifier, None
    # Slug → resolve via public detail endpoint.
    detail = _http("GET", f"/products/{identifier}", token=token, timeout=15)
    if isinstance(detail, dict) and detail.get("error"):
        return None, detail
    return detail.get("id"), None


def _fetch_creator_product(product_id, token):
    """GET /creator/products/:id — returns full product with versions[]."""
    product = _http("GET", f"/creator/products/{product_id}", token=token, timeout=15)
    if isinstance(product, dict) and product.get("error"):
        return None, product
    return product, None


def _compute_next_version(product):
    versions = product.get("versions") or []
    if not versions:
        return 2  # initial v1 already exists somewhere; play it safe.
    highest = max((int(v.get("version", 0)) for v in versions), default=1)
    return highest + 1


def main():
    # Parse args
    args = sys.argv[1:]
    product_arg = None
    i = 0
    while i < len(args):
        if args[i] == "--product-id" and i + 1 < len(args):
            product_arg = args[i + 1]
            i += 2
        else:
            i += 1

    if not product_arg:
        print(json.dumps({"error": True, "message": "Missing --product-id argument"}))
        sys.exit(1)

    # Read payload from stdin
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"error": True, "message": f"Invalid JSON input: {e}"}))
        sys.exit(1)

    # Session
    session = read_session()
    if session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    # Role check up front — fail fast with a clear message.
    me = _get_me(token)
    if me is None:
        print(json.dumps({"error": True, "message": "Could not fetch /users/me."}))
        sys.exit(1)
    role = me.get("role", "")
    if role not in ("CREATOR", "ADMIN"):
        print(json.dumps({"error": True, "message": f"Access denied. Your role is {role}, but CREATOR or ADMIN is required."}))
        sys.exit(1)

    # Resolve slug → UUID if needed.
    product_uuid, err = _resolve_product_uuid(product_arg, token)
    if err:
        print(json.dumps(err))
        sys.exit(1)
    if not product_uuid:
        print(json.dumps({"error": True, "message": f"Could not resolve product: {product_arg}"}))
        sys.exit(1)

    # Fetch full product (also gives us all versions for the bump).
    product, err = _fetch_creator_product(product_uuid, token)
    if err:
        print(json.dumps(err))
        sys.exit(1)

    # Ownership backstop. The backend would let admins rebalance any product
    # via this endpoint; we explicitly forbid that so admins behave "exactly
    # like creator" through this skill (per the skill's design rule).
    if product.get("createdBy") != me.get("id"):
        print(json.dumps({
            "error": True,
            "status": 403,
            "message": "This skill only rebalances baskets you created yourself. Use the admin UI for cross-creator changes.",
            "yourId": me.get("id"),
            "productCreatedBy": product.get("createdBy"),
        }))
        sys.exit(1)

    # Auto-bump version number.
    next_version = _compute_next_version(product)

    # Inject version number; do NOT inject legacy fields (label/riskLevel/etc) —
    # the create-version DTO rejects them. Caller patches those via
    # update_version_metadata.py after this returns.
    version_data = payload.get("version") or {}
    version_data["version"] = next_version
    version_data.setdefault("isDeprecated", False)
    payload["version"] = version_data

    # POST the new version.
    result = _http(
        "POST",
        f"/creator/products/{product_uuid}/versions",
        token=token,
        body=payload,
    )
    if isinstance(result, dict) and result.get("error"):
        print(json.dumps(result))
        sys.exit(1)

    # Normalize: backend returns either `version` or `productVersion`.
    version_obj = result.get("productVersion") or result.get("version") or {}
    print(json.dumps({
        "productId": product_uuid,
        "versionId": version_obj.get("id"),
        "version": version_obj.get("version") or next_version,
        "raw": result,
    }))


if __name__ == "__main__":
    main()
