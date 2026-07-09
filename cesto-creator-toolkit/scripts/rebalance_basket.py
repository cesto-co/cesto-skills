#!/usr/bin/env python3
"""
Create a new ProductVersion (rebalance) for an existing basket.

Reads a {version} payload from stdin and POSTs to
/creator/products/:productId/versions. The `version` block carries the new
`definition` (bucket-model WorkflowDefinition). Automatically fetches all
existing versions via GET /creator/products/:id and computes
nextVersion = max + 1 so the caller doesn't have to.

Usage:
  echo '{"version": {"definition": {...}, "minimumInvestment": "...", ...}}' \
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
from _common import resolve_product_uuid, coerce_minimum_investment

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




def _fetch_creator_product(product_id, token):
    """GET /creator/products/:id — returns full product with versions[]."""
    product = _http("GET", f"/creator/products/{product_id}", token=token, timeout=15)
    if isinstance(product, dict) and product.get("error"):
        return None, product
    return product, None


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
        return None  # No version block — nothing to validate.
    definition = version.get("definition")
    if definition is None:
        return None  # No definition — let the API validate.
    percentages = _extract_percentages_from_definition(definition)
    if not percentages:
        return None  # Can't parse percentages — skip client-side check.
    total = sum(percentages)
    if total != 100:
        return (
            f"Allocations sum to {total}, must equal 100. "
            f"Adjust the node percentages before submitting. "
            f"(Found {len(percentages)} node(s): {percentages})"
        )
    return None


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
        payload = json.loads(sys.stdin.read(), strict=False)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": True, "message": f"Invalid JSON input: {e}"}))
        sys.exit(1)

    if not isinstance(payload, dict):
        print(json.dumps({"error": True, "message": "Payload must be a JSON object with a version block."}))
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
    product_uuid, err = resolve_product_uuid(BASE_URL, product_arg, token)
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

    # Fail fast: validate allocations sum to exactly 100 before hitting the API.
    # The backend does not enforce this — a malformed basket persists silently.
    _alloc_err = _validate_allocations(payload)
    if _alloc_err is not None:
        print(json.dumps({"error": True, "message": _alloc_err}))
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

    # Guard: minimumInvestment must be a string. A JSON number slips past DTO
    # validation and 500s with a raw Prisma error — coerce it to a string here.
    mi_warning = coerce_minimum_investment(payload)

    # POST the new version.
    result = _http(
        "POST",
        f"/creator/products/{product_uuid}/versions",
        token=token,
        body=payload,
    )

    # Version-collision retry: under a race condition or stale read the server
    # may 400 because `next_version` is already taken (another request committed
    # between our GET and this POST). If the 400 error message mentions
    # "version", "duplicate", or "exists" (case-insensitive), we re-read the
    # versions list, recompute the next number, and try once more. A second
    # failure surfaces the original error verbatim without further retries.
    if (
        isinstance(result, dict)
        and result.get("error")
        and result.get("status") == 400
    ):
        err_msg = str(result.get("message") or "").lower()
        if any(kw in err_msg for kw in ("version", "duplicate", "exists")):
            # Re-read the product to get the freshest version list.
            fresh_product, fetch_err = _fetch_creator_product(product_uuid, token)
            if fresh_product is not None:
                next_version = _compute_next_version(fresh_product)
                payload["version"]["version"] = next_version
                retry_result = _http(
                    "POST",
                    f"/creator/products/{product_uuid}/versions",
                    token=token,
                    body=payload,
                )
                # Use the retry result only if it succeeded; otherwise fall
                # through to surface the original error.
                if not (isinstance(retry_result, dict) and retry_result.get("error")):
                    result = retry_result
                # If the retry also failed, `result` still holds the original
                # error — it will be printed below.

    if isinstance(result, dict) and result.get("error"):
        print(json.dumps(result))
        sys.exit(1)

    # Normalize: backend returns either `version` or `productVersion`.
    version_obj = result.get("productVersion") or result.get("version") or {}
    normalized = {
        "productId": product_uuid,
        "versionId": version_obj.get("id"),
        "version": version_obj.get("version") or next_version,
        "raw": result,
    }
    if mi_warning:
        normalized["minimumInvestmentWarning"] = mi_warning
    print(json.dumps(normalized))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
