"""ISIN-keyed symbol master and merger / rename mapping.

The Indian listed universe drifts constantly: tickers are renamed (HCC ->
HCCBSO), companies merge into others (HDFC -> HDFCBANK on 2023-07-13),
and entire ISINs are retired. Naive ``symbol``-keyed analysis pollutes
the historical record. We pin identity to ``ISIN`` and maintain a small
mapping table that lets a caller ask "what symbol was ticker X on date Y,
and what does it map to in today's terms?".

Mappings live in a Parquet file under :attr:`DataPaths.symbols` with
columns: ``isin, old_symbol, new_symbol, effective_date, reason`` where
``reason`` is one of ``rename`` / ``merger`` / ``demerger``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from oq_data.config import DataPaths, get_paths

SYMBOL_SCHEMA = ["isin", "old_symbol", "new_symbol", "effective_date", "reason"]

KNOWN_MAPPINGS: list[dict[str, str]] = [
    {
        "isin": "INE001A01036",
        "old_symbol": "HDFC",
        "new_symbol": "HDFCBANK",
        "effective_date": "2023-07-13",
        "reason": "merger",
    },
    {
        "isin": "INE528G01035",
        "old_symbol": "YESBANK",
        "new_symbol": "YESBANK",
        "effective_date": "2020-03-13",
        "reason": "rename",
    },
]


@dataclass(frozen=True, slots=True)
class SymbolMaster:
    """In-memory view of the symbol mapping table."""

    df: pd.DataFrame

    def resolve_as_of(self, symbol: str, when: date) -> str:
        """Return the symbol that ``symbol`` was known as on ``when``.

        Walks the rename chain backwards from today: if ``when`` predates
        a rename or merger, returns the older symbol. Useful for joining
        historical bhavcopy data to a current ticker.
        """
        when_ts = pd.Timestamp(when)
        chain = self.df[self.df["new_symbol"] == symbol].sort_values("effective_date")
        cur = symbol
        for _, row in chain.iterrows():
            if when_ts < pd.Timestamp(row["effective_date"]):
                cur = row["old_symbol"]
        return cur

    def canonical(self, symbol: str) -> str:
        """Return the most recent symbol that ``symbol`` was renamed into."""
        cur = symbol
        seen: set[str] = set()
        while True:
            if cur in seen:
                return cur
            seen.add(cur)
            forward = self.df[self.df["old_symbol"] == cur].sort_values("effective_date")
            if forward.empty:
                return cur
            cur = forward.iloc[-1]["new_symbol"]


def empty_master() -> pd.DataFrame:
    return pd.DataFrame(columns=SYMBOL_SCHEMA)


def build_default_master() -> pd.DataFrame:
    df = pd.DataFrame(KNOWN_MAPPINGS, columns=SYMBOL_SCHEMA)
    df["effective_date"] = pd.to_datetime(df["effective_date"]).dt.normalize()
    return df


def save_master(df: pd.DataFrame, paths: DataPaths | None = None) -> None:
    paths = paths or get_paths()
    paths.ensure()
    df = df.copy()
    df["effective_date"] = pd.to_datetime(df["effective_date"]).dt.normalize()
    df.to_parquet(paths.symbols, index=False)


def load_master(paths: DataPaths | None = None) -> SymbolMaster:
    """Load the symbol master from disk, seeding defaults on first run."""
    paths = paths or get_paths()
    if not paths.symbols.exists():
        df = build_default_master()
        save_master(df, paths=paths)
    else:
        df = pd.read_parquet(paths.symbols)
    return SymbolMaster(df=df)


def add_mapping(
    isin: str,
    old_symbol: str,
    new_symbol: str,
    effective_date: date | str,
    reason: str = "rename",
    paths: DataPaths | None = None,
) -> None:
    """Append a rename/merger entry to the symbol master."""
    paths = paths or get_paths()
    existing = load_master(paths=paths).df
    row = pd.DataFrame(
        [
            {
                "isin": isin,
                "old_symbol": old_symbol,
                "new_symbol": new_symbol,
                "effective_date": pd.to_datetime(effective_date).normalize(),
                "reason": reason,
            }
        ],
        columns=SYMBOL_SCHEMA,
    )
    combined = pd.concat([existing, row], ignore_index=True).drop_duplicates(
        subset=["isin", "old_symbol", "new_symbol", "effective_date"], keep="last"
    )
    save_master(combined, paths=paths)


__all__ = [
    "KNOWN_MAPPINGS",
    "SYMBOL_SCHEMA",
    "SymbolMaster",
    "add_mapping",
    "build_default_master",
    "empty_master",
    "load_master",
    "save_master",
]
