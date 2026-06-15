#!/usr/bin/env python3
"""
Fetch full detail for a basket including its workflow definition.

For creator-owned baskets, prefers GET /creator/products/:id (richer — returns
all versions, ownership-checked) and falls back to GET /products/:slug (public,
latest version only, flat ProductVersionResponseDto shape).

Usage:
  python3 fetch_basket_detail.py <slug-or-id>

Output:
  Clean summary of the product + latest version, plus the raw `definition`
  object (bucket model: pre/bucket/post → mode + nodes). All versions are
  surfaced when the creator-endpoint path is used.
"""

import sys
sys.dont_write_bytecode = True
import json
import urllib.error
import urllib.request

from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"


def _http_get(path, token=None, timeout=15):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    if token:
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


def _looks_like_uuid(s):
    return len(s) == 36 and s.count("-") == 4


def _resolve_product_uuid(identifier, token):
    if _looks_like_uuid(identifier):
        return identifier
    public, _ = _http_get(f"/products/{identifier}", token=token)
    if public and isinstance(public, dict):
        return public.get("id") or identifier
    return identifier


def _format_creator_response(data):
    """Owner-scope response: product + versions[]. Pick newest non-deprecated as 'current'."""
    versions = data.get("versions") or []
    current = versions[0] if versions else {}
    defn = current.get("definition") or {}
    return {
        "source": "creator",
        "id": data.get("id"),
        "slug": data.get("slug"),
        "name": data.get("name"),
        "description": data.get("description"),
        "category": data.get("category"),
        "tags": data.get("tags") or [],
        "logoUrl": data.get("logoUrl"),
        "isActive": data.get("isActive", False),
        "isPublished": data.get("isPublished", False),
        "createdBy": data.get("createdBy"),
        "currentVersion": {
            "versionId": current.get("id"),
            "version": current.get("version"),
            "changelog": current.get("changelog"),
            "minimumInvestment": current.get("minimumInvestment"),
            "inputTokenMint": current.get("inputTokenMint"),
            "inputTokenDecimals": current.get("inputTokenDecimals"),
            "about": current.get("about"),
            "riskNotes": current.get("riskNotes"),
            "resources": current.get("resources"),
            "isDeprecated": current.get("isDeprecated", False),
            "definition": defn,
        },
        "allVersions": [
            {
                "versionId": v.get("id"),
                "version": v.get("version"),
                "changelog": v.get("changelog"),
                "minimumInvestment": v.get("minimumInvestment"),
                "isDeprecated": v.get("isDeprecated", False),
                "createdAt": v.get("createdAt"),
            }
            for v in versions
        ],
    }


def _format_public_response(data):
    """Public-scope response: flat ProductVersionResponseDto."""
    return {
        "source": "public",
        "id": data.get("id"),
        "versionId": data.get("versionId"),
        "version": data.get("version"),
        "slug": data.get("slug"),
        "name": data.get("name"),
        "description": data.get("description"),
        "category": data.get("category"),
        "tags": data.get("tags") or [],
        "logoUrl": data.get("logoUrl"),
        "isActive": data.get("isActive", False),
        "isPublished": data.get("isPublished", False),
        "minimumInvestment": data.get("minimumInvestment"),
        "inputTokenMint": data.get("inputTokenMint"),
        "inputTokenDecimals": data.get("inputTokenDecimals"),
        "about": data.get("about"),
        "riskNotes": data.get("riskNotes"),
        "resources": data.get("resources"),
        "changelog": data.get("changelog"),
        "tokensInvolved": data.get("tokensInvolved") or [],
        "protocolsInvolved": data.get("protocolsInvolved") or [],
        "tokenPerformance": data.get("tokenPerformance"),
        "tokenPerformance7d": data.get("tokenPerformance7d"),
        "tokenPerformance30d": data.get("tokenPerformance30d"),
        "predictionMarkets": data.get("predictionMarkets"),
        "canInvest": data.get("canInvest", True),
        "definition": data.get("definition") or {},
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "Usage: fetch_basket_detail.py <slug-or-id>"}))
        sys.exit(1)

    identifier = sys.argv[1]
    session = read_session()
    token = session[ACCESS_KEY] if session else None

    if token:
        # Try the owner endpoint first — richer and shows drafts.
        product_uuid = _resolve_product_uuid(identifier, token)
        owner_data, owner_err = _http_get(f"/creator/products/{product_uuid}", token=token)
        if owner_data:
            print(json.dumps(_format_creator_response(owner_data)))
            return
        # 403 means not the owner; 404 means doesn't exist. Either way, fall through.

    # Public path.
    public_data, public_err = _http_get(f"/products/{identifier}", token=token)
    if public_data:
        print(json.dumps(_format_public_response(public_data)))
        return

    print(json.dumps({"error": True, **(public_err or {"message": "Not found"})}))
    sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
