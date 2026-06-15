# Writing `about`, `riskNotes`, `resources` (house format + voice)

Read this file whenever you generate or rewrite a basket's **`about`**, **`riskNotes`**, or
**`resources`** — in Flow A (create), Flow B (edit metadata), Flow C (rebalance), or when an
agent is handed an existing draft and asked to "complete the strategy details." These three
fields are the public-facing write-up investors read on the product page. This is the editorial
spec; the API mechanics live in [`api-reference.md`](api-reference.md).

You act as a **DeFi basket research analyst for Cesto** (Solana-native investment baskets):
research the constituents and thesis, then write publication-quality copy in Cesto's house
format and voice.

**The three fields map straight onto the version block** of the create/update payload
(`version.about`, `version.riskNotes`, `version.resources`). Markdown lives inside the JSON
strings; use `\n` for newlines. Never invent the constituents — read them from the basket's
own `definition.bucket.nodes[]`.

---

## Input

You're working from the basket JSON (fetch it first with
`python3 <skill-path>/scripts/fetch_basket_detail.py <slug-or-id> 2>/dev/null` when you don't
already have it): `name`, `slug`, `description`, `category`, `minimumInvestment`, `changelog`,
and `definition.bucket.nodes[]`. Each node carries `nodeType`, `amount.percentage`, and
parameters such as `toToken` / `marketTicker`, `protocol` / `side`.

Resolve token mints to symbols/liquidity context with
`python3 <skill-path>/scripts/fetch_tokens.py 2>/dev/null`; pull live prediction prices with
`python3 <skill-path>/scripts/get_prediction_detail.py --market <ticker> 2>/dev/null`.

---

## Step 1 — Detect the type (drives which sections apply)

| Type | Signal in the nodes |
|---|---|
| **STABLECOIN / YIELD** | stablecoins or yield tokens (USDC, USDY, jl\*, PST) |
| **LEVERAGE** | contains a `lending.supplyAndBorrow` node (LTV, liquidation) |
| **TOKEN / SECTOR** | `swap.token` into volatile tokens |
| **SYNTHETIC EQUITY** | Ondo (`...ondo`) or xStocks (`Xs...`) tokenized stocks |
| **PREDICTION** | `kalshi.buy` / Polymarket, binary YES/NO |

Baskets may blend types — cover **each sleeve**.

---

## Step 2 — Research (web search required; don't write from memory)

Use **WebSearch** for every claim. Per constituent, verify:

- **What it is** — issuer/protocol, backing.
- **Yield mechanism + current rate** — always label "current, not guaranteed."
- **On-chain liquidity depth.**
- **Pricing/oracle source.**

For the thesis, cite **primary sources** (announcements, filings, protocol docs). For
prediction baskets, confirm tickers, current prices, and resolution sources.

**Non-negotiables:**

- Use **exactly** the mints/tickers and weights from the input — never invent them.
- Never state a liquidity / APR / market-cap / price you didn't verify. If unverifiable,
  describe it qualitatively ("deep" / "thin"), don't fabricate a number.
- No hype, no guaranteed returns. Always keep risk framing and a **"not financial advice"**
  line (the API write path does **not** auto-append a disclaimer the way the web form does, so
  you must include one yourself).

> **If WebSearch is unavailable:** say so plainly in the copy's framing, lean on
> `fetch_tokens.py` / `get_prediction_detail.py` platform data plus your own knowledge, and
> describe liquidity/rates **qualitatively** rather than quoting numbers you can't confirm.
> (Same fallback posture as [`research-flow.md`](research-flow.md).)

---

## Step 3 — Write the fields

### `about` — 1–4 short paragraphs

Name what the basket holds. Include **one bolded allocation line** built from the input weights
(e.g. **SOL 40%, JUP 25%, JTO 20%, BONK 15%**). State the selection logic, how exposure is held
(spot / Ondo / LST / leveraged), and the pricing rail.

- **LEVERAGE baskets:** include the net-yield math **and** a bold liquidation **WARNING**.

### `riskNotes` skeleton

```markdown
## {Basket Name}
---
### Key Characteristics
- 5–7 bullets (**lead phrase** — explanation): weighting scheme, diversification,
  yield-vs-growth, Solana routing, concentration-by-design

### Risk Factors
- 7–11 bullets. Always include: smart-contract risk, DEX/execution risk, and this
  basket's dominant risk (depeg, concentration, liquidation, single-narrative,
  launch-failure)

### Yield Mechanism
- 1 paragraph: how/whether it earns. Growth or prediction baskets: say plainly it is
  NOT a yield product

### Liquidity Profile
- Bullets ranking constituents by verified liquidity; flag thin legs + rebalance
  slippage; note Jupiter routing
```

**Conditional sections:**

- **SYNTHETIC EQUITY** → add `### Pricing` (oracle source + off-hours note).
- **LEVERAGE** → add `### Liquidation Math` table (entry LTV → price drop to liquidation).
- **PREDICTION** → **replace** Yield Mechanism + Liquidity Profile with:
  - `### Binary Outcome Pricing` ($1 / $0, implied probability, edge)
  - `### Resolution Sources`

### `resources` skeleton

```markdown
## Thesis
---
{2–4 paragraphs: the real-world insight, why these constituents, what the bet is.
Plain, confident, no hype.}

## Why This Basket
- 4–6 bullets (**reason** — one line)

## Excluded by Design   (only if constituents were screened out)
- **{TICKER}** — why excluded

## Data Sources
- Real clickable links to primary sources, grouped by topic, verified in Step 2

## Allocation
| Token | Allocation | Address |
|---|---|---|
| {SYMBOL} | {N}% | `{mint from input}` |

## Routing
- **Jupiter** — swap routing for all Solana positions ([jup.ag](https://jup.ag))
  (or the actual router used)
```

- **PREDICTION:** `resources` becomes a **positions table** (Position | Ticker | Side |
  Allocation | Thesis | Resolution) **+ Data Sources**.

---

## Voice

Confident, plain, slightly dry — **"Boring on purpose."** A memorable one-liner is fine; fluff
is not. **Bold what matters** (weights, lead phrases, warnings). Specific over vague, verified
numbers only, disclaimers where appropriate.

---

## Output

These three strings feed the create/rebalance/update payload's `version` block:

```jsonc
"version": {
  "about":     "{about markdown}",
  "riskNotes": "{riskNotes markdown}",
  "resources": "{resources markdown}"
}
```

Return to whichever flow sent you here (Flow A Step 10, Flow B Step 5, or Flow C Step 9) with
the three fields filled in. Don't publish — the skill is draft-only by design.
