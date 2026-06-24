"""High-level Python API for downstream packages.

This is the surface most users will touch: :func:`prices` for a clean
adjusted price series, :func:`universe` for a point-in-time membership
set, and :func:`wide_prices` for a date-indexed wide frame that drops
straight into :func:`oq_backtest.backtest`.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

import pandas as pd

from oq_data import corporate_actions, storage, symbols, universes
from oq_data.config import DataPaths, get_paths


def prices(
    symbol: str | Iterable[str],
    start: date | str | None = None,
    end: date | str | None = None,
    adjusted: bool = True,
    paths: DataPaths | None = None,
) -> pd.DataFrame:
    """Read a long-form OHLCV frame for one or many symbols.

    With ``adjusted=True`` (default), splits, bonuses, and dividends are
    back-adjusted so the returned series is a continuous total-return
    proxy suitable for backtesting.
    """
    paths = paths or get_paths()
    df = storage.read_prices(symbols=symbol, start=start, end=end, paths=paths)
    if df.empty or not adjusted:
        return df
    actions = corporate_actions.load_actions(paths=paths)
    if actions.empty:
        return df
    return corporate_actions.adjust_prices(df, actions)


def wide_prices(
    universe_symbols: Iterable[str],
    start: date | str | None = None,
    end: date | str | None = None,
    field: str = "close",
    adjusted: bool = True,
    paths: DataPaths | None = None,
) -> pd.DataFrame:
    """Return a date-indexed wide DataFrame ready for the backtester.

    The output is what :func:`oq_backtest.backtest` consumes as
    ``prices``: rows are trading dates, columns are symbols, values are
    the requested field (default ``close``).
    """
    syms = list(universe_symbols)
    if not syms:
        raise ValueError("universe_symbols must be non-empty")
    long_df = prices(syms, start=start, end=end, adjusted=adjusted, paths=paths)
    if long_df.empty:
        return pd.DataFrame()
    if field not in long_df.columns:
        raise KeyError(f"field {field!r} not in {sorted(long_df.columns)}")
    wide = long_df.pivot_table(index="date", columns="symbol", values=field, aggfunc="last")
    wide = wide.sort_index()
    wide.index = pd.DatetimeIndex(wide.index)
    return wide


def universe(
    index_name: str,
    as_of: date | str,
    paths: DataPaths | None = None,
) -> list[str]:
    """List the symbols that made up ``index_name`` on ``as_of``."""
    paths = paths or get_paths()
    when = pd.to_datetime(as_of).date()
    members = universes.members_as_of(index_name, when, paths=paths)
    return members["symbol"].tolist()


def resolve_symbol(symbol: str, when: date | str, paths: DataPaths | None = None) -> str:
    """Translate a current ticker to the symbol used on ``when``."""
    paths = paths or get_paths()
    master = symbols.load_master(paths=paths)
    return master.resolve_as_of(symbol, pd.to_datetime(when).date())


def list_symbols(paths: DataPaths | None = None) -> list[str]:
    """All distinct ``symbol`` values present in the EOD dataset."""
    paths = paths or get_paths()
    df = storage.query("SELECT DISTINCT symbol FROM eod ORDER BY symbol", paths=paths)
    return df["symbol"].tolist() if not df.empty else []


__all__ = [
    "list_symbols",
    "prices",
    "resolve_symbol",
    "universe",
    "wide_prices",
]
