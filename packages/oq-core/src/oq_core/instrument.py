"""Instrument model: a typed representation of an exchange-listed instrument."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")
_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9&\-\.]{0,49}$")


class Exchange(StrEnum):
    """Indian exchanges supported by OpenQuant."""

    NSE = "NSE"
    BSE = "BSE"


class Segment(StrEnum):
    """Market segments within an exchange."""

    EQ = "EQ"
    FUT = "FUT"
    OPT = "OPT"
    CDS = "CDS"
    COM = "COM"


@dataclass(frozen=True, slots=True)
class Instrument:
    """A single exchange-listed instrument.

    Identity is ``(exchange, segment, symbol)``. ``isin`` is the canonical
    cross-exchange identifier used to follow corporate actions and renames
    (e.g. the HDFC/HDFC Bank merger).

    Parameters
    ----------
    symbol:
        Trading symbol as listed on the exchange (uppercase). For NSE EQ this
        is the tradingsymbol (e.g. ``"RELIANCE"``).
    isin:
        12-character ISIN (e.g. ``"INE002A01018"``). Required for equities;
        optional for derivatives.
    exchange:
        Listing exchange.
    segment:
        Market segment (EQ, FUT, OPT, CDS, COM).
    lot_size:
        Minimum tradable quantity. ``1`` for cash equities, varies for F&O.
    tick_size:
        Minimum price increment in INR. Defaults to ``0.05``.
    name:
        Human-readable company / contract name.
    """

    symbol: str
    exchange: Exchange = Exchange.NSE
    segment: Segment = Segment.EQ
    isin: str | None = None
    lot_size: int = 1
    tick_size: float = 0.05
    name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol:
            raise ValueError("symbol must be a non-empty string")
        if not _SYMBOL_PATTERN.match(self.symbol):
            raise ValueError(
                f"invalid symbol {self.symbol!r}: must be uppercase alphanumeric "
                "(plus & - .), up to 50 chars"
            )
        if self.isin is not None and not _ISIN_PATTERN.match(self.isin):
            raise ValueError(
                f"invalid ISIN {self.isin!r}: expected 12 chars matching "
                "country(2) + alphanumeric(9) + checksum(1)"
            )
        if self.segment is Segment.EQ and self.isin is None:
            raise ValueError("equity instruments require an ISIN")
        if self.lot_size < 1:
            raise ValueError(f"lot_size must be >= 1, got {self.lot_size}")
        if self.tick_size <= 0:
            raise ValueError(f"tick_size must be > 0, got {self.tick_size}")

    @property
    def key(self) -> tuple[str, str, str]:
        """Stable identity tuple suitable for dict keys."""
        return (self.exchange.value, self.segment.value, self.symbol)

    def __str__(self) -> str:
        return f"{self.exchange.value}:{self.segment.value}:{self.symbol}"
