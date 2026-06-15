"""Shared helpers for cesto-toolkit scripts.

Imported the same way as _store (the script's own directory is on sys.path when
run as `python3 <script>.py`). Keep this module dependency-free beyond stdlib.
"""


def normalize_prediction_legs(allocations):
    """Derive mint/symbol/name for prediction-kind allocation legs.

    The LabsPostAllocation table requires mint/symbol/name (non-null, and mint is
    unique per post) even for prediction legs. The frontend synthesizes these from
    the prediction fields (see labs-allocation-mapper.ts); mirror that exactly so
    callers only need to supply marketId/eventId/side/provider/eventTitle/
    marketTitle. Caller-provided values are always respected. Mutates in place.
    """
    if not isinstance(allocations, list):
        return
    for a in allocations:
        if not isinstance(a, dict) or a.get("kind") != "prediction":
            continue
        provider = (a.get("provider") or "").strip()
        market_id = (a.get("marketId") or "").strip()
        side = (a.get("side") or "").strip()
        if not a.get("mint") and provider and market_id and side:
            a["mint"] = f"{provider}:{market_id}:{side}"[:100]
        if not a.get("symbol") and provider and side:
            prefix = "POLY" if provider == "polymarket" else "KAL"
            a["symbol"] = f"{prefix}-{side}"[:20]
        if not a.get("name"):
            a["name"] = (a.get("marketTitle") or a.get("eventTitle") or "Prediction")[:100]
