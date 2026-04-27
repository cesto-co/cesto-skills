#!/usr/bin/env python3
"""
Check the authenticated user's role. Returns role and endpoint prefix.
Used by other scripts to determine which API path to use.

Usage:
  python3 check_role.py

Output:
  {"role": "CREATOR", "address": "6APV...", "id": "...", "endpoint_prefix": "/creator"}
  {"error": true, "message": "Access denied. Your role is USER, but CREATOR is required."}
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request
from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"
ALLOWED_ROLES = {"CREATOR": "/creator"}

_session = read_session()
if _session is None:
    print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
    sys.exit(1)

_key = _session[ACCESS_KEY]

try:
    req = urllib.request.Request(f"{BASE_URL}/users/me")
    req.add_header("Authorization", f"Bearer {_key}")
    resp = urllib.request.urlopen(req, timeout=15)
    user = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    print(json.dumps({"error": True, "message": f"Failed to fetch user info: HTTP {e.code}"}))
    sys.exit(1)
except Exception as ex:
    print(json.dumps({"error": True, "message": f"Failed to fetch user info: {str(ex)}"}))
    sys.exit(1)

role = user.get("role", "")

if role in ALLOWED_ROLES:
    print(json.dumps({
        "role": role,
        "address": user.get("solanaWalletAddress", ""),
        "id": user.get("id", ""),
        "endpoint_prefix": ALLOWED_ROLES[role],
    }))
else:
    print(json.dumps({
        "error": True,
        "message": f"Access denied. Your role is {role}, but CREATOR is required.",
    }))
    sys.exit(1)
