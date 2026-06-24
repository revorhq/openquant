from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from oq_data import flows
from oq_data.config import DataPaths


def test_build_url() -> None:
    src = flows.build_url(date(2024, 4, 1))
    assert src.filename == "fii_dii_20240401.json"
    assert "fiidiiTradeReact" in src.url


def test_parse_flows_fixture(fixtures_dir: Path) -> None:
    blob = (fixtures_dir / "fii_dii_20240401.json").read_bytes()
    df = flows.parse_flows_blob(blob, date(2024, 4, 1))
    assert list(df.columns) == ["date", "category", "buy_value", "sell_value", "net_value"]
    assert set(df["category"].tolist()) == {"FII", "DII"}
    fii = df[df["category"] == "FII"].iloc[0]
    assert fii["buy_value"] == pytest.approx(10000.0)
    assert fii["net_value"] == pytest.approx(500.0)


def test_download_uses_cache(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "fii_dii_20240401.json").read_bytes()
    calls = {"n": 0}

    def fake_fetch(url: str) -> bytes:
        calls["n"] += 1
        return blob

    flows.download_flows(date(2024, 4, 1), paths=tmp_paths, fetcher=fake_fetch)
    flows.download_flows(date(2024, 4, 1), paths=tmp_paths, fetcher=fake_fetch)
    assert calls["n"] == 1


def test_write_and_read_idempotent(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "fii_dii_20240401.json").read_bytes()
    df = flows.parse_flows_blob(blob, date(2024, 4, 1))
    flows.write_flows(df, paths=tmp_paths)
    flows.write_flows(df, paths=tmp_paths)
    out = flows.read_flows(paths=tmp_paths)
    assert len(out) == 2
    fii_only = flows.read_flows(category="FII", paths=tmp_paths)
    assert len(fii_only) == 1


def test_read_empty(tmp_paths: DataPaths) -> None:
    assert flows.read_flows(paths=tmp_paths).empty


def test_sync_range_validates(tmp_paths: DataPaths) -> None:
    with pytest.raises(ValueError):
        list(flows.sync_range(date(2024, 4, 5), date(2024, 4, 1), paths=tmp_paths))
