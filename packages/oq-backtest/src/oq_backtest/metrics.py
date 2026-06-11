"""Performance metrics.

Functions in this module operate on either an equity curve (a level series
that starts at the initial capital) or a returns series (per-period simple
returns). All annualization assumes daily periodicity by default; pass
``periods_per_year`` to switch to weekly/monthly.

These are the *only* metrics the framework treats as authoritative. If you
need fancier risk decomposition, compute it on top of ``BacktestResult``.
"""

from __future__ import annotations

import math

import pandas as pd

DAYS_PER_YEAR = 252


def to_returns(equity: pd.Series) -> pd.Series:
    """Convert an equity curve to simple period returns."""
    return equity.pct_change().fillna(0.0)


def cagr(equity: pd.Series, periods_per_year: int = DAYS_PER_YEAR) -> float:
    """Compound annual growth rate of an equity curve."""
    equity = equity.dropna()
    if len(equity) < 2:
        return 0.0
    start, end = float(equity.iloc[0]), float(equity.iloc[-1])
    if start <= 0 or end <= 0:
        return float("nan")
    years = (len(equity) - 1) / periods_per_year
    if years <= 0:
        return 0.0
    return (end / start) ** (1.0 / years) - 1.0


def annualized_return(returns: pd.Series, periods_per_year: int = DAYS_PER_YEAR) -> float:
    """Geometric annualization of a returns series."""
    returns = returns.dropna()
    if returns.empty:
        return 0.0
    cum = float((1.0 + returns).prod())
    if cum <= 0:
        return float("nan")
    years = len(returns) / periods_per_year
    if years <= 0:
        return 0.0
    return cum ** (1.0 / years) - 1.0


def annualized_volatility(returns: pd.Series, periods_per_year: int = DAYS_PER_YEAR) -> float:
    """Sample standard deviation of returns, annualized by sqrt(periods)."""
    returns = returns.dropna()
    if len(returns) < 2:
        return 0.0
    return float(returns.std(ddof=1)) * math.sqrt(periods_per_year)


def sharpe(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = DAYS_PER_YEAR,
) -> float:
    """Annualized Sharpe ratio with a constant risk-free rate."""
    returns = returns.dropna()
    if len(returns) < 2:
        return 0.0
    rf_per_period = risk_free_rate / periods_per_year
    excess = returns - rf_per_period
    std = float(excess.std(ddof=1))
    if std == 0:
        return 0.0
    return float(excess.mean()) / std * math.sqrt(periods_per_year)


def sortino(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = DAYS_PER_YEAR,
) -> float:
    """Annualized Sortino ratio: excess return over downside deviation."""
    returns = returns.dropna()
    if len(returns) < 2:
        return 0.0
    rf_per_period = risk_free_rate / periods_per_year
    excess = returns - rf_per_period
    downside = excess.clip(upper=0.0)
    dd_std = math.sqrt(float((downside**2).mean()))
    if dd_std == 0:
        return float("inf") if float(excess.mean()) > 0 else 0.0
    return float(excess.mean()) / dd_std * math.sqrt(periods_per_year)


def max_drawdown(equity: pd.Series) -> float:
    """Worst peak-to-trough drawdown as a negative fraction (e.g. -0.32)."""
    equity = equity.dropna()
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def calmar(equity: pd.Series, periods_per_year: int = DAYS_PER_YEAR) -> float:
    """CAGR divided by the absolute max drawdown."""
    mdd = max_drawdown(equity)
    if mdd == 0:
        return float("inf")
    return cagr(equity, periods_per_year) / abs(mdd)


def turnover(weights: pd.DataFrame, periods_per_year: int = DAYS_PER_YEAR) -> float:
    """Annualized one-way turnover of a weights time series.

    Computes the per-period sum of absolute weight changes, averages it, and
    annualizes. A buy-and-hold portfolio yields ~0; a daily rebalance to
    fully different names yields ~periods_per_year.
    """
    if weights.empty:
        return 0.0
    deltas = weights.diff().abs().sum(axis=1).iloc[1:]
    if deltas.empty:
        return 0.0
    return float(deltas.mean()) * periods_per_year / 2.0


def cost_drag(gross_returns: pd.Series, net_returns: pd.Series) -> float:
    """Annualized cost drag = annualized gross return - annualized net return."""
    return annualized_return(gross_returns) - annualized_return(net_returns)


__all__ = [
    "DAYS_PER_YEAR",
    "annualized_return",
    "annualized_volatility",
    "cagr",
    "calmar",
    "cost_drag",
    "max_drawdown",
    "sharpe",
    "sortino",
    "to_returns",
    "turnover",
]
