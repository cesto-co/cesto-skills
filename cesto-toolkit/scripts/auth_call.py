#!/usr/bin/env python3
"""
Make an authenticated Cesto API call without exposing the token.
Reads the token from ~/.cesto/auth.json internally, makes the request,
and prints only the response body.

Usage:
  python3 auth_call.py <METHOD> <URL> [JSON_BODY]

Examples:
  python3 auth_call.py GET https://backend.cesto.co/tokens
  python3 auth_call.py POST https://backend.cesto.co/cesto-labs/posts '{"title":"My Basket",...}'
"""

import json, os, sys, urllib.request

auth_path = os.path.expanduser("~/.cesto/auth.json")
with open(auth_path) as f:
    token = json.load(f)["accessToken"]

method = sys.argv[1]
url = sys.argv[2]
body = sys.argv[3].encode() if len(sys.argv) > 3 else None

req = urllib.request.Request(url, data=body, method=method)
req.add_header("Authorization", f"Bearer {token}")
if body:
    req.add_header("Content-Type", "application/json")

try:
    resp = urllib.request.urlopen(req)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(json.dumps({"error": True, "status": e.code, "message": e.read().decode()}))
    sys.exit(1)
