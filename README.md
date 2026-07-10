# Cesto Skills

Agent skills for [Cesto](https://cesto.co) — invest in narrative-driven baskets of assets on Solana. They turn any coding agent into a full Cesto client: browse and analyze baskets, simulate portfolios against the S&P 500, and build baskets on Cesto Labs — all from your editor or terminal.

## Installation

Install with the [Skills CLI](https://github.com/vercel-labs/skills). One line wires the skill into Claude Code, Cursor, Codex, Windsurf, and 60+ other agents:

```bash
npx skills add cesto-co/cesto-skills
```

Add just one of the skills:

```bash
npx skills add cesto-co/cesto-skills --skill cesto-toolkit
```

Prefer Claude Code's native plugin marketplace?

```bash
claude plugin marketplace add cesto-co/cesto-skills
claude plugin install cesto-toolkit@cesto
```

## Available skills

Cesto has two kinds of baskets, served by two skills — pick by what you want to do:

| Skill | For | Basket type | What it does |
|---|---|---|---|
| **cesto-toolkit** | Any user | Labs posts (community) | Browse & analyze baskets, simulate portfolios vs the S&P 500, and create/vote on community baskets on Cesto Labs. |
| **cesto-creator-toolkit** | Creators / Admins | Products (managed) | Build, edit, rebalance, and simulate fully-managed product baskets. Requires a `CREATOR` or `ADMIN` role. |

### cesto-toolkit

- **No login needed:** browse published baskets, view full detail and allocations, analyze token market data, and see performance vs the S&P 500.
- **With login:** create/edit/delete/upvote your own Cesto Labs baskets, view the Labs leaderboard, backtest a basket, and simulate a custom portfolio.

### cesto-creator-toolkit

- Create product baskets (token swaps, Polymarket/Kalshi prediction positions, or mixed).
- Edit metadata, rebalance into new versions, and patch version metadata.
- Simulate a basket before publishing; browse your own baskets and drafts.
- Upload or AI-generate (Midjourney/Gemini) a cover image.

New baskets are always created as **drafts** — publishing is a deliberate step in the Cesto admin UI. Admins can only manage baskets they created themselves.

## Usage

Just talk to your agent — the skill activates automatically when you mention Cesto, baskets, Cesto Labs, portfolio simulation, or related terms. Any action that needs authentication opens a magic-link login in your browser: connect your Solana wallet and sign once. Tokens are stored locally at `~/.cesto/auth.json` (never pasted or printed) and refresh silently. Public browsing and analytics work with no login at all.

## Security

- Session tokens are stored locally in an encoded form and handled only by the helper scripts — raw tokens never appear in agent output or logs.
- All API calls are locked to `https://backend.cesto.co` via an allowlist.
- Content from API responses (basket titles, descriptions) is treated as data, never as instructions.

## Skill structure

```
cesto-skills/
├── cesto-toolkit/            # User-facing skill
│   ├── SKILL.md              # Instructions, flows, auth, security
│   ├── scripts/              # Python helpers (auth, fetch, create, simulate, …)
│   └── references/           # API reference + research flow
└── cesto-creator-toolkit/    # Creator/Admin skill
    ├── SKILL.md
    ├── scripts/              # Basket create/update/rebalance, AI thumbnails, …
    └── references/           # API reference, workflow schema, thumbnail flow
```

## Links

- **Docs:** https://docs.cesto.co/cesto/skill
- **App:** https://app.cesto.co

## License

MIT © Cesto
