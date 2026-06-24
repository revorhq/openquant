from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from oq_data import delivery
from oq_data.config import DataPaths


def test_build_url() -> None:
    src = delivery.build_url(date(2024, 4, 1))
    assert src.filename == "sec_bhavdata_full_01042024.csv"
    assert src.url.endswith("/sec_bhavdata_full_01042024.csv")


def test_parse_delivery_fixture(fixtures_dir: Path) -> None:
    blob = (fixtures_dir / "sec_bhavdata_full_01042024.csv").read_bytes()
    df = delivery.parse_delivery_blob(blob, date(2024, 4, 1))
    assert list(df.columns) == [
        "date",
        "symbol",
        "series",
        "traded_qty",
        "delivery_qty",
        "delivery_pct",
    ]
    assert len(df) == 3
    rel = df[df["symbol"] == "RELIANCE"].iloc[0]
    assert int(rel["traded_qty"]) == 1_500_000
    assert int(rel["delivery_qty"]) == 900_000
    assert rel["delivery_pct"] == pytest.approx(60.0)


def test_download_uses_cache(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "sec_bhavdata_full_01042024.csv").read_bytes()
    calls = {"n": 0}

    def fake_fetch(url: str) -> bytes:
        calls["n"] += 1
        return blob

    delivery.download_delivery(date(2024, 4, 1), paths=tmp_paths, fetcher=fake_fetch)
    delivery.download_delivery(date(2024, 4, 1), paths=tmp_paths, fetcher=fake_fetch)
    assert calls["n"] == 1


def test_write_and_read_idempotent(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "sec_bhavdata_full_01042024.csv").read_bytes()
    df = delivery.parse_delivery_blob(blob, date(2024, 4, 1))
    delivery.write_delivery(df, paths=tmp_paths)
    delivery.write_delivery(df, paths=tmp_paths)
    out = delivery.read_delivery(paths=tmp_paths)
    assert len(out) == 3
    rel = delivery.read_delivery(symbols="RELIANCE", paths=tmp_paths)
    assert len(rel) == 1


def test_read_empty(tmp_paths: DataPaths) -> None:
    assert delivery.read_delivery(paths=tmp_paths).empty


def test_sync_range_validates(tmp_paths: DataPaths) -> None:
    with pytest.raises(ValueError):
        list(delivery.sync_range(date(2024, 4, 5), date(2024, 4, 1), paths=tmp_paths))
