"""Tests for the intraday backtesting layer (F2.11)."""

from __future__ import annotations

from datetime import time

import numpy as np
import pandas as pd
import pytest
from oq_backtest import (
    IntradayConfig,
    apply_square_off,
    backtest_intraday,
    intraday_summary,
    is_intraday_preset,
)


def _intraday_index(n_sessions: int = 2, bar_minutes: int = 5) -> pd.DatetimeIndex:
    bars: list[pd.Timestamp] = []
    start_dates = pd.date_range("2024-01-02", periods=n_sessions, freq="B")
    for d in start_dates:
        session_open = pd.Timestamp(d).replace(hour=9, minute=15)
        session_close = pd.Timestamp(d).replace(hour=15, minute=30)
        bars.extend(
            pd.date_range(session_open, session_close, freq=f"{bar_minutes}min", inclusive="left")
        )
    return pd.DatetimeIndex(bars)


def _make_intraday(seed: int = 0, n_sessions: int = 3, bar_minutes: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = _intraday_index(n_sessions=n_sessions, bar_minutes=bar_minutes)
    symbols = ["AAA", "BBB"]
    rets = rng.normal(loc=0.0, scale=0.0005, size=(len(idx), len(symbols)))
    prices = 1000.0 * np.cumprod(1.0 + rets, axis=0)
    return pd.DataFrame(prices, index=idx, columns=symbols)


def test_intraday_config_bars_per_session() -> None:
    cfg = IntradayConfig(bar_minutes=5)
    # 09:15 -> 15:30 = 375 minutes; 375 / 5 = 75 bars.
    assert cfg.bars_per_session == 75
    assert cfg.periods_per_year == 75 * 252


def test_intraday_config_invalid() -> None:
    with pytest.raises(ValueError):
        IntradayConfig(bar_minutes=0)
    with pytest.raises(ValueError):
        IntradayConfig(session_start=time(15, 0), session_end=time(9, 15))


def test_apply_square_off_zeros_last_bar() -> None:
    prices = _make_intraday(seed=1, n_sessions=2, bar_minutes=15)
    signals = pd.DataFrame(0.5, index=prices.index, columns=prices.columns)
    cfg = IntradayConfig(bar_minutes=15)
    flat = apply_square_off(signals, cfg)
    # Last bar of each session must be zero.
    by_date = pd.Series(flat.index, index=flat.index).groupby(flat.index.normalize()).max()
    for last_ts in by_date.tolist():
        row = flat.loc[last_ts]
        assert float(row.abs().sum()) == 0.0
    # And earlier bars retain the signal.
    first_ts = flat.index[0]
    assert float(flat.loc[first_ts].sum()) == pytest.approx(1.0)


def test_apply_square_off_empty() -> None:
    empty = pd.DataFrame(columns=["AAA"])
    out = apply_square_off(empty, IntradayConfig())
    assert out.empty


def test_backtest_intraday_runs_with_defaults() -> None:
    prices = _make_intraday(seed=2, n_sessions=2, bar_minutes=15)
    signals = pd.DataFrame({"AAA": 0.5, "BBB": 0.5}, index=prices.index, dtype=float)
    result = backtest_intraday(signals, prices, config=IntradayConfig(bar_minutes=15))
    assert result.gross_equity.shape == (len(prices),)
    assert result.net_equity.shape == (len(prices),)
    # Square-off default: final bar of last session has zero realised weights.
    last_ts = result.weights.index[-1]
    assert float(result.weights.loc[last_ts].abs().sum()) == 0.0


def test_backtest_intraday_costs_apply() -> None:
    prices = _make_intraday(seed=3, n_sessions=2, bar_minutes=15)
    signals = pd.DataFrame({"AAA": 0.5, "BBB": 0.5}, index=prices.index, dtype=float)
    result = backtest_intraday(signals, prices, config=IntradayConfig(bar_minutes=15))
    total_cost = float(result.costs["total"].sum())
    assert total_cost > 0.0
    # Net equity must be strictly less than gross when costs are positive.
    assert float(result.net_equity.iloc[-1]) < float(result.gross_equity.iloc[-1])


def test_backtest_intraday_allows_short_by_default() -> None:
    prices = _make_intraday(seed=4, n_sessions=1, bar_minutes=30)
    signals = pd.DataFrame({"AAA": -0.5, "BBB": 0.5}, index=prices.index, dtype=float)
    # Must not raise — intraday default allow_short=True, max_leverage=5.
    result = backtest_intraday(signals, prices, config=IntradayConfig(bar_minutes=30))
    assert not result.gross_equity.empty


def test_intraday_summary_annualizes_correctly() -> None:
    prices = _make_intraday(seed=5, n_sessions=3, bar_minutes=15)
    signals = pd.DataFrame({"AAA": 0.5, "BBB": 0.5}, index=prices.index, dtype=float)
    cfg = IntradayConfig(bar_minutes=15)
    result = backtest_intraday(signals, prices, config=cfg)
    summary = intraday_summary(result, cfg)
    assert summary["periods_per_year"] == cfg.periods_per_year
    assert summary["bars_per_session"] == cfg.bars_per_session
    assert "net_sharpe" in summary


def test_is_intraday_preset() -> None:
    assert is_intraday_preset("zerodha_intraday") is True
    assert is_intraday_preset("zerodha") is False
