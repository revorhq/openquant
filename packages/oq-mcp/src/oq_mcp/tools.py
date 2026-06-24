"""Pure-Python implementations of every MCP tool.

These functions accept primitive arguments (so they serialise cleanly
across the MCP wire) and return JSON-serialisable dicts. The MCP server
in :mod:`oq_mcp.server` is a thin wrapper that adapts each function
into a ``FastMCP`` tool. Keeping the logic here makes the tools easy to
test offline without spinning up the server.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import oq_backtest as bt
import oq_data
import pandas as pd
from oq_data.config import DataPaths, get_paths

from oq_mcp.cache import TTLCache
from oq_mcp.screener import screen

_DEFAULT_CACHE: TTLCache[Any] = TTLCache(ttl_seconds=300.0, max_entries=256)


def _resolve_paths(data_dir: str | Path | None) -> DataPaths:
    return get_paths(data_dir) if data_dir else get_paths()


def _coerce_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return pd.to_datetime(value).date()


def _series_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    out = df.copy()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out.to_dict(orient="records")


def get_prices(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    adjusted: bool = True,
    data_dir: str | None = None,
    cache: TTLCache[Any] | None = None,
) -> dict[str, Any]:
    """Return adjusted EOD prices for ``symbol`` between ``start`` and ``end``."""
    paths = _resolve_paths(data_dir)
    key = ("prices", symbol, start, end, adjusted, str(paths.root))
    c = cache or _DEFAULT_CACHE
    hit = c.get(key)
    if hit is not None:
        return hit
    df = oq_data.prices(
        symbol,
        start=_coerce_date(start),
        end=_coerce_date(end),
        adjusted=adjusted,
        paths=paths,
    )
    result = {
        "symbol": symbol,
        "adjusted": adjusted,
        "rows": len(df),
        "data": _series_to_records(df),
    }
    c.set(key, result)
    return result


def get_universe(
    index_name: str,
    as_of: str,
    data_dir: str | None = None,
    cache: TTLCache[Any] | None = None,
) -> dict[str, Any]:
    """Return PIT membership of ``index_name`` as of ``as_of`` (YYYY-MM-DD)."""
    paths = _resolve_paths(data_dir)
    key = ("universe", index_name, as_of, str(paths.root))
    c = cache or _DEFAULT_CACHE
    hit = c.get(key)
    if hit is not None:
        return hit
    members = oq_data.universe(index_name, as_of, paths=paths)
    result = {
        "index": index_name,
        "as_of": as_of,
        "count": len(members),
        "symbols": members,
    }
    c.set(key, result)
    return result


def screen_stocks(
    expressions: Sequence[str],
    index_name: str | None = None,
    as_of: str | None = None,
    lookback_days: int = 300,
    combine: str = "and",
    data_dir: str | None = None,
) -> dict[str, Any]:
    """Run the screener DSL over a (PIT) universe."""
    paths = _resolve_paths(data_dir)
    end = _coerce_date(as_of) or date.today()
    start = end - pd.Timedelta(days=int(lookback_days) + 30)
    if index_name:
        members = oq_data.universe(index_name, end, paths=paths)
    else:
        members = oq_data.list_symbols(paths=paths)
    if not members:
        return {"count": 0, "symbols": [], "universe_size": 0, "as_of": end.isoformat()}
    wide = oq_data.wide_prices(members, start=start, end=end, paths=paths)
    matches = screen(wide, expressions, combine=combine, universe=members)
    return {
        "count": len(matches),
        "symbols": matches,
        "universe_size": len(members),
        "as_of": end.isoformat(),
        "expressions": list(expressions),
        "combine": combine,
    }


def get_fundamentals_basic(
    symbol: str,
    data_dir: str | None = None,
) -> dict[str, Any]:
    """Return basic reference information for ``symbol``.

    Phase 3 ships the *basic* contract only — symbol identity (ISIN,
    series, exchange) plus the latest known close and traded volume.
    Quarterly results and shareholding feeds land in a later phase.
    """
    paths = _resolve_paths(data_dir)
    eod = oq_data.storage.read_prices(symbols=symbol, paths=paths)
    if eod.empty:
        return {"symbol": symbol, "found": False}
    last = eod.iloc[-1]
    master = oq_data.symbols.load_master(paths=paths)
    info: dict[str, Any] = {
        "symbol": symbol,
        "found": True,
        "isin": str(last.get("isin")) if pd.notna(last.get("isin")) else None,
        "series": str(last.get("series")),
        "last_date": pd.to_datetime(last["date"]).strftime("%Y-%m-%d"),
        "last_close": float(last["close"]),
        "last_volume": int(last["volume"]) if pd.notna(last["volume"]) else None,
        "history_rows": len(eod),
    }
    if not master.df.empty:
        match = master.df[(master.df["new_symbol"] == symbol) | (master.df["old_symbol"] == symbol)]
        if not match.empty:
            info["canonical_isin"] = str(match.iloc[-1]["isin"])
    return info


def run_backtest(
    signals_source: str = "momentum",
    index_name: str | None = None,
    start: str | None = None,
    end: str | None = None,
    costs: str = "zerodha",
    slippage_bps: float = 5.0,
    initial_capital: float = 1_000_000.0,
    lookback: int = 252,
    top_k: int = 10,
    schedule: str = "monthly",
    data_dir: str | None = None,
    symbols: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Run an honest backtest and return the tearsheet as a dict.

    ``signals_source`` is one of ``momentum`` (default), ``mean_reversion``,
    or ``equal_weight``. Universe is the PIT membership of ``index_name``
    on ``end`` (or today) unless ``symbols`` is provided explicitly.
    """
    paths = _resolve_paths(data_dir)
    end_d = _coerce_date(end) or date.today()
    start_d = _coerce_date(start)
    if symbols is not None:
        syms = list(symbols)
    elif index_name:
        syms = oq_data.universe(index_name, end_d, paths=paths)
    else:
        syms = oq_data.list_symbols(paths=paths)
    if not syms:
        raise ValueError("no symbols available; ingest data or pass `symbols`")
    prices_df = oq_data.wide_prices(syms, start=start_d, end=end_d, paths=paths)
    if prices_df.empty:
        raise ValueError("price frame is empty; check ingestion and date range")

    src = signals_source.lower()
    if src == "momentum":
        sigs = bt.momentum_signal(prices_df, lookback=lookback, top_k=top_k, schedule=schedule)
    elif src in {"mean_reversion", "mean-reversion", "reversion"}:
        sigs = bt.mean_reversion_signal(
            prices_df, lookback=max(lookback // 50, 2), bottom_k=top_k, schedule=schedule
        )
    elif src in {"equal_weight", "equal-weight", "equal"}:
        sigs = bt.equal_weight(prices_df.columns, prices_df.index)
    else:
        raise ValueError(f"unknown signals_source: {signals_source!r}")

    result = bt.backtest(
        sigs,
        prices_df,
        costs=costs,
        slippage=float(slippage_bps),
        initial_capital=float(initial_capital),
    )
    summary = result.summary()
    attribution = result.cost_attribution().to_dict()
    return {
        "signals_source": src,
        "universe_size": len(prices_df.columns),
        "period": {
            "start": str(prices_df.index[0].date()),
            "end": str(prices_df.index[-1].date()),
        },
        "costs": costs,
        "slippage_bps": float(slippage_bps),
        "initial_capital": float(initial_capital),
        "summary": {k: float(v) for k, v in summary.items()},
        "cost_attribution_inr": {k: float(v) for k, v in attribution.items()},
        "tearsheet": result.tearsheet(),
    }


__all__ = [
    "get_fundamentals_basic",
    "get_prices",
    "get_universe",
    "run_backtest",
    "screen_stocks",
]
