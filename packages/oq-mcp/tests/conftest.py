"""Test fixtures for oq-mcp: a fully seeded tmp DataPaths with prices + a universe."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from oq_data import storage, universes
from oq_data.config import DataPaths

SYMBOLS = ["AAA", "BBB", "CCC", "DDD"]


def _make_eod(symbols: list[str], n_days: int = 320, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start="2023-01-02", periods=n_days)
    rows: list[dict[str, object]] = []
    for i, sym in enumerate(symbols):
        rets = rng.normal(loc=0.0004 + i * 0.0001, scale=0.014, size=n_days)
        rets[0] = 0.0
        closes = 100.0 * np.cumprod(1.0 + rets)
        for d, c in zip(dates, closes, strict=True):
            rows.append(
                {
                    "date": d,
                    "symbol": sym,
                    "isin": f"INE000000{i:03d}",
                    "series": "EQ",
                    "open": c * 0.999,
                    "high": c * 1.005,
                    "low": c * 0.995,
                    "close": c,
                    "prev_close": c * 0.999,
                    "volume": 100_000 + i * 1_000,
                    "value": 100_000 * c,
                    "trades": 500,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def seeded_paths(tmp_path: Path) -> DataPaths:
    paths = DataPaths(tmp_path)
    paths.ensure()
    df = _make_eod(SYMBOLS)
    storage.write_eod(df, paths=paths)
    entries = [
        universes.UniverseEntry(
            index_name="NIFTY 50",
            symbol=sym,
            isin=f"INE000000{i:03d}",
            include_date=date(2023, 1, 2),
        )
        for i, sym in enumerate(SYMBOLS)
    ]
    universes.add_entries(entries, paths=paths)
    return paths
