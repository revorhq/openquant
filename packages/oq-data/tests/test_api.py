from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from oq_data import api, storage
from oq_data import corporate_actions as ca
from oq_data import universes as un
from oq_data.config import DataPaths


def _row(d: date, sym: str, close: float) -> dict:
    return {
        "date": pd.Timestamp(d),
        "symbol": sym,
        "isin": "INE000X01010",
        "series": "EQ",
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "prev_close": close,
        "volume": 1000,
        "value": close * 1000,
        "trades": 10,
    }


def _seed_prices(tmp_paths: DataPaths) -> None:
    rows = [
        _row(date(2024, 1, 2), "ACME", 1000.0),
        _row(date(2024, 1, 3), "ACME", 200.0),
        _row(date(2024, 1, 2), "BETA", 500.0),
        _row(date(2024, 1, 3), "BETA", 505.0),
    ]
    storage.write_eod(pd.DataFrame(rows), paths=tmp_paths)


def test_prices_adjusted_default(tmp_paths: DataPaths) -> None:
    _seed_prices(tmp_paths)
    ca.add_actions(
        [ca.CorporateAction("ACME", date(2024, 1, 3), "split", ratio=5.0, amount=0.0)],
        paths=tmp_paths,
    )
    out = api.prices("ACME", paths=tmp_paths).sort_values("date").reset_index(drop=True)
    assert out.loc[0, "close"] == pytest.approx(200.0)
    assert out.loc[1, "close"] == pytest.approx(200.0)


def test_prices_unadjusted_passes_through(tmp_paths: DataPaths) -> None:
    _seed_prices(tmp_paths)
    ca.add_actions(
        [ca.CorporateAction("ACME", date(2024, 1, 3), "split", ratio=5.0, amount=0.0)],
        paths=tmp_paths,
    )
    out = (
        api.prices("ACME", adjusted=False, paths=tmp_paths)
        .sort_values("date")
        .reset_index(drop=True)
    )
    assert out.loc[0, "close"] == pytest.approx(1000.0)


def test_wide_prices_shape(tmp_paths: DataPaths) -> None:
    _seed_prices(tmp_paths)
    wide = api.wide_prices(["ACME", "BETA"], paths=tmp_paths)
    assert list(wide.columns) == ["ACME", "BETA"]
    assert len(wide) == 2
    assert isinstance(wide.index, pd.DatetimeIndex)


def test_wide_prices_rejects_empty_universe(tmp_paths: DataPaths) -> None:
    with pytest.raises(ValueError):
        api.wide_prices([], paths=tmp_paths)


def test_universe_returns_pit_members(tmp_paths: DataPaths) -> None:
    un.add_entries(
        [
            un.UniverseEntry("NIFTY50", "RELIANCE", "INE002A01018", date(2020, 1, 1), None),
            un.UniverseEntry(
                "NIFTY50", "HDFC", "INE001A01036", date(2020, 1, 1), date(2023, 7, 13)
            ),
        ],
        paths=tmp_paths,
    )
    pre = api.universe("NIFTY50", "2023-07-12", paths=tmp_paths)
    assert set(pre) == {"RELIANCE", "HDFC"}
    post = api.universe("NIFTY50", "2023-07-13", paths=tmp_paths)
    assert set(post) == {"RELIANCE"}


def test_resolve_symbol(tmp_paths: DataPaths) -> None:
    assert api.resolve_symbol("HDFCBANK", "2023-07-12", paths=tmp_paths) == "HDFC"


def test_list_symbols(tmp_paths: DataPaths) -> None:
    _seed_prices(tmp_paths)
    assert api.list_symbols(paths=tmp_paths) == ["ACME", "BETA"]
