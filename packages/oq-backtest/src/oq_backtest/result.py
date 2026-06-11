"""Backtest result container and one-line tearsheet."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from oq_backtest import metrics


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """All outputs of a single backtest run.

    Equity curves start at ``initial_capital`` and are denominated in INR.
    ``costs`` is a per-rebalance breakdown indexed by date with columns:
    brokerage, stt, exchange, sebi, gst, stamp_duty, slippage, total.
    ``weights`` is the realized portfolio weight time series.
    ``trades`` is per-rebalance net rupee buys (positive) and sells (negative)
    per symbol.
    """

    gross_equity: pd.Series
    net_equity: pd.Series
    weights: pd.DataFrame
    costs: pd.DataFrame
    trades: pd.DataFrame
    initial_capital: float
    cost_label: str

    @property
    def gross_returns(self) -> pd.Series:
        return metrics.to_returns(self.gross_equity)

    @property
    def net_returns(self) -> pd.Series:
        return metrics.to_returns(self.net_equity)

    def summary(self) -> dict[str, float]:
        """Compute the headline metrics as a plain dict."""
        gross = self.gross_equity
        net = self.net_equity
        gross_r = self.gross_returns
        net_r = self.net_returns
        return {
            "gross_cagr": metrics.cagr(gross),
            "net_cagr": metrics.cagr(net),
            "gross_sharpe": metrics.sharpe(gross_r),
            "net_sharpe": metrics.sharpe(net_r),
            "net_sortino": metrics.sortino(net_r),
            "net_max_drawdown": metrics.max_drawdown(net),
            "net_calmar": metrics.calmar(net),
            "annual_volatility": metrics.annualized_volatility(net_r),
            "annual_turnover": metrics.turnover(self.weights),
            "cost_drag": metrics.cost_drag(gross_r, net_r),
            "total_cost_inr": float(self.costs["total"].sum()),
            "final_net_value": float(net.iloc[-1]),
            "final_gross_value": float(gross.iloc[-1]),
        }

    def cost_attribution(self) -> pd.Series:
        """Total INR paid per cost component over the whole backtest."""
        return self.costs.drop(columns=["total"], errors="ignore").sum()

    def tearsheet(self) -> str:
        """Render a single-page text summary suitable for stdout or a log."""
        s = self.summary()
        attribution = self.cost_attribution()
        total_cost = float(self.costs["total"].sum())
        lines: list[str] = []
        lines.append("=" * 64)
        lines.append(f" OpenQuant India - Honest Backtest Tearsheet ({self.cost_label})")
        lines.append("=" * 64)
        lines.append(
            f" Period       : {self.gross_equity.index[0].date()} "
            f"-> {self.gross_equity.index[-1].date()}"
        )
        lines.append(f" Initial cap. : INR {self.initial_capital:>16,.2f}")
        lines.append(f" Final (gross): INR {s['final_gross_value']:>16,.2f}")
        lines.append(f" Final (net)  : INR {s['final_net_value']:>16,.2f}")
        lines.append("-" * 64)
        lines.append(f" CAGR  (gross): {s['gross_cagr'] * 100:>8.2f}%")
        lines.append(f" CAGR  (net)  : {s['net_cagr'] * 100:>8.2f}%")
        lines.append(f" Cost drag    : {s['cost_drag'] * 100:>8.2f}% annualised")
        lines.append(f" Sharpe(net)  : {s['net_sharpe']:>8.2f}")
        lines.append(f" Sortino(net) : {s['net_sortino']:>8.2f}")
        lines.append(f" Max DD (net) : {s['net_max_drawdown'] * 100:>8.2f}%")
        lines.append(f" Calmar (net) : {s['net_calmar']:>8.2f}")
        lines.append(f" Vol (annual) : {s['annual_volatility'] * 100:>8.2f}%")
        lines.append(f" Turnover     : {s['annual_turnover'] * 100:>8.2f}% annual one-way")
        lines.append("-" * 64)
        lines.append(" Cost attribution (INR total over the backtest):")
        for name, value in attribution.items():
            pct = (value / total_cost * 100.0) if total_cost else 0.0
            lines.append(f"   {name:<11s} {value:>16,.2f}   ({pct:5.1f}%)")
        lines.append(f"   {'TOTAL':<11s} {total_cost:>16,.2f}")
        lines.append("=" * 64)
        lines.append(" Reminder: net of STT, brokerage, exchange, SEBI, GST, stamp, and slippage.")
        lines.append(" Not investment advice. See DISCLAIMER.md.")
        lines.append("=" * 64)
        return "\n".join(lines)


__all__ = ["BacktestResult"]
