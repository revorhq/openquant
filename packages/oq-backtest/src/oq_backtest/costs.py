"""Indian equity cost engine.

Implements the regulatory and broker charges that a real Indian equity trade
incurs, and exposes a small set of broker presets so a user can swap a single
string in :func:`oq_backtest.backtest` and get a realistic net P&L.

All rates are expressed as decimal fractions of notional (``0.001`` == 0.1%).
Rates are calibrated against published charge sheets as of 2024-2025; consumers
should treat them as a baseline and override via :class:`CostConfig` for exact
broker / state / segment specifics.

References
----------
* SEBI charges: Rs. 10 per crore of turnover (1e-6 of notional).
* NSE cash exchange transaction charge (revised Oct 2024): 0.00297%.
* GST: 18% on (brokerage + exchange + SEBI) charges only.
* STT delivery: 0.1% on both buy and sell legs.
* STT intraday: 0.025% on sell leg only.
* Stamp duty (delivery, buy only): 0.015%. Intraday buy: 0.003%.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

import numpy as np

Side = Literal["buy", "sell"]


@dataclass(frozen=True, slots=True)
class CostConfig:
    """Per-leg cost configuration for an Indian equity broker.

    All ``*_rate`` fields are decimal fractions of order notional. Brokerage
    additionally supports a per-order ``min`` floor and ``max`` ceiling in
    INR (matching the "0.03% or Rs. 20, whichever lower" convention).
    """

    brokerage_rate: float = 0.0
    brokerage_min: float = 0.0
    brokerage_max: float = float("inf")
    stt_buy_rate: float = 0.001
    stt_sell_rate: float = 0.001
    exchange_rate: float = 0.0000297
    sebi_rate: float = 1e-6
    stamp_duty_buy_rate: float = 0.00015
    gst_rate: float = 0.18
    is_intraday: bool = False

    def __post_init__(self) -> None:
        for name in (
            "brokerage_rate",
            "stt_buy_rate",
            "stt_sell_rate",
            "exchange_rate",
            "sebi_rate",
            "stamp_duty_buy_rate",
            "gst_rate",
        ):
            value = getattr(self, name)
            if value < 0:
                raise ValueError(f"{name} must be >= 0, got {value}")
        if self.brokerage_min < 0:
            raise ValueError("brokerage_min must be >= 0")
        if self.brokerage_max < self.brokerage_min:
            raise ValueError("brokerage_max must be >= brokerage_min")


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Per-rebalance cost decomposition in INR."""

    brokerage: float = 0.0
    stt: float = 0.0
    exchange: float = 0.0
    sebi: float = 0.0
    gst: float = 0.0
    stamp_duty: float = 0.0

    @property
    def total(self) -> float:
        return self.brokerage + self.stt + self.exchange + self.sebi + self.gst + self.stamp_duty

    def as_dict(self) -> dict[str, float]:
        return {
            "brokerage": self.brokerage,
            "stt": self.stt,
            "exchange": self.exchange,
            "sebi": self.sebi,
            "gst": self.gst,
            "stamp_duty": self.stamp_duty,
            "total": self.total,
        }

    def __add__(self, other: CostBreakdown) -> CostBreakdown:
        if not isinstance(other, CostBreakdown):
            return NotImplemented
        return CostBreakdown(
            brokerage=self.brokerage + other.brokerage,
            stt=self.stt + other.stt,
            exchange=self.exchange + other.exchange,
            sebi=self.sebi + other.sebi,
            gst=self.gst + other.gst,
            stamp_duty=self.stamp_duty + other.stamp_duty,
        )


ZERODHA_DELIVERY = CostConfig()

ZERODHA_INTRADAY = CostConfig(
    brokerage_rate=0.0003,
    brokerage_max=20.0,
    stt_buy_rate=0.0,
    stt_sell_rate=0.00025,
    stamp_duty_buy_rate=0.00003,
    is_intraday=True,
)

UPSTOX_DELIVERY = CostConfig()

UPSTOX_INTRADAY = CostConfig(
    brokerage_rate=0.0005,
    brokerage_max=20.0,
    stt_buy_rate=0.0,
    stt_sell_rate=0.00025,
    stamp_duty_buy_rate=0.00003,
    is_intraday=True,
)

FYERS_DELIVERY = CostConfig()

FYERS_INTRADAY = CostConfig(
    brokerage_rate=0.0003,
    brokerage_max=20.0,
    stt_buy_rate=0.0,
    stt_sell_rate=0.00025,
    stamp_duty_buy_rate=0.00003,
    is_intraday=True,
)

DHAN_DELIVERY = CostConfig()

