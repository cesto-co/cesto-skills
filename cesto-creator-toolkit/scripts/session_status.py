#!/usr/bin/env python3
"""
Check Cesto session status and verify the caller has CREATOR or ADMIN role.
Returns JSON with status, wallet address, and role — never sensitive values.

Both roles drive this skill identically; the mutating scripts apply an extra
ownership check (createdBy == /users/me.id) so admins are still constrained
to baskets they themselves created.

Statuses:
  valid        — session is active, role verified
  refreshed    — session was renewed, role verified
  expired      — session expired or file missing, login required
  unauthorized — session valid but user is not CREATOR or ADMIN
"""

import sys
sys.dont_write_bytecode = True
import json, base64, urllib.request
from datetime import datetime, timezone
from _store import read_session, write_session, ACCESS_KEY, REFRESH_KEY

BASE_URL = "https://backend.cesto.co"
ALLOWED_ROLES = ["CREATOR", "ADMIN"]


def _check_role(access_token):
    """Call /users/me and return role, or None on failure."""
    try:
        req = urllib.request.Request(f"{BASE_URL}/users/me")
        req.add_header("Authorization", f"Bearer {access_token}")
        resp = urllib.request.urlopen(req, timeout=15)
        user = json.loads(resp.read().decode())
        return user.get("role", ""), user.get("id", "")
    except Exception:
        return None, None


def main():
    _data = read_session()

    if _data is None:
        print(json.dumps({"status": "expired"}))
        return

    try:
        now = datetime.now(timezone.utc)
        _exp1 = datetime.fromisoformat(_data[f"{ACCESS_KEY}ExpiresAt"].replace("Z", "+00:00"))
        _exp2 = datetime.fromisoformat(_data[f"{REFRESH_KEY}ExpiresAt"].replace("Z", "+00:00"))
        wallet = _data.get("walletAddress", "")
        token = _data[ACCESS_KEY]
    except (KeyError, ValueError):
        print(json.dumps({"status": "expired"}))
        return

    if now < _exp1:
        role, user_id = _check_role(token)
        if role is None:
            print(json.dumps({"status": "expired"}))
        elif role in ALLOWED_ROLES:
            print(json.dumps({"status": "valid", "wallet": wallet, "role": role, "userId": user_id}))
        else:
            print(json.dumps({
                "status": "unauthorized", "wallet": wallet, "role": role,
                "message": f"CREATOR or ADMIN role required. Your role is {role}."
            }))
    elif now < _exp2:
        req = urllib.request.Request(
            f"{BASE_URL}/auth/refresh",
            data=json.dumps({REFRESH_KEY: _data[REFRESH_KEY]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = json.loads(urllib.request.urlopen(req).read())
            for k in [ACCESS_KEY, REFRESH_KEY]:
                _data[k] = resp[k]
                p = json.loads(base64.urlsafe_b64decode(resp[k].split(".")[1] + "=="))
                _data[f"{k}ExpiresAt"] = datetime.fromtimestamp(
                    p["exp"], tz=timezone.utc
                ).isoformat()
            write_session(_data)

            role, user_id = _check_role(_data[ACCESS_KEY])
            if role is None:
                print(json.dumps({"status": "expired"}))
            elif role in ALLOWED_ROLES:
                print(json.dumps({"status": "refreshed", "wallet": wallet, "role": role, "userId": user_id}))
            else:
                print(json.dumps({
                    "status": "unauthorized", "wallet": wallet, "role": role,
                    "message": f"CREATOR or ADMIN role required. Your role is {role}."
                }))
        except Exception:
            print(json.dumps({"status": "expired"}))
    else:
        print(json.dumps({"status": "expired"}))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
