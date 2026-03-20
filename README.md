# Cesto Skills

Skills for interacting with the [Cesto](https://app.cesto.co) platform via Claude Code.

## Available Skills

### cesto-toolkit

The primary skill for all Cesto platform interactions. Handles authentication, basket creation, portfolio simulation, and market data.

**Location:** `cesto-toolkit/`

---

## What This Skill Does

The `cesto-toolkit` skill turns Claude Code into a complete Cesto client. When triggered, it can:

- **Authenticate** users via a magic-link wallet connection flow
- **Fetch supported tokens** from the Cesto platform
- **Create basket posts** on Cesto Labs (community section)
- **Simulate portfolio performance** against the S&P 500 benchmark
- **Query basket data** — list baskets, view details, analyze token performance, check analytics

---

## How Authentication Works

The skill uses a magic-link flow — no manual JWT pasting required.

### First-time login

1. Skill loads and detects no stored credentials
2. Creates a login session via the Cesto backend
3. Opens the user's browser to a wallet connection page
4. User connects their Solana wallet (Phantom, Backpack, Solflare, etc.) and signs a message
5. CLI polls the backend until authentication completes
6. Tokens are saved locally to `~/.cesto/auth.json`
7. User is logged in — future sessions use the stored tokens

### Returning users

1. Skill loads and reads `~/.cesto/auth.json`
2. If the access token is valid — proceeds immediately
3. If the access token expired but refresh token is valid — silently refreshes
4. If both are expired — triggers the full login flow again

### Token storage

Credentials are stored at `~/.cesto/auth.json`:

```json
{
  "accessToken": "eyJ...",
  "refreshToken": "eyJ...",
  "accessTokenExpiresAt": "2026-03-20T14:00:00Z",
  "refreshTokenExpiresAt": "2026-03-27T13:00:00Z",
  "walletAddress": "7xKXq9..."
}
```

- File permissions are set to `600` (owner read/write only) on Mac/Linux
- The `~/.cesto/` folder is set to `700` (owner only)
- Tokens are never displayed to the user in CLI output

---

## Available API Endpoints

The skill provides access to 8 Cesto API endpoints:

### Public endpoints (no auth required on backend, but skill authenticates first)

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 1 | `/tokens` | GET | List all supported tokens on the platform |
| 2 | `/products` | GET | List all baskets with summary info |
| 3 | `/products/{slug}` | GET | Full basket detail including strategy and performance |
| 4 | `/products/{id}/analyze` | GET | Per-token market data and price changes |
| 5 | `/products/{id}/graph` | GET | Historical time series (portfolio vs S&P 500) |
| 6 | `/products/analytics` | GET | Cross-basket analytics summary |

### Authenticated endpoints

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 7 | `/cesto-labs/posts` | POST | Create a basket post on Cesto Labs |
| 8 | `/agent/simulate-graph` | POST | Simulate portfolio historical performance |

---

## Creating a Basket Post

The skill can create basket posts on Cesto Labs (the community section where users share investment ideas).

### What you need

- A basket theme or specific token allocations
- All tokens must be available on the Cesto platform (fetched via `/tokens`)
- Allocations must sum to exactly 100%

### What the skill does

1. Authenticates the user
2. Fetches available tokens from the platform
3. Researches the theme (if the user gives a category like "AI stocks" or "DeFi")
4. Proposes an allocation with rationale
5. Creates the post via the API
6. Returns a clean summary with the post link

### Basket post payload structure

```json
{
  "title": "Basket Title (1-100 chars)",
  "description": "Investment thesis (1-1000 chars)",
  "aiGenerateThumbnail": true,
  "allocations": [
    {
      "mint": "So11111111111111111111111111111111111111112",
      "symbol": "SOL",
      "name": "Solana",
      "percentage": 40,
      "logoUrl": "https://...",
      "description": "Why this token is included (max 200 chars)"
    }
  ]
}
```

---

## Portfolio Simulation

The skill can simulate how a custom token allocation would have performed historically, compared against the S&P 500.

### Simulation payload

```json
{
  "allocations": [
    { "token": "SOL", "mint": "So111...", "weight": 50 },
    { "token": "USDC", "mint": "EPjF...", "weight": 50 }
  ],
  "name": "My Portfolio"
}
```

### Response

Returns daily time series data with:
- `portfolioValue` — simulated value starting at 1000
- `sp500Value` — S&P 500 benchmark starting at 1000
- `isLiquidated` — whether the portfolio was liquidated on that date

---

## Skill Trigger Words

The skill activates when the user mentions any of:

- "Cesto", "Cesto Labs"
- "basket", "basket idea", "post a basket", "community basket"
- "create basket post", "share my allocation", "publish basket"
- "Cesto API", "basket performance", "basket analytics"
- "simulate portfolio", "token analysis", "basket detail"

---

## File Structure

```
skills/
├── README.md                                    ← This file
└── cesto-toolkit/
    ├── SKILL.md                                 ← Main skill instructions
    └── references/
        └── api-reference.md                     ← Detailed API endpoint documentation
```

### SKILL.md

The main skill file containing:
- Execution order and presentation rules
- Complete authentication flow (magic-link login, silent refresh, resilient polling)
- Token registry API
- Basket creation API with payload structure
- Portfolio simulation API with payload structure
- Error handling

### references/api-reference.md

Detailed documentation for the read-only API endpoints:
- List all baskets (`GET /products`)
- Basket detail (`GET /products/{slug}`)
- Token analysis (`GET /products/{id}/analyze`)
- Historical graph (`GET /products/{id}/graph`)
- Analytics summary (`GET /products/analytics`)
- Simulate portfolio graph (`POST /agent/simulate-graph`)

Includes full response structures, field types, descriptions, and example responses.

---

## Configuration

### Backend and Frontend URLs

URLs are hardcoded in `cesto-toolkit/SKILL.md`. To switch environments, manually edit the two URL fields at the top of the file:

```markdown
**Backend URL:** `https://backend.cesto.co`
**Frontend URL:** `https://app.cesto.co`
```

| Environment | Backend URL | Frontend URL |
|---|---|---|
| Production | `https://backend.cesto.co` | `https://app.cesto.co` |
| Development | `https://dev.backend.cesto.co` | `https://dev.app.cesto.co` |
| Local | `http://localhost:3000` | `http://localhost:3002` |

---

## Error Handling

| Status | Meaning | Skill Action |
|---|---|---|
| 400 | Validation failed | Shows the API error message to the user |
| 401 | Token expired/invalid | Silently refreshes. If refresh fails, triggers login flow |
| 403 | Forbidden | Informs the user they lack permission |
| 404 | Not found | Suggests checking the slug or ID |