DHAN_INTRADAY = CostConfig(
    brokerage_rate=0.0003,
    brokerage_max=20.0,
    stt_buy_rate=0.0,
    stt_sell_rate=0.00025,
    stamp_duty_buy_rate=0.00003,
    is_intraday=True,
)

FULL_SERVICE_DELIVERY = CostConfig(
    brokerage_rate=0.005,
    brokerage_min=0.0,
    brokerage_max=float("inf"),
)


PRESETS: Mapping[str, CostConfig] = {
    "zerodha": ZERODHA_DELIVERY,
    "zerodha_intraday": ZERODHA_INTRADAY,
    "upstox": UPSTOX_DELIVERY,
    "upstox_intraday": UPSTOX_INTRADAY,
    "fyers": FYERS_DELIVERY,
    "fyers_intraday": FYERS_INTRADAY,
    "dhan": DHAN_DELIVERY,
    "dhan_intraday": DHAN_INTRADAY,
    "full_service": FULL_SERVICE_DELIVERY,
    "zero": CostConfig(
        brokerage_rate=0.0,
        stt_buy_rate=0.0,
        stt_sell_rate=0.0,
        exchange_rate=0.0,
        sebi_rate=0.0,
        stamp_duty_buy_rate=0.0,
        gst_rate=0.0,
    ),
}


def resolve_config(costs: str | CostConfig) -> CostConfig:
    """Look up a preset by name, or return a :class:`CostConfig` unchanged."""
    if isinstance(costs, CostConfig):
        return costs
    if isinstance(costs, str):
        key = costs.lower()
        if key not in PRESETS:
            raise KeyError(f"unknown cost preset {costs!r}; known presets: {sorted(PRESETS)}")
        return PRESETS[key]
    raise TypeError(f"costs must be str or CostConfig, got {type(costs).__name__}")


def _brokerage_per_order(notionals: np.ndarray, cfg: CostConfig) -> np.ndarray:
    """Apply per-order min/max brokerage to an array of per-symbol notionals."""
    raw = notionals * cfg.brokerage_rate
    if cfg.brokerage_min > 0:
        raw = np.where(notionals > 0, np.maximum(raw, cfg.brokerage_min), raw)
    if np.isfinite(cfg.brokerage_max):
        raw = np.where(notionals > 0, np.minimum(raw, cfg.brokerage_max), raw)
    return raw


def compute_costs(
    buy_notionals: np.ndarray | float,
    sell_notionals: np.ndarray | float,
    cfg: CostConfig,
) -> CostBreakdown:
    """Compute the full Indian-market cost breakdown for one rebalance.

    Parameters
    ----------
    buy_notionals, sell_notionals:
        Per-order absolute notional values in INR. May be scalars or arrays.
        Each element is treated as an independent order for brokerage min/max.
    cfg:
        Cost configuration; build one yourself or use :data:`PRESETS`.
    """
    buys = np.atleast_1d(np.asarray(buy_notionals, dtype=float))
    sells = np.atleast_1d(np.asarray(sell_notionals, dtype=float))

    buy_total = float(buys.sum())
    sell_total = float(sells.sum())

    brokerage_buy = float(_brokerage_per_order(buys, cfg).sum())
    brokerage_sell = float(_brokerage_per_order(sells, cfg).sum())
    brokerage = brokerage_buy + brokerage_sell

    stt = buy_total * cfg.stt_buy_rate + sell_total * cfg.stt_sell_rate
    exchange = (buy_total + sell_total) * cfg.exchange_rate
    sebi = (buy_total + sell_total) * cfg.sebi_rate
    gst = (brokerage + exchange + sebi) * cfg.gst_rate
    stamp = buy_total * cfg.stamp_duty_buy_rate

    return CostBreakdown(
        brokerage=brokerage,
        stt=stt,
        exchange=exchange,
        sebi=sebi,
        gst=gst,
        stamp_duty=stamp,
    )


@dataclass(frozen=True, slots=True)
class TaxConfig:
    """Indian equity capital gains tax estimator.

    Not investment advice. Holding period thresholds and rates are based on
    rules as of FY2024-25. Override when legislation changes.
    """

    short_term_days: int = 365
    stcg_rate: float = 0.15
    ltcg_rate: float = 0.125
    ltcg_exempt_inr: float = 125_000.0


__all__ = [
    "DHAN_DELIVERY",
    "DHAN_INTRADAY",
    "FULL_SERVICE_DELIVERY",
    "FYERS_DELIVERY",
    "FYERS_INTRADAY",
    "PRESETS",
    "UPSTOX_DELIVERY",
    "UPSTOX_INTRADAY",
    "ZERODHA_DELIVERY",
    "ZERODHA_INTRADAY",
    "CostBreakdown",
    "CostConfig",
    "TaxConfig",
    "compute_costs",
    "resolve_config",
]
