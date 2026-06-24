"""Parquet + DuckDB storage layer for EOD equity data.

EOD bhavcopy rows are written to a year-partitioned Parquet dataset under
``paths.eod_equity/year=YYYY/month=MM.parquet``. Reads go through DuckDB
so a user can run ad-hoc SQL against the whole archive without loading
it into memory.

The contract:

* Schema is exactly the normalised bhavcopy schema from
  :mod:`oq_data.bhavcopy`.
* Writes are idempotent: re-ingesting the same date replaces, not
  duplicates, that day's rows.
* Reads return a tidy :class:`pandas.DataFrame` sorted by ``date``.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from oq_data.config import DataPaths, get_paths


def _partition_path(root: Path, year: int) -> Path:
    return root / f"year={year}" / "data.parquet"


def write_eod(
    df: pd.DataFrame,
    paths: DataPaths | None = None,
) -> int:
    """Append (or replace) bhavcopy rows into the year-partitioned dataset.

    Returns the number of rows actually written. The caller may pass rows
    from multiple dates; they are partitioned by year on the way out.
    """
    if df.empty:
        return 0
    paths = paths or get_paths()
    paths.ensure()
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["year"] = df["date"].dt.year
    written = 0
    for year, chunk in df.groupby("year", sort=True):
        chunk = chunk.drop(columns=["year"]).reset_index(drop=True)
        part = _partition_path(paths.eod_equity, int(year))
        part.parent.mkdir(parents=True, exist_ok=True)
        if part.exists():
            existing = pd.read_parquet(part)
            new_dates = set(chunk["date"].unique())
            existing = existing[~existing["date"].isin(new_dates)]
            combined = pd.concat([existing, chunk], ignore_index=True)
        else:
            combined = chunk
        combined = combined.sort_values(["date", "symbol"]).reset_index(drop=True)
        combined.to_parquet(part, index=False)
        written += len(chunk)
    return written


def _connect(paths: DataPaths) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(database=":memory:")


def _glob(paths: DataPaths) -> str:
    return str(paths.eod_equity / "year=*" / "data.parquet")


def query(
    sql: str,
    paths: DataPaths | None = None,
    params: list[object] | None = None,
) -> pd.DataFrame:
    """Run an ad-hoc DuckDB query against the EOD dataset.

    The dataset is mounted as a table called ``eod``. Example::

        oq_data.storage.query("SELECT symbol, COUNT(*) FROM eod GROUP BY symbol")
    """
    paths = paths or get_paths()
    if not any(paths.eod_equity.glob("year=*/data.parquet")):
        return pd.DataFrame()
    con = _connect(paths)
    try:
        con.execute(f"CREATE OR REPLACE VIEW eod AS SELECT * FROM read_parquet('{_glob(paths)}')")
        return con.execute(sql, params or []).fetch_df()
    finally:
        con.close()


def read_prices(
    symbols: str | Iterable[str] | None = None,
    start: date | str | None = None,
    end: date | str | None = None,
    series: Iterable[str] | None = ("EQ",),
    paths: DataPaths | None = None,
) -> pd.DataFrame:
    """Read EOD rows for one or many symbols within an optional date range."""
    paths = paths or get_paths()
    if not any(paths.eod_equity.glob("year=*/data.parquet")):
        return pd.DataFrame(
            columns=[
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
        )
    where: list[str] = []
    params: list[object] = []
    if symbols is not None:
        syms = [symbols] if isinstance(symbols, str) else list(symbols)
        placeholders = ", ".join(["?"] * len(syms))
        where.append(f"symbol IN ({placeholders})")
        params.extend(syms)
    if start is not None:
        where.append("date >= ?")
        params.append(pd.to_datetime(start).to_pydatetime())
    if end is not None:
        where.append("date <= ?")
        params.append(pd.to_datetime(end).to_pydatetime())
    if series is not None:
        series_list = list(series)
        placeholders = ", ".join(["?"] * len(series_list))
        where.append(f"series IN ({placeholders})")
        params.extend(series_list)
    sql = "SELECT * FROM eod"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date, symbol"
    return query(sql, paths=paths, params=params)


def list_dates(paths: DataPaths | None = None) -> list[date]:
    """Return every distinct trading date present in the EOD dataset."""
    paths = paths or get_paths()
    if not any(paths.eod_equity.glob("year=*/data.parquet")):
        return []
    df = query("SELECT DISTINCT date FROM eod ORDER BY date", paths=paths)
    return [d.date() for d in pd.to_datetime(df["date"])]


def coverage(paths: DataPaths | None = None) -> pd.DataFrame:
    """Per-year row counts and distinct trading-date counts."""
    paths = paths or get_paths()
    if not any(paths.eod_equity.glob("year=*/data.parquet")):
        return pd.DataFrame(columns=["year", "rows", "trading_days"])
    return query(
        "SELECT YEAR(date) AS year, COUNT(*) AS rows, COUNT(DISTINCT date) AS trading_days "
        "FROM eod GROUP BY 1 ORDER BY 1",
        paths=paths,
    )


__all__ = [
    "coverage",
    "list_dates",
    "query",
    "read_prices",
    "write_eod",
]
