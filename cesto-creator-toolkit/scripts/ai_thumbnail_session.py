#!/usr/bin/env python3
"""
Poll an AI-thumbnail session for status, previews, and the final upscaled URL.

GET /thumbnails/ai/:sessionId

With --wait, polls every 5s up to 3 minutes for the grid to become "ready",
emitting a brief progress message to stderr every 15s. Without --wait, returns
the current session view once and exits.

Usage:
  python3 ai_thumbnail_session.py --session-id <id>           # one-shot
  python3 ai_thumbnail_session.py --session-id <id> --wait    # poll until ready (or timeout)
  python3 ai_thumbnail_session.py --session-id <id> --wait --wait-for upscale
      # poll until upscaleStatus="ready" instead of gridStatus

Output:
  {
    "sessionId": "...",
    "gridStatus": "pending|ready|failed",
    "previews": [{"index": 1, "url": "...", "downloadUrl": "..."}, ...],
    "upscaleStatus": "idle|pending|ready|failed",
    "selectedIndex": 1|2|3|4|null,
    "finalUrl": "...",
    "provider": "midjourney|gemini",
    "fellBack": false,
    "error": null
  }
"""

import json
import sys
import time
import urllib.error
import urllib.request

sys.dont_write_bytecode = True

from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 180
PROGRESS_EVERY_SECONDS = 15


def _fetch(session_id, token):
    req = urllib.request.Request(f"{BASE_URL}/thumbnails/ai/{session_id}")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
        except Exception:
            err = {"message": body}
        return None, {"status": e.code, **err}
    except Exception as e:
        return None, {"message": str(e)}


def main():
    args = sys.argv[1:]
    session_id = None
    wait = False
    wait_for = "grid"  # "grid" or "upscale"
    i = 0
    while i < len(args):
        if args[i] == "--session-id" and i + 1 < len(args):
            session_id = args[i + 1]; i += 2
        elif args[i] == "--wait":
            wait = True; i += 1
        elif args[i] == "--wait-for" and i + 1 < len(args):
            wait_for = args[i + 1]; i += 2
        else:
            i += 1

    if not session_id:
        print(json.dumps({"error": True, "message": "Missing --session-id"}))
        sys.exit(1)
    if wait_for not in ("grid", "upscale"):
        print(json.dumps({"error": True, "message": "--wait-for must be 'grid' or 'upscale'"}))
        sys.exit(1)

    session = read_session()
    if session is None:
        print(json.dumps({"error": True, "message": "No valid session found. Please log in first."}))
        sys.exit(1)
    token = session[ACCESS_KEY]

    if not wait:
        data, err = _fetch(session_id, token)
        if err:
            print(json.dumps({"error": True, **err}))
            sys.exit(1)
        print(json.dumps(data))
        return

    # Poll loop.
    started = time.time()
    last_progress = started
    while True:
        data, err = _fetch(session_id, token)
        if err:
            print(json.dumps({"error": True, **err}))
            sys.exit(1)

        status_field = "gridStatus" if wait_for == "grid" else "upscaleStatus"
        status = data.get(status_field)

        if status == "ready":
            print(json.dumps(data))
            return
        if status == "failed":
            error_msg = data.get("error") or f"{wait_for} generation failed"
            print(json.dumps({"error": True, "message": error_msg, "session": data}))
            sys.exit(1)

        elapsed = time.time() - started
        if elapsed > POLL_TIMEOUT_SECONDS:
            print(json.dumps({
                "error": True,
                "message": f"Timed out after {POLL_TIMEOUT_SECONDS}s waiting for {wait_for}=ready",
                "session": data,
            }))
            sys.exit(1)

        if time.time() - last_progress >= PROGRESS_EVERY_SECONDS:
            sys.stderr.write(f"[{int(elapsed)}s] {wait_for}={status}, waiting...\n")
            sys.stderr.flush()
            last_progress = time.time()

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
