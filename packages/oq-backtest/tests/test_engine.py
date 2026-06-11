from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from oq_backtest import (
    CostConfig,
    backtest,
    equal_weight,
    momentum_signal,
    synthetic_universe,
)


def _flat_prices(symbols: list[str], n: int = 50) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame(100.0, index=idx, columns=symbols)


def _trending_prices(symbols: list[str], n: int = 100, drift: float = 0.001) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-01", periods=n)
    series = 100.0 * np.cumprod(1.0 + np.full(n, drift))
    return pd.DataFrame({s: series for s in symbols}, index=idx)


def test_zero_cost_flat_universe_preserves_capital():
    prices = _flat_prices(["A", "B"], n=20)
    signals = equal_weight(["A", "B"], prices.index)
    result = backtest(signals, prices, costs="zero", slippage=0.0, initial_capital=1_000_000)
    assert result.gross_equity.iloc[-1] == pytest.approx(1_000_000.0)
    assert result.net_equity.iloc[-1] == pytest.approx(1_000_000.0)


def test_zero_cost_trending_universe_compounds():
    prices = _trending_prices(["A"], n=50, drift=0.002)
    signals = pd.DataFrame(1.0, index=prices.index, columns=["A"])
    result = backtest(signals, prices, costs="zero", slippage=0.0, initial_capital=1_000_000)
    final_ret = prices["A"].iloc[-1] / prices["A"].iloc[0] - 1.0
    assert result.gross_equity.iloc[-1] == pytest.approx(1_000_000 * (1 + final_ret), rel=1e-6)
    assert result.net_equity.iloc[-1] == pytest.approx(result.gross_equity.iloc[-1], rel=1e-6)


def test_net_strictly_less_than_gross_when_trading():
    prices = _trending_prices(["A", "B"], n=30, drift=0.001)
    signals = equal_weight(["A", "B"], prices.index)
    result = backtest(signals, prices, costs="zerodha", slippage=5.0)
    assert result.net_equity.iloc[-1] < result.gross_equity.iloc[-1]


def test_costs_dataframe_columns():
    prices = _flat_prices(["A", "B"])
    signals = equal_weight(["A", "B"], prices.index)
    result = backtest(signals, prices, costs="zerodha")
    assert set(result.costs.columns) == {
        "brokerage",
        "stt",
        "exchange",
        "sebi",
        "gst",
        "stamp_duty",
        "slippage",
        "total",
    }


def test_short_disallowed_by_default():
    prices = _flat_prices(["A"])
    signals = pd.DataFrame(-0.5, index=prices.index, columns=["A"])
    with pytest.raises(ValueError, match="negative weights"):
        backtest(signals, prices)


def test_short_allowed_when_opted_in():
    prices = _flat_prices(["A"])
    signals = pd.DataFrame(-0.5, index=prices.index, columns=["A"])
    result = backtest(signals, prices, allow_short=True, costs="zero", slippage=0.0)
    assert result.net_equity.iloc[-1] == pytest.approx(1_000_000.0)


def test_leverage_validation():
    prices = _flat_prices(["A", "B"])
    signals = pd.DataFrame({"A": [1.0] * len(prices), "B": [1.0] * len(prices)}, index=prices.index)
    with pytest.raises(ValueError, match="max_leverage"):
        backtest(signals, prices)


def test_no_common_symbols_raises():
    prices = _flat_prices(["A"])
    signals = pd.DataFrame(1.0, index=prices.index, columns=["B"])
    with pytest.raises(ValueError, match="no symbols"):
        backtest(signals, prices)


def test_invalid_initial_capital():
    prices = _flat_prices(["A"])
    signals = equal_weight(["A"], prices.index)
    with pytest.raises(ValueError):
        backtest(signals, prices, initial_capital=0)


def test_invalid_max_leverage():
    prices = _flat_prices(["A"])
    signals = equal_weight(["A"], prices.index)
    with pytest.raises(ValueError):
        backtest(signals, prices, max_leverage=0)


def test_summary_keys_present():
    prices = synthetic_universe(n_symbols=5, n_days=300, seed=7)
    signals = momentum_signal(prices, lookback=60, top_k=2, schedule="monthly")
    result = backtest(signals, prices, costs="zerodha")
    s = result.summary()
    for key in (
        "gross_cagr",
        "net_cagr",
        "gross_sharpe",
        "net_sharpe",
        "net_sortino",
        "net_max_drawdown",
        "net_calmar",
        "annual_volatility",
        "annual_turnover",
        "cost_drag",
        "total_cost_inr",
        "final_net_value",
        "final_gross_value",
    ):
        assert key in s


def test_tearsheet_renders():
    prices = _trending_prices(["A", "B"], n=30)
    signals = equal_weight(["A", "B"], prices.index)
    result = backtest(signals, prices, costs="zerodha")
    text = result.tearsheet()
    assert "OpenQuant India" in text
    assert "CAGR" in text
    assert "Cost attribution" in text
    assert "Not investment advice" in text


def test_custom_costconfig_works():
    prices = _flat_prices(["A"])
    signals = equal_weight(["A"], prices.index)
    cfg = CostConfig(brokerage_rate=0.001)
    result = backtest(signals, prices, costs=cfg, slippage=0.0)
    assert result.cost_label == "custom"


def test_cost_attribution_sums_match_total():
    prices = _trending_prices(["A", "B"], n=20)
    signals = equal_weight(["A", "B"], prices.index)
    result = backtest(signals, prices, costs="zerodha")
    attribution = result.cost_attribution()
    assert attribution.sum() == pytest.approx(result.costs["total"].sum())
