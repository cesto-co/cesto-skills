#!/usr/bin/env python3
"""
List community Labs posts (the baskets users create and share).

Public endpoint — works with no session. If a session exists it is sent
best-effort so each post gets a `userVote` field.

Usage:
  python3 fetch_labs_posts.py [--sort=new|trending|pnl] [--limit=N] [--cursor=X]

Sort options:
  new       - newest first (default)
  trending  - trending by recent votes
  pnl       - ranked by pnl score

Output:
  {"posts": [{slug, title, author, voteCount, userVote?, pnlScore, ...}],
   "nextCursor": "..."}
  Frontend link for each post: https://app.cesto.co/labs/<slug>
"""

import json, os, sys, urllib.request, urllib.parse

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15
ALLOWED_SORTS = {"new", "trending", "pnl"}


def fetch_optional_auth(path):
    """GET a path. Sends bearer token if a session exists (best-effort)."""
    token = None
    try:
        from _store import read_session, ACCESS_KEY
        session = read_session()
        if session:
            token = session.get(ACCESS_KEY)
    except Exception:
        token = None
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return json.loads(resp.read().decode())
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        return None


def parse_args():
    sort_by = "new"
    limit = None
    cursor = None
    for arg in sys.argv[1:]:
        if arg.startswith("--sort="):
            sort_by = arg.split("=", 1)[1]
        elif arg.startswith("--limit="):
            limit = arg.split("=", 1)[1]
        elif arg.startswith("--cursor="):
            cursor = arg.split("=", 1)[1]
    if sort_by not in ALLOWED_SORTS:
        sort_by = "new"
    return sort_by, limit, cursor


def main():
    sort_by, limit, cursor = parse_args()

    params = {"sort": sort_by}
    if limit:
        params["limit"] = limit
    if cursor:
        params["cursor"] = cursor

    data = fetch_optional_auth(f"/labs/posts?{urllib.parse.urlencode(params)}")
    if data is None:
        print(json.dumps({"error": True, "message": "Failed to fetch Labs posts"}))
        sys.exit(1)

    items = data.get("data", []) if isinstance(data, dict) else []
    pagination = data.get("pagination", {}) if isinstance(data, dict) else {}

    posts = []
    for p in items:
        posts.append({
            "slug": p.get("slug", ""),
            "title": p.get("title", ""),
            "author": p.get("authorUsername") or p.get("authorAddress") or "",
            "voteCount": p.get("voteCount", 0),
            "userVote": p.get("userVote"),
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
