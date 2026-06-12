#!/usr/bin/env python3
"""
Convert a human-readable USDC amount to base units (smallest denomination).

USDC has 6 decimals: 10 USDC → "10000000". Missing or extra a zero is a
10x–1000x error with no server-side guardrail, so always use this helper
when building minimumInvestment payloads.

Usage:
  python3 to_base_units.py <amount> [--decimals=6]

Examples:
  python3 to_base_units.py 10        → {"amount": "10000000", "decimals": 6, "human": "10"}
  python3 to_base_units.py 12.5      → {"amount": "12500000", "decimals": 6, "human": "12.5"}
  python3 to_base_units.py 0.001     → {"amount": "1000", "decimals": 6, "human": "0.001"}
  python3 to_base_units.py -5        → error + non-zero exit
  python3 to_base_units.py 1.1234567 → error (more fractional digits than decimals allows)
"""

import sys
sys.dont_write_bytecode = True
import json
from decimal import Decimal, InvalidOperation, ROUND_DOWN


def _parse_decimals(args):
    """Extract --decimals=N or --decimals N from args. Default 6."""
    decimals = 6
    for i, arg in enumerate(args):
        if arg.startswith("--decimals="):
            try:
                decimals = int(arg.split("=", 1)[1])
            except ValueError:
                print(json.dumps({"error": True, "message": "Invalid --decimals value; must be a non-negative integer."}))
                sys.exit(1)
        elif arg == "--decimals" and i + 1 < len(args):
            try:
                decimals = int(args[i + 1])
            except ValueError:
                print(json.dumps({"error": True, "message": "Invalid --decimals value; must be a non-negative integer."}))
                sys.exit(1)
    if decimals < 0:
        print(json.dumps({"error": True, "message": "--decimals must be >= 0."}))
        sys.exit(1)
    return decimals


def _parse_amount(raw):
    """Parse amount string into a Decimal. Returns Decimal or raises."""
    return Decimal(raw)


def main():
    args = sys.argv[1:]

    # Filter out --decimals flags to isolate the positional amount argument.
    positional = [a for a in args if not a.startswith("--decimals")]

    if not positional:
        print(json.dumps({"error": True, "message": "Usage: python3 to_base_units.py <amount> [--decimals=6]"}))
        sys.exit(1)

    raw_amount = positional[0]
    decimals = _parse_decimals(args)

    # Parse with Decimal to avoid floating-point errors.
    try:
        amount = _parse_amount(raw_amount)
    except InvalidOperation:
        print(json.dumps({"error": True, "message": f"Invalid amount '{raw_amount}': must be a positive number (e.g. 10 or 12.5)."}))
        sys.exit(1)

    # Must be strictly positive.
    if amount <= 0:
        print(json.dumps({"error": True, "message": f"Amount must be a positive number greater than zero; got '{raw_amount}'."}))
        sys.exit(1)

    # Check that the input doesn't have more fractional digits than `decimals` allows.
    # sign, digits, exponent = amount.as_tuple()
    sign, digits_tuple, exponent = amount.as_tuple()
    # exponent is negative when there are fractional digits, e.g. 12.5 → exponent=-1.
    frac_digits = -exponent if exponent < 0 else 0
    if frac_digits > decimals:
        print(json.dumps({
            "error": True,
            "message": (
                f"Amount '{raw_amount}' has {frac_digits} fractional digit(s), "
                f"but {decimals} decimal(s) are allowed. "
                f"The smallest unit is {Decimal(10) ** -decimals} — you cannot express finer precision."
            ),
        }))
        sys.exit(1)

    # Multiply by 10^decimals using integer arithmetic to stay exact.
    multiplier = Decimal(10) ** decimals
    base_units = amount * multiplier

    # Quantize to integer (should already be exact, but be explicit).
    base_int = int(base_units.to_integral_value(rounding=ROUND_DOWN))

    print(json.dumps({
        "amount": str(base_int),
        "decimals": decimals,
        "human": raw_amount,
    }))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
