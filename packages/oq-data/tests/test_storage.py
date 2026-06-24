from __future__ import annotations

from datetime import date

import pandas as pd
from oq_data import storage
from oq_data.config import DataPaths


def _make_rows(d: date, symbol: str, close: float) -> dict:
    return {
        "date": pd.Timestamp(d),
        "symbol": symbol,
        "isin": f"INE{symbol[:3]:<3}A01000",
        "series": "EQ",
        "open": close - 1,
        "high": close + 1,
        "low": close - 2,
        "close": close,
        "prev_close": close - 0.5,
        "volume": 1000,
        "value": close * 1000,
        "trades": 10,
    }


def _sample_df() -> pd.DataFrame:
    rows = [
        _make_rows(date(2024, 1, 2), "RELIANCE", 2500.0),
        _make_rows(date(2024, 1, 2), "TCS", 3500.0),
        _make_rows(date(2024, 1, 3), "RELIANCE", 2510.0),
        _make_rows(date(2024, 1, 3), "TCS", 3520.0),
        _make_rows(date(2023, 12, 29), "RELIANCE", 2490.0),
    ]
    return pd.DataFrame(rows)


def test_write_eod_partitions_by_year(tmp_paths: DataPaths) -> None:
    df = _sample_df()
    n = storage.write_eod(df, paths=tmp_paths)
    assert n == len(df)
    assert (tmp_paths.eod_equity / "year=2024" / "data.parquet").exists()
    assert (tmp_paths.eod_equity / "year=2023" / "data.parquet").exists()


def test_write_eod_idempotent_replaces(tmp_paths: DataPaths) -> None:
    df = _sample_df()
    storage.write_eod(df, paths=tmp_paths)
    storage.write_eod(df, paths=tmp_paths)
    out = storage.read_prices(paths=tmp_paths)
    assert len(out) == len(df)


def test_write_eod_replaces_same_date(tmp_paths: DataPaths) -> None:
    storage.write_eod(_sample_df(), paths=tmp_paths)
    updated = pd.DataFrame([_make_rows(date(2024, 1, 2), "RELIANCE", 9999.0)])
    storage.write_eod(updated, paths=tmp_paths)
    out = storage.read_prices(
        symbols="RELIANCE", start="2024-01-02", end="2024-01-02", paths=tmp_paths
    )
    assert out["close"].tolist() == [9999.0]


def test_read_prices_filters(tmp_paths: DataPaths) -> None:
    storage.write_eod(_sample_df(), paths=tmp_paths)
    rel = storage.read_prices(symbols="RELIANCE", paths=tmp_paths)
    assert (rel["symbol"] == "RELIANCE").all()
    assert len(rel) == 3


def test_read_prices_date_range(tmp_paths: DataPaths) -> None:
    storage.write_eod(_sample_df(), paths=tmp_paths)
    out = storage.read_prices(start="2024-01-01", end="2024-01-31", paths=tmp_paths)
    assert out["date"].min() >= pd.Timestamp("2024-01-01")
    assert out["date"].max() <= pd.Timestamp("2024-01-31")


def test_query_eod_view(tmp_paths: DataPaths) -> None:
    storage.write_eod(_sample_df(), paths=tmp_paths)
    res = storage.query(
        "SELECT symbol, COUNT(*) AS n FROM eod GROUP BY 1 ORDER BY 1", paths=tmp_paths
    )
    assert set(res["symbol"]) == {"RELIANCE", "TCS"}


def test_coverage_and_list_dates(tmp_paths: DataPaths) -> None:
    storage.write_eod(_sample_df(), paths=tmp_paths)
    cov = storage.coverage(paths=tmp_paths)
    assert {int(y) for y in cov["year"]} == {2023, 2024}
    dates = storage.list_dates(paths=tmp_paths)
    assert date(2024, 1, 2) in dates


def test_empty_store_returns_empty(tmp_paths: DataPaths) -> None:
    assert storage.read_prices(paths=tmp_paths).empty
    assert storage.list_dates(paths=tmp_paths) == []
    assert storage.coverage(paths=tmp_paths).empty
