# OpenQuant India — Discord channel structure (F5.3)

Goal: a server that is easy to navigate on day one, scales to thousands,
and mirrors the project's principles (honesty, paper-first, composability).

## Categories and channels

### `#welcome`
- `#read-me-first` — rules, disclaimer, paper-first culture
- `#introductions` — `name / city / one strategy you'd like to honestly backtest`
- `#announcements` — releases, postmortems, events (read-only)
- `#community-rules` — code of conduct, moderation policy

### `#help`
- `#install-and-setup` — `uv`, Python, environment issues
- `#oq-data-help` — bhavcopy, corporate actions, PIT universes
- `#oq-backtest-help` — costs, tearsheets, walk-forward
- `#oq-mcp-help` — Claude Desktop, screener DSL
- `#oq-broker-help` — Kite/Dhan/Upstox/Fyers, paper engine, SEBI-2026

### `#research`
- `#strategy-ideas` — share, not sell
- `#honest-teardowns` — "famous strategy, net of costs"
- `#data-questions` — corporate actions, mergers, splits edge cases
- `#papers` — Indian-market literature

### `#contribute`
- `#good-first-issues` — bot-mirrored from GitHub
- `#oq-zoo-strategies` — propose, get reviewed before PR
- `#docs-and-cookbook` — doc-only contributors
- `#contributor-lounge` — meta, planning, RFC discussions

### `#compliance`
- `#sebi-2026` — circulars, interpretations
- `#broker-tos` — Kite Connect ToS, automation policy
- `#audit-and-logs` — Algo-IDs, immutable journals

### `#cohorts`
- `#cohort-current` (rotates each cohort)
- `#cohort-archive`
- `#challenge-30-days` — daily prompts, submissions

### `#community`
- `#showcase` — what you built (research, blog posts, talks)
- `#jobs` — hiring/looking
- `#off-topic` — keep it civil, no calls/tips

### Voice
- `#voice-coworking`
- `#voice-office-hours` (maintainers, weekly)

## Roles

- `@maintainer` — repo write access
- `@contributor` — has a merged PR
- `@cohort-X` — current cohort participants
- `@zoo-strategist` — has a strategy in `oq-zoo`
- `@compliance-watcher` — flagged interest in SEBI updates
- `@member` — default

## Bots

- GitHub bot mirrors `good-first-issues`, releases, security advisories
- Modmail for DMing the mod team
- Disboard for discoverability

## Moderation guardrails

- **No tips, signals, or returns talk.** Auto-warn on `pump`, `tip`, `target`,
  `guaranteed`, `multibagger`. Three strikes = mute.
- **No DM solicitation.** Posts with "DM me for…" auto-flagged.
- **Promote = contribute first.** New accounts must have one help/research
  post before posting in `#showcase`.

## Onboarding ritual

1. Read `#read-me-first`, react with ✅
2. Post in `#introductions`
3. Try the 60-second quickstart, share tearsheet in `#showcase`
4. Pick one `#good-first-issue`
