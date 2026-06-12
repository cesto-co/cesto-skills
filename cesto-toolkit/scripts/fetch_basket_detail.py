#!/usr/bin/env python3
"""
Deep dive into a single basket — fetches detail, token analysis, and graph data
in one call.

Usage:
  python3 fetch_basket_detail.py <slug-or-name> [--include=detail,tokens,graph]

Arguments:
  slug-or-name  Basket slug (e.g., "defense-mode") or partial name for fuzzy match
  --include     Comma-separated sections to fetch. Default: detail,tokens,graph (all)
                Options: detail, tokens, graph

Examples:
  python3 fetch_basket_detail.py war-mode
  python3 fetch_basket_detail.py "defense" --include=tokens
  python3 fetch_basket_detail.py made-in-america --include=detail,graph
"""

import json, os, sys, urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))

BASE_URL = "https://backend.cesto.co"
TIMEOUT = 15


def _get_token():
    """Best-effort: read the caller's bearer token if a session exists."""
    try:
        from _store import read_session, ACCESS_KEY
        session = read_session()
        if session:
            return session.get(ACCESS_KEY)
    except Exception:
        return None
    return None


def fetch(path, authed=False):
    """GET a path. If authed=True, attach the bearer token when a session exists
    (lets an owner view their OWN draft). Falls back to anonymous behaviour."""
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}")
        if authed:
            token = _get_token()
            if token:
                req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return json.loads(resp.read().decode())
    except Exception:
        return None


def build_token_mint_map():
    """Fetch /tokens and return a dict keyed by mint address -> token info."""
    tokens = fetch("/tokens")
    if not tokens or not isinstance(tokens, list):
        return {}
    return {t["mint"]: t for t in tokens if "mint" in t}


def safe_num(val, default=None):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def find_basket(query):
    """Find basket by slug or fuzzy name match.

    Searches published+active products, plus the caller's OWN drafts when a
    session exists (best-effort GET /products?mine=true). Exact slug/name
    match wins immediately. If MORE THAN ONE candidate matches partially by
    name, returns a disambiguation marker instead of guessing:
      ({"_ambiguous": True, "matches": [{name, slug}, ...]}, products)
    """
    products = fetch("/products")
    if not products:
        return None, None

    # Filter to published+active only so we don't accidentally resolve someone else's draft
    candidates = [p for p in products if p.get("isPublished") and p.get("isActive")]

    # Best-effort: merge in the caller's own drafts (auth optional).
    own = fetch("/products?mine=true", authed=True)
    if own and isinstance(own, list):
        seen_ids = {p.get("id") for p in candidates}
        for op in own:
            if op.get("id") not in seen_ids:
                candidates.append(op)
                seen_ids.add(op.get("id"))

    query_lower = query.lower().strip()

    # Try exact slug match first
    for p in candidates:
        if p.get("slug", "").lower() == query_lower:
            return p, products

    # Try exact name match
    for p in candidates:
        if p.get("name", "").lower() == query_lower:
            return p, products

    # Partial name matches — disambiguate if more than one
    name_matches = [p for p in candidates if query_lower in p.get("name", "").lower()]
    if len(name_matches) == 1:
        return name_matches[0], products
    if len(name_matches) > 1:
        return {
            "_ambiguous": True,
            "matches": [{"name": p.get("name"), "slug": p.get("slug")} for p in name_matches],
        }, products

    # Partial slug match (fallback)
    for p in candidates:
        if query_lower in p.get("slug", "").lower():
            return p, products

    return None, products


def parse_args():
    slug_or_name = None
    include = {"detail", "tokens", "graph"}

    for arg in sys.argv[1:]:
        if arg.startswith("--include="):
            include = set(arg.split("=", 1)[1].split(","))
        elif not slug_or_name:
            slug_or_name = arg

    return slug_or_name, include


