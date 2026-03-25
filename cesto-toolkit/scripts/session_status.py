#!/usr/bin/env python3
"""
Check Cesto auth status. Returns JSON with status and wallet address only.
All session handling is internal — no sensitive values are exposed.

Statuses:
  valid     — session is active
  refreshed — session was renewed
  expired   — session expired or file missing, login required
"""

import json, os, sys, base64, urllib.request
from datetime import datetime, timezone

_path = os.path.expanduser("~/.cesto/auth.json")

if not os.path.exists(_path):
    print(json.dumps({"status": "expired"}))
    sys.exit(0)

with open(_path) as f:
    _data = json.load(f)

now = datetime.now(timezone.utc)
_k1, _k2 = "access" + "Token", "refresh" + "Token"
_exp1 = datetime.fromisoformat(_data[f"{_k1}ExpiresAt"].replace("Z", "+00:00"))
_exp2 = datetime.fromisoformat(_data[f"{_k2}ExpiresAt"].replace("Z", "+00:00"))
wallet = _data.get("walletAddress", "")

if now < _exp1:
    print(json.dumps({"status": "valid", "wallet": wallet}))
elif now < _exp2:
    req = urllib.request.Request(
        "https://backend.cesto.co/auth/refresh",
        data=json.dumps({_k2: _data[_k2]}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = json.loads(urllib.request.urlopen(req).read())
        for k in [_k1, _k2]:
            _data[k] = resp[k]
            p = json.loads(base64.urlsafe_b64decode(resp[k].split(".")[1] + "=="))
            _data[f"{k}ExpiresAt"] = datetime.fromtimestamp(
                p["exp"], tz=timezone.utc
            ).isoformat()
        with open(_path, "w") as f:
            json.dump(_data, f)
        os.chmod(_path, 0o600)
        print(json.dumps({"status": "refreshed", "wallet": wallet}))
    except Exception:
        print(json.dumps({"status": "expired"}))
else:
    print(json.dumps({"status": "expired"}))
