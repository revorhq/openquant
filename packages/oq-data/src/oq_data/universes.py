"""Point-in-time index constituents (Nifty 50 / 100 / 500).

Naive backtests on today's index constituents are survivorship-biased:
the names that survived to 2026 outperformed the ones that were kicked
out somewhere along the way. The fix is point-in-time membership: ask
"who was in Nifty 50 on 2018-04-01?" and get the answer that was true
on that day, not today.

NSE publishes index change announcements; this module models them as a
table of inclusion/exclusion events and reconstructs the membership set
as of any historical date.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import pandas as pd

from oq_data.config import DataPaths, get_paths

UNIVERSE_SCHEMA = ["index_name", "symbol", "isin", "include_date", "exclude_date"]


@dataclass(frozen=True, slots=True)
class UniverseEntry:
    """A single membership window for one symbol in one index."""

    index_name: str
    symbol: str
    isin: str
    include_date: date
    exclude_date: date | None = None

    def to_row(self) -> dict[str, object]:
        return {
            "index_name": self.index_name,
            "symbol": self.symbol,
            "isin": self.isin,
            "include_date": pd.Timestamp(self.include_date),
            "exclude_date": pd.Timestamp(self.exclude_date) if self.exclude_date else pd.NaT,
        }


def empty_universes() -> pd.DataFrame:
    return pd.DataFrame(columns=UNIVERSE_SCHEMA)


def save_universes(df: pd.DataFrame, paths: DataPaths | None = None) -> None:
    paths = paths or get_paths()
    paths.ensure()
    df = df.copy()
    df["include_date"] = pd.to_datetime(df["include_date"]).dt.normalize()
    df["exclude_date"] = pd.to_datetime(df["exclude_date"]).dt.normalize()
    df.to_parquet(paths.universes, index=False)


def load_universes(paths: DataPaths | None = None) -> pd.DataFrame:
    paths = paths or get_paths()
    if not paths.universes.exists():
        return empty_universes()
    df = pd.read_parquet(paths.universes)
    df["include_date"] = pd.to_datetime(df["include_date"]).dt.normalize()
    df["exclude_date"] = pd.to_datetime(df["exclude_date"]).dt.normalize()
    return df


def add_entries(entries: Iterable[UniverseEntry], paths: DataPaths | None = None) -> None:
    paths = paths or get_paths()
    rows = pd.DataFrame([e.to_row() for e in entries], columns=UNIVERSE_SCHEMA)
    existing = load_universes(paths=paths)
    combined = pd.concat([existing, rows], ignore_index=True).drop_duplicates(
        subset=["index_name", "isin", "include_date"], keep="last"
    )
    save_universes(combined, paths=paths)


def members_as_of(
    index_name: str,
    when: date,
    paths: DataPaths | None = None,
    df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return the membership set of ``index_name`` as it stood on ``when``.

    A symbol is a member if ``include_date <= when`` and either
    ``exclude_date`` is null or ``when < exclude_date``.
    """
    table = df if df is not None else load_universes(paths=paths)
    if table.empty:
        return pd.DataFrame(columns=["symbol", "isin", "include_date", "exclude_date"])
    when_ts = pd.Timestamp(when).normalize()
    mask = (
        (table["index_name"] == index_name)
        & (table["include_date"] <= when_ts)
        & (table["exclude_date"].isna() | (when_ts < table["exclude_date"]))
    )
    return (
        table.loc[mask, ["symbol", "isin", "include_date", "exclude_date"]]
        .sort_values("symbol")
        .reset_index(drop=True)
    )


def membership_history(
    index_name: str,
    paths: DataPaths | None = None,
    df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """All historical entries for ``index_name``, sorted by inclusion date."""
    table = df if df is not None else load_universes(paths=paths)
    if table.empty:
        return empty_universes()
    return (
        table[table["index_name"] == index_name].sort_values("include_date").reset_index(drop=True)
    )


__all__ = [
    "UNIVERSE_SCHEMA",
    "UniverseEntry",
    "add_entries",
    "empty_universes",
    "load_universes",
    "members_as_of",
    "membership_history",
    "save_universes",
]
