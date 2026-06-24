"""Tiny screener DSL evaluated against a wide adjusted-price frame.

Supported expressions (case-insensitive on the field name):

* ``close > 100``
* ``returns_20d > 0.05``
* ``returns_252d >= 0.10``
* ``pct_from_52w_high <= 0.05``  (within 5% of 52-week high)
* ``pct_from_52w_low >= 0.20``
* ``sma_50_above_sma_200``
* ``volume > 100000``  (requires a volume frame)

Multiple expressions can be combined with ``&`` (AND) or ``|`` (OR).
Symbols missing data for the most-recent observation are dropped.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

import numpy as np
import pandas as pd

_NUMERIC_FIELDS = {
    "close",
    "volume",
    "returns_5d",
    "returns_20d",
    "returns_60d",
    "returns_252d",
    "pct_from_52w_high",
    "pct_from_52w_low",
}
_BOOLEAN_FIELDS = {"sma_50_above_sma_200"}

_OP_RE = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(<=|>=|==|<|>)\s*(-?\d+(?:\.\d+)?)\s*$")
_BOOL_RE = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*$")


def _last(prices: pd.DataFrame, lookback: int) -> pd.Series:
    if lookback <= 0 or lookback >= len(prices):
        return pd.Series(index=prices.columns, dtype=float)
    return prices.iloc[-1] / prices.iloc[-1 - lookback] - 1.0


def _features(prices: pd.DataFrame, volume: pd.DataFrame | None) -> pd.DataFrame:
    if prices.empty:
        return pd.DataFrame()
    last = prices.iloc[-1]
    high_52w = prices.tail(252).max()
    low_52w = prices.tail(252).min()
    sma_50 = prices.tail(50).mean()
    sma_200 = prices.tail(200).mean()
    feats = pd.DataFrame(
        {
            "close": last,
            "returns_5d": _last(prices, 5),
            "returns_20d": _last(prices, 20),
            "returns_60d": _last(prices, 60),
            "returns_252d": _last(prices, 252),
            "pct_from_52w_high": (high_52w - last) / high_52w,
            "pct_from_52w_low": (last - low_52w) / low_52w,
            "sma_50_above_sma_200": sma_50 > sma_200,
        }
    )
    if volume is not None and not volume.empty:
        feats["volume"] = volume.iloc[-1].reindex(feats.index)
    return feats.replace([np.inf, -np.inf], np.nan)


def _parse_atom(expr: str) -> tuple[str, str, float | bool]:
    m = _OP_RE.match(expr)
    if m:
        field, op, num = m.group(1), m.group(2), float(m.group(3))
        if field not in _NUMERIC_FIELDS:
            raise ValueError(f"unknown numeric field: {field}")
        return field, op, num
    m = _BOOL_RE.match(expr)
    if m:
        field = m.group(1)
        if field not in _BOOLEAN_FIELDS:
            raise ValueError(f"unknown boolean field: {field}")
        return field, "==", True
    raise ValueError(f"could not parse screener expression: {expr!r}")


def _apply(feats: pd.DataFrame, atom: tuple[str, str, float | bool]) -> pd.Series:
    field, op, rhs = atom
    series = feats[field]
    if op == ">":
        return series > rhs
    if op == ">=":
        return series >= rhs
    if op == "<":
        return series < rhs
    if op == "<=":
        return series <= rhs
    if op == "==":
        return series == rhs
    raise ValueError(f"unknown operator: {op}")


def screen(
    prices: pd.DataFrame,
    expressions: Iterable[str],
    combine: str = "and",
    volume: pd.DataFrame | None = None,
    universe: Iterable[str] | None = None,
) -> list[str]:
    """Return the symbols passing every (or any) supplied expression."""
    exprs = [e.strip() for e in expressions if e and e.strip()]
    if not exprs:
        raise ValueError("at least one expression is required")
    if prices.empty:
        return []
    if universe is not None:
        keep = [s for s in universe if s in prices.columns]
        prices = prices[keep]
        if volume is not None:
            volume = volume[[c for c in volume.columns if c in keep]]
    feats = _features(prices, volume)
    masks = [_apply(feats, _parse_atom(e)) for e in exprs]
    combined = masks[0].astype(bool)
    op = combine.lower()
    for m in masks[1:]:
        combined = (combined & m) if op == "and" else (combined | m)
    return sorted(combined[combined.fillna(False)].index.tolist())


__all__ = ["screen"]
