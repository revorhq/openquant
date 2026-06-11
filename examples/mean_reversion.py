"""Short-horizon mean reversion on a synthetic universe.

Holds the worst-performing names from the prior week, rebalanced weekly.
Demonstrates that high-turnover strategies pay a much larger cost drag than
a monthly momentum strategy on the same universe.
"""

from __future__ import annotations

from oq_backtest import backtest, mean_reversion_signal, synthetic_universe


def main() -> None:
    prices = synthetic_universe(n_symbols=30, n_days=1500, seed=42)
    signals = mean_reversion_signal(prices, lookback=5, bottom_k=5, schedule="weekly")
    result = backtest(signals, prices, costs="zerodha", slippage=10.0)
    print(result.tearsheet())


if __name__ == "__main__":
    main()
