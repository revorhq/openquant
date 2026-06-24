"""Corporate-action adjustments for splits, bonuses, and dividends.

The convention follows the standard "back-adjustment" used by Bloomberg,
Yahoo Finance, and zipline: today's price is the truth, and history is
multiplied down so a continuous price series reflects total return.

For a split / bonus on ``ex_date`` with ``ratio`` (e.g. ``5.0`` for a
5-for-1 split or ``2.0`` for a 1:1 bonus that doubles share count):

    adjusted_close[t < ex_date] = close[t] / ratio

For a cash dividend of ``amount`` per share, the adjustment factor is
``(close_prev - amount) / close_prev`` applied to all dates strictly
before ``ex_date``.

Adjustments compound multiplicatively; the function takes a frame of
actions and an unadjusted price series and returns the adjusted series.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

import pandas as pd

from oq_data.config import DataPaths, get_paths

ActionType = Literal["split", "bonus", "dividend"]
ACTION_SCHEMA = ["symbol", "ex_date", "action_type", "ratio", "amount"]


@dataclass(frozen=True, slots=True)
class CorporateAction:
    """One declared corporate action on one symbol."""

    symbol: str
    ex_date: date
    action_type: ActionType
    ratio: float = 1.0
    amount: float = 0.0

    def to_row(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "ex_date": pd.Timestamp(self.ex_date),
            "action_type": self.action_type,
            "ratio": float(self.ratio),
            "amount": float(self.amount),
        }


def empty_actions() -> pd.DataFrame:
    return pd.DataFrame(columns=ACTION_SCHEMA)


def save_actions(df: pd.DataFrame, paths: DataPaths | None = None) -> None:
    paths = paths or get_paths()
    paths.ensure()
    df = df.copy()
    df["ex_date"] = pd.to_datetime(df["ex_date"]).dt.normalize()
    df.to_parquet(paths.corporate_actions, index=False)


def load_actions(paths: DataPaths | None = None) -> pd.DataFrame:
    paths = paths or get_paths()
    if not paths.corporate_actions.exists():
        return empty_actions()
    return pd.read_parquet(paths.corporate_actions)


def add_actions(actions: list[CorporateAction], paths: DataPaths | None = None) -> None:
    paths = paths or get_paths()
    existing = load_actions(paths=paths)
    rows = pd.DataFrame([a.to_row() for a in actions], columns=ACTION_SCHEMA)
    combined = pd.concat([existing, rows], ignore_index=True).drop_duplicates(
        subset=["symbol", "ex_date", "action_type"], keep="last"
    )
    save_actions(combined, paths=paths)


def _factor_series(prices: pd.Series, actions: pd.DataFrame) -> pd.Series:
    """Compute a per-date back-adjustment multiplier for one symbol."""
    factors = pd.Series(1.0, index=prices.index, dtype=float)
    if actions.empty:
        return factors
    actions = actions.sort_values("ex_date")
    closes = prices.copy()
    for _, row in actions.iterrows():
        ex = pd.Timestamp(row["ex_date"]).normalize()
        atype = row["action_type"]
        ratio = float(row["ratio"]) if not pd.isna(row["ratio"]) else 1.0
        amount = float(row["amount"]) if not pd.isna(row["amount"]) else 0.0
        if atype in ("split", "bonus"):
            if ratio <= 0:
                continue
            mask = factors.index < ex
            factors.loc[mask] = factors.loc[mask] / ratio
        elif atype == "dividend":
            prior = closes[closes.index < ex]
            if prior.empty:
                continue
            prev_close = float(prior.iloc[-1])
            if prev_close <= 0 or amount <= 0:
                continue
            adj = max(0.0, (prev_close - amount) / prev_close)
            mask = factors.index < ex
            factors.loc[mask] = factors.loc[mask] * adj
    return factors


def adjust_prices(
    prices: pd.DataFrame,
    actions: pd.DataFrame,
    fields: tuple[str, ...] = ("open", "high", "low", "close", "prev_close"),
) -> pd.DataFrame:
    """Back-adjust a long-form EOD frame for splits, bonuses, and dividends.

    ``prices`` is the long-form EOD schema (one row per symbol per date)
    written by :mod:`oq_data.storage`. ``actions`` matches
    :data:`ACTION_SCHEMA`. Returns a copy with the listed ``fields``
    replaced by their back-adjusted values and ``volume`` scaled up by
    split/bonus ratios so dollar volume is preserved.
    """
    if prices.empty:
        return prices.copy()
    out = prices.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    if actions.empty:
        return out
    actions = actions.copy()
    actions["ex_date"] = pd.to_datetime(actions["ex_date"]).dt.normalize()
    for symbol, group in out.groupby("symbol", sort=False):
        sym_actions = actions[actions["symbol"] == symbol]
        if sym_actions.empty:
            continue
        group = group.sort_values("date").set_index("date")
        factor = _factor_series(group["close"], sym_actions)
        for col in fields:
            if col in group.columns:
                group[col] = group[col].astype(float) * factor
        if "volume" in group.columns:
            inv = pd.Series(1.0, index=factor.index, dtype=float)
            split_bonus = sym_actions[sym_actions["action_type"].isin(["split", "bonus"])]
            for _, row in split_bonus.sort_values("ex_date").iterrows():
                ratio = float(row["ratio"])
                if ratio <= 0:
                    continue
                ex = pd.Timestamp(row["ex_date"]).normalize()
                mask = inv.index < ex
                inv.loc[mask] = inv.loc[mask] * ratio
            group["volume"] = (group["volume"].astype(float) * inv).round().astype("Int64")
        group = group.reset_index()
        sym_mask = out["symbol"] == symbol
        out_sym_sorted = out[sym_mask].sort_values("date")
        for col in [*fields, "volume"]:
            if col in group.columns:
                out.loc[out_sym_sorted.index, col] = group[col].to_numpy()
    return out


__all__ = [
    "ACTION_SCHEMA",
    "ActionType",
    "CorporateAction",
    "add_actions",
    "adjust_prices",
    "empty_actions",
    "load_actions",
    "save_actions",
]
