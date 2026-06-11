from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from oq_backtest import (
    equal_weight,
    mean_reversion_signal,
    momentum_signal,
    rebalance_dates,
    synthetic_universe,
)


def test_synthetic_universe_deterministic():
    a = synthetic_universe(n_symbols=5, n_days=20, seed=99)
    b = synthetic_universe(n_symbols=5, n_days=20, seed=99)
    assert a.equals(b)


def test_synthetic_universe_shape():
    u = synthetic_universe(n_symbols=8, n_days=50)
    assert u.shape == (50, 8)
    assert (u > 0).all().all()


def test_equal_weight_sums_to_one():
    idx = pd.bdate_range("2024-01-01", periods=5)
    w = equal_weight(["A", "B", "C", "D"], idx)
    assert np.allclose(w.sum(axis=1).to_numpy(), 1.0)


def test_equal_weight_requires_symbols():
    with pytest.raises(ValueError):
        equal_weight([], pd.bdate_range("2024-01-01", periods=3))


def test_rebalance_dates_monthly_count():
    idx = pd.bdate_range("2024-01-01", "2024-12-31")
    rebal = rebalance_dates(idx, "monthly")
    assert 10 <= len(rebal) <= 13


def test_rebalance_dates_daily_is_pass_through():
    idx = pd.bdate_range("2024-01-01", periods=20)
    assert rebalance_dates(idx, "daily").equals(idx)


def test_rebalance_dates_unknown_raises():
    idx = pd.bdate_range("2024-01-01", periods=5)
    with pytest.raises(ValueError):
        rebalance_dates(idx, "hourly")


def test_momentum_signal_holds_top_k():
    prices = synthetic_universe(n_symbols=10, n_days=400, seed=3)
    sig = momentum_signal(prices, lookback=60, top_k=3, schedule="monthly")
    last = sig.iloc[-1]
    held = (last > 0).sum()
    assert held == 3
    assert last.sum() == pytest.approx(1.0)


def test_momentum_invalid_args():
    prices = synthetic_universe(n_symbols=5, n_days=20)
    with pytest.raises(ValueError):
        momentum_signal(prices, lookback=1)
    with pytest.raises(ValueError):
        momentum_signal(prices, top_k=0)


def test_mean_reversion_holds_bottom_k():
    prices = synthetic_universe(n_symbols=8, n_days=200, seed=5)
    sig = mean_reversion_signal(prices, lookback=5, bottom_k=2, schedule="weekly")
    last = sig.iloc[-1]
    assert (last > 0).sum() == 2
    assert last.sum() == pytest.approx(1.0)


def test_mean_reversion_invalid_args():
    prices = synthetic_universe(n_symbols=5, n_days=30)
    with pytest.raises(ValueError):
        mean_reversion_signal(prices, lookback=1)
    with pytest.raises(ValueError):
        mean_reversion_signal(prices, bottom_k=0)
