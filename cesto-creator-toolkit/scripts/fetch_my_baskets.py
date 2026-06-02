#!/usr/bin/env python3
"""
List the authenticated creator's own baskets via GET /products?mine=true.

Surfaces draft status (isActive/isPublished) and the latest version's number
and minimum investment, so the agent can render a clean table that
distinguishes DRAFT from LIVE baskets.

Usage:
  python3 fetch_my_baskets.py

Output:
  {
    "baskets": [
      {
        "id": "...",
        "slug": "...",
        "name": "...",
        "description": "...",
        "category": "prediction",
        "tags": [...],
        "logoUrl": "...",
        "isActive": true,
        "isPublished": true,
        "status": "LIVE" | "DRAFT",
        "latestVersion": 3,
        "minimumInvestment": "10000000"
      }
    ],
    "total": N,
    "drafts": M
  }
"""

import sys
sys.dont_write_bytecode = True
import json
import urllib.error
import urllib.request

from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"


def _derive_status(p):
    # The skill treats anything not isActive AND isPublished as DRAFT, since both
    # have to flip to true (admin action) for investors to see the basket.
    return "LIVE" if (p.get("isActive") and p.get("isPublished")) else "DRAFT"


def main():
    session = read_session()
    if session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)

    token = session[ACCESS_KEY]

    try:
        req = urllib.request.Request(f"{BASE_URL}/products?mine=true")
        req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
        except Exception:
            err = {"message": body}
        print(json.dumps({"error": True, "status": e.code, **err}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)

    baskets = []
    for p in data:
        # The list endpoint returns the latest non-deprecated version as the
        # first (and only) entry in `versions[]`.
        latest_version_obj = (p.get("versions") or [{}])[0]
        baskets.append({
            "id": p.get("id"),
            "slug": p.get("slug"),
            "name": p.get("name"),
            "description": p.get("description"),
            "category": p.get("category"),
            "tags": p.get("tags") or [],
            "logoUrl": p.get("logoUrl"),
            "isActive": p.get("isActive", False),
            "isPublished": p.get("isPublished", False),
            "status": _derive_status(p),
            "latestVersion": latest_version_obj.get("version"),
            "minimumInvestment": latest_version_obj.get("minimumInvestment"),
        })

    drafts = sum(1 for b in baskets if b["status"] == "DRAFT")
    print(json.dumps({"baskets": baskets, "total": len(baskets), "drafts": drafts}))


if __name__ == "__main__":
    main()
