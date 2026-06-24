# Contributing

The source of truth is [`CONTRIBUTING.md`](https://github.com/revorhq/openquant/blob/main/CONTRIBUTING.md)
in the repo. Highlights:

- Sign off commits with `git commit -s` (we use the DCO).
- New code needs tests. Data-touching code needs **golden-dataset** tests.
- One logical change per PR.
- Lint: `uv run ruff check . && uv run ruff format --check .`
- Tests: `uv run pytest`.

## The honesty bar

- No claim without a number or a test.
- Data correctness is a P0 bug. Bad adjusted prices are reverted within
  hours and post-mortemed publicly.
- Cost calculations are exact — use `Decimal` or integer paise where
  rounding matters.
- Survivorship bias is forbidden. Backtests against fixed modern
  universes are not accepted.
