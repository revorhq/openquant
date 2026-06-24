"""Paper broker end-to-end behaviour."""

from __future__ import annotations

import pytest
from oq_broker import (
    InstrumentSpec,
    KillSwitchTriggered,
    OrderRejected,
    OrderRequest,
    OrderStatus,
    OrderType,
    PaperBroker,
    Quote,
    Side,
)


async def test_connect_and_market_buy_fills(paper: PaperBroker) -> None:
    await paper.connect()
    order = await paper.place_order(OrderRequest(symbol="RELIANCE", side=Side.BUY, quantity=10))
    assert order.status == OrderStatus.COMPLETE
    assert order.filled_quantity == 10
    assert order.average_price > 2500.0  # buy + slippage
    positions = await paper.list_positions()
    assert len(positions) == 1
    assert positions[0].quantity == 10


async def test_round_trip_realises_pnl(paper: PaperBroker) -> None:
    await paper.place_order(OrderRequest(symbol="RELIANCE", side=Side.BUY, quantity=10))
    paper.set_quote(Quote(symbol="RELIANCE", last_price=2600.0))
    await paper.place_order(OrderRequest(symbol="RELIANCE", side=Side.SELL, quantity=10))
    positions = await paper.list_positions()
    assert positions == []
    all_pos = await paper.list_holdings()
    assert all_pos[0].quantity == 10  # CNC holdings stay until COA


async def test_limit_outside_circuit_rejected(paper: PaperBroker) -> None:
    with pytest.raises(OrderRejected):
        await paper.place_order(
            OrderRequest(
                symbol="RELIANCE",
                side=Side.BUY,
                quantity=1,
                order_type=OrderType.LIMIT,
                price=5000.0,
            )
        )


async def test_lot_size_enforced(paper: PaperBroker) -> None:
    with pytest.raises(OrderRejected):
        await paper.place_order(OrderRequest(symbol="NIFTY24JUNFUT", side=Side.BUY, quantity=10))


async def test_freeze_quantity_enforced(paper: PaperBroker) -> None:
    with pytest.raises(OrderRejected):
        await paper.place_order(OrderRequest(symbol="NIFTY24JUNFUT", side=Side.BUY, quantity=2000))


async def test_kill_switch_blocks_new_orders(paper: PaperBroker) -> None:
    paper.kill_switch.engage("test")
    with pytest.raises(KillSwitchTriggered):
        await paper.place_order(OrderRequest(symbol="RELIANCE", side=Side.BUY, quantity=1))


async def test_audit_log_records_lifecycle(paper: PaperBroker) -> None:
    await paper.connect()
    await paper.place_order(OrderRequest(symbol="RELIANCE", side=Side.BUY, quantity=1))
    events = [e.event for e in paper.audit.entries()]
    assert "broker.connect" in events
    assert "order.placed" in events
    assert "order.filled" in events
    assert paper.audit.verify()


async def test_cancel_pending(paper: PaperBroker) -> None:
    paper.register_instrument(InstrumentSpec(symbol="ILLIQ", lot_size=1, tick_size=0.05))
    paper.set_quote(Quote(symbol="ILLIQ", last_price=100.0))
    order = await paper.place_order(
        OrderRequest(
            symbol="ILLIQ",
            side=Side.BUY,
            quantity=1,
            order_type=OrderType.LIMIT,
            price=90.0,
        )
    )
    assert order.status == OrderStatus.OPEN
    cancelled = await paper.cancel_order(order.order_id)
    assert cancelled.status == OrderStatus.CANCELLED


async def test_partial_fill(registration) -> None:
    from oq_broker import PaperConfig

    broker = PaperBroker(
        registration=registration,
        config=PaperConfig(partial_fill_ratio=0.5),
    )
    broker.register_instrument(InstrumentSpec(symbol="X", lot_size=1, tick_size=0.05))
    broker.set_quote(Quote(symbol="X", last_price=100.0))
    order = await broker.place_order(OrderRequest(symbol="X", side=Side.BUY, quantity=10))
    assert order.status == OrderStatus.PARTIAL
    assert order.filled_quantity == 5


async def test_stamp_attaches_algo_id(paper: PaperBroker) -> None:
    order = await paper.place_order(OrderRequest(symbol="RELIANCE", side=Side.BUY, quantity=1))
    assert order.request.algo_id == "OQTEST001"
    assert order.request.strategy_id == "momentum_v1"


async def test_paper_live_parity_runs_same_request(paper: PaperBroker) -> None:
    request = OrderRequest(symbol="RELIANCE", side=Side.BUY, quantity=2)
    order = await paper.place_order(request)
    assert order.broker == "paper"
    assert order.status == OrderStatus.COMPLETE
