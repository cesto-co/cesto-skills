# Research-Assisted Basket Creation Flow (Creator)

Read this file when the user wants to create a basket but doesn't know what tokens or prediction
markets to include. This flow guides you through researching the crypto/Solana market AND prediction
markets, then translating findings into a basket the user can publish.

After this flow completes, return to the main **Create a basket flow** in SKILL.md at **Step 3
(Token selection)** with the user's finalized tokens, predictions, allocations, title, and description.

---

## Phase 1: Research — Tokens

Research happens in four rounds. Each round builds on the previous one. Use WebSearch for all
searches — if WebSearch is unavailable, skip to the [Fallback](#fallback-when-web-search-is-unavailable)
section at the bottom.

### Round 1: Ecosystem Mapping (Theme → Real-World Connections)

Goal: Map the user's theme to a broader real-world ecosystem of companies, industries, and
economic forces that are connected to it — even if they aren't directly "about" the theme.

**This is the most important research step.** Don't just search for tokens that match the theme
by name. Think about who profits, who sponsors, who broadcasts, who supplies, and who benefits
when this theme succeeds.

Ask yourself these questions about the user's theme:

| Question | Example (F1 theme) |
|----------|-------------------|
| **Who sponsors/partners?** | Oracle (Red Bull), Amazon (Aston Martin), Visa (F1 global sponsor) |
| **Who has media/streaming rights?** | Amazon Prime Video (F1 broadcasts), Apple (F1 movie) |
| **Who provides technology?** | Microsoft (McLaren tech partner), Google Cloud |
| **Who benefits from growing viewership?** | Spotify (F1 podcasts), YouTube/Google (content) |
| **What industries are adjacent?** | Luxury brands, automotive, energy drinks, travel |
| **What financial instruments correlate?** | Related ETFs, sector indices |

For any theme, run searches like:
```
"{theme} sponsors {current_year}"
"{theme} media rights streaming deals"
"{theme} partnerships technology"
"{theme} industry revenue breakdown"
"companies that benefit from {theme} growth"
```

Build an **ecosystem map** — a list of companies/assets and their connection to the theme.
Each entry should have: company name, connection type (sponsor, media, tech, adjacent), and
a one-line explanation of why they benefit.

### Round 2: Macro narratives and sector trends

Goal: Identify 3–5 active narratives or sector trends in the Solana/crypto ecosystem that
intersect with the ecosystem map from Round 1.

Run these searches (adapt phrasing based on the current date):

```
"Solana ecosystem trends {current_month} {current_year}"
"top performing crypto sectors this week"
"crypto narrative {current_month} {current_year}"
"Solana DeFi TVL growth {current_year}"
"trending Solana tokens this week"
```

From the results, extract the dominant narratives. Examples:
- "AI tokens surging on Solana"
- "RWA tokenization gaining traction"
- "Meme coin rotation into utility tokens"
- "DePIN protocols seeing adoption growth"
- "Solana DeFi blue chips outperforming"
- "Tokenized equities gaining liquidity on Solana"

Pick the 3–5 strongest narratives. Prioritize narratives that align with the ecosystem map.

### Round 3: Token discovery within narratives + ecosystem

Goal: Build a candidate list of 10–15 tokens by combining two sources:

**Source A — Narrative-based tokens** (same as before):
For each narrative, run a targeted search:
```
"top {narrative} tokens Solana {current_year}"
"best {narrative} coins Solana"
```

**Source B — Ecosystem-mapped tokens** (from Round 1):
For each company/asset in the ecosystem map, check if a tokenized version exists on the
platform. This includes:
- Tokenized equities (e.g., ORCLx for Oracle, AMZNx for Amazon, AAPLx for Apple)
- Native crypto tokens of ecosystem participants (e.g., if a blockchain sponsors a team)
- Sector ETFs that capture the broader industry

For each token candidate, note: name, symbol, ecosystem connection (one line), and whether
it's from narrative research or ecosystem mapping.

### Round 4: Validation and filtering

Goal: Filter candidates to tokens supported on Cesto.

1. Fetch supported tokens:
   ```bash
   python3 <skill-path>/scripts/fetch_tokens.py 2>/dev/null
   ```
2. Cross-reference candidates against this list. Match by symbol (case-insensitive).
3. Drop unsupported tokens. Note dropped popular candidates to mention to the user.
4. If fewer than 3 survive, browse the full token list for alternatives that fit the
   ecosystem map or narrative.
5. **Prioritize tokens with clear ecosystem connections** — a token with a direct sponsor/media
   relationship to the theme is more compelling than a loosely related one.

---

## Phase 1.5: Research — Prediction Markets

Goal: Find prediction markets related to the user's theme or current trending events.

### If the user has a theme:

Search for prediction events related to their theme:
```bash
python3 <skill-path>/scripts/search_predictions.py --query "{theme_keywords}" 2>/dev/null
```

For example, if the theme is "AI crypto":
```bash
python3 <skill-path>/scripts/search_predictions.py --query "bitcoin" 2>/dev/null
python3 <skill-path>/scripts/search_predictions.py --query "crypto price" 2>/dev/null
```

### If exploring broadly:

Browse trending markets across categories:
```bash
python3 <skill-path>/scripts/search_predictions.py --filter trending 2>/dev/null
python3 <skill-path>/scripts/search_predictions.py --category crypto --filter trending 2>/dev/null
python3 <skill-path>/scripts/search_predictions.py --category sports --filter live 2>/dev/null
```

### For each relevant event found:

Note:
- Event title and ID
- Available markets with YES/NO prices
- Close time (is it relevant to the basket's timeframe?)
- How it correlates with the token picks (e.g., "Bitcoin $150k" pairs with BTC allocation)

---

## Phase 2: Present Findings

Present research grouped by **ecosystem connection** (not just narrative), showing the user
*why* each token is relevant to their theme:

```
Here's what I found:

**Ecosystem Map: {Theme}**

**Sponsors & Partners:**
- ORCLx (Oracle) — Title sponsor of Red Bull Racing; F1 visibility drives brand value
- AMZNx (Amazon) — F1 streaming rights on Prime Video; subscriber growth catalyst

**Media & Entertainment:**
- AAPLx (Apple) — Produced the F1 movie; potential future streaming rights play
- SPOTon (Spotify) — F1 podcasts and content partnerships

**Technology:**
- GOOGLx (Google) — YouTube F1 content, Google Cloud team partnerships

**Related prediction markets:**
- "George Russell - Drivers' Champion" → YES at $0.44
- "Mercedes - Constructors' Champion" → YES at $0.78

**Thesis:** {1-2 sentences explaining how the tokens and predictions are connected —
e.g., "Mercedes dominance drives both the prediction bets AND the sponsor tokens.
If F1 viewership keeps growing, the media & sponsor stocks benefit regardless of who wins."}
```

If some tokens aren't on Cesto, briefly mention it.

Then ask:
> "Which themes interest you? We can combine tokens and prediction markets into a single basket.
> Which tokens and markets would you like to include?"

---

## Phase 3: Collaborative Allocation

Once the user picks their tokens and prediction markets:

### 1. Suggest an initial allocation

Common patterns for mixed baskets:
- **Token-heavy (70-30):** 70% tokens, 30% predictions — for users who want market exposure with some event bets
- **Prediction-heavy (30-70):** 30% tokens, 70% predictions — for users who want to bet on specific outcomes
- **Balanced (50-50):** Equal split

Within each category:
- Higher market cap tokens → larger allocation (30-50%)
- Mid-cap narrative tokens → moderate (15-30%)
- Speculative tokens → smaller (5-15%)
- High-confidence predictions → larger allocation
- Speculative predictions → smaller allocation

Present clearly:

```
Here's a starting allocation:

| Type | Asset | Allocation | Rationale |
|------|-------|-----------|-----------|
| Token | SOL | 30% | Ecosystem backbone |
| Token | BTC | 20% | Store of value |
| Prediction | BTC $150k Dec 2026 YES | 25% | Bull thesis |
| Prediction | MicroStrategy holds BTC YES | 25% | Correlated bet |

Total: 100%
Base token: USDC

Want to adjust anything?
```

Base token is always USDC for all baskets.

### 2. Let the user adjust

Iterate until they're happy. Show updated table after each change. Verify sum = 100%.

### 3. Draft metadata

Based on the research and selections, suggest:

- **Title**: Short, reflects thesis (under 100 chars)
- **Description**: 2-4 sentences summarizing the thesis (under 1000 chars)
- **About**: Detailed strategy description (>= 20 chars). Explain each position and why.
- **Risk**: What could go wrong (>= 10 chars). Cover prediction risks (binary outcomes), token volatility.
- **Resources**: Thesis writeup with links/reasoning (>= 20 chars). Explain winning/losing scenarios.
- **Risk level**: LOW, MEDIUM, or HIGH based on the allocation composition
- **Minimum investment**: Always ask the creator how much the minimum should be (in USDC). Suggest a default based on the basket type (typically 10-15 USDC for prediction baskets, 5-10 USDC for token-only)

---

## Phase 4: Handoff

Once the user has confirmed everything, return to the main **Create a basket flow** in SKILL.md
at **Step 3 (Token selection)**. The tokens were already validated during Round 3, but
re-validate before creating. Then proceed through Steps 4-9 as normal.

---

## Fallback: When Web Search Is Unavailable

If WebSearch tools are not available, use your own knowledge to perform ecosystem mapping
and then validate against platform data.

1. **Ecosystem mapping from knowledge:** Use your training knowledge to map the user's theme
   to real-world companies and industries. Ask the same ecosystem questions from Round 1:
   - Who sponsors/partners in this space?
   - Who has media/streaming rights?
   - Who provides technology?
   - What industries are adjacent?
   
   Build the ecosystem map from your knowledge, then validate which tokens exist on the platform.

2. Fetch available tokens with prices:
   ```bash
   python3 <skill-path>/scripts/fetch_tokens.py 2>/dev/null
   ```

3. Cross-reference the ecosystem map against available tokens. Look for:
   - Tokenized equities of ecosystem companies (e.g., ORCLx, AMZNx)
   - Native crypto tokens of ecosystem participants
   - Relevant sector ETFs

4. Browse prediction markets related to the theme:
   ```bash
   python3 <skill-path>/scripts/search_predictions.py --query "{theme_keywords}" 2>/dev/null
   python3 <skill-path>/scripts/search_predictions.py --filter trending 2>/dev/null
   ```

5. Check existing baskets for inspiration:
   ```bash
   python3 <skill-path>/scripts/fetch_my_baskets.py 2>/dev/null
   ```

6. Present findings grouped by ecosystem connection (sponsors, media, tech, adjacent) —
   not just by token type.

7. Be upfront: "I don't have access to web search right now, so I'm using platform data
   and my knowledge of {theme} partnerships and sponsors to suggest tokens. For the latest
   deals and partnerships, you might want to verify before publishing."

Then continue to Phase 3 (Collaborative Allocation) and Phase 4 (Handoff) as normal.
