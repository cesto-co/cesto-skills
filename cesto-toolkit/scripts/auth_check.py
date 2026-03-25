#!/usr/bin/env python3
"""
Check Cesto auth status without exposing token values.
Returns JSON with status and wallet address only.

Statuses:
  valid     — access token is still valid
  refreshed — access token was expired, successfully refreshed
  expired   — both tokens expired or file missing, login required
"""

import json, os, sys, base64, urllib.request
from datetime import datetime, timezone

auth_path = os.path.expanduser("~/.cesto/auth.json")

if not os.path.exists(auth_path):
    print(json.dumps({"status": "expired"}))
    sys.exit(0)

with open(auth_path) as f:
    auth = json.load(f)

now = datetime.now(timezone.utc)
access_exp = datetime.fromisoformat(auth["accessTokenExpiresAt"].replace("Z", "+00:00"))
refresh_exp = datetime.fromisoformat(auth["refreshTokenExpiresAt"].replace("Z", "+00:00"))
wallet = auth.get("walletAddress", "")

if now < access_exp:
    print(json.dumps({"status": "valid", "wallet": wallet}))
elif now < refresh_exp:
    req = urllib.request.Request(
        "https://backend.cesto.co/auth/refresh",
        data=json.dumps({"refreshToken": auth["refreshToken"]}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = json.loads(urllib.request.urlopen(req).read())
        for key in ["accessToken", "refreshToken"]:
            auth[key] = resp[key]
            payload = json.loads(base64.urlsafe_b64decode(resp[key].split(".")[1] + "=="))
            auth[f"{key}ExpiresAt"] = datetime.fromtimestamp(
                payload["exp"], tz=timezone.utc
            ).isoformat()
        with open(auth_path, "w") as f:
            json.dump(auth, f)
        print(json.dumps({"status": "refreshed", "wallet": wallet}))
    except Exception:
        print(json.dumps({"status": "expired"}))
else:
    print(json.dumps({"status": "expired"}))
