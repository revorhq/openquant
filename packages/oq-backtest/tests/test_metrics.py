from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from oq_backtest import metrics


def _equity_curve(returns: list[float]) -> pd.Series:
    r = pd.Series(returns)
    return (1.0 + r).cumprod() * 1_000_000.0


def test_to_returns_first_is_zero():
    eq = _equity_curve([0.0, 0.01, -0.005])
    r = metrics.to_returns(eq)
    assert r.iloc[0] == 0.0
    assert r.iloc[1] == pytest.approx(0.01)


def test_cagr_constant_one_year():
    dates = pd.bdate_range("2020-01-01", periods=metrics.DAYS_PER_YEAR + 1)
    eq = pd.Series(np.linspace(1.0, 1.2, len(dates)), index=dates)
    assert metrics.cagr(eq) == pytest.approx(0.2, rel=1e-2)


def test_cagr_short_series():
    assert metrics.cagr(pd.Series([1.0])) == 0.0


def test_annualized_return_matches_cagr():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.0005, 0.01, size=504))
    eq = (1.0 + r).cumprod()
    assert metrics.annualized_return(r) == pytest.approx(metrics.cagr(eq), rel=0.05)


def test_annualized_volatility_nonzero():
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0, 0.01, size=252))
    vol = metrics.annualized_volatility(r)
    assert vol == pytest.approx(0.01 * np.sqrt(252), rel=0.2)


def test_sharpe_zero_for_flat():
    r = pd.Series([0.0] * 10)
    assert metrics.sharpe(r) == 0.0


def test_sharpe_positive_for_positive_mean():
    rng = np.random.default_rng(2)
    r = pd.Series(rng.normal(0.001, 0.01, size=252))
    assert metrics.sharpe(r) > 0


def test_sortino_only_penalizes_downside():
    r = pd.Series([0.01] * 100 + [-0.02])
    s = metrics.sortino(r)
    assert s > 0


def test_max_drawdown_known_case():
    eq = pd.Series([100.0, 110.0, 121.0, 60.5])
    assert metrics.max_drawdown(eq) == pytest.approx(-0.5)


def test_max_drawdown_increasing_is_zero():
    eq = pd.Series([1.0, 1.1, 1.2, 1.3])
    assert metrics.max_drawdown(eq) == 0.0


def test_calmar_handles_zero_dd():
    eq = pd.Series([1.0, 1.1, 1.2])
    assert metrics.calmar(eq) == float("inf")


def test_turnover_buy_and_hold_is_zero():
    weights = pd.DataFrame(
        {"A": [0.5, 0.5, 0.5], "B": [0.5, 0.5, 0.5]},
        index=pd.bdate_range("2020-01-01", periods=3),
    )
    assert metrics.turnover(weights) == 0.0


def test_turnover_full_flip_each_day():
    weights = pd.DataFrame(
        {"A": [1.0, 0.0, 1.0], "B": [0.0, 1.0, 0.0]},
        index=pd.bdate_range("2020-01-01", periods=3),
    )
    t = metrics.turnover(weights)
    assert t > 0


def test_cost_drag_zero_for_identical_returns():
    r = pd.Series([0.001] * 252)
    assert metrics.cost_drag(r, r) == pytest.approx(0.0)


def test_cost_drag_positive_when_gross_outperforms():
    g = pd.Series([0.002] * 252)
    n = pd.Series([0.001] * 252)
    assert metrics.cost_drag(g, n) > 0
