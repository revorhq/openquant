"""Cross-sectional momentum on a synthetic Nifty-like universe.

This script is a runnable smoke test of ``oq-backtest`` end-to-end:

* generate a reproducible synthetic price universe
* build a monthly top-K momentum signal
* backtest with Zerodha delivery costs + 5 bps slippage
* print a gross-vs-net tearsheet

It uses synthetic data so it works without any external download. Once
``oq-data`` ships, swap ``synthetic_universe`` for ``oq.prices``.
"""

from __future__ import annotations

from oq_backtest import backtest, momentum_signal, synthetic_universe


def main() -> None:
    prices = synthetic_universe(n_symbols=30, n_days=1500, seed=42)
    signals = momentum_signal(prices, lookback=126, top_k=5, schedule="monthly")
    result = backtest(signals, prices, costs="zerodha", slippage=5.0)
    print(result.tearsheet())


if __name__ == "__main__":
    main()
