#!/usr/bin/env python3
"""
Update an existing product basket (metadata only, no rebalance).
Reads partial update payload from stdin and PUTs to the role-appropriate endpoint.

Usage:
  echo '{"product": {...}, "workflow": {...}, "version": {...}}' | python3 update_basket.py --product-id <id>

Output:
  The updated product response from the API.
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request
from _store import read_session, ACCESS_KEY

BASE_URL = "https://dev.backend.cesto.co"
ROLE_ENDPOINTS = {"CREATOR": "/creator/products", "ADMIN": "/admin/products"}


def _get_role(token):
    """Fetch user role from /users/me."""
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

    # Determine endpoint from role
    role = _get_role(token)
    if role not in ROLE_ENDPOINTS:
        print(json.dumps({"error": True, "message": f"Access denied. Your role is {role}, but CREATOR or ADMIN is required."}))
        sys.exit(1)

    endpoint = ROLE_ENDPOINTS[role]
    url = f"{BASE_URL}{endpoint}/{product_id}"

    # PUT
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="PUT")
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
