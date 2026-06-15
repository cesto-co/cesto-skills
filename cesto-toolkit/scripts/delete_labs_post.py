#!/usr/bin/env python3
"""
Soft-delete a community Labs post you authored.

Requires an authenticated session (author only). Prints a clean JSON error
if no session exists.

Usage:
  python3 delete_labs_post.py <slug>

Output:
  {"ok": true, "slug": "...", "deleted": true}
"""

import json, os, sys, urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))

from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else None
    if not slug:
        print(json.dumps({"error": True, "message": "Usage: delete_labs_post.py <slug>"}))
        sys.exit(1)

    session = read_session()
    if not session or not session.get(ACCESS_KEY):
        print(json.dumps({"error": True, "status": 401, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    try:
        req = urllib.request.Request(f"{BASE_URL}/labs/posts/{slug}", method="DELETE")
        req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        raw = resp.read().decode()
        data = json.loads(raw, strict=False) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": True, "status": e.code, "message": e.read().decode()}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)

    print(json.dumps({"ok": True, "slug": slug, "deleted": True, "raw": data}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
