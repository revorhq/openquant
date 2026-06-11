"""Vectorized daily-frequency portfolio backtest engine.

The engine consumes a ``signals`` DataFrame of target weights and a
``prices`` DataFrame of close prices, both indexed by date with symbols as
columns. It produces gross and net equity curves, per-rebalance cost
attribution, and the realized weights and trades, all wrapped in a
:class:`BacktestResult`.

Design choices
--------------
* **Close-to-close**: signals dated ``t`` are executed at the close of ``t``
  and earn the close-to-close return from ``t`` to ``t+1``. To avoid look-
  ahead, generate your signals from data up to and including ``t``'s close
  (typical research practice) and let the engine handle the lag.
* **Weights, not lot sizes**: positions are stored as fractions of portfolio
  value. Lot-size rounding belongs in execution, not research.
* **Costs come out of the portfolio**: net equity at each step is gross
  equity minus the regulatory + slippage charges incurred at the rebalance.
* **NaN-tolerant**: a NaN price for a symbol on a date means "no quote" and
  forces the prior weight forward without a return contribution. A NaN
  signal is treated as 0 (no allocation).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from oq_backtest.costs import CostConfig, compute_costs, resolve_config
from oq_backtest.result import BacktestResult
from oq_backtest.slippage import SlippageModel, resolve_slippage


def _align(signals: pd.DataFrame, prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    symbols = signals.columns.intersection(prices.columns)
    if symbols.empty:
        raise ValueError("signals and prices share no symbols in common")
    s = signals[symbols].copy()
    p = prices[symbols].copy()
    s.index = pd.DatetimeIndex(s.index)
    p.index = pd.DatetimeIndex(p.index)
    common = s.index.intersection(p.index)
    if common.empty:
        raise ValueError("signals and prices share no dates in common")
    s = s.loc[common].sort_index()
    p = p.loc[common].sort_index()
    s = s.fillna(0.0)
    return s, p


def _validate_weights(signals: pd.DataFrame, allow_short: bool, max_leverage: float) -> None:
    if not allow_short and (signals.to_numpy() < -1e-9).any():
        raise ValueError(
            "signals contain negative weights but allow_short=False; "
            "pass allow_short=True or clip to >= 0"
        )
    gross = signals.abs().sum(axis=1)
    if (gross > max_leverage + 1e-9).any():
        bad = gross[gross > max_leverage + 1e-9]
        raise ValueError(
            f"signals exceed max_leverage={max_leverage:g} on "
            f"{len(bad)} dates; first offender: {bad.index[0].date()} = {bad.iloc[0]:.4f}"
        )


def backtest(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    costs: str | CostConfig = "zerodha",
    slippage: SlippageModel | float | int = 5.0,
    initial_capital: float = 1_000_000.0,
    allow_short: bool = False,
    max_leverage: float = 1.0,
) -> BacktestResult:
    """Run an honest, cost-aware backtest of a weight-based strategy.

    Parameters
    ----------
    signals:
        DataFrame of target portfolio weights, indexed by date, columns are
        symbols. A row summing to 1.0 is fully invested; 0.5 is half cash.
    prices:
        DataFrame of close prices in INR, indexed by date, columns are
        symbols. Must overlap with ``signals``.
    costs:
        Either a preset name from :data:`oq_backtest.costs.PRESETS`
        (``"zerodha"``, ``"upstox"``, ``"fyers"``, ``"dhan"``,
        ``"full_service"``, ``"zero"``, and ``*_intraday`` variants) or a
        :class:`CostConfig` instance.
    slippage:
        A :class:`SlippageModel` instance or a number interpreted as fixed
        bps via :class:`FixedBpsSlippage`. Default is 5 bps.
    initial_capital:
        Starting portfolio value in INR. Default 10 lakhs.
    allow_short:
        If False, negative weights raise. Default False (cash-account safe).
    max_leverage:
        Maximum gross exposure (sum of absolute weights). Default 1.0.

    Returns
    -------
    :class:`BacktestResult`
    """
    if initial_capital <= 0:
        raise ValueError("initial_capital must be > 0")
    if max_leverage <= 0:
        raise ValueError("max_leverage must be > 0")

    cfg = resolve_config(costs)
    slip = resolve_slippage(slippage)
    cost_label = costs if isinstance(costs, str) else "custom"

    s, p = _align(signals, prices)
    _validate_weights(s, allow_short=allow_short, max_leverage=max_leverage)

    symbols = s.columns
    dates = s.index
    n_dates = len(dates)

    rets = p.pct_change().fillna(0.0).to_numpy(dtype=float)
    target = s.to_numpy(dtype=float)

    gross_equity = np.empty(n_dates, dtype=float)
    net_equity = np.empty(n_dates, dtype=float)
    realised_weights = np.zeros_like(target)
    trade_buys = np.zeros_like(target)
    trade_sells = np.zeros_like(target)

    cost_rows: list[dict[str, float]] = []

    pv_gross = initial_capital
    pv_net = initial_capital
    prev_w = np.zeros(len(symbols), dtype=float)

    for i in range(n_dates):
        r = rets[i] if i > 0 else np.zeros(len(symbols))
        day_ret = float(prev_w @ r)
        pv_gross *= 1.0 + day_ret
        pv_net *= 1.0 + day_ret

        new_w = target[i]
        delta = new_w - prev_w
        buy_per = np.clip(delta, 0.0, None) * pv_net
        sell_per = np.clip(-delta, 0.0, None) * pv_net

        cost_bd = compute_costs(buy_per, sell_per, cfg)
        slip_cost = slip.slippage_cost(dates[i].date(), symbols, buy_per, sell_per)
        total_cost = cost_bd.total + slip_cost
        pv_net -= total_cost

        gross_equity[i] = pv_gross
        net_equity[i] = pv_net
        realised_weights[i] = new_w
        trade_buys[i] = buy_per
        trade_sells[i] = sell_per

        cost_rows.append(
            {
                "brokerage": cost_bd.brokerage,
                "stt": cost_bd.stt,
                "exchange": cost_bd.exchange,
                "sebi": cost_bd.sebi,
                "gst": cost_bd.gst,
                "stamp_duty": cost_bd.stamp_duty,
                "slippage": slip_cost,
                "total": total_cost,
            }
        )

        prev_w = new_w

    costs_df = pd.DataFrame(cost_rows, index=dates)
    weights_df = pd.DataFrame(realised_weights, index=dates, columns=symbols)
    trades_df = pd.DataFrame(trade_buys - trade_sells, index=dates, columns=symbols)

    return BacktestResult(
        gross_equity=pd.Series(gross_equity, index=dates, name="gross_equity"),
        net_equity=pd.Series(net_equity, index=dates, name="net_equity"),
        weights=weights_df,
        costs=costs_df,
        trades=trades_df,
        initial_capital=float(initial_capital),
        cost_label=cost_label,
    )


__all__ = ["backtest"]
