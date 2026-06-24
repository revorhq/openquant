from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from oq_data import corporate_actions as ca
from oq_data.config import DataPaths


def _series(symbol: str, dates: list[date], closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp(d) for d in dates],
            "symbol": symbol,
            "isin": "INE000X01010",
            "series": "EQ",
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "prev_close": closes,
            "volume": [1000] * len(closes),
            "value": [c * 1000 for c in closes],
            "trades": [10] * len(closes),
        }
    )


def test_split_back_adjusts_history() -> None:
    prices = _series(
        "ACME",
        [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)],
        [1000.0, 1010.0, 200.0, 205.0],
    )
    actions = pd.DataFrame(
        [
            {
                "symbol": "ACME",
                "ex_date": pd.Timestamp("2024-01-03"),
                "action_type": "split",
                "ratio": 5.0,
                "amount": 0.0,
            }
        ]
    )
    out = ca.adjust_prices(prices, actions)
    out_sorted = out.sort_values("date").reset_index(drop=True)
    assert out_sorted.loc[0, "close"] == pytest.approx(200.0)
    assert out_sorted.loc[1, "close"] == pytest.approx(202.0)
    assert out_sorted.loc[2, "close"] == pytest.approx(200.0)
    assert out_sorted.loc[3, "close"] == pytest.approx(205.0)
    assert int(out_sorted.loc[0, "volume"]) == 5000
    assert int(out_sorted.loc[2, "volume"]) == 1000


def test_dividend_back_adjusts_with_amount() -> None:
    prices = _series(
        "ACME",
        [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
        [100.0, 100.0, 90.0],
    )
    actions = pd.DataFrame(
        [
            {
                "symbol": "ACME",
                "ex_date": pd.Timestamp("2024-01-03"),
                "action_type": "dividend",
                "ratio": 1.0,
                "amount": 10.0,
            }
        ]
    )
    out = ca.adjust_prices(prices, actions).sort_values("date").reset_index(drop=True)
    assert out.loc[0, "close"] == pytest.approx(90.0)
    assert out.loc[1, "close"] == pytest.approx(90.0)
    assert out.loc[2, "close"] == pytest.approx(90.0)


def test_bonus_back_adjusts_like_split() -> None:
    prices = _series(
        "ACME",
        [date(2024, 1, 1), date(2024, 1, 2)],
        [200.0, 100.0],
    )
    actions = pd.DataFrame(
        [
            {
                "symbol": "ACME",
                "ex_date": pd.Timestamp("2024-01-02"),
                "action_type": "bonus",
                "ratio": 2.0,
                "amount": 0.0,
            }
        ]
    )
    out = ca.adjust_prices(prices, actions).sort_values("date").reset_index(drop=True)
    assert out.loc[0, "close"] == pytest.approx(100.0)
    assert out.loc[1, "close"] == pytest.approx(100.0)


def test_no_actions_returns_copy() -> None:
    prices = _series("ACME", [date(2024, 1, 1)], [100.0])
    out = ca.adjust_prices(prices, ca.empty_actions())
    pd.testing.assert_series_equal(out["close"], prices["close"], check_names=False)


def test_persist_round_trip(tmp_paths: DataPaths) -> None:
    ca.add_actions(
        [
            ca.CorporateAction("ACME", date(2024, 1, 1), "split", ratio=2.0, amount=0.0),
        ],
        paths=tmp_paths,
    )
    df = ca.load_actions(paths=tmp_paths)
    assert len(df) == 1
    assert df.iloc[0]["symbol"] == "ACME"
