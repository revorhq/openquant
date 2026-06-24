from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from oq_data import bhavcopy
from oq_data.config import DataPaths


def test_is_udiff_date_boundary() -> None:
    assert bhavcopy.is_udiff_date(date(2020, 7, 11))
    assert not bhavcopy.is_udiff_date(date(2020, 7, 10))


def test_build_url_legacy() -> None:
    src = bhavcopy.build_url(date(2020, 6, 30))
    assert src.is_udiff is False
    assert src.filename == "cm30JUN2020bhav.csv.zip"
    assert "EQUITIES/2020/JUN/cm30JUN2020bhav.csv.zip" in src.url


def test_build_url_udiff() -> None:
    src = bhavcopy.build_url(date(2024, 4, 1))
    assert src.is_udiff is True
    assert src.filename == "BhavCopy_NSE_CM_0_0_0_20240401_F_0000.csv.zip"
    assert src.url.endswith("/cm/BhavCopy_NSE_CM_0_0_0_20240401_F_0000.csv.zip")


def test_parse_legacy_fixture(fixtures_dir: Path) -> None:
    blob = (fixtures_dir / "cm01JUL2020bhav.csv.zip").read_bytes()
    df = bhavcopy.parse_bhavcopy_blob(blob, date(2020, 7, 1))
    assert list(df.columns) == [
        "date",
        "symbol",
        "isin",
        "series",
        "open",
        "high",
        "low",
        "close",
        "prev_close",
        "volume",
        "value",
        "trades",
    ]
    assert len(df) == 3
    reliance = df[df["symbol"] == "RELIANCE"].iloc[0]
    assert reliance["close"] == pytest.approx(2510.0)
    assert reliance["isin"] == "INE002A01018"
    assert int(reliance["volume"]) == 1_000_000


def test_parse_udiff_fixture(fixtures_dir: Path) -> None:
    blob = (fixtures_dir / "BhavCopy_NSE_CM_0_0_0_20240401_F_0000.csv.zip").read_bytes()
    df = bhavcopy.parse_bhavcopy_blob(blob, date(2024, 4, 1))
    assert len(df) == 3
    hdfcbank = df[df["symbol"] == "HDFCBANK"].iloc[0]
    assert hdfcbank["isin"] == "INE040A01034"
    assert hdfcbank["close"] == pytest.approx(1510.0)


def test_download_bhavcopy_uses_fetcher_and_caches(
    fixtures_dir: Path, tmp_paths: DataPaths
) -> None:
    blob = (fixtures_dir / "BhavCopy_NSE_CM_0_0_0_20240401_F_0000.csv.zip").read_bytes()
    calls = {"n": 0}

    def fake_fetch(url: str) -> bytes:
        calls["n"] += 1
        return blob

    df1 = bhavcopy.download_bhavcopy(date(2024, 4, 1), paths=tmp_paths, fetcher=fake_fetch)
    assert calls["n"] == 1
    assert not df1.empty
    df2 = bhavcopy.download_bhavcopy(date(2024, 4, 1), paths=tmp_paths, fetcher=fake_fetch)
    assert calls["n"] == 1
    pd.testing.assert_frame_equal(df1, df2)


def test_sync_range_skips_weekends(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "BhavCopy_NSE_CM_0_0_0_20240401_F_0000.csv.zip").read_bytes()
    seen: list[date] = []

    def fake_fetch(url: str) -> bytes:
        return blob

    for d in bhavcopy.sync_range(
        date(2024, 4, 1), date(2024, 4, 7), paths=tmp_paths, fetcher=fake_fetch
    ):
        seen.append(d)
    weekdays = [
        date(2024, 4, 1),
        date(2024, 4, 2),
        date(2024, 4, 3),
        date(2024, 4, 4),
        date(2024, 4, 5),
    ]
    assert seen == weekdays


def test_sync_range_skips_missing_when_default(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "BhavCopy_NSE_CM_0_0_0_20240401_F_0000.csv.zip").read_bytes()

    def fake_fetch(url: str) -> bytes:
        if "20240402" in url:
            raise RuntimeError("404")
        return blob

    result = list(
        bhavcopy.sync_range(date(2024, 4, 1), date(2024, 4, 3), paths=tmp_paths, fetcher=fake_fetch)
    )
    assert result == [date(2024, 4, 1), date(2024, 4, 3)]


def test_sync_range_raises_when_configured(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    def fake_fetch(url: str) -> bytes:
        raise RuntimeError("404")

    with pytest.raises(RuntimeError):
        list(
            bhavcopy.sync_range(
                date(2024, 4, 1),
                date(2024, 4, 1),
                paths=tmp_paths,
                fetcher=fake_fetch,
                on_missing="raise",
            )
        )


def test_parse_filename_date_round_trip() -> None:
    assert bhavcopy.parse_filename_date("cm01JUL2020bhav.csv.zip") == date(2020, 7, 1)
    assert bhavcopy.parse_filename_date("BhavCopy_NSE_CM_0_0_0_20240401_F_0000.csv.zip") == date(
        2024, 4, 1
    )
    with pytest.raises(ValueError):
        bhavcopy.parse_filename_date("garbage.zip")


def test_sync_range_validates_dates(tmp_paths: DataPaths) -> None:
    with pytest.raises(ValueError):
        list(bhavcopy.sync_range(date(2024, 4, 5), date(2024, 4, 1), paths=tmp_paths))
