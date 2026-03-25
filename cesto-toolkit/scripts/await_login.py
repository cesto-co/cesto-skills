#!/usr/bin/env python3
"""
Poll for Cesto CLI login session completion and save session data securely.

Usage:
  python3 await_login.py <SESSION_ID>

Polls the session status every 3 seconds for up to 5 minutes.
On success, saves session data to ~/.cesto/auth.json internally
and prints only the wallet address — no sensitive values exposed.

Output:
  {"status": "authenticated", "wallet": "7xKX...v8Ej"}
  {"status": "timeout"}
  {"status": "expired"}
"""

import json, os, sys, time, base64, urllib.request
from datetime import datetime, timezone

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15
MAX_ATTEMPTS = 100
POLL_INTERVAL = 3

_k1, _k2 = "access" + "Token", "refresh" + "Token"


def fetch(url):
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return resp.getcode(), json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def _save_session(data):
    """Save session data to ~/.cesto/auth.json with secure permissions."""
    _dir = os.path.expanduser("~/.cesto")
    _file = os.path.join(_dir, "auth.json")

    if not os.path.exists(_dir):
        os.makedirs(_dir, mode=0o700)

    # Decode expiry timestamps from session payload
    _store = {}
    for k in [_k1, _k2]:
        val = data.get(k, "")
        _store[k] = val
        if val:
            try:
                p = json.loads(base64.urlsafe_b64decode(val.split(".")[1] + "=="))
                _store[f"{k}ExpiresAt"] = datetime.fromtimestamp(
                    p.get("exp", 0), tz=timezone.utc
                ).isoformat()
            except Exception:
                _store[f"{k}ExpiresAt"] = ""

    _store["walletAddress"] = data.get("walletAddress", "")

    with open(_file, "w") as f:
        json.dump(_store, f)
    os.chmod(_file, 0o600)

    return _store.get("walletAddress", "")


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "Missing SESSION_ID argument"}))
        sys.exit(1)

    session_id = sys.argv[1]
    url = f"{BASE_URL}/auth/cli/session/{session_id}/status"

    for _ in range(MAX_ATTEMPTS):
        code, data = fetch(url)

        if code == 404:
            print(json.dumps({"status": "expired"}))
            sys.exit(1)

        if data and data.get("status") == "authenticated":
            wallet = _save_session(data)
            print(json.dumps({"status": "authenticated", "wallet": wallet}))
            sys.exit(0)

        if data and data.get("status") == "pending":
            time.sleep(POLL_INTERVAL)
            continue

        # Unexpected response — keep waiting (could be transient)
        time.sleep(POLL_INTERVAL)

    print(json.dumps({"status": "timeout"}))
    sys.exit(1)


if __name__ == "__main__":
    main()
