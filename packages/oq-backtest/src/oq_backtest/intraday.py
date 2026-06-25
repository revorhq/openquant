"""Intraday backtesting (F2.11).

Thin layer over :func:`oq_backtest.backtest` for bar data finer than daily
(typically 1-min to 60-min NSE bars). Adds:

* a sensible default cost preset (intraday brokerage / STT sell-only /
  reduced stamp duty),
* an optional **session square-off** that forces all positions to zero at
  the configured session-end bar — the dominant SEBI-2026 retail-intraday
  pattern,
* periods-per-year aware metrics so Sharpe and annualization are right
  on minute bars.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

import pandas as pd

from oq_backtest import metrics
from oq_backtest.costs import CostConfig, resolve_config
from oq_backtest.engine import backtest
from oq_backtest.result import BacktestResult
from oq_backtest.slippage import SlippageModel

NSE_OPEN = time(9, 15)
NSE_CLOSE = time(15, 30)


@dataclass(frozen=True, slots=True)
class IntradayConfig:
    """Intraday-specific knobs."""

    bar_minutes: int = 1
    session_start: time = NSE_OPEN
    session_end: time = NSE_CLOSE
    square_off: bool = True

    def __post_init__(self) -> None:
        if self.bar_minutes <= 0:
            raise ValueError("bar_minutes must be > 0")
        if self.session_end <= self.session_start:
            raise ValueError("session_end must be after session_start")

    @property
    def bars_per_session(self) -> int:
        start_min = self.session_start.hour * 60 + self.session_start.minute
        end_min = self.session_end.hour * 60 + self.session_end.minute
        span = end_min - start_min
        return max(1, span // self.bar_minutes)

    @property
    def periods_per_year(self) -> int:
        return self.bars_per_session * 252


def apply_square_off(signals: pd.DataFrame, config: IntradayConfig) -> pd.DataFrame:
    """Force the last bar of each trading session to zero weights."""
    if signals.empty:
        return signals
    idx = pd.DatetimeIndex(signals.index)
    out = signals.copy()
    out.index = idx
    session_dates = idx.normalize()
    # For each date, find the last bar at or before session_end and zero it.
    session_end = config.session_end
    out_arr = out.to_numpy(copy=True)
    last_pos_per_date: dict[pd.Timestamp, int] = {}
    for pos, ts in enumerate(idx):
        if ts.time() <= session_end:
            last_pos_per_date[session_dates[pos]] = pos
    for pos in last_pos_per_date.values():
        out_arr[pos, :] = 0.0
    return pd.DataFrame(out_arr, index=idx, columns=out.columns)


def backtest_intraday(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    costs: str | CostConfig = "zerodha_intraday",
    slippage: SlippageModel | float | int = 2.0,
    initial_capital: float = 1_000_000.0,
    allow_short: bool = True,
    max_leverage: float = 5.0,
    config: IntradayConfig | None = None,
) -> BacktestResult:
    """Run an intraday backtest with session-aware defaults.

    Parameters
    ----------
    signals, prices:
        Same shape as :func:`oq_backtest.backtest` but indexed by intraday
        timestamps (e.g. one row per minute).
    costs:
        Defaults to ``"zerodha_intraday"`` — the right preset for the
        typical Indian retail intraday user. Override with any
        :class:`CostConfig`.
    slippage:
        Defaults to 2 bps — tighter than daily because intraday spreads on
        liquid Indian equities are sub-5 bps. Override for less liquid
        symbols.
    allow_short:
        Defaults to True — intraday short selling is allowed in MIS.
    max_leverage:
        Defaults to 5.0 — broker MIS leverage typically 5x on liquid
        equities; reduce for conservative paper runs.
    config:
        Intraday session configuration. If ``square_off`` is True (default)
        every session-end bar's weights are forced to zero so positions
        flatten before the close.
    """
    cfg = config or IntradayConfig()
    sigs = apply_square_off(signals, cfg) if cfg.square_off else signals
    result = backtest(
        signals=sigs,
        prices=prices,
        costs=costs,
        slippage=slippage,
        initial_capital=initial_capital,
        allow_short=allow_short,
        max_leverage=max_leverage,
    )
    return result


def intraday_summary(result: BacktestResult, config: IntradayConfig) -> dict[str, float]:
    """Compute summary metrics annualized for the intraday bar frequency."""
    ppy = config.periods_per_year
    gross = result.gross_equity
    net = result.net_equity
    gross_r = result.gross_returns
    net_r = result.net_returns
    return {
        "gross_cagr": metrics.cagr(gross, periods_per_year=ppy),
        "net_cagr": metrics.cagr(net, periods_per_year=ppy),
        "gross_sharpe": metrics.sharpe(gross_r, periods_per_year=ppy),
        "net_sharpe": metrics.sharpe(net_r, periods_per_year=ppy),
        "net_sortino": metrics.sortino(net_r, periods_per_year=ppy),
        "net_max_drawdown": metrics.max_drawdown(net),
        "net_calmar": metrics.calmar(net, periods_per_year=ppy),
        "annual_volatility": metrics.annualized_volatility(net_r, periods_per_year=ppy),
        "annual_turnover": metrics.turnover(result.weights, periods_per_year=ppy),
        "total_cost_inr": float(result.costs["total"].sum()),
        "final_net_value": float(net.iloc[-1]),
        "final_gross_value": float(gross.iloc[-1]),
        "bars_per_session": config.bars_per_session,
        "periods_per_year": ppy,
    }


__all__ = [
    "NSE_CLOSE",
    "NSE_OPEN",
    "IntradayConfig",
    "apply_square_off",
    "backtest_intraday",
    "intraday_summary",
]


# Backwards-compat helper for users who only need to validate that a CostConfig
# is intraday-flavoured. Useful in MCP server tools.
def is_intraday_preset(costs: str | CostConfig) -> bool:
    cfg = resolve_config(costs)
    return cfg.is_intraday
