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

Usage:
  echo '{"label": "v1.0.0", "riskLevel": "MEDIUM", "estimatedApy": null}' \
    | python3 update_version_metadata.py --version-id <productVersionId>

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


def _check_creator(token):
    try:
        req = urllib.request.Request(f"{BASE_URL}/users/me")
        req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode()).get("role", "")
    except Exception:
        return None


def main():
    # Parse args
    args = sys.argv[1:]
    version_id = None
    i = 0
    while i < len(args):
        if args[i] == "--version-id" and i + 1 < len(args):
            version_id = args[i + 1]
            i += 2
        else:
            i += 1

    if not version_id:
        print(json.dumps({"error": True, "message": "Missing --version-id argument"}))
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

    role = _check_creator(token)
    if role not in ("CREATOR", "ADMIN"):
        print(json.dumps({"error": True, "message": f"Access denied. Your role is {role}, but CREATOR or ADMIN is required."}))
        sys.exit(1)

    url = f"{BASE_URL}/creator/products/versions/{version_id}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        print(json.dumps(json.loads(resp.read().decode())))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            err = json.loads(body_text)
        except Exception:
            err = {"message": body_text}
        print(json.dumps({"error": True, "status": e.code, **err}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
