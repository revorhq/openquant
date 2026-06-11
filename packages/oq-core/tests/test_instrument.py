"""Tests for oq_core.instrument."""

from __future__ import annotations

import pytest
from oq_core import Exchange, Instrument, Segment


class TestInstrumentValid:
    def test_minimal_equity(self) -> None:
        ins = Instrument(symbol="RELIANCE", isin="INE002A01018")
        assert ins.symbol == "RELIANCE"
        assert ins.isin == "INE002A01018"
        assert ins.exchange is Exchange.NSE
        assert ins.segment is Segment.EQ
        assert ins.lot_size == 1
        assert ins.tick_size == 0.05

    def test_symbol_with_special_chars(self) -> None:
        ins = Instrument(symbol="M&M", isin="INE101A01026")
        assert ins.symbol == "M&M"

    def test_hyphen_and_dot_allowed(self) -> None:
        Instrument(symbol="L&T-FH", isin="INE498L01015")
        Instrument(symbol="NIFTY-25JUN", segment=Segment.FUT, lot_size=75)

    def test_derivative_no_isin_ok(self) -> None:
        ins = Instrument(
            symbol="NIFTY25JUNFUT",
            segment=Segment.FUT,
            lot_size=75,
            tick_size=0.05,
        )
        assert ins.isin is None
        assert ins.lot_size == 75

    def test_frozen(self) -> None:
        ins = Instrument(symbol="RELIANCE", isin="INE002A01018")
        with pytest.raises(AttributeError):
            ins.symbol = "INFY"  # type: ignore[misc]

    def test_key_tuple(self) -> None:
        ins = Instrument(symbol="RELIANCE", isin="INE002A01018")
        assert ins.key == ("NSE", "EQ", "RELIANCE")

    def test_str(self) -> None:
        ins = Instrument(symbol="RELIANCE", isin="INE002A01018")
        assert str(ins) == "NSE:EQ:RELIANCE"

    def test_hashable(self) -> None:
        a = Instrument(symbol="RELIANCE", isin="INE002A01018")
        b = Instrument(symbol="RELIANCE", isin="INE002A01018")
        assert hash(a) == hash(b)
        assert {a, b} == {a}


class TestInstrumentInvalid:
    def test_empty_symbol(self) -> None:
        with pytest.raises(ValueError, match="symbol"):
            Instrument(symbol="", isin="INE002A01018")

    def test_lowercase_symbol(self) -> None:
        with pytest.raises(ValueError, match="symbol"):
            Instrument(symbol="reliance", isin="INE002A01018")

    def test_bad_isin_length(self) -> None:
        with pytest.raises(ValueError, match="ISIN"):
            Instrument(symbol="RELIANCE", isin="INE002A0101")

    def test_bad_isin_country(self) -> None:
        with pytest.raises(ValueError, match="ISIN"):
            Instrument(symbol="RELIANCE", isin="1NE002A01018")

    def test_equity_requires_isin(self) -> None:
        with pytest.raises(ValueError, match="equity"):
            Instrument(symbol="RELIANCE")

    def test_zero_lot_size(self) -> None:
        with pytest.raises(ValueError, match="lot_size"):
            Instrument(symbol="RELIANCE", isin="INE002A01018", lot_size=0)

    def test_negative_tick(self) -> None:
        with pytest.raises(ValueError, match="tick_size"):
            Instrument(symbol="RELIANCE", isin="INE002A01018", tick_size=-0.01)
