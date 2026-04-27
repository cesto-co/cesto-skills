#!/usr/bin/env python3
"""
Fetch the authenticated creator's own baskets.

Usage:
  python3 fetch_my_baskets.py

Output:
  {"baskets": [{"id": "...", "slug": "...", "name": "...", "isActive": true, ...}]}
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request
from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"

_session = read_session()
if _session is None:
    print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
    sys.exit(1)

_key = _session[ACCESS_KEY]

try:
    req = urllib.request.Request(f"{BASE_URL}/products?mine=true")
    req.add_header("Authorization", f"Bearer {_key}")
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    print(json.dumps({"error": True, "status": e.code, "message": e.read().decode()}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({"error": True, "message": str(e)}))
    sys.exit(1)

# data is an array of products
baskets = []
for p in data:
    baskets.append({
        "id": p.get("id", ""),
        "slug": p.get("slug", ""),
        "name": p.get("name", ""),
        "description": p.get("description", ""),
        "category": p.get("category"),
        "tags": p.get("tags", []),
        "logoUrl": p.get("logoUrl"),
        "isActive": p.get("isActive", False),
        "isPublished": p.get("isPublished", False),
    })

print(json.dumps({"baskets": baskets, "total": len(baskets)}))
