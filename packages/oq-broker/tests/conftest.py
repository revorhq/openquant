"""Shared test fixtures for oq-broker."""

from __future__ import annotations

import pytest
from oq_broker import (
    InstrumentSpec,
    PaperBroker,
    PaperConfig,
    Quote,
    StrategyRegistration,
)


@pytest.fixture
def registration() -> StrategyRegistration:
    return StrategyRegistration(
        algo_id="OQTEST001",
        strategy_id="momentum_v1",
        strategy_name="Test Momentum",
        owner="qa@example.com",
    )


@pytest.fixture
def paper(registration: StrategyRegistration) -> PaperBroker:
    broker = PaperBroker(
        registration=registration,
        config=PaperConfig(starting_cash=1_000_000.0, slippage_bps=10.0),
    )
    broker.register_instrument(InstrumentSpec(symbol="RELIANCE", lot_size=1, tick_size=0.05))
    broker.register_instrument(
        InstrumentSpec(
            symbol="NIFTY24JUNFUT",
            lot_size=25,
            tick_size=0.05,
            freeze_quantity=1800,
        )
    )
    broker.set_quote(Quote(symbol="RELIANCE", last_price=2500.0, bid=2499.95, ask=2500.05))
    broker.set_quote(Quote(symbol="NIFTY24JUNFUT", last_price=23000.0))
    return broker
