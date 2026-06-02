#!/usr/bin/env python3
"""
Start a 2x2 AI-thumbnail grid generation.

POST /thumbnails/ai/grid
Body: { title, description, provider: "midjourney"|"gemini", prompt }

The backend kicks off image generation in the background. This call returns
immediately with a sessionId; poll ai_thumbnail_session.py to watch progress
and pick up the 4 preview URLs once gridStatus="ready".

Provider notes:
  - Midjourney: 30-90s typical, returns low-res previews; need upscale for full-res.
  - Gemini: faster, returns full-res previews directly (no upscale needed for download).
  - The backend auto-falls-back to the other provider if the primary fails — check
    the session's `provider` and `fellBack` fields after generation.

Reads JSON from stdin OR accepts --title/--description/--provider/--prompt flags.

Usage:
  echo '{"title":"Football Glory","description":"...","provider":"midjourney","prompt":"..."}' \
    | python3 ai_thumbnail_grid.py

  python3 ai_thumbnail_grid.py --title "..." --description "..." --provider midjourney --prompt "..."

Output:
  { "sessionId": "..." }
"""

import sys
sys.dont_write_bytecode = True
import json
import urllib.error
import urllib.request

from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"


def _parse_args():
    args = sys.argv[1:]
    out = {}
    i = 0
    while i < len(args):
        flag = args[i]
        if flag in ("--title", "--description", "--provider", "--prompt") and i + 1 < len(args):
            out[flag[2:]] = args[i + 1]
            i += 2
        else:
            i += 1
    return out


def main():
    # CLI flags take precedence; fall back to stdin JSON when flags absent.
    payload = _parse_args()
    if not all(k in payload for k in ("title", "description", "provider", "prompt")):
        stdin_text = sys.stdin.read().strip()
        if stdin_text:
            try:
                stdin_payload = json.loads(stdin_text)
                for k, v in stdin_payload.items():
                    payload.setdefault(k, v)
            except json.JSONDecodeError as e:
                print(json.dumps({"error": True, "message": f"Invalid JSON on stdin: {e}"}))
                sys.exit(1)

    missing = [k for k in ("title", "description", "provider", "prompt") if k not in payload]
    if missing:
        print(json.dumps({"error": True, "message": f"Missing required fields: {missing}"}))
        sys.exit(1)
    if payload["provider"] not in ("midjourney", "gemini"):
        print(json.dumps({"error": True, "message": "provider must be 'midjourney' or 'gemini'"}))
        sys.exit(1)

    session = read_session()
    if session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    body = json.dumps({
        "title": payload["title"],
        "description": payload["description"],
        "provider": payload["provider"],
        "prompt": payload["prompt"],
    }).encode()

    req = urllib.request.Request(f"{BASE_URL}/thumbnails/ai/grid", data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        print(json.dumps(json.loads(resp.read().decode())))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            err = json.loads(body_text)
        except Exception:
            err = {"message": body_text}
        print(json.dumps({"error": True, "status": e.code, **err}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
