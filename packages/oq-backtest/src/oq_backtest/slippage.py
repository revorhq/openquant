"""Slippage models.

A slippage model converts a desired notional trade into an extra cost charged
to the portfolio at execution time. The result is in INR and is *additive* to
the regulatory cost engine in :mod:`oq_backtest.costs`.

Signed convention: slippage is always a positive cost (you pay more on buys,
receive less on sells). The vectorized engine applies it symmetrically to
``buy + sell`` traded notional.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd


class SlippageModel(ABC):
    """Strategy interface for slippage cost models."""

    @abstractmethod
    def slippage_cost(
        self,
        when: date,
        symbols: pd.Index,
        buy_notional: np.ndarray,
        sell_notional: np.ndarray,
    ) -> float:
        """Return slippage cost in INR for the given trade on ``when``."""


@dataclass(frozen=True, slots=True)
class FixedBpsSlippage(SlippageModel):
    """Charge a flat number of basis points on traded notional.

    The default of 5 bps is a reasonable rough estimate for liquid Nifty 100
    names traded at the closing print. Illiquid names should use a larger
    value or :class:`VolumeParticipationSlippage`.
    """

    bps: float = 5.0

    def __post_init__(self) -> None:
        if self.bps < 0:
            raise ValueError(f"bps must be >= 0, got {self.bps}")

    def slippage_cost(
        self,
        when: date,
        symbols: pd.Index,
        buy_notional: np.ndarray,
        sell_notional: np.ndarray,
    ) -> float:
        traded = float(np.asarray(buy_notional).sum() + np.asarray(sell_notional).sum())
        return traded * self.bps / 10_000.0


@dataclass(frozen=True, slots=True)
class VolumeParticipationSlippage(SlippageModel):
    """Slippage that grows with participation in average daily volume.

    Cost in bps per leg is approximated as ``impact_coeff * participation^0.5``
    (a standard square-root impact form). ``participation`` is the trade's
    rupee notional divided by the symbol's rupee average daily volume.

    Volumes must be a wide DataFrame indexed by date with symbols as columns,
    stated in rupees (price * shares). Symbols missing from the table fall
    back to ``default_bps``.
    """

    adv_rupees: pd.DataFrame
    impact_coeff: float = 10.0
    default_bps: float = 10.0

    def __post_init__(self) -> None:
        if self.impact_coeff < 0:
            raise ValueError("impact_coeff must be >= 0")
        if self.default_bps < 0:
            raise ValueError("default_bps must be >= 0")

    def slippage_cost(
        self,
        when: date,
        symbols: pd.Index,
        buy_notional: np.ndarray,
        sell_notional: np.ndarray,
    ) -> float:
        traded_per = np.asarray(buy_notional) + np.asarray(sell_notional)
        if not traded_per.any():
            return 0.0
        when_ts = pd.Timestamp(when)
        idx = self.adv_rupees.index
        if when_ts not in idx:
            pos = idx.searchsorted(when_ts) - 1
            if pos < 0:
                return float((traded_per * self.default_bps / 10_000.0).sum())
            row_date = idx[pos]
        else:
            row_date = when_ts
        adv = self.adv_rupees.loc[row_date].reindex(symbols).to_numpy(dtype=float)
        cost = 0.0
        for traded, adv_v in zip(traded_per, adv, strict=True):
            if traded <= 0:
                continue
            if not np.isfinite(adv_v) or adv_v <= 0:
                cost += traded * self.default_bps / 10_000.0
                continue
            participation = traded / adv_v
            bps = self.impact_coeff * np.sqrt(participation) * 100.0
            cost += traded * bps / 10_000.0
        return float(cost)


@dataclass(frozen=True, slots=True)
class SpreadSlippage(SlippageModel):
    """Pay half the quoted bid-ask spread on every leg.

    ``spread_bps`` may be a scalar (applied uniformly) or a wide DataFrame
    of bid-ask spread in basis points indexed by date with symbols as
    columns. Missing values fall back to ``default_bps``.
    """

    spread_bps: float | pd.DataFrame = 4.0
    default_bps: float = 4.0

    def __post_init__(self) -> None:
        if isinstance(self.spread_bps, int | float) and self.spread_bps < 0:
            raise ValueError("spread_bps must be >= 0")
        if self.default_bps < 0:
            raise ValueError("default_bps must be >= 0")

    def slippage_cost(
        self,
        when: date,
        symbols: pd.Index,
        buy_notional: np.ndarray,
        sell_notional: np.ndarray,
    ) -> float:
        traded_per = np.asarray(buy_notional) + np.asarray(sell_notional)
        if not traded_per.any():
            return 0.0
        if isinstance(self.spread_bps, int | float):
            half = float(self.spread_bps) / 2.0
            return float((traded_per * half / 10_000.0).sum())
        when_ts = pd.Timestamp(when)
        idx = self.spread_bps.index
        if when_ts not in idx:
            pos = idx.searchsorted(when_ts) - 1
            if pos < 0:
                half = self.default_bps / 2.0
                return float((traded_per * half / 10_000.0).sum())
            row_date = idx[pos]
        else:
            row_date = when_ts
        spreads = (
            self.spread_bps.loc[row_date]
            .reindex(symbols)
            .fillna(self.default_bps)
            .to_numpy(dtype=float)
        )
        halves = spreads / 2.0
        return float((traded_per * halves / 10_000.0).sum())


def resolve_slippage(slippage: SlippageModel | float | int) -> SlippageModel:
    """Coerce a number to :class:`FixedBpsSlippage`, pass models through."""
    if isinstance(slippage, SlippageModel):
        return slippage
    if isinstance(slippage, int | float):
        return FixedBpsSlippage(bps=float(slippage))
    raise TypeError(
        f"slippage must be SlippageModel or a numeric bps value, got {type(slippage).__name__}"
    )


__all__ = [
    "FixedBpsSlippage",
    "SlippageModel",
    "SpreadSlippage",
    "VolumeParticipationSlippage",
    "resolve_slippage",
]
