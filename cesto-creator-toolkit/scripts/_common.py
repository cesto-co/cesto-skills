"""Shared helpers for cesto-creator-toolkit scripts.

Imported the same way as _store (the script's own directory is on sys.path when
run as `python3 <script>.py`). Self-contained (its own HTTP call) so it doesn't
depend on each script's local _http helper, whose signatures differ.
"""

import json
import urllib.error
import urllib.request


def resolve_product_uuid(base_url, identifier, token, timeout=15):
    """Accept either a UUID or a slug and resolve to the canonical product UUID.

    Returns (product_uuid, None) on success or (None, error_dict) on failure, so a
    caller can surface a clean error instead of 404-ing on a slug. Used by the
    mutating scripts (update_basket, update_version_metadata, rebalance_basket).
    """
    # UUIDs are 36 chars with 4 dashes; slugs aren't. Cheap heuristic.
    if len(identifier) == 36 and identifier.count("-") == 4:
        return identifier, None

    req = urllib.request.Request(f"{base_url}/products/{identifier}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        detail = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
        except Exception:
            err = {"message": body}
        return None, {"status": e.code, **err}
    except Exception as e:
        return None, {"message": str(e)}

    pid = (detail or {}).get("id") if isinstance(detail, dict) else None
    if not pid:
        return None, {"message": f"No basket found for '{identifier}'."}
    return pid, None
