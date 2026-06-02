# Workflow Definition — Bucket-Model Reference

Open this file whenever you need to construct, inspect, or modify a `definition` object that you'll send to the Cesto backend (create, rebalance, simulate). The backend validates definitions against `WorkflowParser` and rejects anything that doesn't conform — so the rules here matter literally.

## Table of contents

1. [Why a bucket model](#why-a-bucket-model)
2. [Top-level `WorkflowDefinition` shape](#top-level-workflowdefinition-shape)
3. [A bucket: `WorkflowNodes`](#a-bucket-workflownodes)
4. [A node: `WorkflowNode`](#a-node-workflownode)
5. [The `amount` field — `AmountSource` variants](#the-amount-field--amountsource-variants)
6. [Placeholders inside `parameters`](#placeholders-inside-parameters)
7. [`submitMethod` — which one to use](#submitmethod--which-one-to-use)
8. [Per-`nodeType` reference](#per-nodetype-reference)
   - [`swap.token`](#swaptoken)
   - [`prediction.open`](#predictionopen)
   - [`prediction.close`](#predictionclose)
9. [Drop-in templates](#drop-in-templates)
   - [Token-only open basket](#template-1--token-only-open-basket)
   - [Mixed open basket (swap + prediction)](#template-2--mixed-open-basket-swap--prediction)
   - [Prediction-only open basket](#template-3--prediction-only-open-basket)
10. [Allocation rules](#allocation-rules)
11. [Migration from the legacy flat shape](#migration-from-the-legacy-flat-shape)

---

## Why a bucket model

The old shape stored a flat `nodes` array plus a `connections` array that wired START → action → submit. The new shape replaces all that wiring with three named phases that run in order:

```
pre?  →  bucket  →  post?
```

Each phase is a "bucket" of nodes that runs either in parallel or sequentially. The submit step is no longer a node — every action node carries its own `submitMethod`. This makes rebalance possible: sells go in `bucket` (`amount.fixed`), buys go in `post` (`amount.proceeds`).

For a creator-built basket, you almost always need only `bucket`. Use `mode: "parallel"` so every position opens at the same time off a single user input.

## Top-level `WorkflowDefinition` shape

```jsonc
{
  "pre":    { /* WorkflowNodes — optional, runs first */ },
  "bucket": { /* WorkflowNodes — REQUIRED main stage */ },
  "post":   { /* WorkflowNodes — optional, runs last  */ }
}
```

`bucket` is the only required key. The backend rejects any definition without it.

## A bucket: `WorkflowNodes`

```jsonc
{
  "mode": "parallel",            // "parallel" | "sequential"  (required)
  "nodes": [ /* WorkflowNode[] — at least one */ ],
  "simulateBeforeSubmit": false, // optional
  "delayAfterMs": 0,             // optional, ms to wait after the bucket completes
  "delayBeforeMs": 0             // optional, ms to wait before the bucket starts
}
```

- `mode: "parallel"` — all nodes fire off the same input, no ordering dependency. Use this for "fan-out" baskets where each allocation is independent.
- `mode: "sequential"` — nodes run one after another; a later node can reference an earlier node's output via `amount: { node, output }`. Rare in creator-built open baskets.

## A node: `WorkflowNode`

```jsonc
{
  "id": "swap-sol",              // required, unique across the whole definition
  "nodeType": "swap.token",      // required, see registry below
  "submitMethod": "jupiter",     // required, "jupiter" | "rpc"
  "amount": { "percentage": 40 },// optional but almost always present for buys
  "delayAfterMs": 0,             // optional
  "parameters": { /* node-specific */ }
}
```

Rules the parser enforces:
- `id` must be unique across `pre`, `bucket`, and `post` combined.
- `nodeType` must be a string the executor recognizes.
- `submitMethod` must be exactly `"jupiter"` or `"rpc"` — `"jito"` is gone, do not use it.
- `parameters` must be an object (never null).
- Within a `parallel` bucket, no node may reference a sibling via `amount.node` — siblings have no defined order.

## The `amount` field — `AmountSource` variants

`amount` is at the **node level**, not inside `parameters`. Exactly one of these four shapes:

| Shape | When | Example |
|---|---|---|
| `{ "percentage": N }` | Open / new version. Take `N` percent of the user's input amount. `N` is an integer 0-100. | `{ "percentage": 40 }` |
| `{ "proceeds": N }` | Rebalance buys (`post` bucket). Take `N` percent of the realised sell proceeds. | `{ "proceeds": 50 }` |
| `{ "fixed": "<base-units>" }` | Rebalance sells (`bucket`). Exact base-unit amount the analyzer pre-computed. | `{ "fixed": "5000000" }` |
| `{ "node": "id", "output": "name" }` | Chain off an earlier node's named output. Only in sequential buckets. | `{ "node": "lend-1", "output": "borrowAmount" }` |

For creator-built **open** baskets (the common case in this skill), every action node uses `{ "percentage": N }`. The skill never builds explicit rebalance-style sell/buy definitions — that's the backend's job once a new open-style version is published and an investor rebalances their position.

## Placeholders inside `parameters`

Use the literal string `"$userAddress"` anywhere a node needs the investor's wallet (e.g. `recipient` on swap, `userWallet` on prediction). The executor substitutes the real pubkey at runtime.

```jsonc
"recipient":  "$userAddress",
"userWallet": "$userAddress"
```

The old Liquid-template syntax (`"{{ $input.userAddress }}"`, `"{{ $input.amount * 0.13 }}"`) is no longer interpreted. Don't use it.

## `submitMethod` — which one to use

| Node category | `submitMethod` |
|---|---|
| Token swaps (`swap.token`) | `"jupiter"` |
| Prediction markets (`prediction.open`, `prediction.close`) | `"rpc"` |
| Lending / perps (`lending.*`, `drift.*`) | `"rpc"` |

The reason: swaps route through Jupiter's aggregator (which has its own submission path); prediction and DeFi positions land via standard Solana RPC.

---

## Per-`nodeType` reference

### `swap.token`

Swap input tokens for an output token via Jupiter (or DFlow). The canonical action for token allocations in a basket.

**`parameters` fields**

| Field | Type | Required | Notes |
|---|---|---|---|
| `chain` | `string` | yes | Always `"solana"` today. |
| `fromToken` | `string` | yes | Source mint. For an open basket funded by USDC: `"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"`. |
| `toToken` | `string` | yes | Destination mint (the token you're buying). |
| `recipient` | `string` | yes | Use `"$userAddress"`. |
| `slippage` | `number` | optional | Basis points (1-1000). Default `50`. Use `100` for volatile tokens. |
| `purpose` | `"buy" \| "swap"` | optional | Default `"buy"`. Use `"buy"` for basket allocations (tracked as positions). `"swap"` is for intermediary hops. |
| `protocol` | `"jupiter" \| "dflow"` | optional | Default `"jupiter"`. |
| `router` | `string` | optional | Comma-separated routers (e.g. `"iris,dflow"`). Default empty. |

**Note**: `amount` is **not** in `parameters` — it goes at the node level as `amount: { percentage: N }`.

**Canonical node**

```jsonc
{
  "id": "swap-sol",
  "nodeType": "swap.token",
  "submitMethod": "jupiter",
  "amount": { "percentage": 40 },
  "parameters": {
    "chain": "solana",
    "fromToken": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "toToken": "So11111111111111111111111111111111111111112",
    "recipient": "$userAddress",
    "slippage": 50,
    "purpose": "buy",
    "protocol": "jupiter"
  }
}
```

### `prediction.open`

Buy a YES/NO outcome on a Polymarket or Kalshi market. Use for prediction-market allocations in a basket.

**`parameters` fields**

| Field | Type | Required | Notes |
|---|---|---|---|
| `protocol` | `"polymarket" \| "kalshi"` | yes | Match the market ID prefix: `POLY-…` → `polymarket`, `KX…` → `kalshi`. |
| `marketTicker` | `string` | yes | Full market id (e.g. `"POLY-573656"`, `"KXBTCMAX150-25-26FEB28-149999.99"`). |
| `eventTicker` | `string` | yes | Event id the market belongs to. |
| `seriesTicker` | `string` | yes | Same as `eventTicker` for Polymarket; the series root (e.g. `"KXBTCMAX150"`) for Kalshi. When unsure, use the event id — the enrichment step backfills the right value. |
| `title` | `string` | yes | Human-readable market title (used in UI). |
| `side` | `"YES" \| "NO"` | yes | Uppercase. |
| `closeTime` | `number` | yes | Unix seconds. Pulled from the market detail response. |
| `userWallet` | `string` | yes | Use `"$userAddress"`. |
| `slippageBps` | `number` | optional | Basis points (100-1500). Default `500`. |
| `eventTitle` | `string` | optional | Event-level question for nicer UI rendering. |
| `eventImageUrl` | `string` | optional | Fallback image when market image is missing. |

**Note**: `amount` is at the node level (`amount: { percentage: N }`), not in `parameters`. The old "amount as base-units string in parameters" convention is gone.

**Canonical node**

```jsonc
{
  "id": "pred-btc150k-yes",
  "nodeType": "prediction.open",
  "submitMethod": "rpc",
  "amount": { "percentage": 30 },
  "parameters": {
    "protocol": "polymarket",
    "marketTicker": "POLY-573656",
    "eventTicker": "POLY-36173",
    "seriesTicker": "POLY-36173",
    "title": "Bitcoin $150k by Dec 2026",
    "side": "YES",
    "closeTime": 1798776000,
    "userWallet": "$userAddress",
    "slippageBps": 500
  }
}
```

### `prediction.close`

Closes an existing prediction position. Not used in creator-built open baskets — the backend handles closes server-side when a basket is exited. Included here only so you recognize it in existing definitions.

---

## Drop-in templates

Copy, adjust the IDs / mints / market tickers / percentages, and validate that allocations sum to 100.

### Template 1 — Token-only open basket

```jsonc
{
  "bucket": {
    "mode": "parallel",
    "nodes": [
      {
        "id": "swap-sol",
        "nodeType": "swap.token",
        "submitMethod": "jupiter",
        "amount": { "percentage": 40 },
        "parameters": {
          "chain": "solana",
          "fromToken": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
          "toToken": "So11111111111111111111111111111111111111112",
          "recipient": "$userAddress",
          "slippage": 50,
          "purpose": "buy",
          "protocol": "jupiter"
        }
      },
      {
        "id": "swap-jup",
        "nodeType": "swap.token",
        "submitMethod": "jupiter",
        "amount": { "percentage": 35 },
        "parameters": {
          "chain": "solana",
          "fromToken": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
          "toToken": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
          "recipient": "$userAddress",
          "slippage": 100,
          "purpose": "buy",
          "protocol": "jupiter"
        }
      },
      {
        "id": "swap-bonk",
        "nodeType": "swap.token",
        "submitMethod": "jupiter",
        "amount": { "percentage": 25 },
        "parameters": {
          "chain": "solana",
          "fromToken": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
          "toToken": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
          "recipient": "$userAddress",
          "slippage": 100,
          "purpose": "buy",
          "protocol": "jupiter"
        }
      }
    ]
  }
}
```

### Template 2 — Mixed open basket (swap + prediction)

```jsonc
{
  "bucket": {
    "mode": "parallel",
    "nodes": [
      {
        "id": "swap-sol",
        "nodeType": "swap.token",
        "submitMethod": "jupiter",
        "amount": { "percentage": 40 },
        "parameters": {
          "chain": "solana",
          "fromToken": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
          "toToken": "So11111111111111111111111111111111111111112",
          "recipient": "$userAddress",
          "slippage": 50,
          "purpose": "buy",
          "protocol": "jupiter"
        }
      },
      {
        "id": "pred-btc150k-yes",
        "nodeType": "prediction.open",
        "submitMethod": "rpc",
        "amount": { "percentage": 30 },
        "parameters": {
          "protocol": "polymarket",
          "marketTicker": "POLY-573656",
          "eventTicker": "POLY-36173",
          "seriesTicker": "POLY-36173",
          "title": "Bitcoin $150k by Dec 2026",
          "side": "YES",
          "closeTime": 1798776000,
          "userWallet": "$userAddress",
          "slippageBps": 500
        }
      },
      {
        "id": "pred-eth-eoy-no",
        "nodeType": "prediction.open",
        "submitMethod": "rpc",
        "amount": { "percentage": 30 },
        "parameters": {
          "protocol": "polymarket",
          "marketTicker": "POLY-481223",
          "eventTicker": "POLY-30221",
          "seriesTicker": "POLY-30221",
          "title": "ETH > $5k by Dec 2026",
          "side": "NO",
          "closeTime": 1798776000,
          "userWallet": "$userAddress",
          "slippageBps": 500
        }
      }
    ]
  }
}
```

### Template 3 — Prediction-only open basket

```jsonc
{
  "bucket": {
    "mode": "parallel",
    "nodes": [
      {
        "id": "pred-1",
        "nodeType": "prediction.open",
        "submitMethod": "rpc",
        "amount": { "percentage": 60 },
        "parameters": {
          "protocol": "polymarket",
          "marketTicker": "POLY-573656",
          "eventTicker": "POLY-36173",
          "seriesTicker": "POLY-36173",
          "title": "Bitcoin $150k by Dec 2026",
          "side": "YES",
          "closeTime": 1798776000,
          "userWallet": "$userAddress",
          "slippageBps": 500
        }
      },
      {
        "id": "pred-2",
        "nodeType": "prediction.open",
        "submitMethod": "rpc",
        "amount": { "percentage": 40 },
        "parameters": {
          "protocol": "kalshi",
          "marketTicker": "KXBTCMAX150-25-26FEB28-149999.99",
          "eventTicker": "KXBTCMAX150-25",
          "seriesTicker": "KXBTCMAX150",
          "title": "BTC max above $150k by Feb 2026",
          "side": "YES",
          "closeTime": 1772352000,
          "userWallet": "$userAddress",
          "slippageBps": 500
        }
      }
    ]
  }
}
```

---

## Allocation rules

1. **Integer percentages only.** `{ "percentage": 33 }` is valid; `{ "percentage": 33.3 }` is not.
2. **Sum to exactly 100.** If you have a remainder (e.g. five tokens at 20%), good. If you have rounding error (e.g. three positions at 33% summing to 99%), add the extra point to the largest allocation.
3. **One node per allocation.** Don't try to split a single token across two nodes; merge them.
4. **Node IDs must be unique across the entire definition.** `swap-sol` and `swap-sol-2` are fine; two nodes both named `swap-sol` will be rejected.
5. **At least one node** in `bucket`. Empty buckets are rejected.

---

## Migration from the legacy flat shape

If you're reading a definition from an older basket (or a stale doc), here's how to translate:

| Old field | New equivalent |
|---|---|
| `definition.id` | Drop. The version row's id is the ProductVersion UUID. |
| `definition.name`, `definition.type` | Drop. Name lives on the product/workflow; type is implicit. |
| `definition.about` | Move to ProductVersion: `version.about`. |
| `definition.risk` | Move to ProductVersion: `version.riskNotes`. |
| `definition.resources` | Move to ProductVersion: `version.resources`. |
| `definition.tokenMint` | Move to ProductVersion: `version.inputTokenMint` (defaults to USDC). |
| `definition.tokenDecimal` | Move to ProductVersion: `version.inputTokenDecimals` (defaults to 6). |
| `definition.nodes[]` | Move inside `definition.bucket.nodes[]`. |
| `definition.connections[]` | Drop. `bucket.mode: "parallel"` replaces it. |
| `definition.tokenAllocations[]` | Drop. Derived at read time from each node's `amount`. |
| Node field `label` | Drop. Display labels are computed from `nodeType` + `parameters`. |
| Node field `description` | Drop (same reason). |
| Node field `protocols` | Drop. Protocols are inferred from `nodeType` and the parameter `protocol`. |
| Node `parameters.amount` (Liquid template) | Move to node-level `amount: { percentage: N }`. |
| `transaction.submit` node | Delete the node. Set `submitMethod` per action node instead. |
| `parameters.recipient: "{{ $input.userAddress }}"` | `parameters.recipient: "$userAddress"`. |
| `submitMethod: "jito"` | Use `"jupiter"` (swaps) or `"rpc"` (predictions/lending). |

When in doubt, prefer the templates above — they reflect the current parser exactly.
