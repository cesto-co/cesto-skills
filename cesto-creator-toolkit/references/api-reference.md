# Creator Toolkit — API Reference

Base URL: `https://dev.backend.cesto.co`

## Table of Contents

1. [Token Registry](#1-token-registry)
2. [User Profile + Role](#2-user-profile--role)
3. [Prediction Events — Browse](#3-prediction-events--browse)
4. [Prediction Events — Search](#4-prediction-events--search)
5. [Prediction Event — Detail](#5-prediction-event--detail)
6. [Prediction Market — Detail](#6-prediction-market--detail)
7. [Upload Thumbnail](#7-upload-thumbnail)
8. [Simulate Workflow](#8-simulate-workflow)
9. [Create Product](#9-create-product)
10. [Update Product](#10-update-product)
11. [Create Version / Rebalance](#11-create-version--rebalance)
12. [List Creator's Products](#12-list-creators-products)
13. [Product Detail](#13-product-detail)
14. [Workflow Node Types](#14-workflow-node-types)

---

## 1. Token Registry

**GET** `/tokens` — No auth required

Returns all supported tokens on the platform.

```json
[
  {
    "mint": "So11111111111111111111111111111111111111112",
    "symbol": "SOL",
    "name": "Solana",
    "logoUrl": "https://..."
  }
]
```

---

## 2. User Profile + Role

**GET** `/users/me` — Bearer token required

```json
{
  "id": "8b0f3ada-...",
  "solanaWalletAddress": "6APVCc144...",
  "embeddedWalletAddress": "9A7r7EZR...",
  "role": "CREATOR",
  "email": null,
  "username": null,
  "createdAt": "2026-04-14T12:53:35.830Z",
  "authType": "externalWallet"
}
```

Roles: `USER`, `CREATOR`, `ADMIN`. Only CREATOR can create/edit products via this skill.

---

## 3. Prediction Events — Browse

**GET** `/prediction/events` — No auth required

| Param | Type | Description |
|-------|------|-------------|
| category | string | crypto, sports, politics, economics, finance, esports, weather |
| filter | string | new, live, trending |
| provider | string | polymarket, kalshi |
| includeMarkets | boolean | Include nested market objects |

Response: `{ "data": PredictionEvent[] }`

---

## 4. Prediction Events — Search

**GET** `/prediction/events/search` — No auth required

| Param | Type | Description |
|-------|------|-------------|
| query | string | Search text (1-200 chars, required) |
| provider | string | polymarket, kalshi |
| limit | number | 1-20 (default 10) |

Response: `{ "data": PredictionEvent[] }`

---

## 5. Prediction Event — Detail

**GET** `/prediction/events/{eventId}` — No auth required

Returns a single `PredictionEvent` (no `{ data }` wrapper).

### PredictionEvent shape

```json
{
  "eventId": "POLY-36173",
  "isActive": true,
  "isLive": false,
  "category": "crypto",
  "metadata": {
    "title": "When will Bitcoin hit $150k?",
    "subtitle": "",
    "closeTime": "2026-12-31T12:00:00Z",
    "imageUrl": "https://..."
  },
  "volumeUsd": "3134484000000",
  "markets": [PredictionMarket]
}
```

---

## 6. Prediction Market — Detail

**GET** `/prediction/markets/{marketId}` — No auth required

Returns a single `PredictionMarket` (no wrapper).

### PredictionMarket shape

```json
{
  "marketId": "POLY-573656",
  "status": "open",
  "result": null,
  "title": "by December 31, 2026",
  "closeTime": 1798776000,
  "pricing": {
    "buyYesPriceUsd": 110000,
    "buyNoPriceUsd": 910000,
    "sellYesPriceUsd": 90000,
    "sellNoPriceUsd": 890000,
    "volume": 291903
  },
  "outcomes": ["Yes", "No"],
  "outcomePrices": ["0.095", "0.905"],
  "marketOptions": [
    {"label": "Yes", "buyYes": true},
    {"label": "No", "buyYes": false}
  ]
}
```

Note: `pricing.*PriceUsd` values are in **micro-USD** (divide by 1,000,000 for dollar amount).

---

## 7. Upload Thumbnail

**POST** `/labs/upload-thumbnail` — Bearer token required

Content-Type: `multipart/form-data`
Body: FormData with `file` field

Response: `{ "url": "https://res.cloudinary.com/..." }`

---

## 8. Simulate Workflow

**POST** `/positions/simulate` — No auth required

Request:
```json
{
  "definition": {
    "id": "temp-simulation",
    "name": "Workflow Simulation",
    "nodes": [WorkflowNode],
    "connections": [{"source": "START", "target": "swap-0"}],
    "tokenAllocations": [TokenAllocation]
  },
  "amount": 100,
  "refresh": true
}
```

Response includes `analytics.aggregates.tokenPerformance` with PnL, APY, and per-node analyses.

---

## 9. Create Product

**POST** `/creator/products` — Bearer token required (CREATOR role)

```json
{
  "product": {
    "name": "Basket Title",
    "slug": "basket-title",
    "description": "Description text",
    "logoUrl": null,
    "isActive": true,
    "category": "prediction",
    "tags": []
  },
  "workflow": {
    "name": "Basket Title",
    "description": "Description text",
    "category": "prediction",
    "tags": [],
    "definition": {
      "id": "uuid",
      "name": "Basket Title",
      "type": "open",
      "about": "Strategy description (>= 20 chars)",
      "risk": "Risk disclosure (>= 10 chars)",
      "resources": "Thesis/links (>= 20 chars)",
      "tokenMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "tokenDecimal": 6,
      "nodes": [],
      "connections": [],
      "tokenAllocations": []
    }
  },
  "version": {
    "label": "v1.0.0",
    "changelog": "Initial version",
    "estimatedApy": null,
    "riskLevel": "MEDIUM",
    "minimumInvestment": "10000000",
    "isStable": false,
    "isDeprecated": false
  }
}
```

Response: Created product object with `id`, `slug`.

---

## 10. Update Product

**PUT** `/creator/products/{productId}` — Bearer token required (CREATOR role)

Same body structure as create, but all fields optional within each sub-object.

---

## 11. Create Version / Rebalance

**POST** `/creator/products/{productId}/versions` — Bearer token required (CREATOR role)

```json
{
  "workflow": {
    "name": "...",
    "description": "...",
    "definition": { "...full new definition..." }
  },
  "version": {
    "version": 2,
    "label": "v2.0.0",
    "changelog": "Rebalanced to version 2",
    "estimatedApy": null,
    "riskLevel": "MEDIUM",
    "minimumInvestment": "10000000",
    "isStable": false,
    "isDeprecated": false
  }
}
```

---

## 12. List Creator's Products

**GET** `/products?mine=true` — Bearer token required

Returns array of the creator's own products:
```json
[
  {
    "id": "41082d06-...",
    "slug": "football-glory",
    "name": "Football Glory",
    "description": "...",
    "category": "prediction",
    "isActive": false,
    "isPublished": false
  }
]
```

---

## 13. Product Detail

**GET** `/products/{slug_or_id}` — Auth optional (enriched with auth)

Returns full product with workflow definition including nodes, connections, tokenAllocations,
about, risk, resources, tokenPerformance, etc.

---

## 14. Workflow Node Types

**GET** `/products/nodes` — No auth required

Returns available node types: `swap.token`, `prediction.open`, `prediction.close`,
`transaction.submit`, lending nodes, drift nodes.

Each includes metadata (id, displayName, description) and parameter schemas.
