#!/usr/bin/env python3
"""
View a single community Labs post (a user-created community basket) by slug,
including its allocations (token + prediction legs) and inline performance.

Public endpoint — works with no session. A session, if present, is sent
best-effort so the post includes the caller's `userVote`.

Usage:
  python3 fetch_labs_post.py <slug>

Output:
  Clean post object with token + prediction legs distinguished, inline
  tokenPerformance / tokenPerformance7d / tokenPerformance30d, and the
  frontend link https://app.cesto.co/labs/<slug>.
"""

import json, os, sys, urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15


def fetch_optional_auth(path):
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
    except urllib.error.HTTPError as e:
        return {"error": True, "status": e.code, "message": e.read().decode()}
    except Exception as e:
        return {"error": True, "message": str(e)}


def safe_num(val, default=None):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def format_allocation(a):
    kind = a.get("kind") or "token"
    if kind == "prediction":
        return {
            "kind": "prediction",
            "marketId": a.get("marketId", ""),
            "eventId": a.get("eventId", ""),
            "side": a.get("side", ""),
            "provider": a.get("provider", ""),
            "eventTitle": a.get("eventTitle", ""),
            "marketTitle": a.get("marketTitle", ""),
            "closeTime": a.get("closeTime"),
            "entryPriceCents": a.get("entryPriceCents"),
            "percentage": safe_num(a.get("percentage")),
            "description": a.get("description"),
        }
    return {
        "kind": "token",
        "mint": a.get("mint", ""),
        "symbol": a.get("symbol", ""),
        "name": a.get("name", ""),
        "logoUrl": a.get("logoUrl"),
        "percentage": safe_num(a.get("percentage")),
        "description": a.get("description"),
    }


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else None
    if not slug:
        print(json.dumps({"error": True, "message": "Please provide a Labs post slug"}))
        sys.exit(1)

    data = fetch_optional_auth(f"/labs/posts/{slug}")
    if isinstance(data, dict) and data.get("error"):
        print(json.dumps(data))
        sys.exit(1)

    post = data.get("data") if isinstance(data, dict) else None
    if not post:
        print(json.dumps({"error": True, "message": f"No Labs post found for slug '{slug}'"}))
        sys.exit(1)

    allocations = [format_allocation(a) for a in post.get("allocations", [])]
    token_legs = [a for a in allocations if a["kind"] == "token"]
    prediction_legs = [a for a in allocations if a["kind"] == "prediction"]

    out = {
        "slug": post.get("slug", ""),
        "title": post.get("title", ""),
        "description": post.get("description", ""),
        "thumbnailUrl": post.get("thumbnailUrl"),
        "author": post.get("authorUsername") or post.get("authorAddress") or "",
        "authorAddress": post.get("authorAddress", ""),
        "voteCount": post.get("voteCount", 0),
        "userVote": post.get("userVote"),
        "pnlScore": post.get("pnlScore"),
        "pnl7d": post.get("pnl7d"),
        "pnl30d": post.get("pnl30d"),
        "pnl1y": post.get("pnl1y"),
        "createdAt": post.get("createdAt", ""),
        "tokenLegs": token_legs,
        "predictionLegs": prediction_legs,
        "performance": {
            "tokenPerformance": post.get("tokenPerformance"),
            "tokenPerformance7d": post.get("tokenPerformance7d"),
            "tokenPerformance30d": post.get("tokenPerformance30d"),
        },
        "link": f"https://app.cesto.co/labs/{post.get('slug', '')}",
    }

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
