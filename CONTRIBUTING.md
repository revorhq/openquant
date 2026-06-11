# Contributing to OpenQuant India

Thanks for considering a contribution. This document covers what we expect,
how to get set up, and the merge bar.

## TL;DR

- Be honest about costs, data, and limitations. The whole project rests on it.
- Sign off your commits (`git commit -s`) — we use the [DCO](https://developercertificate.org/).
- New code needs tests. Data-touching code needs golden-dataset tests.
- Follow the [Code of Conduct](./CODE_OF_CONDUCT.md).

## Ways to contribute

- **Bug reports** — especially data correctness bugs. Use the issue template
  and include a reproducible example and the expected vs actual values.
- **Good-first-issues** — look for the `good first issue` label.
- **Documentation** — clarifications, fixes, cookbook recipes.
- **Strategy contributions** (when `oq-zoo` opens) — must pass the
  honest-cost backtest + walk-forward gate.
- **Compliance updates** — when SEBI/NSE/BSE change a rule, PRs welcome.

## Dev setup

We use [`uv`](https://github.com/astral-sh/uv) for environment management
and [`ruff`](https://github.com/astral-sh/ruff) for lint/format.

```bash
git clone https://github.com/openquant-india/openquant
cd openquant
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

If everything passes, you're ready to make changes. Run the same commands
before pushing.

## Coding standards

- **Python 3.11+.** Use `StrEnum`, `dataclass(slots=True)`, `from __future__
  import annotations` where helpful.
- **Type hints everywhere** in `src/`. We will progressively enable strict
  type checking.
- **Docstrings** for every public class and function. Explain *what* and
  *why*, not *how*.
- **Tests** under `packages/<pkg>/tests/`, mirroring the source layout.
- **No new dependencies** in `oq-core` without strong justification —
  the core package must stay lean.
- **Line length 100**, formatting handled by `ruff format`.

## Commits and PRs

- **Conventional commit prefixes** preferred: `feat:`, `fix:`, `docs:`,
  `test:`, `chore:`, `refactor:`, `ci:`.
- **DCO sign-off required**: `git commit -s -m "feat(core): add Instrument"`.
- **One logical change per PR.** Smaller PRs ship faster.
- **PR description** should explain the *why*, not just the *what*.
- **Tests must pass** in CI before review.

## The honesty bar (this is what makes the project worth using)

- **No claim without a number or a test.** If you say "this is faster" or
  "this is more accurate", include benchmarks or a regression test.
- **Data correctness is a P0 bug.** If you ship a bad adjusted price, expect
  it to be reverted within hours and post-mortemed publicly. We don't hide
  bugs.
- **Cost calculations are exact.** Use `Decimal` or integer paise where
  rounding matters. No silently-truncating floats.
- **Survivorship bias is forbidden.** Any backtest example using a fixed
  modern universe ("today's Nifty 500 since 2010") must be flagged in code
  comments and replaced with a point-in-time universe as soon as `oq-data`
  Phase 1.5 lands.

## Reporting security issues

Please do not file public issues for security problems. Email the maintainers
(address will be added in the repo settings once published). For
non-security bugs, GitHub issues are the right place.

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](./LICENSE), and you certify the DCO with every commit.
