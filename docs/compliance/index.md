# Compliance

OpenQuant India is built for the SEBI 2026 regime.

- [SEBI 2026 explainer](sebi-2026.md) — what the framework requires.
- [Disclaimer](disclaimer.md) — what this project is and isn't.

## TL;DR

- Every live order carries a SEBI-registered `algo_id` and strategy
  metadata.
- Every action is appended to a hash-chained, append-only audit log.
- A kill switch is mandatory and lives in framework core.
- Live mode requires `OQ_LIVE_TRADING=1` + `i_accept_live_risk=True`.
- Paper-first by default. Always.