def main():
    slug_or_name, include = parse_args()

    if not slug_or_name:
        print(json.dumps({"error": True, "message": "Please provide a basket slug or name"}))
        sys.exit(1)

    basket_list_item, all_products = find_basket(slug_or_name)

    # Multiple partial-name matches — ask the caller to disambiguate.
    if isinstance(basket_list_item, dict) and basket_list_item.get("_ambiguous"):
        print(json.dumps({
            "error": True,
            "message": f"Multiple baskets match '{slug_or_name}'",
            "matches": basket_list_item["matches"],
        }))
        sys.exit(1)

    if not basket_list_item:
        available = [{"name": p.get("name"), "slug": p.get("slug")} for p in (all_products or [])]
        print(json.dumps({
            "error": True,
            "message": f"No basket found matching '{slug_or_name}'",
            "availableBaskets": available
        }))
        sys.exit(1)

    slug = basket_list_item.get("slug", "")
    basket_id = basket_list_item.get("id", "")
    result = {}

    # Fetch detail via /products/{slug}
    if "detail" in include:
        # Authed so an owner can view their OWN draft (drafts 404 for anonymous).
        detail = fetch(f"/products/{slug}", authed=True)
        if detail:
            min_inv_raw = safe_num(detail.get("minimumInvestment"), 0)

            # Parse allocations from definition.bucket.nodes (bucket model)
            defn = detail.get("definition") or {}
            bucket = defn.get("bucket", {}) if isinstance(defn, dict) else {}
            nodes = bucket.get("nodes", []) if isinstance(bucket, dict) else []

            # Build a mint->token-info lookup (lazy: only fetch if needed)
            _mint_map = None

            def get_mint_map():
                nonlocal _mint_map
                if _mint_map is None:
                    _mint_map = build_token_mint_map()
                return _mint_map

            allocations = []
            for node in nodes:
                node_id = node.get("id", "")
                node_type = node.get("nodeType", "")
                amount_obj = node.get("amount") or {}
                params = node.get("parameters") or {}

                # Percentage lives in node.amount.percentage (real number, e.g. 22)
                pct = safe_num(amount_obj.get("percentage"))

                # Determine a human-readable token label
                token_label = ""
                mint = ""
                description = node.get("description", "")

                if node_type == "swap.token":
                    # toToken is the output mint; look it up in /tokens for the name
                    mint = params.get("toToken", "")
                    if mint:
                        tok = get_mint_map().get(mint)
                        if tok:
                            # Use the friendly name (e.g. "RTX") over the on-chain symbol
                            token_label = tok.get("name") or tok.get("symbol") or ""
                    # Fall back to node id (e.g. "swap-to-rtx" → "rtx")
                    if not token_label and node_id:
                        token_label = node_id.replace("swap-to-", "").replace("swap-", "").upper()

                elif node_type.startswith("prediction."):
                    # Prediction markets: use the market title as the label
                    token_label = params.get("title", "") or node.get("label", "") or node_id
                    if not description:
                        description = params.get("eventTitle", "")

                else:
                    # Unknown node type — use label or id
                    token_label = node.get("label", "") or node_id

                allocations.append({
                    "token": token_label,
                    "nodeId": node_id,
                    "percentage": pct,
                    "mint": mint,
                    "description": description,
                })

            # Performance from detail response
            tp = detail.get("tokenPerformance") or {}
            tp7 = detail.get("tokenPerformance7d") or {}
            tp30 = detail.get("tokenPerformance30d") or {}

            result["basket"] = {
                "id": basket_id,
                "name": detail.get("name", ""),
                "slug": slug,
                "category": detail.get("category", ""),
                "description": detail.get("description", ""),
                "riskLevel": detail.get("riskLevel", ""),
                "minInvestmentUSDC": min_inv_raw / 1_000_000 if min_inv_raw else 0,
                "strategy": detail.get("about", ""),
                "allocations": allocations,
                "performance": {
                    "return1y": safe_num(tp.get("netPnL", tp.get("annualizedReturn", tp.get("avgPercentChange")))),
                    "return7d": safe_num(tp7.get("return", tp7.get("avgPercentChange")) if tp7 else None),
                    "return30d": safe_num(tp30.get("return", tp30.get("avgPercentChange")) if tp30 else None),
                    "annualizedReturn": safe_num(tp.get("annualizedReturn")),
                },
            }
        else:
            result["basket"] = None

    # Fetch token analysis via /products/{id}/analyze
    if "tokens" in include and basket_id:
        analyze_data = fetch(f"/products/{basket_id}/analyze")
        if analyze_data and isinstance(analyze_data, dict):
            node_analyses = analyze_data.get("nodeAnalyses", [])
            result["tokens"] = []
            for na in node_analyses:
                md = na.get("marketData") or {}
                tp = md.get("tokenPerformance") or {}
                result["tokens"].append({
                    "nodeId": na.get("id", ""),
                    "inputSymbol": na.get("inputSymbol", ""),
                    "outputSymbol": na.get("outputSymbol", ""),
                    "protocol": na.get("protocol", ""),
                    "currentPrice": safe_num(tp.get("currentPrice")),
                    "priceChange24h": safe_num(tp.get("priceChange24h")),
                    "priceChange7d": safe_num(tp.get("priceChange7d")),
                    "priceChange30d": safe_num(tp.get("priceChange30d")),
                    "priceChange1y": safe_num(tp.get("priceChange1y")),
                })
        else:
            result["tokens"] = None

    # Fetch graph via /products/{id}/graph
    if "graph" in include and basket_id:
        graph_data = fetch(f"/products/{basket_id}/graph")
        if graph_data and isinstance(graph_data, dict):
            series = graph_data.get("timeSeries", [])
            metrics = graph_data.get("metrics") or {}

            if series:
                values = [(s.get("timestamp", ""), s.get("portfolioValue", 0)) for s in series if s.get("portfolioValue") is not None]
                sp500 = [s.get("sp500Value", 0) for s in series if s.get("sp500Value") is not None]

                start_val = values[0][1] if values else 0
                end_val = values[-1][1] if values else 0
                sp_start = sp500[0] if sp500 else 0
                sp_end = sp500[-1] if sp500 else 0

                best = max(values, key=lambda x: x[1]) if values else ("", 0)
                worst = min(values, key=lambda x: x[1]) if values else ("", 0)

                has_liquidations = any(s.get("isLiquidated", False) for s in series)

                result["graph"] = {
                    "startValue": start_val,
                    "endValue": round(end_val, 2),
                    "totalReturn": metrics.get("totalReturn", round((end_val - start_val) / start_val * 100, 2) if start_val else 0),
                    "sp500Return": round((sp_end - sp_start) / sp_start * 100, 2) if sp_start else 0,
                    "volatility": metrics.get("volatility"),
                    "maxDrawdown": metrics.get("maxDrawdown"),
                    "sharpe": metrics.get("sharpe"),
                    "bestDay": {"date": best[0], "value": round(best[1], 2)},
                    "worstDay": {"date": worst[0], "value": round(worst[1], 2)},
                    "hasLiquidations": has_liquidations,
                    "dataPoints": len(series),
                }
            else:
                result["graph"] = None
        else:
            result["graph"] = None

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _e:
        import json, sys
        print(json.dumps({"error": True, "message": f"Unexpected error: {_e}"}))
        sys.exit(1)
