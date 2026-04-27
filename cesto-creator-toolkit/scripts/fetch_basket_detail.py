#!/usr/bin/env python3
"""
Fetch full detail for a basket including its workflow definition.
Used for edit and rebalance flows.

Usage:
  python3 fetch_basket_detail.py <slug_or_id>

Output:
  Full product object with definition (nodes, connections, tokenAllocations, etc.)
"""

import sys
sys.dont_write_bytecode = True
import json, urllib.request
from _store import read_session, ACCESS_KEY

BASE_URL = "https://backend.cesto.co"

if len(sys.argv) < 2:
    print(json.dumps({"error": True, "message": "Usage: fetch_basket_detail.py <slug_or_id>"}))
    sys.exit(1)

slug_or_id = sys.argv[1]

_session = read_session()
headers = {}
if _session:
    headers["Authorization"] = f"Bearer {_session[ACCESS_KEY]}"

try:
    req = urllib.request.Request(f"{BASE_URL}/products/{slug_or_id}")
    for k, v in headers.items():
        req.add_header(k, v)
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    print(json.dumps({"error": True, "status": e.code, "message": e.read().decode()}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({"error": True, "message": str(e)}))
    sys.exit(1)

# Extract key fields for a clean summary alongside the full definition
defn = data.get("definition", {})
output = {
    "id": data.get("id", ""),
    "slug": data.get("slug", ""),
    "name": data.get("name", ""),
    "description": data.get("description", ""),
    "category": data.get("category"),
    "tags": data.get("tags", []),
    "logoUrl": data.get("logoUrl"),
    "isActive": data.get("isActive", False),
    "version": data.get("version", 1),
    "workflowId": data.get("workflowId", ""),
    "riskLevel": data.get("riskLevel"),
    "minimumInvestment": data.get("minimumInvestment", "0"),
    "tokensInvolved": data.get("tokensInvolved", []),
    "protocolsInvolved": data.get("protocolsInvolved", []),
    "tokenPerformance": data.get("tokenPerformance"),
    "definition": {
        "id": defn.get("id", ""),
        "name": defn.get("name", ""),
        "type": defn.get("type", "open"),
        "about": defn.get("about", ""),
        "risk": defn.get("risk", ""),
        "resources": defn.get("resources", ""),
        "tokenMint": defn.get("tokenMint", ""),
        "tokenDecimal": defn.get("tokenDecimal", 6),
        "nodes": defn.get("nodes", []),
        "connections": defn.get("connections", []),
        "tokenAllocations": defn.get("tokenAllocations", []),
    },
}

print(json.dumps(output))
