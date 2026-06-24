"""Paper trading engine with realistic Indian-market fills.

Models the frictions retail backtests usually skip: slippage, partial
fills against displayed size, circuit limits (5/10/20% bands), exchange
freeze quantities, lot sizes for F&O, and the SEBI-mandated audit trail
on every action. Identical interface to the live adapters so a strategy
runs unchanged in paper or live mode.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field

from oq_broker.base import AsyncBroker, OrderRejected
from oq_broker.compliance import AuditLog, KillSwitch, StrategyRegistration
from oq_broker.models import (
    Fill,
    Holding,
    Margin,
    Order,
    OrderRequest,
    OrderStatus,
    OrderType,
    Position,
    Product,
    Quote,
    Side,
    _new_id,
)


@dataclass(slots=True)
class InstrumentSpec:
    """Per-instrument microstructure used by the paper engine."""

    symbol: str
    lot_size: int = 1
    tick_size: float = 0.05
    freeze_quantity: int | None = None
    circuit_pct: float = 0.20
    displayed_size: int | None = None


@dataclass(slots=True)
class PaperConfig:
    starting_cash: float = 1_000_000.0
    slippage_bps: float = 5.0
    partial_fill_ratio: float = 1.0
    reject_on_circuit: bool = True
    default_lot_size: int = 1
    default_tick_size: float = 0.05


@dataclass(slots=True)
class _Book:
    cash: float
    orders: dict[str, Order] = field(default_factory=dict)
    fills: list[Fill] = field(default_factory=list)
    positions: dict[str, Position] = field(default_factory=dict)
    holdings: dict[str, Holding] = field(default_factory=dict)
    quotes: dict[str, Quote] = field(default_factory=dict)
    specs: dict[str, InstrumentSpec] = field(default_factory=dict)


class PaperBroker(AsyncBroker):
    """In-memory broker that mimics NSE microstructure."""

    name = "paper"
    is_paper = True

    def __init__(
        self,
        registration: StrategyRegistration,
        config: PaperConfig | None = None,
        kill_switch: KillSwitch | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        super().__init__(registration=registration, kill_switch=kill_switch, audit=audit)
        self.config = config or PaperConfig()
        self._book = _Book(cash=self.config.starting_cash)
        self._connected = False

    # -- microstructure helpers --------------------------------------------------

    def register_instrument(self, spec: InstrumentSpec) -> None:
        self._book.specs[spec.symbol] = spec

    def _spec(self, symbol: str) -> InstrumentSpec:
        return self._book.specs.get(
            symbol,
            InstrumentSpec(
                symbol=symbol,
                lot_size=self.config.default_lot_size,
                tick_size=self.config.default_tick_size,
            ),
        )

    def set_quote(self, quote: Quote) -> None:
        self._book.quotes[quote.symbol] = quote
        if quote.symbol in self._book.positions:
            self._book.positions[quote.symbol].last_price = quote.last_price
        if quote.symbol in self._book.holdings:
            self._book.holdings[quote.symbol].last_price = quote.last_price

    def _round_tick(self, price: float, tick: float) -> float:
        if tick <= 0:
            return price
        return round(round(price / tick) * tick, 4)

    def _apply_slippage(self, price: float, side: Side, tick: float) -> float:
        bump = price * (self.config.slippage_bps / 10_000.0)
        adjusted = price + bump if side == Side.BUY else price - bump
        return self._round_tick(adjusted, tick)

    def _validate(self, request: OrderRequest) -> None:
        self.kill_switch.check()
        spec = self._spec(request.symbol)
        if spec.lot_size > 1 and request.quantity % spec.lot_size != 0:
            raise OrderRejected(
                f"qty {request.quantity} is not a multiple of lot_size {spec.lot_size}"
            )
        if spec.freeze_quantity is not None and request.quantity > spec.freeze_quantity:
            raise OrderRejected(
                f"qty {request.quantity} exceeds exchange freeze qty {spec.freeze_quantity}"
            )
        quote = self._book.quotes.get(request.symbol)
        if quote is None:
            raise OrderRejected(f"no quote available for {request.symbol}")
        if self.config.reject_on_circuit and request.order_type == OrderType.LIMIT:
            assert request.price is not None
            band = quote.last_price * spec.circuit_pct
            lo, hi = quote.last_price - band, quote.last_price + band
            if not (lo <= request.price <= hi):
                raise OrderRejected(
                    f"limit price {request.price} outside circuit band [{lo:.2f}, {hi:.2f}]"
                )

    def _execution_price(self, request: OrderRequest, quote: Quote, spec: InstrumentSpec) -> float:
        if request.order_type == OrderType.MARKET:
            return self._apply_slippage(quote.last_price, request.side, spec.tick_size)
        if request.order_type == OrderType.LIMIT:
            assert request.price is not None
            if request.side == Side.BUY and quote.last_price <= request.price:
                return self._round_tick(min(request.price, quote.last_price), spec.tick_size)
            if request.side == Side.SELL and quote.last_price >= request.price:
                return self._round_tick(max(request.price, quote.last_price), spec.tick_size)
            return 0.0
        return self._apply_slippage(quote.last_price, request.side, spec.tick_size)

    def _fill_quantity(self, requested: int, spec: InstrumentSpec) -> int:
        ratio = max(0.0, min(self.config.partial_fill_ratio, 1.0))
        displayed = spec.displayed_size if spec.displayed_size is not None else requested
        target = min(requested, round(requested * ratio), displayed)
        if spec.lot_size > 1:
            target = (target // spec.lot_size) * spec.lot_size
        return max(target, 0)

    def _update_position(self, request: OrderRequest, fill: Fill) -> None:
        signed_qty = fill.quantity if request.side == Side.BUY else -fill.quantity
        pos = self._book.positions.get(request.symbol)
        if pos is None:
            self._book.positions[request.symbol] = Position(
                symbol=request.symbol,
                quantity=signed_qty,
                average_price=fill.price,
                last_price=fill.price,
                product=request.product,
            )
        else:
            new_qty = pos.quantity + signed_qty
            if pos.quantity == 0 or (pos.quantity > 0) == (signed_qty > 0):
                total_cost = pos.average_price * pos.quantity + fill.price * signed_qty
                pos.average_price = total_cost / new_qty if new_qty else 0.0
            else:
                closed = min(abs(signed_qty), abs(pos.quantity))
                direction = 1 if pos.quantity > 0 else -1
                pos.realised_pnl += direction * (fill.price - pos.average_price) * closed
                if new_qty * pos.quantity < 0:
                    pos.average_price = fill.price
            pos.quantity = new_qty
            pos.last_price = fill.price
        if request.product == Product.CNC and signed_qty > 0:
            h = self._book.holdings.get(request.symbol)
            if h is None:
                self._book.holdings[request.symbol] = Holding(
                    symbol=request.symbol,
                    isin=None,
                    quantity=signed_qty,
                    average_price=fill.price,
                    last_price=fill.price,
                )
            else:
                total = h.average_price * h.quantity + fill.price * signed_qty
                h.quantity += signed_qty
                h.average_price = total / h.quantity if h.quantity else 0.0
                h.last_price = fill.price

    # -- AsyncBroker API ---------------------------------------------------------

    async def connect(self) -> None:
        self._connected = True
        self.audit.record(
            "broker.connect",
            {"broker": self.name, "algo_id": self.registration.algo_id},
        )

    async def disconnect(self) -> None:
        self._connected = False
        self.audit.record("broker.disconnect", {"broker": self.name})

    async def place_order(self, request: OrderRequest) -> Order:
        self._stamp(request)
        order_id = _new_id("paper")
        order = Order(order_id=order_id, request=request, broker=self.name)
        try:
            self._validate(request)
        except OrderRejected as exc:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = str(exc)
            self._book.orders[order_id] = order
            self.audit.record(
                "order.rejected",
                {
                    "order_id": order_id,
                    "reason": str(exc),
                    "symbol": request.symbol,
                    "side": request.side.value,
                    "qty": request.quantity,
                },
            )
            raise
        self._book.orders[order_id] = order
        self.audit.record(
            "order.placed",
            {
                "order_id": order_id,
                "symbol": request.symbol,
                "side": request.side.value,
                "qty": request.quantity,
                "type": request.order_type.value,
                "price": request.price,
                "algo_id": request.algo_id,
                "strategy_id": request.strategy_id,
            },
        )
        await self._execute(order)
        return order

    async def _execute(self, order: Order) -> None:
        request = order.request
        quote = self._book.quotes[request.symbol]
        spec = self._spec(request.symbol)
        price = self._execution_price(request, quote, spec)
        if price <= 0:
            order.status = OrderStatus.OPEN
            return
        qty = self._fill_quantity(request.quantity, spec)
        if qty <= 0:
            order.status = OrderStatus.OPEN
            return
        fill = Fill(
            fill_id=_new_id("fill"),
            order_id=order.order_id,
            symbol=request.symbol,
            side=request.side,
            quantity=qty,
            price=price,
        )
        self._book.fills.append(fill)
        order.filled_quantity += qty
        order.average_price = (
            order.average_price * (order.filled_quantity - qty) + price * qty
        ) / order.filled_quantity
        order.status = (
            OrderStatus.COMPLETE
            if order.filled_quantity >= request.quantity
            else OrderStatus.PARTIAL
        )
        self._update_position(request, fill)
        self._book.cash -= (price * qty) * (1 if request.side == Side.BUY else -1)
        self.audit.record(
            "order.filled",
            {
                "order_id": order.order_id,
                "fill_id": fill.fill_id,
                "qty": qty,
                "price": price,
                "status": order.status.value,
            },
        )

    async def cancel_order(self, order_id: str) -> Order:
        order = self._book.orders.get(order_id)
        if order is None:
            raise OrderRejected(f"unknown order_id {order_id}")
        if order.is_terminal:
            return order
        order.status = OrderStatus.CANCELLED
        self.audit.record("order.cancelled", {"order_id": order_id})
        return order

    async def get_order(self, order_id: str) -> Order:
        order = self._book.orders.get(order_id)
        if order is None:
            raise OrderRejected(f"unknown order_id {order_id}")
        return order

    async def list_orders(self) -> list[Order]:
        return list(self._book.orders.values())

    async def list_fills(self) -> list[Fill]:
        return list(self._book.fills)

    async def list_positions(self) -> list[Position]:
        return [p for p in self._book.positions.values() if p.quantity != 0]

    async def list_holdings(self) -> list[Holding]:
        return [h for h in self._book.holdings.values() if h.quantity != 0]

    async def get_margin(self) -> Margin:
        used = sum(abs(p.market_value) for p in self._book.positions.values())
        return Margin(available=self._book.cash, used=used, total=self._book.cash + used)

    async def get_quote(self, symbol: str) -> Quote:
        q = self._book.quotes.get(symbol)
        if q is None:
            raise OrderRejected(f"no quote for {symbol}")
        return q

    async def stream_quotes(self, symbols: Iterable[str]) -> AsyncIterator[Quote]:
        async def _gen() -> AsyncIterator[Quote]:
            for s in symbols:
                q = self._book.quotes.get(s)
                if q is not None:
                    yield q
                await asyncio.sleep(0)

        return _gen()


__all__ = [
    "InstrumentSpec",
    "PaperBroker",
    "PaperConfig",
]
