from __future__ import annotations

import pandas as pd
import pytest
from oq_backtest import TaxConfig, estimate_taxes


def test_short_term_disposal_taxed_at_stcg():
    dates = pd.DatetimeIndex([pd.Timestamp("2024-04-01"), pd.Timestamp("2024-09-01")])
    trades = pd.DataFrame({"A": [100_000.0, -200_000.0]}, index=dates)
    prices = pd.DataFrame({"A": [100.0, 200.0]}, index=dates)
    df = estimate_taxes(trades, prices)
    assert df.loc[2024, "realized_stcg"] == pytest.approx(100_000.0)
    assert df.loc[2024, "stcg_tax"] == pytest.approx(15_000.0)
    assert df.loc[2024, "realized_ltcg"] == 0.0


def test_long_term_disposal_uses_ltcg_with_exemption():
    dates = pd.DatetimeIndex([pd.Timestamp("2022-04-01"), pd.Timestamp("2024-04-15")])
    trades = pd.DataFrame({"A": [100_000.0, -300_000.0]}, index=dates)
    prices = pd.DataFrame({"A": [100.0, 300.0]}, index=dates)
    df = estimate_taxes(trades, prices)
    assert df.loc[2024, "realized_ltcg"] == pytest.approx(200_000.0)
    taxable = 200_000.0 - 125_000.0
    assert df.loc[2024, "ltcg_tax"] == pytest.approx(taxable * 0.125)


def test_financial_year_split_around_april():
    dates = pd.DatetimeIndex([pd.Timestamp("2024-03-15"), pd.Timestamp("2024-04-05")])
    trades = pd.DataFrame({"A": [100_000.0, -100_000.0]}, index=dates)
    prices = pd.DataFrame({"A": [100.0, 100.0]}, index=dates)
    df = estimate_taxes(trades, prices)
    assert 2024 in df.index
    assert 2023 not in df.index
    assert df.loc[2024, "realized_stcg"] == pytest.approx(0.0)


def test_zero_trade_rows_ignored():
    dates = pd.DatetimeIndex([pd.Timestamp("2024-04-01"), pd.Timestamp("2024-05-01")])
    trades = pd.DataFrame({"A": [0.0, 0.0]}, index=dates)
    prices = pd.DataFrame({"A": [100.0, 110.0]}, index=dates)
    df = estimate_taxes(trades, prices)
    assert df.empty


def test_custom_tax_config_rates():
    dates = pd.DatetimeIndex([pd.Timestamp("2024-04-01"), pd.Timestamp("2024-06-01")])
    trades = pd.DataFrame({"A": [100_000.0, -200_000.0]}, index=dates)
    prices = pd.DataFrame({"A": [100.0, 200.0]}, index=dates)
    cfg = TaxConfig(stcg_rate=0.20)
    df = estimate_taxes(trades, prices, cfg)
    assert df.loc[2024, "stcg_tax"] == pytest.approx(20_000.0)


def test_partial_lot_consumption():
    dates = pd.DatetimeIndex(
        [
            pd.Timestamp("2024-04-01"),
            pd.Timestamp("2024-04-15"),
            pd.Timestamp("2024-09-01"),
        ]
    )
    trades = pd.DataFrame({"A": [100_000.0, 100_000.0, -150_000.0]}, index=dates)
    prices = pd.DataFrame({"A": [100.0, 200.0, 300.0]}, index=dates)
    df = estimate_taxes(trades, prices)
    assert df.loc[2024, "realized_stcg"] > 0
