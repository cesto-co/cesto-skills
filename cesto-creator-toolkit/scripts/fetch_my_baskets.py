#!/usr/bin/env python3
"""
List the authenticated creator's own baskets via GET /products?mine=true,
enriched with version info from GET /creator/products/:id.

Surfaces draft status (isActive/isPublished) and the latest version's number
and minimum investment, so the agent can render a clean table that
distinguishes DRAFT from LIVE baskets.

Note: the /products?mine=true list endpoint does not include a versions[]
array in its response. This script fetches each product's detail from
GET /creator/products/:id to surface the highest version number (latestVersion).

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


def _http_get(path, token, timeout=15):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
        except Exception:
            err = {"message": body}
        return None, {"status": e.code, **err}
    except Exception as e:
        return None, {"message": str(e)}


def _derive_status(p):
    # The skill treats anything not isActive AND isPublished as DRAFT, since both
    # have to flip to true (admin action) for investors to see the basket.
    return "LIVE" if (p.get("isActive") and p.get("isPublished")) else "DRAFT"


def _max_version_info(versions):
    """Return (latestVersionNumber, minimumInvestment) from a versions list."""
    if not versions:
        return None, None
    # Take the version object with the highest version number.
    best = max(versions, key=lambda v: v.get("version") or 0)
    return best.get("version"), best.get("minimumInvestment")


def main():
    session = read_session()
    if session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)

    token = session[ACCESS_KEY]

    # Step 1: list the caller's products (basic info only; no versions[]).
    data, err = _http_get("/products?mine=true", token)
    if err:
        print(json.dumps({"error": True, **err}))
        sys.exit(1)

    baskets = []
    for p in data:
        product_id = p.get("id")
        latest_version_num = None
        minimum_investment = None

        # Step 2: fetch creator-detail to get versions[] with version numbers.
        # GET /creator/products/:id returns all versions; GET /products?mine=true doesn't.
        if product_id:
            detail, detail_err = _http_get(f"/creator/products/{product_id}", token)
            if detail and not detail_err:
                versions = detail.get("versions") or []
                version_numbers = [
                    v.get("version") for v in versions
                    if isinstance(v.get("version"), int)
                ]
                latest_version_num = max(version_numbers) if version_numbers else None
                # Use the version object with the highest number for minimumInvestment.
                if versions:
                    best = max(versions, key=lambda v: v.get("version") or 0)
                    minimum_investment = best.get("minimumInvestment")

        baskets.append({
            "id": product_id,
            "slug": p.get("slug"),
            "name": p.get("name"),
            "description": p.get("description"),
            "category": p.get("category"),
            "tags": p.get("tags") or [],
            "logoUrl": p.get("logoUrl"),
            "isActive": p.get("isActive", False),
            "isPublished": p.get("isPublished", False),
            "status": _derive_status(p),
            "latestVersion": latest_version_num,
            "minimumInvestment": minimum_investment,
        })

    drafts = sum(1 for b in baskets if b["status"] == "DRAFT")
    print(json.dumps({"baskets": baskets, "total": len(baskets), "drafts": drafts}))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
