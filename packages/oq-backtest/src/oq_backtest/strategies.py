"""Strategy construction helpers.

Small, well-tested utilities for building common signal DataFrames. These are
not "trading strategies" you should deploy with money - they are reference
constructions used by the example scripts and the regression tests, and
shaped so a contributor can read the code in a minute.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

_REBAL_RULES = {"daily": None, "weekly": "W-FRI", "monthly": "BME", "quarterly": "BQE"}


def rebalance_dates(index: pd.DatetimeIndex, schedule: str) -> pd.DatetimeIndex:
    """Pick the rebalance dates inside ``index`` for a named schedule."""
    if schedule not in _REBAL_RULES:
        raise ValueError(f"unknown schedule {schedule!r}; choose from {sorted(_REBAL_RULES)}")
    rule = _REBAL_RULES[schedule]
    if rule is None:
        return index
    target = pd.date_range(index.min(), index.max(), freq=rule)
    snapped: list[pd.Timestamp] = []
    last_kept: pd.Timestamp | None = None
    for ts in target:
        pos = index.searchsorted(ts, side="right") - 1
        if pos < 0:
            continue
        chosen = index[pos]
        if last_kept is None or chosen != last_kept:
            snapped.append(chosen)
            last_kept = chosen
    return pd.DatetimeIndex(snapped)


def equal_weight(symbols: Iterable[str], dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Equal-weighted long-only signal across ``symbols`` for every date."""
    syms = list(symbols)
    if not syms:
        raise ValueError("symbols must be non-empty")
    w = 1.0 / len(syms)
    return pd.DataFrame(w, index=dates, columns=syms)


def momentum_signal(
    prices: pd.DataFrame,
    lookback: int = 252,
    top_k: int = 10,
    schedule: str = "monthly",
) -> pd.DataFrame:
    """Cross-sectional momentum: hold the top-``k`` by trailing return.

    Returns a target-weight DataFrame aligned with ``prices.index``. Weights
    are equal across the selected names and zero elsewhere. The portfolio
    is rebalanced according to ``schedule`` (``daily``/``weekly``/``monthly``
    /``quarterly``) and held flat between rebalances.
    """
    if lookback < 2:
        raise ValueError("lookback must be >= 2")
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    momentum = prices.pct_change(lookback)
    rebal = rebalance_dates(prices.index, schedule)
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    last_w: pd.Series | None = None
    for ts in prices.index:
        if ts in rebal:
            row = momentum.loc[ts].dropna()
            if row.empty:
                last_w = pd.Series(0.0, index=prices.columns)
            else:
                chosen = row.nlargest(min(top_k, len(row))).index
                w = pd.Series(0.0, index=prices.columns)
                w.loc[chosen] = 1.0 / len(chosen)
                last_w = w
        if last_w is not None:
            weights.loc[ts] = last_w
    return weights


def mean_reversion_signal(
    prices: pd.DataFrame,
    lookback: int = 5,
    bottom_k: int = 5,
    schedule: str = "weekly",
) -> pd.DataFrame:
    """Short-horizon mean reversion: hold the worst-performing recent names."""
    if lookback < 2:
        raise ValueError("lookback must be >= 2")
    if bottom_k < 1:
        raise ValueError("bottom_k must be >= 1")
    short_ret = prices.pct_change(lookback)
    rebal = rebalance_dates(prices.index, schedule)
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    last_w: pd.Series | None = None
    for ts in prices.index:
        if ts in rebal:
            row = short_ret.loc[ts].dropna()
            if row.empty:
                last_w = pd.Series(0.0, index=prices.columns)
            else:
                chosen = row.nsmallest(min(bottom_k, len(row))).index
                w = pd.Series(0.0, index=prices.columns)
                w.loc[chosen] = 1.0 / len(chosen)
                last_w = w
        if last_w is not None:
            weights.loc[ts] = last_w
    return weights


def synthetic_universe(
    n_symbols: int = 20,
    n_days: int = 750,
    seed: int = 42,
    start: str = "2020-01-01",
    drift: float = 0.0003,
    vol: float = 0.018,
) -> pd.DataFrame:
    """Generate a reproducible synthetic price universe for examples / tests."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, periods=n_days)
    rets = rng.normal(loc=drift, scale=vol, size=(n_days, n_symbols))
    rets[0] = 0.0
    prices = 100.0 * np.cumprod(1.0 + rets, axis=0)
    symbols = [f"SYM{i:03d}" for i in range(n_symbols)]
    return pd.DataFrame(prices, index=dates, columns=symbols)


__all__ = [
    "equal_weight",
    "mean_reversion_signal",
    "momentum_signal",
    "rebalance_dates",
    "synthetic_universe",
]
