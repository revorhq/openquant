from __future__ import annotations

import os
from pathlib import Path

from oq_data.config import DataPaths, default_root, get_paths


def test_default_root_respects_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENQUANT_DATA_DIR", str(tmp_path / "od"))
    assert default_root() == (tmp_path / "od").resolve()


def test_default_root_respects_xdg(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENQUANT_DATA_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert default_root() == (tmp_path / "xdg").resolve() / "openquant"


def test_default_root_falls_back_to_home(monkeypatch) -> None:
    monkeypatch.delenv("OPENQUANT_DATA_DIR", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert default_root() == Path(os.path.expanduser("~")) / ".openquant"


def test_get_paths_with_explicit_root(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)
    assert paths.root == tmp_path.resolve()
    assert paths.bhavcopy == paths.raw / "bhavcopy"
    assert paths.eod_equity == paths.parquet / "eod_equity"


def test_data_paths_ensure_creates_dirs(tmp_path: Path) -> None:
    paths = DataPaths(tmp_path)
    paths.ensure()
    assert paths.bhavcopy.exists()
    assert paths.eod_equity.exists()
    assert paths.reference.exists()
