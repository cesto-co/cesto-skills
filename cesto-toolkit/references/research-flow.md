# Research-Assisted Basket Creation Flow

Read this file when the user wants to create a basket but doesn't know what tokens to include.
This flow guides you through researching the crypto/Solana market and translating findings into
a basket the user can publish on Cesto Labs.

After this flow completes, return to the main **Create a basket flow** in SKILL.md at **Step 3
(Validate tokens)** with the user's finalized tokens, allocations, title, and description.

---

## Phase 1: Research

Research happens in three rounds. Each round builds on the previous one. Use WebSearch for all
searches — if WebSearch is unavailable, skip to the [Fallback](#fallback-when-web-search-is-unavailable)
section at the bottom.

### Round 1: Macro narratives and sector trends

Goal: Identify 3–5 active narratives or sector trends in the Solana/crypto ecosystem.

Run these searches (adapt phrasing based on the current date):

```
"Solana ecosystem trends {current_month} {current_year}"
"top performing crypto sectors this week"
"crypto narrative {current_month} {current_year}"
"Solana DeFi TVL growth {current_year}"
"trending Solana tokens this week"
```

From the results, extract the dominant narratives. Examples of what a narrative looks like:
- "AI tokens surging on Solana"
- "RWA tokenization gaining traction"
- "Meme coin rotation into utility tokens"
- "DePIN protocols seeing adoption growth"
- "Solana DeFi blue chips outperforming"
- "Gaming/metaverse tokens rallying"

Pick the 3–5 strongest narratives based on how frequently they appear across sources and
how recent the momentum is.

### Round 2: Token discovery within narratives

Goal: Build a candidate list of 10–15 tokens across the identified narratives.

For each narrative from Round 1, run a targeted search:

```
"top {narrative} tokens Solana {current_year}"
"best {narrative} coins Solana"
"{narrative} Solana projects to watch"
```

For example, if "AI tokens" is a narrative:
```
"top AI tokens Solana 2025"
"best AI crypto projects Solana ecosystem"
```

For each token you find, note:
- Token name and symbol
- Why it's relevant to the narrative (one line)
- Any recent catalysts (launches, partnerships, exchange listings)

### Round 3: Validation and filtering

Goal: Filter candidates down to only tokens supported on Cesto.

1. Fetch the Cesto supported token list:
   ```bash
   python3 <skill-path>/scripts/api_request.py GET https://backend.cesto.co/tokens 2>/dev/null
   ```

2. Cross-reference your candidate tokens against this list. Match by symbol (case-insensitive).

3. Drop any tokens not supported on Cesto. Note which popular candidates were dropped — you'll
   mention this to the user so they understand the available options.
   If fewer than 3 tokens survive filtering, browse the full Cesto token list and suggest
   additional tokens that fit the narrative or complement the user's theme.

4. Optionally, check how these tokens appear in existing Cesto baskets for additional context:
   ```bash
   python3 <skill-path>/scripts/fetch_baskets.py 2>/dev/null
   ```
   This shows what other basket creators have done with these tokens — useful for allocation inspiration.

---

## Phase 2: Present Findings

Present your research to the user grouped by narrative — not as a flat token list. This helps
the user understand the "why" behind each token, not just the "what."

Use this format:

```
Here's what I found happening in the crypto market right now:

**[Narrative 1: e.g., "AI Infrastructure on Solana"]**
Brief context: [1-2 sentences on why this narrative is active]
- [Token A (SYMBOL)] — [one-line reason it's relevant]
- [Token B (SYMBOL)] — [one-line reason]
Available on Cesto: [list which of the above are supported]

**[Narrative 2: e.g., "DeFi Blue Chips"]**
Brief context: [1-2 sentences]
- [Token C (SYMBOL)] — [one-line reason]
Available on Cesto: [list]

**[Narrative 3]**
...
```

If some popular tokens from the research aren't on Cesto, briefly mention it:
> "Note: [Token X] and [Token Y] came up frequently in my research but aren't currently
> available on the Cesto platform."

Then ask the user:
> "Which of these themes interest you? We can build a basket around one narrative, or
> mix tokens from multiple themes. What sounds good to you?"

Wait for the user's response before proceeding.

---

## Phase 3: Collaborative Allocation

Once the user picks their preferred themes and tokens:

### 1. Suggest an initial allocation

Propose a starting allocation using common portfolio construction principles:
- **Higher market cap / more established tokens** → larger allocation (e.g., 30–50%)
- **Mid-cap tokens with strong narrative momentum** → moderate allocation (e.g., 15–30%)
- **Smaller / more speculative tokens** → smaller allocation (e.g., 5–15%)
- All allocations must sum to exactly 100%

Present the suggestion clearly:

```
Here's a starting allocation based on what we discussed:

| Token | Allocation | Rationale |
|-------|-----------|-----------|
| SOL   | 40%       | Ecosystem backbone, most liquid |
| RNDR  | 25%       | Leading AI narrative, strong momentum |
| JTO   | 20%       | DeFi blue chip, Jito staking growth |
| BONK  | 15%       | Community token, high social momentum |

This weights heavier toward established tokens for stability, with smaller
positions in higher-momentum plays. Want to adjust anything?
```

### 2. Let the user adjust

The user may want to change percentages, add tokens, or remove tokens. Iterate until
they're happy. After each change, show the updated table and confirm allocations still
sum to 100%.

### 3. Draft title and description

Based on the research narrative and the user's chosen tokens, suggest a basket title and
description:

- **Title**: Short, catchy, reflects the thesis (e.g., "Solana AI Wave", "DeFi Power Pack",
  "Narrative Alpha"). Keep it under 100 characters.
- **Description**: 2–4 sentences summarizing the investment thesis. Reference the narrative
  from the research — why these tokens, why now. Keep it under 1000 characters.

Show both to the user and let them edit before finalizing.

---

## Phase 4: Handoff

Once the user has confirmed:
- Token selection and allocations (summing to 100%)
- Basket title
- Basket description

Return to the main **Create a basket flow** in SKILL.md at **Step 3 (Validate tokens)**.
The tokens were already cross-referenced with the `/tokens` API during Round 3, but
re-validate to catch any edge cases (e.g., a token was delisted between research and
creation). Then proceed through Preview → Publish → Result as normal.

---

## Fallback: When Web Search Is Unavailable

If WebSearch and WebFetch tools are not available, you can still help the user build a
basket using existing Cesto data:

1. Fetch all baskets and analytics:
   ```bash
   python3 <skill-path>/scripts/fetch_baskets.py --sort=24h 2>/dev/null
   ```

2. Run an investment analysis for deeper token-level data:
   ```bash
   python3 <skill-path>/scripts/analyze_investment.py --top=5 2>/dev/null
   ```

3. Present what other basket creators have built — their themes, token choices, and
   performance. Use this as inspiration rather than real-time research.

4. Ask the user which existing baskets or tokens interest them, and help them build
   a new basket from there.

5. Be upfront: "I don't have access to web search right now, so I'm using data from
   existing Cesto baskets to help you decide. For the latest market trends, you might
   want to check crypto news sources and come back with specific tokens in mind."

Then continue to Phase 3 (Collaborative Allocation) and Phase 4 (Handoff) as normal.
