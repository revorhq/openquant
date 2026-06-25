"""Educational strategy: equal-weight buy-and-hold across the declared universe.

This is intentionally **not** alpha. It exists so contributors can see the
shape of a registered strategy and so the honesty gate has a known-good
educational entry. Tagged ``educational`` so the gate does not require
beating a benchmark.
"""

from __future__ import annotations

import pandas as pd

from oq_zoo.registry import StrategyEntry, register


def equal_weight_signal(prices: pd.DataFrame) -> pd.DataFrame:
    """Allocate equal weight to every column for every row."""
    if prices.empty:
        return pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    n = prices.shape[1]
    w = 1.0 / n if n else 0.0
    return pd.DataFrame(w, index=prices.index, columns=prices.columns, dtype=float)


ENTRY = register(
    StrategyEntry(
        name="buy_and_hold_equal_weight",
        category="educational",
        author="OpenQuant India",
        description=(
            "Equal-weight buy-and-hold across the declared universe. "
            "Reference baseline; explicitly educational."
        ),
        signal_fn=equal_weight_signal,
        benchmark="NIFTY500_EQUAL_WEIGHT",
        universe="NIFTY500",
        cost_preset="zerodha",
        rebalance="ME",
        tags=("educational", "baseline"),
    )
)
