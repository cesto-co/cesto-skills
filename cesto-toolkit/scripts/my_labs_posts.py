#!/usr/bin/env python3
"""
List the caller's OWN community Labs posts.

Requires an authenticated session. Prints a clean JSON error if none exists.

Usage:
  python3 my_labs_posts.py [--limit=N] [--cursor=X]

Output:
  {"posts": [{slug, title, voteCount, pnlScore, ...}], "nextCursor": "..."}
"""

import json, os, sys, urllib.request, urllib.parse

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))

from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15


def parse_args():
    limit = None
    cursor = None
    for arg in sys.argv[1:]:
        if arg.startswith("--limit="):
            limit = arg.split("=", 1)[1]
        elif arg.startswith("--cursor="):
            cursor = arg.split("=", 1)[1]
    return limit, cursor


def main():
    session = read_session()
    if not session or not session.get(ACCESS_KEY):
        print(json.dumps({"error": True, "status": 401, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    limit, cursor = parse_args()
    params = {}
    if limit:
        params["limit"] = limit
    if cursor:
        params["cursor"] = cursor
    qs = ("?" + urllib.parse.urlencode(params)) if params else ""

    try:
        req = urllib.request.Request(f"{BASE_URL}/labs/posts/me{qs}")
        req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": True, "status": e.code, "message": e.read().decode()}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)

    items = data.get("data", []) if isinstance(data, dict) else []
    pagination = data.get("pagination", {}) if isinstance(data, dict) else {}

    posts = []
    for p in items:
        posts.append({
            "slug": p.get("slug", ""),
            "title": p.get("title", ""),
            "voteCount": p.get("voteCount", 0),
            "pnlScore": p.get("pnlScore"),
            "pnl7d": p.get("pnl7d"),
            "pnl30d": p.get("pnl30d"),
            "pnl1y": p.get("pnl1y"),
            "createdAt": p.get("createdAt", ""),
            "link": f"https://app.cesto.co/labs/{p.get('slug', '')}",
        })

    out = {"posts": posts, "count": len(posts)}
    if pagination.get("nextCursor"):
        out["nextCursor"] = pagination["nextCursor"]

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
