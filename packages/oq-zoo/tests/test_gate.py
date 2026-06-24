"""Tests for the honesty gate."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from oq_zoo.gate import HonestyGate, HonestyGateConfig, StrategySpec
from oq_zoo.registry import StrategyEntry


def _make_prices(seed: int = 0, n_days: int = 1500, n_symbols: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-01", periods=n_days, freq="B")
    daily_ret = rng.normal(loc=0.0005, scale=0.012, size=(n_days, n_symbols))
    prices = 100.0 * np.cumprod(1.0 + daily_ret, axis=0)
    cols = [f"SYM{i}" for i in range(n_symbols)]
    return pd.DataFrame(prices, index=dates, columns=cols)


def _benchmark_returns(prices: pd.DataFrame) -> pd.Series:
    return prices.mean(axis=1).pct_change().fillna(0.0)


def _equal_weight(prices: pd.DataFrame) -> pd.DataFrame:
    n = prices.shape[1]
    return pd.DataFrame(1.0 / n, index=prices.index, columns=prices.columns)


def _zero_weight(prices: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(0.0, index=prices.index, columns=prices.columns)


def _make_entry(
    name: str,
    signal_fn,
    tags: tuple[str, ...] = (),
    benchmark: str = "EQUAL_WEIGHT",
    universe: str = "NIFTY500",
    cost_preset: str = "zerodha",
) -> StrategyEntry:
    return StrategyEntry(
        name=name,
        category="educational",
        author="tester",
        description="test entry",
        signal_fn=signal_fn,
        benchmark=benchmark,
        universe=universe,
        cost_preset=cost_preset,
        tags=tags,
    )


def test_gate_passes_for_educational_strategy() -> None:
    prices = _make_prices(seed=42)
    bench = _benchmark_returns(prices)
    entry = _make_entry("edu", _equal_weight, tags=("educational",))
    gate = HonestyGate(
        config=HonestyGateConfig(
            require_walk_forward=False,
        )
    )
    result = gate.run([StrategySpec(entry=entry, prices=prices, benchmark_returns=bench)])
    assert result.passed
    assert result.reports[0].ran_backtest


def test_gate_fails_when_missing_declarations() -> None:
    prices = _make_prices(seed=1)
    bench = _benchmark_returns(prices)
    entry = _make_entry("missing", _equal_weight, tags=("educational",), benchmark="", universe="")
    gate = HonestyGate(config=HonestyGateConfig(require_walk_forward=False))
    result = gate.run([StrategySpec(entry=entry, prices=prices, benchmark_returns=bench)])
    assert not result.passed
    failures = result.failures()[0].failures
    assert any("benchmark" in f for f in failures)
    assert any("universe" in f for f in failures)


def test_gate_fails_when_alpha_negative_and_not_educational() -> None:
    prices = _make_prices(seed=7)
    bench = _benchmark_returns(prices)
    # Zero-weight strategy: 0% return, will not beat a positive benchmark.
    entry = _make_entry("flat", _zero_weight, tags=())
    gate = HonestyGate(config=HonestyGateConfig(min_alpha_bps=0.0, require_walk_forward=False))
    result = gate.run([StrategySpec(entry=entry, prices=prices, benchmark_returns=bench)])
    report = result.reports[0]
    if report.benchmark_cagr > 0:
        assert not result.passed
        assert any("does not beat benchmark" in f for f in report.failures)


def test_gate_runs_walk_forward_when_enabled() -> None:
    prices = _make_prices(seed=11, n_days=1500)
    bench = _benchmark_returns(prices)
    entry = _make_entry("wf", _equal_weight, tags=("educational",))
    gate = HonestyGate(
        config=HonestyGateConfig(
            require_walk_forward=True,
            walk_forward_train_periods=400,
            walk_forward_test_periods=200,
        )
    )
    result = gate.run([StrategySpec(entry=entry, prices=prices, benchmark_returns=bench)])
    assert result.reports[0].ran_walk_forward


def test_registry_duplicate_raises() -> None:
    from oq_zoo.registry import REGISTRY, register

    name = "dup-test-strategy"
    entry = _make_entry(name, _equal_weight, tags=("educational",))
    REGISTRY.pop(name, None)
    register(entry)
    with pytest.raises(ValueError):
        register(entry)
    REGISTRY.pop(name, None)
