# `oq-backtest`

Vectorized daily-frequency portfolio engine with an honest Indian
cost model.

## One-line API

```python
from oq_backtest import backtest

result = backtest(signals, costs="zerodha")
result.tearsheet()
```

## Inputs

- `signals` — `pd.DataFrame[time, symbol] -> float weight` or
  `pd.Series[time] -> 0/1` for single-name.
- `costs` — preset name or `CostModel` instance.
- `slippage` — bps, callable, or one of the built-in models.
- `rebalance` — `"D"`, `"W"`, `"ME"`, `"QE"`.

## Output

```python
result.equity_curve       # pd.Series — net of costs
result.gross_equity_curve # pd.Series — gross
result.metrics            # dict — CAGR, Sharpe, Sortino, MaxDD, turnover, cost_drag
result.cost_attribution   # pd.DataFrame — bps_of_aum per category
result.fills              # pd.DataFrame
result.tearsheet()        # prints + plots
```

## Slippage models

```python
from oq_backtest.slippage import FixedBps, VolumeParticipation, SpreadSlippage

FixedBps(bps=5)
VolumeParticipation(pct=0.05)
SpreadSlippage(spread_bps=10)
```

## Walk-forward

```python
from oq_backtest.walk_forward import walk_forward

result = walk_forward(strategy_fn, prices, train="3y", test="1y", step="1y")
result.combined_oos       # pd.Series
```

## Tax estimator

```python
from oq_backtest.taxes import estimate

est = estimate(result.fills, regime="india_individual_fy26")
# Returns STCG + LTCG estimates by holding-period bucket.
# Clearly labeled: ESTIMATE — NOT TAX ADVICE.
```
