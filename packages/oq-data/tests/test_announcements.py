from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from oq_data import announcements
from oq_data.config import DataPaths


def test_build_url() -> None:
    src = announcements.build_url(date(2024, 4, 1))
    assert src.filename == "announcements_20240401.json"
    assert "corporate-announcements" in src.url
    assert "from_date=01-04-2024" in src.url


def test_parse_announcements_fixture(fixtures_dir: Path) -> None:
    blob = (fixtures_dir / "announcements_20240401.json").read_bytes()
    df = announcements.parse_announcements_blob(blob, date(2024, 4, 1))
    assert list(df.columns) == ["date", "symbol", "category", "subject", "attachment"]
    assert len(df) == 2
    rel = df[df["symbol"] == "RELIANCE"].iloc[0]
    assert rel["category"] == "Board Meeting"
    assert rel["attachment"].endswith("a.pdf")


def test_download_uses_cache(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "announcements_20240401.json").read_bytes()
    calls = {"n": 0}

    def fake_fetch(url: str) -> bytes:
        calls["n"] += 1
        return blob

    announcements.download_announcements(date(2024, 4, 1), paths=tmp_paths, fetcher=fake_fetch)
    announcements.download_announcements(date(2024, 4, 1), paths=tmp_paths, fetcher=fake_fetch)
    assert calls["n"] == 1


def test_write_and_read_idempotent(fixtures_dir: Path, tmp_paths: DataPaths) -> None:
    blob = (fixtures_dir / "announcements_20240401.json").read_bytes()
    df = announcements.parse_announcements_blob(blob, date(2024, 4, 1))
    announcements.write_announcements(df, paths=tmp_paths)
    announcements.write_announcements(df, paths=tmp_paths)
    out = announcements.read_announcements(paths=tmp_paths)
    assert len(out) == 2
    rel = announcements.read_announcements(symbols="RELIANCE", paths=tmp_paths)
    assert len(rel) == 1


def test_read_empty(tmp_paths: DataPaths) -> None:
    assert announcements.read_announcements(paths=tmp_paths).empty


def test_sync_range_validates(tmp_paths: DataPaths) -> None:
    with pytest.raises(ValueError):
        list(announcements.sync_range(date(2024, 4, 5), date(2024, 4, 1), paths=tmp_paths))
