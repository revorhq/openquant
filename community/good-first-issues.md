# Good-first-issues pipeline (F5.5)

A standing pipeline of low-context, high-clarity issues for first-time
contributors. Goal: a beginner ships in ≤60 minutes from cloning.

## Standing template

```
title: [GFI] <verb the file> <what>
labels: good first issue, area/<package>

### Context
One paragraph: what this is, why it exists.

### Acceptance criteria
- [ ] Code change
- [ ] Test added or updated
- [ ] Docs updated if user-facing
- [ ] `uv run pytest -q` passes

### Hints
- Files: `packages/<pkg>/src/...`
- Related: <link to PR or docs page>

### How to ask for help
Open in `#good-first-issues` on Discord, tag the maintainer who labeled.
```

## Mandatory hygiene

- Every GFI has a single owner-of-the-week (rotating).
- An issue stale ≥14 days is unassigned automatically by the bot.
- Maintainers MUST not steal a GFI; the point is the contributor lands.
- Reviews on GFI PRs prioritized in <48h.

## Starter buckets we always keep stocked

1. **Docs**: typo, broken anchor, missing example.
2. **`oq-data`**: add a new corporate-action fixture and the matching test.
3. **`oq-backtest`**: add a broker cost preset (Groww, AngelOne, IIFL) with a
   reference link and unit test against fees.
4. **`oq-broker`**: extend paper engine with a documented edge case
   (e.g. freeze quantity for a specific symbol family).
5. **`oq-mcp`**: add a screener filter (e.g. `marketcap.lt`).
6. **`oq-zoo`**: write the README for an educational strategy.

## Funneling

- Quarterly bug-bash: pin one GFI sprint, three maintainers on call.
- Cohort GFIs (see cohorts.md): each cohort participant ships ≥1 GFI to graduate.
- Conference recruiting: hand out QR codes pointing to the GFI label filter.
