#!/usr/bin/env python3
"""
Create a new version (rebalance) for an existing product basket.
Reads the new workflow+version payload from stdin.
Automatically fetches current version and bumps it.

Usage:
  echo '{"workflow": {...}, "version": {...}}' | python3 rebalance_basket.py --product-id <id>

Output:
  The new version response from the API.
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request
from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"
ENDPOINT = "/creator/products"


def _get(url, token=None, timeout=15):
    try:
        req = urllib.request.Request(url)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": True, "status": e.code, "message": e.read().decode()}
    except Exception as e:
        return {"error": True, "message": str(e)}


def _check_creator(token):
    """Fetch user role from /users/me and verify it is CREATOR."""
    try:
        req = urllib.request.Request(f"{BASE_URL}/users/me")
        req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=15)
        user = json.loads(resp.read().decode())
        return user.get("role", "")
    except Exception:
        return None


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

    # Fetch current product to get version number and real UUID
    # The identifier may be a slug or UUID — /products/ accepts both but may need auth
    product = _get(f"{BASE_URL}/products/{product_id}", token=token)
    if isinstance(product, dict) and product.get("error"):
        print(json.dumps(product))
        sys.exit(1)

    # Use the real UUID from the response for the POST call
    real_product_id = product.get("id", product_id)
    current_version = product.get("version", 1)
    next_version = current_version + 1

    # Auto-fill version fields if not provided
    version_data = payload.get("version", {})
    version_data.setdefault("version", next_version)
    version_data.setdefault("label", f"v{next_version}.0.0")
    version_data.setdefault("changelog", f"Rebalanced to version {next_version}")
    version_data.setdefault("estimatedApy", None)
    version_data.setdefault("riskLevel", product.get("riskLevel", "MEDIUM"))
    version_data.setdefault("minimumInvestment", product.get("minimumInvestment", "10000000"))
    version_data.setdefault("isStable", False)
    version_data.setdefault("isDeprecated", False)
    payload["version"] = version_data

    # Verify CREATOR role
    role = _check_creator(token)
    if role != "CREATOR":
        print(json.dumps({"error": True, "message": f"Access denied. Your role is {role}, but CREATOR is required."}))
        sys.exit(1)

    url = f"{BASE_URL}{ENDPOINT}/{real_product_id}/versions"

    # POST
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read().decode())
        print(json.dumps(result))
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
