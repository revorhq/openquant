# Your first backtest

A momentum strategy on the Nifty 500, honestly.

```python
import oq_data as oq
from oq_backtest import backtest

# 1. Point-in-time universe — no survivorship bias.
universe = oq.universe("NIFTY500", as_of="2010-01-01")

# 2. Adjusted prices for the full universe.
prices = oq.prices_panel(universe, start="2010-01-01", adjusted=True)

# 3. 12-1 month momentum (skip the last month to avoid reversal bias).
returns = prices["close"].pct_change(252).shift(21)

# 4. Top 20 each month, equal-weighted.
ranks = returns.rank(axis=1, ascending=False)
weights = (ranks <= 20).astype(float)
weights = weights.div(weights.sum(axis=1), axis=0).fillna(0)

# 5. Resample monthly.
monthly = weights.resample("ME").last()

# 6. Backtest with Zerodha costs.
result = backtest(monthly, prices=prices, costs="zerodha", rebalance="ME")
result.tearsheet()
```

What you should see:

- A gross curve that looks great.
- A net curve a couple of hundred basis points lower per year.
- A cost attribution table showing STT and slippage as the biggest drags.

If the gap between gross and net surprises you, that is the project
doing its job.
