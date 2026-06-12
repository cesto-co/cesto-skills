#!/usr/bin/env python3
"""
Show the community Labs leaderboard (top creators by votes).

Public endpoint — works with no session. Cursor pagination.

Usage:
  python3 labs_leaderboard.py [--limit=N] [--cursor=X]

Output:
  {"leaderboard": [{rank, username, address, votes}], "nextCursor": "..."}
"""

import json, sys, urllib.request, urllib.parse

sys.dont_write_bytecode = True

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
    limit, cursor = parse_args()
    params = {}
    if limit:
        params["limit"] = limit
    if cursor:
        params["cursor"] = cursor
    qs = ("?" + urllib.parse.urlencode(params)) if params else ""

    try:
        req = urllib.request.Request(f"{BASE_URL}/labs/leaderboard{qs}")
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

    rows = []
    for r in items:
        rows.append({
            "rank": r.get("rank"),
            "username": r.get("username") or r.get("address") or "",
            "address": r.get("address", ""),
            "votes": r.get("votes", 0),
        })

    out = {"leaderboard": rows, "count": len(rows)}
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
