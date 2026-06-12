#!/usr/bin/env python3
"""
Upvote or downvote a community Labs post. Re-voting toggles/switches.

Requires an authenticated session. Prints a clean JSON error if none exists.

Usage:
  python3 vote_labs_post.py <slug> up
  python3 vote_labs_post.py <slug> down

Output:
  The updated vote state returned by the API.
"""

import json, os, sys, urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))

from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else None
    direction = sys.argv[2].lower() if len(sys.argv) > 2 else None

    if not slug or direction not in ("up", "down"):
        print(json.dumps({"error": True, "message": "Usage: vote_labs_post.py <slug> <up|down>"}))
        sys.exit(1)

    session = read_session()
    if not session or not session.get(ACCESS_KEY):
        print(json.dumps({"error": True, "status": 401, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    vote_type = 1 if direction == "up" else -1
    body = json.dumps({"voteType": vote_type}).encode()

    try:
        req = urllib.request.Request(f"{BASE_URL}/labs/posts/{slug}/vote", data=body, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        raw = resp.read().decode()
        data = json.loads(raw, strict=False) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": True, "status": e.code, "message": e.read().decode()}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)

    result = data.get("data", data) if isinstance(data, dict) else data
    print(json.dumps({"ok": True, "slug": slug, "voteType": vote_type, "result": result}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
