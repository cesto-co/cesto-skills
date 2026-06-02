#!/usr/bin/env python3
"""
Fetch a default AI-thumbnail prompt template to pre-fill before generation.

GET /thumbnails/ai/prompt-template?provider=...&title=...&description=...

Different prose per provider:
  - Midjourney: uses only the title.
  - Gemini: weaves the description into the prose.

Usage:
  python3 ai_thumbnail_prompt.py --provider midjourney --title "Football Glory"
  python3 ai_thumbnail_prompt.py --provider gemini --title "Football Glory" --description "..."

Output:
  { "prompt": "..." }   — the suggested prompt; user can edit before sending to grid.
"""

import sys
sys.dont_write_bytecode = True
import json
import urllib.error
import urllib.parse
import urllib.request

from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"


def main():
    args = sys.argv[1:]
    provider = title = description = None
    i = 0
    while i < len(args):
        if args[i] == "--provider" and i + 1 < len(args):
            provider = args[i + 1]; i += 2
        elif args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]; i += 2
        elif args[i] == "--description" and i + 1 < len(args):
            description = args[i + 1]; i += 2
        else:
            i += 1

    if not provider or provider not in ("midjourney", "gemini"):
        print(json.dumps({"error": True, "message": "Missing or invalid --provider (midjourney|gemini)"}))
        sys.exit(1)
    if not title:
        print(json.dumps({"error": True, "message": "Missing --title"}))
        sys.exit(1)

    session = read_session()
    if session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    qs = {"provider": provider, "title": title}
    if description:
        qs["description"] = description
    url = f"{BASE_URL}/thumbnails/ai/prompt-template?{urllib.parse.urlencode(qs)}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        print(json.dumps(json.loads(resp.read().decode())))
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
        except Exception:
            err = {"message": body}
        print(json.dumps({"error": True, "status": e.code, **err}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
