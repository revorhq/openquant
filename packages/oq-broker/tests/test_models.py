"""Order/position model invariants."""

from __future__ import annotations

import pytest
from oq_broker import OrderRequest, OrderType, Side


def test_order_request_rejects_zero_quantity() -> None:
    with pytest.raises(ValueError):
        OrderRequest(symbol="X", side=Side.BUY, quantity=0)


def test_limit_order_requires_price() -> None:
    with pytest.raises(ValueError):
        OrderRequest(symbol="X", side=Side.BUY, quantity=1, order_type=OrderType.LIMIT)


def test_sl_order_requires_trigger() -> None:
    with pytest.raises(ValueError):
        OrderRequest(symbol="X", side=Side.BUY, quantity=1, order_type=OrderType.SL, price=10.0)


def test_market_order_ok() -> None:
    req = OrderRequest(symbol="X", side=Side.BUY, quantity=5)
    assert req.order_type == OrderType.MARKET
    assert req.quantity == 5
