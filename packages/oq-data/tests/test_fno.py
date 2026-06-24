from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from oq_data import fno, storage
from oq_data.config import DataPaths


def test_build_url_legacy() -> None:
    src = fno.build_url(date(2020, 7, 1))
    assert src.is_udiff is False
    assert src.filename == "fo01JUL2020bhav.csv.zip"
    assert "DERIVATIVES/2020/JUL/fo01JUL2020bhav.csv.zip" in src.url


def test_build_url_udiff() -> None:
    src = fno.build_url(date(2024, 4, 1))
    assert src.is_udiff is True
    assert src.filename == "BhavCopy_NSE_FO_0_0_0_20240401_F_0000.csv.zip"
    assert src.url.endswith("/fo/BhavCopy_NSE_FO_0_0_0_20240401_F_0000.csv.zip")


def test_parse_legacy_fixture(fixtures_dir: Path) -> None:
    blob = (fixtures_dir / "fo01JUL2020bhav.csv.zip").read_bytes()
    df = fno.parse_fno_blob(blob, date(2020, 7, 1))
    assert list(df.columns) == [
        "date",
        "instrument",
        "symbol",
        "expiry",
        "strike",
        "option_type",
        "open",
        "high",
        "low",
        "close",
        "settle",
        "volume",
        "value",
        "open_interest",
        "change_in_oi",
    ]
    assert len(df) == 4
    fut = df[(df["symbol"] == "RELIANCE") & (df["instrument"] == "FUTSTK")].iloc[0]
    assert fut["close"] == pytest.approx(2510.0)
    assert int(fut["volume"]) == 12000
    assert fut["value"] == pytest.approx(30120.0 * 100_000)
    ce = df[(df["symbol"] == "RELIANCE") & (df["option_type"] == "CE")].iloc[0]
    assert ce["strike"] == pytest.approx(2500.0)


def test_parse_udiff_fixture(fixtures_dir: Path) -> None:
    blob = (fixtures_dir / "BhavCopy_NSE_FO_0_0_0_20240401_F_0000.csv.zip").read_bytes()
    df = fno.parse_fno_blob(blob, date(2024, 4, 1))
    assert len(df) == 3
    fut = df[df["instrument"] == "STF"].iloc[0]
    assert fut["symbol"] == "RELIANCE"
    assert fut["close"] == pytest.approx(2925.0)
    assert int(fut["open_interest"]) == 750000
    pe = df[(df["instrument"] == "STO") & (df["option_type"] == "PE")].iloc[0]
    assert pe["strike"] == pytest.approx(2900.0)
    assert pe["settle"] == pytest.approx(35.0)


def test_download_fno_uses_fetcher_and_caches(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "BhavCopy_NSE_FO_0_0_0_20240401_F_0000.csv.zip").read_bytes()
    calls = {"n": 0}

    def fake_fetch(url: str) -> bytes:
        calls["n"] += 1
        return blob

    df1 = fno.download_fno(date(2024, 4, 1), paths=tmp_paths, fetcher=fake_fetch)
    assert calls["n"] == 1
    assert not df1.empty
    df2 = fno.download_fno(date(2024, 4, 1), paths=tmp_paths, fetcher=fake_fetch)
    assert calls["n"] == 1
    pd.testing.assert_frame_equal(df1, df2)


def test_sync_range_skips_weekends(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "BhavCopy_NSE_FO_0_0_0_20240401_F_0000.csv.zip").read_bytes()
    seen: list[date] = []

    def fake_fetch(url: str) -> bytes:
        return blob

    for d in fno.sync_range(
        date(2024, 4, 1), date(2024, 4, 7), paths=tmp_paths, fetcher=fake_fetch
    ):
        seen.append(d)
    assert seen == [
        date(2024, 4, 1),
        date(2024, 4, 2),
        date(2024, 4, 3),
        date(2024, 4, 4),
        date(2024, 4, 5),
    ]


def test_parse_filename_date_round_trip() -> None:
    assert fno.parse_filename_date("fo01JUL2020bhav.csv.zip") == date(2020, 7, 1)
    assert fno.parse_filename_date("BhavCopy_NSE_FO_0_0_0_20240401_F_0000.csv.zip") == date(
        2024, 4, 1
    )
    with pytest.raises(ValueError):
        fno.parse_filename_date("garbage.zip")


def test_write_fno_is_idempotent(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "BhavCopy_NSE_FO_0_0_0_20240401_F_0000.csv.zip").read_bytes()
    df = fno.parse_fno_blob(blob, date(2024, 4, 1))
    n1 = storage.write_fno(df, paths=tmp_paths)
    n2 = storage.write_fno(df, paths=tmp_paths)
    assert n1 == len(df)
    assert n2 == len(df)
    read = storage.read_fno(paths=tmp_paths)
    assert len(read) == len(df)


def test_read_fno_filters(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "BhavCopy_NSE_FO_0_0_0_20240401_F_0000.csv.zip").read_bytes()
    df = fno.parse_fno_blob(blob, date(2024, 4, 1))
    storage.write_fno(df, paths=tmp_paths)
    futures = storage.read_fno(instrument=["STF"], paths=tmp_paths)
    assert len(futures) == 1
    assert futures.iloc[0]["symbol"] == "RELIANCE"
    rel = storage.read_fno(symbols="RELIANCE", paths=tmp_paths)
    assert len(rel) == 3


def test_read_fno_empty_when_no_data(tmp_paths: DataPaths) -> None:
    df = storage.read_fno(paths=tmp_paths)
    assert df.empty
    assert "instrument" in df.columns


def test_sync_range_validates_dates(tmp_paths: DataPaths) -> None:
    with pytest.raises(ValueError):
        list(fno.sync_range(date(2024, 4, 5), date(2024, 4, 1), paths=tmp_paths))
