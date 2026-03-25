#!/usr/bin/env python3
"""
Poll for Cesto CLI login session completion and save tokens securely.

Usage:
  python3 poll_login.py <SESSION_ID>

Polls the session status every 3 seconds for up to 5 minutes.
On successful auth, saves tokens to ~/.cesto/auth.json internally
and prints only the wallet address — never raw tokens.

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


def fetch(url):
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return resp.getcode(), json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def save_tokens(data):
    """Save tokens to ~/.cesto/auth.json with secure permissions."""
    auth_dir = os.path.expanduser("~/.cesto")
    auth_path = os.path.join(auth_dir, "auth.json")

    # Create directory if needed
    if not os.path.exists(auth_dir):
        os.makedirs(auth_dir, mode=0o700)

    # Decode JWT expiry timestamps
    auth = {}
    for key in ["accessToken", "refreshToken"]:
        token = data.get(key, "")
        auth[key] = token
        if token:
            try:
                payload = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
                auth[f"{key}ExpiresAt"] = datetime.fromtimestamp(
                    payload.get("exp", 0), tz=timezone.utc
                ).isoformat()
            except Exception:
                auth[f"{key}ExpiresAt"] = ""

    auth["walletAddress"] = data.get("walletAddress", "")

    # Write with secure permissions
    with open(auth_path, "w") as f:
        json.dump(auth, f)
    os.chmod(auth_path, 0o600)

    return auth.get("walletAddress", "")


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
            wallet = save_tokens(data)
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
