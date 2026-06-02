#!/usr/bin/env python3
"""
Select one of the 4 generated quadrants as the final basket cover.

POST /thumbnails/ai/upscale
Body: { sessionId, index: 1-4 }

Starts an upscale of the chosen quadrant. Returns immediately with sessionId;
poll ai_thumbnail_session.py --wait --wait-for upscale to get the final URL.

After selecting, the session's `finalUrl` is the Cloudinary URL to use as
`product.logoUrl` in the create/update payload.

Usage:
  python3 ai_thumbnail_select.py --session-id <id> --index <1-4>

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


def main():
    args = sys.argv[1:]
    session_id = None
    index = None
    i = 0
    while i < len(args):
        if args[i] == "--session-id" and i + 1 < len(args):
            session_id = args[i + 1]; i += 2
        elif args[i] == "--index" and i + 1 < len(args):
            try:
                index = int(args[i + 1])
            except ValueError:
                index = None
            i += 2
        else:
            i += 1

    if not session_id:
        print(json.dumps({"error": True, "message": "Missing --session-id"}))
        sys.exit(1)
    if index not in (1, 2, 3, 4):
        print(json.dumps({"error": True, "message": "--index must be 1, 2, 3, or 4"}))
        sys.exit(1)

    session = read_session()
    if session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    body = json.dumps({"sessionId": session_id, "index": index}).encode()
    req = urllib.request.Request(f"{BASE_URL}/thumbnails/ai/upscale", data=body, method="POST")
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
