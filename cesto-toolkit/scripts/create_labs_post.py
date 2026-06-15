#!/usr/bin/env python3
"""
Create a community Labs post (a community basket) from a full CreatePostDto.

Requires an authenticated session. Reads the full CreatePostDto JSON from
stdin, validates that allocations sum to 100, then POSTs to /labs/posts.
Supports BOTH token legs and prediction legs.

This REPLACES the old pattern of posting to /labs/posts via api_request.py.

CreatePostDto shape:
  {
    "title": "1-100 chars",
    "description": "1-1000 chars",
    "aiGenerateThumbnail": true,        # OR "thumbnailUrl": "https://..."
    "allocations": [
      {"kind":"token","mint":"...","symbol":"...","name":"...","percentage":60},
      {"kind":"prediction","marketId":"...","eventId":"...","side":"YES",
       "provider":"polymarket","eventTitle":"...","marketTitle":"...","percentage":40}
    ]
  }

Usage:
  cat payload.json | python3 create_labs_post.py

Output:
  {"slug": "...", "title": "...", "link": "https://app.cesto.co/labs/<slug>", "raw": {...}}
"""

import json, os, sys, urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))

from _store import read_session, ACCESS_KEY
from _common import normalize_prediction_legs

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 30
TOLERANCE = 0.01


def validate_allocations(allocations):
    """Mirror validate_allocations.py: sum percentage across all legs == 100."""
    if not isinstance(allocations, list) or not allocations:
        return False, 0, "At least one allocation is required."
    total = 0.0
    for a in allocations:
        if not isinstance(a, dict):
            return False, None, "Each allocation must be an object."
        try:
            total += float(a.get("percentage"))
        except (ValueError, TypeError):
            return False, None, "Each allocation must have a numeric 'percentage'."
    total_display = round(total, 2)
    if abs(total - 100.0) <= TOLERANCE:
        return True, total_display, None
    return False, total_display, f"Allocations sum to {total_display}, must equal 100."


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw, strict=False)
    except Exception as e:
        print(json.dumps({"error": True, "message": f"Invalid JSON payload on stdin: {e}"}))
        sys.exit(1)

    if not isinstance(payload, dict):
        print(json.dumps({"error": True, "message": "Payload must be a JSON object (CreatePostDto)."}))
        sys.exit(1)

    if not payload.get("title"):
        print(json.dumps({"error": True, "message": "Missing required field: title (1-100 chars)."}))
        sys.exit(1)
    if not payload.get("description"):
        print(json.dumps({"error": True, "message": "Missing required field: description (1-1000 chars)."}))
        sys.exit(1)

    # Derive mint/symbol/name for prediction legs (DB requires them, like the frontend does)
    normalize_prediction_legs(payload.get("allocations"))

    valid, total, msg = validate_allocations(payload.get("allocations"))
    if not valid:
        print(json.dumps({"error": True, "valid": False, "sum": total, "message": msg}))
        sys.exit(1)

    session = read_session()
    if not session or not session.get(ACCESS_KEY):
        print(json.dumps({"error": True, "status": 401, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    body = json.dumps(payload).encode()
    try:
        req = urllib.request.Request(f"{BASE_URL}/labs/posts", data=body, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": True, "status": e.code, "message": e.read().decode()}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)

    post = data.get("data", data) if isinstance(data, dict) else data
    slug = post.get("slug", "") if isinstance(post, dict) else ""
    print(json.dumps({
        "slug": slug,
        "title": post.get("title") if isinstance(post, dict) else None,
        "link": f"https://app.cesto.co/labs/{slug}",
        "raw": post,
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
