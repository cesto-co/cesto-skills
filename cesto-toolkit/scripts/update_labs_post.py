#!/usr/bin/env python3
"""
Update a community Labs post you authored (partial update).

Requires an authenticated session (author only). Reads a partial JSON
payload from stdin and PUTs it to /labs/posts/:slug. Same fields as create:
title, description, thumbnailUrl|aiGenerateThumbnail, allocations[].

Usage:
  echo '{"title":"New title"}' | python3 update_labs_post.py <slug>

Output:
  Normalized {slug, title, link, raw} of the updated post.
"""

import json, os, sys, urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))

from _store import read_session, ACCESS_KEY
from _common import normalize_prediction_legs

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 20
TOLERANCE = 0.01


def validate_allocations(allocations):
    """If allocations are being changed, they must still sum to 100."""
    total = 0.0
    for a in allocations:
        try:
            total += float(a.get("percentage"))
        except (ValueError, TypeError):
            return False, None, "Each allocation must have a numeric 'percentage'."
    total = round(total, 2)
    if abs(total - 100.0) <= TOLERANCE:
        return True, total, None
    return False, total, f"Allocations sum to {total}, must equal 100."


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else None
    if not slug:
        print(json.dumps({"error": True, "message": "Usage: update_labs_post.py <slug>  (payload on stdin)"}))
        sys.exit(1)

    raw_input = sys.stdin.read()
    try:
        payload = json.loads(raw_input, strict=False)
    except Exception as e:
        print(json.dumps({"error": True, "message": f"Invalid JSON payload on stdin: {e}"}))
        sys.exit(1)

    if not isinstance(payload, dict) or not payload:
        print(json.dumps({"error": True, "message": "Payload must be a non-empty JSON object of fields to update."}))
        sys.exit(1)

    # If allocations are being changed, derive prediction-leg fields and re-check the 100% sum.
    if isinstance(payload.get("allocations"), list):
        normalize_prediction_legs(payload["allocations"])
        valid, total, msg = validate_allocations(payload["allocations"])
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
        req = urllib.request.Request(f"{BASE_URL}/labs/posts/{slug}", data=body, method="PUT")
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
    new_slug = post.get("slug", slug) if isinstance(post, dict) else slug
    print(json.dumps({
        "ok": True,
        "slug": new_slug,
        "title": post.get("title") if isinstance(post, dict) else None,
        "link": f"https://app.cesto.co/labs/{new_slug}",
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
