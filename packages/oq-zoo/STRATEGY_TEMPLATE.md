# Strategy template

Copy this file (and the surrounding `strategies/<your_strategy>/`
folder layout) when proposing a new strategy.

```
packages/oq-zoo/src/oq_zoo/strategies/<your_strategy>/
├── __init__.py        # registers the strategy with REGISTRY
├── signal.py          # signal_fn(prices) -> weights
├── README.md          # claim, mechanism, benchmark, sources
└── tests/test_honest.py  # honesty-gate hook (build spec from a small fixture)
```

## Required fields

- `name`: snake_case, globally unique.
- `category`: one of `momentum`, `mean_reversion`, `factor`, `event`, `educational`.
- `author`: GitHub handle or full name.
- `description`: one-paragraph what + why.
- `signal_fn`: callable `(prices: pd.DataFrame) -> pd.DataFrame` of target weights.
- `benchmark`: a meaningful comparator, e.g. `"NIFTY500_EQUAL_WEIGHT"`.
- `universe`: `"NIFTY50"`, `"NIFTY100"`, `"NIFTY500"`, etc. — point-in-time.
- `cost_preset`: `"zerodha"`, `"upstox"`, `"fyers"`, `"dhan"`, `"full_service"`.
- `rebalance`: `"D"`, `"W"`, `"ME"`, `"QE"`.

## The merge gate

Your PR runs `oq-zoo gate` in CI. It must:

1. Produce a clean reference backtest.
2. Beat the declared benchmark **net of costs** (unless tagged `educational`).
3. Show a non-negative walk-forward OOS Sharpe.

If your strategy is an *honest loser* with educational value, tag it
`educational` in the `tags` field and explain what it teaches.
