"""Live adapter gating + translation tests using fake clients."""

from __future__ import annotations

from typing import Any

import pytest
from oq_broker import (
    DhanBroker,
    OrderRequest,
    Side,
    StrategyRegistration,
    ZerodhaBroker,
)


class FakeKite:
    def __init__(self) -> None:
        self.placed: list[dict[str, Any]] = []

    def place_order(self, **kwargs: Any) -> dict[str, Any]:
        self.placed.append(kwargs)
        return {
            "order_id": "K123",
            "status": "OPEN",
            "tradingsymbol": kwargs["tradingsymbol"],
            "transaction_type": kwargs["transaction_type"],
            "quantity": kwargs["quantity"],
            "filled_quantity": 0,
            "average_price": 0.0,
        }

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        return {"order_id": order_id, "status": "CANCELLED"}

    def orders(self) -> list[dict[str, Any]]:
        return [
            {
                "order_id": "K123",
                "status": "COMPLETE",
                "tradingsymbol": "RELIANCE",
                "transaction_type": "BUY",
                "quantity": 1,
                "filled_quantity": 1,
                "average_price": 2500.0,
            }
        ]

    def trades(self) -> list[dict[str, Any]]:
        return [
            {
                "trade_id": "T1",
                "order_id": "K123",
                "tradingsymbol": "RELIANCE",
                "transaction_type": "BUY",
                "quantity": 1,
                "average_price": 2500.0,
            }
        ]

    def positions(self) -> list[dict[str, Any]]:
        return [
            {
                "tradingsymbol": "RELIANCE",
                "quantity": 1,
                "average_price": 2500.0,
                "last_price": 2510.0,
                "product": "CNC",
                "realised": 0.0,
            }
        ]

    def holdings(self) -> list[dict[str, Any]]:
        return [
            {
                "tradingsymbol": "RELIANCE",
                "isin": "INE002A01018",
                "quantity": 1,
                "average_price": 2500.0,
                "last_price": 2510.0,
            }
        ]

    def margins(self) -> dict[str, Any]:
        return {"available": 50000.0, "used": 2500.0}

    def quote(self, symbol: str) -> dict[str, Any]:
        return {"last_price": 2510.0, "bid": 2509.95, "ask": 2510.05, "volume": 1000}


@pytest.fixture
def registration() -> StrategyRegistration:
    return StrategyRegistration(
        algo_id="OQLIVE001",
        strategy_id="live_test",
        strategy_name="Live Test",
        owner="qa@example.com",
    )


def test_live_mode_requires_explicit_acceptance(registration: StrategyRegistration) -> None:
    with pytest.raises(PermissionError):
        ZerodhaBroker(client=FakeKite(), registration=registration, i_accept_live_risk=False)


def test_live_mode_requires_env_var(registration: StrategyRegistration, monkeypatch) -> None:
    monkeypatch.delenv("OQ_LIVE_TRADING", raising=False)
    with pytest.raises(PermissionError):
        ZerodhaBroker(client=FakeKite(), registration=registration, i_accept_live_risk=True)


@pytest.fixture
def live_env(monkeypatch) -> None:
    monkeypatch.setenv("OQ_LIVE_TRADING", "1")


async def test_zerodha_place_order_translates_fields(
    live_env: None, registration: StrategyRegistration, capsys
) -> None:
    client = FakeKite()
    broker = ZerodhaBroker(client=client, registration=registration, i_accept_live_risk=True)
    order = await broker.place_order(OrderRequest(symbol="RELIANCE", side=Side.BUY, quantity=1))
    assert order.broker == "zerodha"
    assert client.placed[0]["tradingsymbol"] == "RELIANCE"
    assert client.placed[0]["transaction_type"] == "BUY"
    assert client.placed[0]["tag"] == "OQLIVE001"


async def test_zerodha_positions_and_holdings(
    live_env: None, registration: StrategyRegistration
) -> None:
    broker = ZerodhaBroker(client=FakeKite(), registration=registration, i_accept_live_risk=True)
    positions = await broker.list_positions()
    holdings = await broker.list_holdings()
    margin = await broker.get_margin()
    assert positions[0].symbol == "RELIANCE"
    assert holdings[0].isin == "INE002A01018"
    assert margin.available == 50000.0


class FakeDhan:
    def place_order(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "order_id": "D1",
            "order_status": "PENDING",
            "security_id": kwargs["security_id"],
            "transaction_type": kwargs["transaction_type"],
            "quantity": kwargs["quantity"],
        }

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        return {"order_id": order_id, "order_status": "CANCELLED"}

    def orders(self) -> list[dict[str, Any]]:
        return []

    def trades(self) -> list[dict[str, Any]]:
        return []

    def positions(self) -> list[dict[str, Any]]:
        return []

    def holdings(self) -> list[dict[str, Any]]:
        return []

    def margins(self) -> dict[str, Any]:
        return {"available": 10000.0, "used": 0.0}

    def quote(self, symbol: str) -> dict[str, Any]:
        return {"last_price": 100.0}


async def test_dhan_place_order_translates(
    live_env: None, registration: StrategyRegistration
) -> None:
    broker = DhanBroker(client=FakeDhan(), registration=registration, i_accept_live_risk=True)
    order = await broker.place_order(OrderRequest(symbol="11536", side=Side.SELL, quantity=2))
    assert order.broker == "dhan"
    assert order.broker_order_id == "D1"


def test_dhan_blocks_without_env(registration: StrategyRegistration, monkeypatch) -> None:
    monkeypatch.delenv("OQ_LIVE_TRADING", raising=False)
    with pytest.raises(PermissionError):
        DhanBroker(client=FakeDhan(), registration=registration, i_accept_live_risk=True)
