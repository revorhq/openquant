from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from click.testing import CliRunner
from oq_data import storage
from oq_data import universes as un
from oq_data.cli import main


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


def test_cli_coverage_empty(tmp_path: Path) -> None:
    runner = CliRunner()
    res = runner.invoke(main, ["--data-dir", str(tmp_path), "coverage"], obj={})
    assert res.exit_code == 1
    assert (
        "no data" in res.output.lower() or "no data" in (res.stderr_bytes or b"").decode().lower()
    )


def test_cli_coverage_after_write(tmp_path: Path) -> None:
    from oq_data.config import DataPaths

    paths = DataPaths(tmp_path)
    paths.ensure()
    storage.write_eod(pd.DataFrame([_row(date(2024, 1, 2), "ACME", 100.0)]), paths=paths)
    runner = CliRunner()
    res = runner.invoke(main, ["--data-dir", str(tmp_path), "coverage"], obj={})
    assert res.exit_code == 0
    assert "2024" in res.output


def test_cli_prices(tmp_path: Path) -> None:
    from oq_data.config import DataPaths

    paths = DataPaths(tmp_path)
    paths.ensure()
    storage.write_eod(pd.DataFrame([_row(date(2024, 1, 2), "ACME", 100.0)]), paths=paths)
    runner = CliRunner()
    res = runner.invoke(main, ["--data-dir", str(tmp_path), "prices", "ACME"], obj={})
    assert res.exit_code == 0
    assert "ACME" in res.output


def test_cli_universe(tmp_path: Path) -> None:
    from oq_data.config import DataPaths

    paths = DataPaths(tmp_path)
    paths.ensure()
    un.add_entries(
        [un.UniverseEntry("NIFTY50", "RELIANCE", "INE002A01018", date(2020, 1, 1), None)],
        paths=paths,
    )
    runner = CliRunner()
    res = runner.invoke(
        main, ["--data-dir", str(tmp_path), "universe", "NIFTY50", "--date", "2024-01-01"], obj={}
    )
    assert res.exit_code == 0
    assert "RELIANCE" in res.output
