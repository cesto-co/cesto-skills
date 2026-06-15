#!/usr/bin/env python3
"""
Validate that a set of basket allocations sums to exactly 100%.

Reads JSON from stdin — either {"allocations": [...]} or a raw array [...].
Sums `percentage` across ALL legs (token + prediction). Allows a tiny
floating-point tolerance.

Usage:
  echo '{"allocations":[{"percentage":60},{"percentage":40}]}' | python3 validate_allocations.py
  echo '[{"percentage":50},{"percentage":50}]' | python3 validate_allocations.py

Output:
  {"valid": true, "sum": 100}                                  (exit 0)
  {"valid": false, "sum": X, "message": "..."}                 (exit 1)
"""

import json, sys

sys.dont_write_bytecode = True

TOLERANCE = 0.01


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw, strict=False)
    except Exception as e:
        print(json.dumps({"valid": False, "sum": None, "message": f"Invalid JSON on stdin: {e}"}))
        sys.exit(1)

    # Accept {"allocations": [...]}, a raw array, or a bucket-model definition
    # ({"bucket": {"nodes": [...]}} or {"definition": {"bucket": ...}}).
    allocations = None
    if isinstance(data, list):
        allocations = data
    elif isinstance(data, dict):
        if isinstance(data.get("allocations"), list):
            allocations = data["allocations"]
        else:
            bucket = data.get("bucket")
            if not isinstance(bucket, dict) and isinstance(data.get("definition"), dict):
                bucket = data["definition"].get("bucket")
            if isinstance(bucket, dict) and isinstance(bucket.get("nodes"), list):
                # Each node carries amount.percentage; treat that as the leg's percentage.
                allocations = [
                    n.get("amount", {}) for n in bucket["nodes"] if isinstance(n, dict)
                ]

    if not isinstance(allocations, list) or not allocations:
        print(json.dumps({"valid": False, "sum": 0, "message": "No allocations found. Provide {\"allocations\":[...]} or a JSON array."}))
        sys.exit(1)

    total = 0.0
    for a in allocations:
        if not isinstance(a, dict):
            print(json.dumps({"valid": False, "sum": None, "message": "Each allocation must be an object."}))
            sys.exit(1)
        pct = a.get("percentage")
        try:
            total += float(pct)
        except (ValueError, TypeError):
            print(json.dumps({"valid": False, "sum": None, "message": "Each allocation must have a numeric 'percentage'."}))
            sys.exit(1)

    # Round to drop trailing float noise for display
    total_display = round(total, 2)

    if abs(total - 100.0) <= TOLERANCE:
        print(json.dumps({"valid": True, "sum": total_display}))
        sys.exit(0)

    print(json.dumps({
        "valid": False,
        "sum": total_display,
        "message": f"Allocations sum to {total_display}, must equal 100.",
    }))
    sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
