from __future__ import annotations

from pathlib import Path

import pytest
from oq_data.config import DataPaths

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_paths(tmp_path: Path) -> DataPaths:
    paths = DataPaths(tmp_path)
    paths.ensure()
    return paths


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES
