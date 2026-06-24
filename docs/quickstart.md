# Quickstart

Get from `pip install` to an honest tearsheet in 60 seconds.

## 1. Install

```bash
pip install oq-data oq-backtest
```

Or, with [`uv`](https://github.com/astral-sh/uv):

```bash
uv pip install oq-data oq-backtest
```

## 2. Sync data

Download the NSE bhavcopy archive and build the local store:

```bash
oq sync                 # full historical sync (15+ years)
oq sync --quick         # last 2 years only (fastest first run)
oq universe --date 2020-01-01 --index NIFTY50
```

Storage lives under `~/.openquant/data/` as year-partitioned Parquet,
queryable via DuckDB.

## 3. Your first backtest

```python
import oq_data as oq
from oq_backtest import backtest

# Adjusted prices, split- and bonus-corrected.
prices = oq.prices("RELIANCE", start="2015-01-01", adjusted=True)

# Trivial trend signal: long when above 200-day SMA.
sma = prices["close"].rolling(200).mean()
signals = (prices["close"] > sma).astype(int)

result = backtest(signals, costs="zerodha")
result.tearsheet()
```

You get:

- Gross vs net equity curves
- CAGR / Sharpe / Sortino / max drawdown
- Cost-attribution breakdown (STT, brokerage, GST, etc.)
- Turnover and cost drag

## 4. Add a broker

```python
from oq_broker import PaperBroker, PaperConfig, StrategyRegistration

reg = StrategyRegistration(
    algo_id="OPENQ001",
    strategy_id="trend-200d",
    strategy_name="Reliance trend",
    owner="you@example.com",
)
broker = PaperBroker(registration=reg, config=PaperConfig(starting_cash=500_000))
```

Same interface, paper or live. Live mode is gated behind
`OQ_LIVE_TRADING=1` plus an explicit `i_accept_live_risk=True`.

## What's next

- [Honest backtesting](honest-backtesting.md) — why net is non-negotiable
- [Cookbook](cookbook/index.md) — recipes for common workflows
- [API reference](api/index.md)
