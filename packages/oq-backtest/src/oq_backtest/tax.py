"""STCG / LTCG tax estimator with holding-period tracking.

**This is an estimate, not tax advice.** The Indian Income Tax Act and SEBI's
STT framework determine your actual liability. This module models the common
case: listed equity shares with STT paid, taxed at the STCG rate for holdings
under one year and at the LTCG rate (with an annual exemption) for longer
holdings.

The estimator runs a per-symbol FIFO lot ledger against the realized
``trades`` output of a backtest, computes realized P&L per disposal, and
buckets it into short-term and long-term using a configurable holding-period
threshold.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

import pandas as pd

from oq_backtest.costs import TaxConfig


@dataclass(frozen=True, slots=True)
class TaxBreakdown:
    """Annual tax estimate in INR."""

    realized_stcg: float
    realized_ltcg: float
    ltcg_exempt_used: float
    stcg_tax: float
    ltcg_tax: float

    @property
    def total_tax(self) -> float:
        return self.stcg_tax + self.ltcg_tax


@dataclass(slots=True)
class _Lot:
    qty: float
    cost_per_unit: float
    acquired: pd.Timestamp


def estimate_taxes(
    trades_rupees: pd.DataFrame,
    prices: pd.DataFrame,
    cfg: TaxConfig | None = None,
) -> pd.DataFrame:
    """Estimate annual STCG/LTCG taxes from a backtest's rupee trades.

    ``trades_rupees`` is a DataFrame of signed INR trade values per symbol
    per date (positive == buy, negative == sell), matching
    :attr:`BacktestResult.trades`. ``prices`` is the corresponding close
    price table used to back out share quantities.

    Returns a DataFrame indexed by financial year (April-March) with
    columns matching :class:`TaxBreakdown`.
    """
    cfg = cfg or TaxConfig()
    threshold = pd.Timedelta(days=cfg.short_term_days)

    lots: dict[str, deque[_Lot]] = defaultdict(deque)
    realized_per_year: dict[int, dict[str, float]] = defaultdict(lambda: {"stcg": 0.0, "ltcg": 0.0})

    aligned_prices = prices.reindex(index=trades_rupees.index, columns=trades_rupees.columns)

    for ts, row in trades_rupees.iterrows():
        price_row = aligned_prices.loc[ts]
        fy = _financial_year(ts)
        for sym, rupee in row.items():
            if rupee == 0 or pd.isna(rupee):
                continue
            price = price_row.get(sym)
            if pd.isna(price) or price <= 0:
                continue
            qty = float(rupee) / float(price)
            if qty > 0:
                lots[sym].append(_Lot(qty=qty, cost_per_unit=float(price), acquired=ts))
            else:
                qty_to_close = -qty
                proceeds_per_unit = float(price)
                while qty_to_close > 1e-12 and lots[sym]:
                    lot = lots[sym][0]
                    take = min(lot.qty, qty_to_close)
                    pnl = take * (proceeds_per_unit - lot.cost_per_unit)
                    holding = ts - lot.acquired
                    bucket = "stcg" if holding < threshold else "ltcg"
                    realized_per_year[fy][bucket] += pnl
                    lot.qty -= take
                    qty_to_close -= take
                    if lot.qty <= 1e-12:
                        lots[sym].popleft()

    rows: list[dict[str, float]] = []
    index_years: list[int] = []
    for year in sorted(realized_per_year):
        stcg = realized_per_year[year]["stcg"]
        ltcg = realized_per_year[year]["ltcg"]
        ltcg_taxable = max(0.0, ltcg - cfg.ltcg_exempt_inr)
        ltcg_exempt_used = min(max(ltcg, 0.0), cfg.ltcg_exempt_inr)
        stcg_tax = max(0.0, stcg) * cfg.stcg_rate
        ltcg_tax = ltcg_taxable * cfg.ltcg_rate
        rows.append(
            {
                "realized_stcg": stcg,
                "realized_ltcg": ltcg,
                "ltcg_exempt_used": ltcg_exempt_used,
                "stcg_tax": stcg_tax,
                "ltcg_tax": ltcg_tax,
                "total_tax": stcg_tax + ltcg_tax,
            }
        )
        index_years.append(year)
    return pd.DataFrame(rows, index=pd.Index(index_years, name="financial_year"))


def _financial_year(ts: pd.Timestamp) -> int:
    """Indian financial year starts on April 1. FY2024-25 = year 2024."""
    return ts.year if ts.month >= 4 else ts.year - 1


__all__ = ["TaxBreakdown", "estimate_taxes"]
