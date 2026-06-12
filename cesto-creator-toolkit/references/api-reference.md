# Creator Toolkit — API Reference

The contract this skill talks to. Open this file when you're constructing a request body, parsing a response, or debugging a 400/403/404.

**Base URL:** `https://backend.cesto.co`

## Table of contents

1. [Auth model](#1-auth-model)
2. [`GET /tokens`](#2-get-tokens)
3. [`GET /users/me`](#3-get-usersme)
4. [Prediction proxy — `GET /prediction/*`](#4-prediction-proxy--get-prediction)
5. [`POST /labs/upload-thumbnail`](#5-post-labsupload-thumbnail)
6. [`POST /positions/simulate`](#6-post-positionssimulate)
7. [`POST /creator/products`](#7-post-creatorproducts)
8. [`PUT /creator/products/:id`](#8-put-creatorproductsid)
9. [`GET /creator/products/:id`](#9-get-creatorproductsid)
10. [`POST /creator/products/:productId/versions`](#10-post-creatorproductsproductidversions)
11. [`PUT /creator/products/versions/:versionId`](#11-put-creatorproductsversionsversionid)
12. [`GET /products?mine=true`](#12-get-productsminetrue)
13. [`GET /products/:slug`](#13-get-productsslug)
14. [Out of scope — user-side rebalance](#14-out-of-scope--user-side-rebalance)
15. [Error codes](#15-error-codes)
16. [AI thumbnail builder — `/thumbnails/ai/*`](#16-ai-thumbnail-builder--thumbnailsai)

---

## 1. Auth model

- Bearer token in `Authorization: Bearer <jwt>`.
- JWT claims include `sub` (user id) and `addr` (Solana wallet). Role is looked up server-side from the database, not from the JWT.
- Roles: `USER`, `CREATOR`, `ADMIN`. Creator endpoints require `CREATOR` or `ADMIN`.
- Request body limit: 100 KB.
- `forbidNonWhitelisted: true` is on — sending fields a DTO doesn't declare returns 400 with a validation error. Always match the DTOs below exactly.

## 2. `GET /tokens`

Public. Returns the token registry.

**Response**
```jsonc
[
  {
    "mint": "So11111111111111111111111111111111111111112",
    "symbol": "SOL",
    "name": "Solana",
    "logoUrl": "https://...",
    "decimals": 9,
    "tags": ["wrapped"],
    "price": 142.31
  }
]
```

Response is cached and ETag-aware. Optional companion: `GET /tokens/yield-rates` returns per-mint yield info.

## 3. `GET /users/me`

Auth required.

**Response**
```jsonc
{
  "id": "8b0f3ada-...",
  "solanaWalletAddress": "6APVCc144...",
  "embeddedWalletAddress": "9A7r7EZR...",
  "provider": "external" | "privy" | "dynamic",
  "role": "USER" | "CREATOR" | "ADMIN",
  "email": null,
  "username": null,
  "authType": "externalWallet",
  "oAuthMethod": null,
  "createdAt": "2026-04-14T12:53:35.830Z",
  "updatedAt": "2026-05-30T08:11:22.541Z"
}
```

The skill accepts `role in {"CREATOR", "ADMIN"}`. Both roles drive the same flows
through the same scripts. The skill enforces a client-side rule that admins, like
creators, may only manage baskets they themselves created — even though the backend
would let admins act on any product. Cross-creator admin actions (publish, toggle
active, edit someone else's basket) belong in the admin UI / `/admin/*` endpoints,
not this skill.

## 4. Prediction proxy — `GET /prediction/*`

Public. Everything under `/prediction/*` proxies to Jupiter's Prediction API (Polymarket + Kalshi). Responses are cached server-side for 30s; pass `?refresh=true` to bypass.

| Path | Use |
|---|---|
| `GET /prediction/events?category=crypto&filter=trending` | Browse events by category/filter. Optional `provider`, `includeMarkets`. |
| `GET /prediction/events/search?query=bitcoin&limit=10` | Keyword search across events. |
| `GET /prediction/events/{eventId}` | Single event with its markets. |
| `GET /prediction/markets/{marketId}` | Single market — pricing, outcomes, close time. |

Common categories: `crypto`, `sports`, `politics`, `economics`, `finance`, `esports`, `weather`.
Common filters: `new`, `live`, `trending`.

**Event shape (abbreviated)**
```jsonc
{
  "eventId": "POLY-36173",
  "isActive": true,
  "category": "crypto",
  "metadata": {
    "title": "When will Bitcoin hit $150k?",
    "closeTime": "2026-12-31T12:00:00Z",
    "imageUrl": "https://..."
  },
  "markets": [ /* PredictionMarket[] */ ]
}
```

**Market shape (abbreviated)**
```jsonc
{
  "marketId": "POLY-573656",
  "status": "open",
  "title": "by December 31, 2026",
  "closeTime": 1798776000,           // Unix seconds — use directly in prediction.open
  "pricing": {
    "buyYesPriceUsd": 110000,        // micro-USD; divide by 1_000_000 for dollars
    "buyNoPriceUsd":  910000
  },
  "outcomes": ["Yes", "No"],
  "outcomePrices": ["0.095", "0.905"]
}
```

## 5. `POST /labs/upload-thumbnail`

Auth required. Multipart `file` field, max 10 MB. Accepts JPEG, PNG, WebP, GIF.

**Response**
```jsonc
{
  "url": "https://res.cloudinary.com/...",
  "publicId": "thumbnails/abc123",
  "format": "png",
  "width": 1024,
  "height": 1024,
  "bytes": 184227
}
```

Set `product.logoUrl` to the returned `url`. The alternative is to skip this endpoint entirely and set `product.aiGenerateThumbnail: true` on the create payload — see §7.

## 6. `POST /positions/simulate`

Public. Run a workflow definition against historical data to preview performance.

**Request**
```jsonc
{
  "definition": { /* WorkflowDefinition — bucket model, see references/workflow-definition.md */ },
  "amount": 100,                     // optional, base units
  "refresh": true,                   // optional
  "timeRange": "1y"                  // optional: 7d | 1m | 3m | 6m | 1y | all
}
```

**Response**
```jsonc
{
  "analytics": {
    "aggregates": {
      "netAPY": 0.142,
      "tokensInvolved": ["USDC", "SOL", "JUP"],
      "tokenPerformance":    { /* TokenPerformanceDto */ },
      "tokenPerformance7d":  { /* ... */ },
      "tokenPerformance30d": { /* ... */ }
    },
    "nodeAnalyses": [ /* per-node breakdown */ ]
  },
  "graph": { /* optional time-series + metrics */ }
}
```

`TokenPerformanceDto` includes `return`, `netPnL`, `priceAPY`, `annualizedReturn`, `daysAvailable`, `startDate`/`endDate`, and `predictionPerformance` (only for baskets with `prediction.open` nodes).

## 7. `POST /creator/products`

Auth + `CREATOR` (or `ADMIN`) role. Creates a product plus its first ProductVersion atomically.

**Important constraints enforced server-side**
- `isActive` and `isPublished` are FORCED to false server-side on create for every role (including admins), so a created product is always a DRAFT. create_basket.py also strips them client-side as belt-and-suspenders. (Note: on UPDATE via PUT /creator/products/:id, the backend instead honors these from an admin payload — see §8.)
- `slug` is required by the DTO (any non-empty string), but the controller overwrites it with `toSlug(name)` before persisting (lowercased, hyphenated, deduplicated with a random suffix on collision). The skill's `create_basket.py` auto-derives slug from name when missing — you never need to send it yourself.
- Either `logoUrl` (valid URL) or `aiGenerateThumbnail: true` must be present. Sending neither is a 400.

**Request — `CreateCreatorProductDto`**

Note: `product.slug` is required by class-validator (`CreateProductDto.slug!: string`).
`create_basket.py` auto-derives it from `name` when missing — agents calling through
the skill don't need to include it. If you're hitting the endpoint directly (via
`api_request.py` or curl), pass any non-empty slug; the controller overwrites it
with `toSlug(name)` server-side regardless.

```jsonc
{
  "product": {
    "name": "Football Glory",                       // required, ≤200 chars
    // slug: omit when calling via create_basket.py; auto-derived from name
    "description": "European football meets crypto",// optional, ≤1000 chars
    "category": "prediction",                       // optional, ≤100 chars — auto-derive: prediction/leverage/pool/swap
    "tags": ["football", "polymarket"],             // optional string[]
    "logoUrl": "https://res.cloudinary.com/.../image.png",
    "aiGenerateThumbnail": false,                   // set true to omit logoUrl and let the backend generate one
    "pointsMultiplier": 1,                          // optional, ≥0
    "metadata": {}                                  // optional, free-form
  },
  "workflow": {
    "name": "Football Glory",                       // required, ≤200 chars
    "description": "...",                           // optional, ≤1000 chars
    "category": "prediction",                       // optional, mirrors product.category
    "tags": [],                                     // optional
    "definition": { /* bucket-model WorkflowDefinition */ }
  },
  "version": {                                      // CreateVersionDataDto
    "changelog": "Initial version",                 // optional, ≤1000 chars
    "minimumInvestment": "10000000",                // REQUIRED, base units (10 USDC = "10000000")
    "isDeprecated": false,                          // optional
    "inputTokenMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  // optional, defaults to USDC mint
    "inputTokenDecimals": 6,                        // optional, defaults to 6
    "about": "Full strategy description (≥20 chars)",
    "riskNotes": "**No Liquidation Risk** — ...",   // markdown, bullet-format encouraged
    "resources": "**Thesis** — ..."                 // markdown, bullet-format encouraged
  }
}
```

**Fields the create endpoint does NOT accept (don't send them — `forbidNonWhitelisted` will 400):**
- `version.label`
- `version.riskLevel`
- `version.estimatedApy`
- `version.isStable`
- `version.tradingSchedule`

Note: `label`, `riskLevel`, `estimatedApy`, and `isStable` are also **not** settable
via §11 — the backend DTO accepts them without error but the service layer silently
ignores them. They are managed by the Cesto team during review.
`tradingSchedule` IS settable via §11 after creation.

**Response (raw)** — the version object's key is either `version` or
`productVersion` depending on the codepath. The skill's `create_basket.py`
normalizes this; the raw shape looks like:

```jsonc
{
  "product": {
    "id": "41082d06-...",
    "slug": "football-glory",
    "name": "Football Glory",
    "createdBy": "8b0f3ada-...",
    "isActive": false,
    "isPublished": false,
    "createdAt": "..."
  },
  "version": {                     // or "productVersion" — same shape, either key
    "id": "9d2c1f60-...",          // versionId — pass to step-2 PUT
    "productId": "41082d06-...",
    "version": 1,                  // always 1 on first create
    "minimumInvestment": "10000000",
    "inputTokenMint": "EPjFWdd5...",
    "inputTokenDecimals": 6,
    "about": "...",
    "riskNotes": "...",
    "resources": "...",
    "isDeprecated": false,
    "createdAt": "..."
  }
}
```

**Normalized output from `create_basket.py`** (read this instead of the raw shape):

```jsonc
{
  "productId":   "41082d06-...",
  "productSlug": "football-glory",
  "versionId":   "9d2c1f60-...",
  "version":     1,
  "raw":         { /* the full backend response above */ }
}
```

Use `productSlug` for the preview link (`https://app.cesto.co/product/{slug}`) —
backend may have suffix-randomized it.

## 8. `PUT /creator/products/:id`

Auth + `CREATOR`/`ADMIN`. Partial update — only send fields you want changed.

**Path param**: `id` — product UUID (not slug).

**Request — `UpdateCreatorProductDto`**: same nested shape as create, but everything optional within each sub-object.

```jsonc
{
  "product": {                       // optional partial
    "name": "Renamed Basket",        // setting name regenerates the slug server-side
    "description": "...",
    "category": "...",
    "tags": [...],
    "logoUrl": "...",
    "aiGenerateThumbnail": true,     // can flip to regenerate AI cover
    "pointsMultiplier": 1,
    "creatorFeeSharePercentage": 0.1,// 0-1; null clears
    "metadata": null
    // isActive / isPublished are honored from admin payloads server-side, but
    // update_basket.py strips them client-side for BOTH roles — the skill
    // never publishes a basket. Publish from the frontend admin UI instead.
  },
  "workflow": {                      // optional partial — usually omit; use POST /versions for definition changes
    "name": "...",
    "description": "...",
    "category": "...",
    "tags": [...],
    "definition": { /* full new bucket-model definition */ }
  },
  "version": {                       // optional partial — updates the LATEST version's metadata
    "changelog": "...",
    "minimumInvestment": "...",
    "isDeprecated": false,
    "inputTokenMint": "...",
    "inputTokenDecimals": 6,
    "about": "...",
    "riskNotes": "...",
    "resources": "..."
  }
}
```

Note: `riskLevel`, `label`, `estimatedApy`, and `isStable` cannot be set through §11 either — the backend accepts them without error but silently ignores them. Those fields are managed by the Cesto team during review.

**Response**: full updated product.

## 9. `GET /creator/products/:id`

Auth + `CREATOR`/`ADMIN`. Server-side, admins bypass the ownership check and can read
any product. **The skill's mutating scripts (`update_basket.py`,
`rebalance_basket.py`) refuse to act if `createdBy !== /users/me.id`** — admins
behave exactly like creators through this skill. Returns the product with **all**
versions.

**Response (abbreviated)**
```jsonc
{
  "id": "41082d06-...",
  "slug": "football-glory",
  "name": "Football Glory",
  "createdBy": "8b0f3ada-...",
  "isActive": false,
  "isPublished": false,
  "category": "prediction",
  "tags": [...],
  "logoUrl": "...",
  "versions": [                       // newest first
    {
      "id": "abc...",
      "version": 3,
      "minimumInvestment": "10000000",
      "inputTokenMint": "EPjFWdd5...",
      "inputTokenDecimals": 6,
      "about": "...",
      "riskNotes": "...",
      "resources": "...",
      "changelog": "Reduced PSG; added Real",
      "definition": { /* bucket-model */ },
      "isDeprecated": false,
      "createdAt": "..."
    },
    { "id": "...", "version": 2, /* ... */ },
    { "id": "...", "version": 1, /* ... */ }
  ]
}
```

Use this to fetch the latest version's number when computing `nextVersion = max + 1` for a rebalance.

## 10. `POST /creator/products/:productId/versions`

Auth + `CREATOR`/`ADMIN`. Creates a new version of an existing product (the creator-side "rebalance").

**Path param**: `productId` — product UUID.

**Request — `CreateCreatorProductVersionDto`**
```jsonc
{
  "workflow": {                     // CreateWorkflowDataDto
    "name": "Football Glory v3",
    "description": "Reweighted after CL draw",
    "category": "prediction",
    "tags": [],
    "definition": { /* full new bucket-model definition */ }
  },
  "version": {                      // CreateProductVersionDataDto
    "version": 3,                   // REQUIRED, ≥1 — must be higher than any existing version
    "changelog": "Reduced PSG by 10%, added Real Madrid YES",
    "minimumInvestment": "10000000",
    "isDeprecated": false,
    "inputTokenMint": "EPjFWdd5...",   // optional, defaults to USDC
    "inputTokenDecimals": 6,           // optional, defaults to 6
    "about": "...",
    "riskNotes": "...",
    "resources": "..."
  }
}
```

Same field constraints as create — `label`/`riskLevel`/`estimatedApy`/`isStable` are **not** accepted here. Note: §11 does not persist these either — they are managed by the Cesto team during review.

**Response**
```jsonc
{
  "version": {
    "id": "9d2c1f60-...",        // new versionId
    "productId": "41082d06-...",
    "version": 3,
    "minimumInvestment": "10000000",
    "inputTokenMint": "EPjFWdd5...",
    "inputTokenDecimals": 6,
    "changelog": "...",
    "about": "...", "riskNotes": "...", "resources": "...",
    "definition": { /* */ },
    "isDeprecated": false,
    "createdAt": "..."
  }
}
```

## 11. `PUT /creator/products/versions/:versionId`

Auth + `CREATOR`/`ADMIN`. Server-side ownership is checked for creators but
bypassed for admins. The skill's `update_version_metadata.py` enforces ownership
client-side (refuses if the parent product's `createdBy !== /users/me.id`), so
admins are constrained to their own versions through this skill. Patches metadata
on a specific version row — never changes the workflow definition.

**⚠ Persistence reality — only 4 fields are actually written:**

The backend's `updateProductVersion` service method only persists:
`changelog`, `minimumInvestment`, `tradingSchedule`, `isDeprecated`.

The DTO also declares `label`, `riskLevel`, `estimatedApy`, `isStable` —
these are accepted without a validation error (no 400), but the service layer
**silently ignores** them and they are **never written to the database**. A
follow-up GET will show them still null/unchanged even after a 200 response.

The skill's `update_version_metadata.py` strips those four fields client-side
and includes a `"warning"` in the output so the caller gets honest feedback.
`riskLevel`, `label`, `estimatedApy`, and `isStable` are managed by the Cesto
team during review.

**Request — `UpdateProductVersionDto` (all optional; only send what's changing)**
```jsonc
{
  "changelog": "Rebalance: reduce PSG; add Real",  // persisted ✓
  "minimumInvestment": "15000000",                 // persisted ✓
  "tradingSchedule": null,                         // persisted ✓
  "isDeprecated": false                            // persisted ✓

  // NOT persisted (DTO accepts, service ignores — skill strips these):
  // "label": "v3.0.0"
  // "estimatedApy": 23.5
  // "riskLevel": "MEDIUM"
  // "isStable": false
}
```

Flipping `isDeprecated: true → false` (re-activating a deprecated version) triggers the auto-rebalance scheduler server-side. Usually you'll only ever set this to `true` to retire a version.

**Response**: the updated version object (plus a `"warning"` key if the skill stripped any unsupported fields).

## 12. `GET /products?mine=true`

Auth required. Returns the calling creator's products only (or all visible products if `mine` is omitted).

**Query params**
| Param | Notes |
|---|---|
| `mine=true` | Restrict to caller's products. Without auth this 403s. |
| `category` | Filter by category. |

**Response — array of products**
```jsonc
[
  {
    "id": "41082d06-...",
    "slug": "football-glory",
    "name": "Football Glory",
    "description": "...",
    "category": "prediction",
    "tags": [...],
    "logoUrl": "...",
    "isActive": false,
    "isPublished": false,
    "createdBy": "8b0f3ada-...",
    "versions": [
      { "id": "...", "version": 3, "isDeprecated": false, "minimumInvestment": "10000000" }
    ],
    "geoStatus": { "canView": true, "canInvest": true }
  }
]
```

Surface `isActive`/`isPublished` to the creator — anything with `isActive: false` is a DRAFT awaiting admin publish.

## 13. `GET /products/:slug`

Public (auth optional — enriches some fields when authenticated). Returns the latest version of a product. The response shape is **flat** — no `{ product, workflow, version }` nesting.

**Path param**: slug or product UUID.

**Response — `ProductVersionResponseDto`**
```jsonc
{
  "id": "41082d06-...",              // productId
  "versionId": "9d2c1f60-...",       // ProductVersion.id
  "version": 3,
  "changelog": "...",
  "minimumInvestment": "10000000",
  "inputTokenMint": "EPjFWdd5...",
  "inputTokenDecimals": 6,
  "about": "...",
  "riskNotes": "...",
  "resources": "...",

  "name": "Football Glory",
  "slug": "football-glory",
  "description": "...",
  "logoUrl": "...",
  "category": "prediction",
  "tags": [...],
  "isActive": true,
  "isPublished": true,
  "metadata": null,
  "pointMultiplier": 1,

  "tokensInvolved": ["USDC", "SOL"],
  "protocolsInvolved": ["jupiter", "polymarket"],
  "tokenPerformance":    { /* TokenPerformanceDto | null */ },
  "tokenPerformance7d":  { /* ... */ },
  "tokenPerformance30d": { /* ... */ },

  "predictionMarkets": [               // present only when the basket includes prediction.open
    {
      "marketTicker": "POLY-573656",
      "protocol": "polymarket",
      "side": "YES",
      "title": "Bitcoin $150k by Dec 2026",
      "closeTime": 1798776000,
      "status": "active",              // "active" | "determined" | "finalized"
      "result": null
    }
  ],
  "canInvest": true,                   // false if any predictionMarket is past "active"

  "definition": { /* bucket-model WorkflowDefinition */ }
}
```

Inactive products are 404 for everyone except the creator and admins.

## 14. Out of scope — user-side rebalance

These endpoints exist but are **not** called by this skill. Mentioned for situational awareness so you can tell a confused creator "that's an investor action, not a creator action":

| Endpoint | Purpose |
|---|---|
| `GET /products/:slug/rebalance-state` | Per-user state: auto-rebalance toggle, pending REBALANCE execution, USDC deficit. |
| `PUT /products/:slug/auto-rebalance` (body `{ enabled: boolean }`) | Toggle auto-rebalance for the authenticated investor's holding. |
| `POST /positions/rebalance/:productId` | Manual rebalance for the investor's existing position. Signed-action protected. |

If a creator asks "how do my investors get the new allocations", the answer: their position tracks the latest published version and they (or auto-rebalance on their behalf) move into it via the endpoints above.

## 15. Error codes

| HTTP | Common cause | Action |
|---|---|---|
| 400 | DTO validation failed — extra/missing field, wrong type, slug too long, allocations not summing to 100, etc. | Surface the API message. Check the request against the DTO. |
| 401 | Missing/expired JWT. | Refresh via `session_status.py`, retry. If refresh fails, run `start_login.py`. |
| 403 | Role check failed (caller isn't CREATOR/ADMIN), or the skill's own ownership pre-flight rejected the request (admin trying to edit a basket they didn't create). | If role: "Access denied — needs CREATOR or ADMIN role." If ownership: "This skill only edits baskets you created yourself — admin cross-edits go through the admin UI." |
| 404 | Slug/ID unknown, or product `isActive: false` and caller isn't the owner. | Verify slug/UUID; for draft baskets, use `GET /creator/products/:id`. |
| 429 | Rate-limited. | Brief backoff, retry. |

Validation errors include a flattened `message` field. Common server-side codes you may see in the error body: `WORKFLOW_VALIDATION_FAILED`, `FORBIDDEN_OPERATION`, `RESOURCE_NOT_FOUND`, `INVALID_INPUT`, `DUPLICATE_RESOURCE`.

## 16. AI thumbnail builder — `/thumbnails/ai/*`

All endpoints require auth + `CREATOR`/`ADMIN`. They drive an interactive
2×2-grid generator backed by Midjourney or Gemini. A "session" carries the
state across calls; session id is the only handle the client needs.

Flow:
1. (Optional) Generate a starter prompt the user can edit — **client-side only**
   (see note below).
2. Generate a 2×2 grid → 4 preview URLs.
3. Either **Select** one quadrant as the basket cover (returns `finalUrl` —
   use as `product.logoUrl`), or **upscale-for-download** to fetch a
   full-resolution copy without committing it as the cover.

**Starter prompt — generated client-side, no backend endpoint:**
`GET /thumbnails/ai/prompt-template` does **NOT** exist on the backend. Any
request to that path is matched by `GET /thumbnails/ai/:sessionId` with
`sessionId="prompt-template"`, returning a 404 "Thumbnail session not found".
The starter prompt is instead generated locally by `scripts/ai_thumbnail_prompt.py`
— the `grid` endpoint accepts any prompt the client supplies, so a server-suggested
starter is entirely optional and works just as well when built client-side.

### `POST /thumbnails/ai/grid` — `CreateGridDto`

```jsonc
{
  "title": "Football Glory",          // ≤100, required — used for Cloudinary folder + persisted
  "description": "European football meets crypto", // ≤1000, required
  "provider": "midjourney",           // "midjourney" | "gemini"
  "prompt": "..."                     // ≤~1900 chars — user's edited prompt; MJ flags appended server-side
}
```

**Response**: `{ "sessionId": "..." }` — generation runs in the background.
Poll the session to pick up the previews.

### `GET /thumbnails/ai/:sessionId` — `ThumbnailSessionView`

```jsonc
{
  "sessionId": "...",
  "gridStatus": "pending" | "ready" | "failed",
  "previews": [
    {
      "index": 1,                    // 1..4
      "url": "https://res.cloudinary.com/...",  // preview (low-res on MJ, full-res on Gemini)
      "downloadUrl": "..."           // present once an upscale-for-download (or select) ran on this quadrant; Gemini fills it immediately
    }
    // ... 4 entries
  ],
  "upscaleStatus": "idle" | "pending" | "ready" | "failed",
  "selectedIndex": 1,                // present after select-as-final
  "finalUrl": "https://res.cloudinary.com/...",  // the picked + upscaled URL; use as logoUrl
  "provider": "midjourney" | "gemini",          // backend that actually produced the previews
  "fellBack": false,                            // true if primary provider failed and backend swapped to the other
  "error": null
}
```

Poll every 5s, ~3 min ceiling. Statuses to act on:
- `gridStatus="ready"` → previews are available; show to user.
- `gridStatus="failed"` → surface `error` to user; offer regenerate.
- `upscaleStatus="ready"` → `finalUrl` is set; use it as `logoUrl`.

### `POST /thumbnails/ai/upscale` — `SelectUpscaleDto`

```jsonc
{ "sessionId": "...", "index": 1 }   // index must be 1..4
```

Picks one quadrant as the final basket cover. Backend upscales it; poll the
session again for `upscaleStatus="ready"` and read `finalUrl`. Pass that URL
as `product.logoUrl` in your create/update payload — do **not** set
`aiGenerateThumbnail` alongside it.

**Response**: `{ "sessionId": "..." }`

### `POST /thumbnails/ai/:sessionId/upscale-for-download` — `UpscaleForDownloadDto`

```jsonc
{ "index": 1 }                       // 1..4
```

Distinct from select-as-final: just returns a full-resolution URL for the
user to download. Does **not** mark the quadrant as the basket cover. The
result is cached per-quadrant on the session, so a follow-up Select on the
same index reuses the upscale (no second Midjourney call).

**Response**: `{ "url": "...", "publicId": "..." }` — the URL is an
unauthenticated Cloudinary GET; the skill HTTP-fetches it and writes to disk.
