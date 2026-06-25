# Strategy zoo

Community-contributed strategies that pass the honesty gate.

The zoo lives under [`packages/oq-zoo/`](https://github.com/revorhq/openquant/tree/main/packages/oq-zoo).

## What the gate is

Every strategy PR runs a CI job that:

1. Executes the reference backtest with `costs="zerodha"` and the
   strategy's declared universe at point-in-time.
2. Runs walk-forward with the strategy's declared train/test windows.
3. Compares **net** CAGR to the strategy's declared benchmark.
4. **Fails the PR** if any of:
   - Net CAGR ≤ benchmark CAGR.
   - Walk-forward OOS Sharpe < 0.
   - Backtest uses a fixed modern universe.
   - Strategy declares no benchmark.

Honest losers are welcome — they're labeled `educational`. Strategies
that quietly outperform only in-sample are not.

## Adding a strategy

```
packages/oq-zoo/strategies/<your_strategy>/
├── README.md              # claim, mechanism, benchmark
├── strategy.py            # signal logic
├── notebook.ipynb         # walkthrough
└── tests/test_honest.py   # honesty-gate hook
```

Template lives at
[`packages/oq-zoo/STRATEGY_TEMPLATE.md`](https://github.com/revorhq/openquant/blob/main/packages/oq-zoo/STRATEGY_TEMPLATE.md).

## Categories

- `momentum/` — cross-sectional, time-series, dual
- `mean_reversion/` — pairs, single-name, basket
- `factor/` — value, quality, low-vol
- `event/` — earnings drift, index inclusion
- `educational/` — clear honest losers that teach a concept

## Disclaimer

Strategies in the zoo are research reproductions. They are not
recommendations, not signals, not advice. See [Disclaimer](../compliance/disclaimer.md).
