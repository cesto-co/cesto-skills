#!/usr/bin/env python3
"""
Validate that allocation percentages sum to exactly 100.

The backend does NOT enforce this rule — a malformed basket with percentages
summing to 99 or 101 persists silently. Always pipe your definition through
this helper before submitting to the API.

Reads JSON from stdin. Accepts any of:
  1. {"allocations": [{"percentage": 60}, {"percentage": 40}]}
  2. [{"percentage": 60}, {"percentage": 40}]  (raw array)
  3. {"bucket": {"nodes": [{"amount": {"percentage": 60}}, ...]}}  (bucket model)

Outputs:
  {"valid": true,  "sum": 100}
  {"valid": false, "sum": 99, "message": "Allocations sum to 99, must equal 100."}

Also warns (via "warnings" key) if any percentage is non-integer — the skill
uses integer percentages and fractional values may indicate a typo.

Exit codes:
  0 — valid (sum == 100)
  1 — invalid (sum != 100) or JSON parse error
"""

import sys
sys.dont_write_bytecode = True
import json


def _extract_percentages(data):
    """
    Walk the data structure and return a list of percentage values.
    Returns (percentages: list, error: str|None).
    """
    # Raw array of allocation objects.
    if isinstance(data, list):
        return [item.get("percentage") for item in data if isinstance(item, dict) and "percentage" in item], None

    if not isinstance(data, dict):
        return [], "Input must be a JSON object or array."

    # Bucket model: {"bucket": {"nodes": [{"amount": {"percentage": N}}, ...]}}
    if "bucket" in data:
        bucket = data["bucket"]
        if not isinstance(bucket, dict):
            return [], "Expected 'bucket' to be an object."
        nodes = bucket.get("nodes", [])
        if not isinstance(nodes, list):
            return [], "Expected 'bucket.nodes' to be an array."
        percentages = []
        for node in nodes:
            if isinstance(node, dict):
                amount = node.get("amount")
                if isinstance(amount, dict) and "percentage" in amount:
                    percentages.append(amount["percentage"])
        return percentages, None

    # Wrapper with "allocations" key.
    if "allocations" in data:
        allocations = data["allocations"]
        if not isinstance(allocations, list):
            return [], "Expected 'allocations' to be an array."
        return [item.get("percentage") for item in allocations if isinstance(item, dict) and "percentage" in item], None

    # Nested: definition → bucket model.
    if "definition" in data:
        return _extract_percentages(data["definition"])

    # Workflow wrapper.
    if "workflow" in data and isinstance(data["workflow"], dict):
        wf = data["workflow"]
        if "definition" in wf:
            return _extract_percentages(wf["definition"])

    return [], "Could not find allocations. Expected 'allocations', a raw array, or a bucket model with 'bucket.nodes[].amount.percentage'."


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw, strict=False)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": True, "message": f"Invalid JSON input: {e}"}))
        sys.exit(1)

    percentages, err = _extract_percentages(data)

    if err:
        print(json.dumps({"error": True, "message": err}))
        sys.exit(1)

    if not percentages:
        print(json.dumps({"error": True, "message": "No percentage values found. Nothing to validate."}))
        sys.exit(1)

    # Sum using integer arithmetic where possible to avoid float drift.
    total = sum(percentages)

    warnings = []
    for p in percentages:
        if not isinstance(p, int):
            warnings.append(f"Non-integer percentage detected: {p}. The skill uses integer percentages only.")

    result = {}

    if warnings:
        result["warnings"] = warnings

    if total == 100:
        result.update({"valid": True, "sum": total})
        print(json.dumps(result))
        sys.exit(0)
    else:
        result.update({
            "valid": False,
            "sum": total,
            "message": f"Allocations sum to {total}, must equal 100.",
        })
        print(json.dumps(result))
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
