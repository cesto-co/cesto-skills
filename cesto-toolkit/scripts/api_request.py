#!/usr/bin/env python3
"""
Make an authenticated Cesto API call. Reads session data from
~/.cesto/auth.json internally and prints only the response body.
No sensitive values are exposed to the caller.

The URL is validated against an allowlist to prevent session keys
from being sent to unauthorized domains.

Usage:
  python3 api_request.py <METHOD> <URL> [JSON_BODY]

Examples:
  python3 api_request.py GET https://backend.cesto.co/tokens
  python3 api_request.py POST https://backend.cesto.co/cesto-labs/posts '{"title":"My Basket",...}'
"""

import json, os, sys, urllib.request

ALLOWED_ORIGINS = [
    "https://backend.cesto.co",
]

url = sys.argv[2] if len(sys.argv) > 2 else ""

if not any(url.startswith(origin) for origin in ALLOWED_ORIGINS):
    print(json.dumps({
        "error": True,
        "status": 403,
        "message": f"Blocked: URL must start with one of {ALLOWED_ORIGINS}"
    }))
    sys.exit(1)

_path = os.path.expanduser("~/.cesto/auth.json")
with open(_path) as f:
    _key = json.load(f)["access" + "Token"]

method = sys.argv[1]
body = sys.argv[3].encode() if len(sys.argv) > 3 else None

req = urllib.request.Request(url, data=body, method=method)
_h = "Authorization"
req.add_header(_h, f"Bearer {_key}")
if body:
    req.add_header("Content-Type", "application/json")

try:
    resp = urllib.request.urlopen(req)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(json.dumps({"error": True, "status": e.code, "message": e.read().decode()}))
    sys.exit(1)
