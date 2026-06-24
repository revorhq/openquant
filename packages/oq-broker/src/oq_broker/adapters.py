"""Live broker adapters.

These adapters provide a thin, typed shim over each broker's official
client SDK. The actual HTTP/WebSocket calls are delegated to a
user-injected ``client`` object that implements the duck-typed protocol
the adapter expects. This keeps the package dependency-light, lets
users pin whichever SDK version they need, and makes the adapters easy
to test offline.

Live-mode is opt-in: instantiating a live adapter raises unless
``OQ_LIVE_TRADING=1`` is set AND the caller passes ``i_accept_live_risk=True``.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterable
from typing import Any, ClassVar, Protocol

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
    _utcnow,
)

LIVE_ACK_BANNER = (
    "\n"
    "============================================================\n"
    "  OPENQUANT LIVE TRADING MODE — REAL MONEY AT RISK\n"
    "  Strategy: {strategy}\n"
    "  Algo-ID:  {algo_id}  (SEBI-registered)\n"
    "  Broker:   {broker}\n"
    "  Kill switch is ARMED. Max-loss: {max_loss}\n"
    "  By proceeding, you accept full responsibility for orders\n"
    "  placed by this process.\n"
    "============================================================\n"
)


def _ensure_live_allowed(broker: str, registration: StrategyRegistration, accepted: bool) -> None:
    """Hard gate on live mode. Refuses to enable without explicit opt-in."""
    if not accepted:
        raise PermissionError(
            "live trading requires i_accept_live_risk=True (paper-first by default)"
        )
    if os.environ.get("OQ_LIVE_TRADING") != "1":
        raise PermissionError("live trading requires environment variable OQ_LIVE_TRADING=1")
    if not registration.algo_id:
        raise PermissionError("SEBI Algo-ID is required for live trading")


class _BrokerClient(Protocol):
    """Duck-typed protocol every adapter expects from an injected SDK client."""

    def place_order(self, **kwargs: Any) -> dict[str, Any]: ...
    def cancel_order(self, order_id: str) -> dict[str, Any]: ...
    def orders(self) -> list[dict[str, Any]]: ...
    def trades(self) -> list[dict[str, Any]]: ...
    def positions(self) -> list[dict[str, Any]]: ...
    def holdings(self) -> list[dict[str, Any]]: ...
    def margins(self) -> dict[str, Any]: ...
    def quote(self, symbol: str) -> dict[str, Any]: ...


def _print_live_banner(broker: str, registration: StrategyRegistration, kill: KillSwitch) -> None:
    print(
        LIVE_ACK_BANNER.format(
            strategy=f"{registration.strategy_name} ({registration.strategy_id})",
            algo_id=registration.algo_id,
            broker=broker,
            max_loss=kill.max_loss if kill.max_loss is not None else "UNSET (dangerous)",
        )
    )


class _BaseLiveAdapter(AsyncBroker):
    """Common live-adapter scaffolding. Concrete adapters override translators."""

    is_paper = False

    def __init__(
        self,
        client: _BrokerClient,
        registration: StrategyRegistration,
        i_accept_live_risk: bool = False,
        kill_switch: KillSwitch | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        super().__init__(registration=registration, kill_switch=kill_switch, audit=audit)
        _ensure_live_allowed(self.name, registration, i_accept_live_risk)
        self.client = client
        _print_live_banner(self.name, registration, self.kill_switch)
        self.audit.record(
            "broker.live_armed",
            {
                "broker": self.name,
                "algo_id": registration.algo_id,
                "strategy_id": registration.strategy_id,
            },
        )

    # subclasses override translators below ------------------------------------

    def _to_client_order(self, request: OrderRequest) -> dict[str, Any]:
        raise NotImplementedError

    def _from_client_order(self, payload: dict[str, Any]) -> Order:
        raise NotImplementedError

    # AsyncBroker API ----------------------------------------------------------

    async def connect(self) -> None:
        self.audit.record("broker.connect", {"broker": self.name})

    async def disconnect(self) -> None:
        self.audit.record("broker.disconnect", {"broker": self.name})

    async def place_order(self, request: OrderRequest) -> Order:
        self.kill_switch.check()
        self._stamp(request)
        payload = self._to_client_order(request)
        resp = self.client.place_order(**payload)
        order = self._from_client_order(resp)
        order.request = request
        order.broker = self.name
        self.audit.record(
            "order.placed",
            {
                "broker": self.name,
                "order_id": order.order_id,
                "broker_order_id": order.broker_order_id,
                "symbol": request.symbol,
                "side": request.side.value,
                "qty": request.quantity,
                "algo_id": request.algo_id,
            },
        )
        return order

    async def cancel_order(self, order_id: str) -> Order:
        resp = self.client.cancel_order(order_id)
        order = self._from_client_order(resp)
        self.audit.record("order.cancelled", {"order_id": order_id})
        return order

    async def get_order(self, order_id: str) -> Order:
        for raw in self.client.orders():
            o = self._from_client_order(raw)
            if o.order_id == order_id or o.broker_order_id == order_id:
                return o
        raise OrderRejected(f"unknown order_id {order_id}")

    async def list_orders(self) -> list[Order]:
        return [self._from_client_order(o) for o in self.client.orders()]

    async def list_fills(self) -> list[Fill]:
        out: list[Fill] = []
        for t in self.client.trades():
            out.append(
                Fill(
                    fill_id=str(t.get("trade_id") or t.get("fill_id") or _new_id("fill")),
                    order_id=str(t.get("order_id", "")),
                    symbol=str(t.get("tradingsymbol") or t.get("symbol")),
                    side=Side(str(t.get("transaction_type") or t.get("side")).upper()),
                    quantity=int(t.get("quantity", 0)),
                    price=float(t.get("average_price") or t.get("price", 0.0)),
                    timestamp=_utcnow(),
                )
            )
        return out

    async def list_positions(self) -> list[Position]:
        out: list[Position] = []
        for p in self.client.positions():
            qty = int(p.get("quantity", 0))
            if qty == 0:
                continue
            out.append(
                Position(
                    symbol=str(p.get("tradingsymbol") or p.get("symbol")),
                    quantity=qty,
                    average_price=float(p.get("average_price", 0.0)),
                    last_price=float(p.get("last_price", 0.0)),
                    product=Product(str(p.get("product", "CNC"))),
                    realised_pnl=float(p.get("realised", 0.0)),
                )
            )
        return out

    async def list_holdings(self) -> list[Holding]:
        out: list[Holding] = []
        for h in self.client.holdings():
            out.append(
                Holding(
                    symbol=str(h.get("tradingsymbol") or h.get("symbol")),
                    isin=h.get("isin"),
                    quantity=int(h.get("quantity", 0)),
                    average_price=float(h.get("average_price", 0.0)),
                    last_price=float(h.get("last_price", 0.0)),
                )
            )
        return out

    async def get_margin(self) -> Margin:
        m = self.client.margins()
        available = float(m.get("available", m.get("net", 0.0)))
        used = float(m.get("used", 0.0))
        return Margin(available=available, used=used, total=available + used)

    async def get_quote(self, symbol: str) -> Quote:
        q = self.client.quote(symbol)
        return Quote(
            symbol=symbol,
            last_price=float(q.get("last_price", 0.0)),
            bid=float(q.get("bid", 0.0)),
            ask=float(q.get("ask", 0.0)),
            volume=int(q.get("volume", 0)),
        )

    async def stream_quotes(self, symbols: Iterable[str]) -> AsyncIterator[Quote]:
        async def _gen() -> AsyncIterator[Quote]:
            for s in symbols:
                yield await self.get_quote(s)

        return _gen()


class ZerodhaBroker(_BaseLiveAdapter):
    """Zerodha Kite Connect adapter (live).

    Users inject a ``KiteConnect`` instance (or any compatible client)
    so the package itself doesn't pull the SDK as a hard dependency.
    """

    name = "zerodha"

    _ORDER_TYPE: ClassVar[dict[OrderType, str]] = {
        OrderType.MARKET: "MARKET",
        OrderType.LIMIT: "LIMIT",
        OrderType.SL: "SL",
        OrderType.SL_M: "SL-M",
    }

    def _to_client_order(self, request: OrderRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tradingsymbol": request.symbol,
            "exchange": request.exchange,
            "transaction_type": request.side.value,
            "quantity": request.quantity,
            "product": request.product.value,
            "order_type": self._ORDER_TYPE[request.order_type],
            "validity": request.validity.value,
            "tag": (request.tag or request.algo_id or "")[:20],
        }
        if request.price is not None:
            payload["price"] = request.price
        if request.trigger_price is not None:
            payload["trigger_price"] = request.trigger_price
        return payload

    def _from_client_order(self, payload: dict[str, Any]) -> Order:
        status_raw = str(payload.get("status", "PENDING")).upper()
        status_map = {
            "OPEN": OrderStatus.OPEN,
            "PUT_ORDER_REQ_RECEIVED": OrderStatus.PENDING,
            "VALIDATION_PENDING": OrderStatus.PENDING,
            "COMPLETE": OrderStatus.COMPLETE,
            "CANCELLED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "TRIGGER PENDING": OrderStatus.OPEN,
        }
        status = status_map.get(status_raw, OrderStatus.PENDING)
        broker_id = str(payload.get("order_id", ""))
        return Order(
            order_id=broker_id or _new_id("zerodha"),
            request=OrderRequest(
                symbol=str(payload.get("tradingsymbol", "")),
                side=Side(str(payload.get("transaction_type", "BUY")).upper()),
                quantity=int(payload.get("quantity", 0) or 0),
            ),
            status=status,
            filled_quantity=int(payload.get("filled_quantity", 0) or 0),
            average_price=float(payload.get("average_price", 0.0) or 0.0),
            broker=self.name,
            broker_order_id=broker_id,
            rejection_reason=payload.get("status_message"),
        )


class DhanBroker(_BaseLiveAdapter):
    """Dhan adapter (live)."""

    name = "dhan"

    _ORDER_TYPE: ClassVar[dict[OrderType, str]] = {
        OrderType.MARKET: "MARKET",
        OrderType.LIMIT: "LIMIT",
        OrderType.SL: "STOP_LOSS",
        OrderType.SL_M: "STOP_LOSS_MARKET",
    }
    _PRODUCT: ClassVar[dict[Product, str]] = {
        Product.CNC: "CNC",
        Product.MIS: "INTRADAY",
        Product.NRML: "MARGIN",
    }

    def _to_client_order(self, request: OrderRequest) -> dict[str, Any]:
        return {
            "security_id": request.symbol,
            "exchange_segment": request.exchange,
            "transaction_type": request.side.value,
            "quantity": request.quantity,
            "order_type": self._ORDER_TYPE[request.order_type],
            "product_type": self._PRODUCT[request.product],
            "price": request.price or 0,
            "trigger_price": request.trigger_price or 0,
            "validity": request.validity.value,
            "tag": (request.tag or request.algo_id or "")[:20],
        }

    def _from_client_order(self, payload: dict[str, Any]) -> Order:
        status_map = {
            "TRANSIT": OrderStatus.PENDING,
            "PENDING": OrderStatus.PENDING,
            "TRADED": OrderStatus.COMPLETE,
            "CANCELLED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "PART_TRADED": OrderStatus.PARTIAL,
        }
        status = status_map.get(
            str(payload.get("order_status", "PENDING")).upper(), OrderStatus.PENDING
        )
        broker_id = str(payload.get("order_id", ""))
        return Order(
            order_id=broker_id or _new_id("dhan"),
            request=OrderRequest(
                symbol=str(payload.get("security_id", "")),
                side=Side(str(payload.get("transaction_type", "BUY")).upper()),
                quantity=int(payload.get("quantity", 0) or 0),
            ),
            status=status,
            filled_quantity=int(payload.get("filled_qty", 0) or 0),
            average_price=float(payload.get("avg_price", 0.0) or 0.0),
            broker=self.name,
            broker_order_id=broker_id,
        )


class UpstoxBroker(_BaseLiveAdapter):
    """Upstox adapter (live, minimal pass-through)."""

    name = "upstox"

    def _to_client_order(self, request: OrderRequest) -> dict[str, Any]:
        return {
            "instrument_token": request.symbol,
            "transaction_type": request.side.value,
            "quantity": request.quantity,
            "order_type": request.order_type.value,
            "product": request.product.value,
            "price": request.price or 0,
            "trigger_price": request.trigger_price or 0,
            "validity": request.validity.value,
            "tag": request.tag or request.algo_id,
        }

    def _from_client_order(self, payload: dict[str, Any]) -> Order:
        broker_id = str(payload.get("order_id", ""))
        return Order(
            order_id=broker_id or _new_id("upstox"),
            request=OrderRequest(
                symbol=str(payload.get("instrument_token", "")),
                side=Side(str(payload.get("transaction_type", "BUY")).upper()),
                quantity=int(payload.get("quantity", 0) or 0),
            ),
            status=OrderStatus(str(payload.get("status", "PENDING")).upper())
            if str(payload.get("status", "")).upper() in OrderStatus.__members__
            else OrderStatus.PENDING,
            filled_quantity=int(payload.get("filled_quantity", 0) or 0),
            average_price=float(payload.get("average_price", 0.0) or 0.0),
            broker=self.name,
            broker_order_id=broker_id,
        )


class FyersBroker(_BaseLiveAdapter):
    """Fyers adapter (live, minimal pass-through)."""

    name = "fyers"

    _ORDER_TYPE: ClassVar[dict[OrderType, int]] = {
        OrderType.MARKET: 2,
        OrderType.LIMIT: 1,
        OrderType.SL: 4,
        OrderType.SL_M: 3,
    }

    def _to_client_order(self, request: OrderRequest) -> dict[str, Any]:
        return {
            "symbol": request.symbol,
            "qty": request.quantity,
            "type": self._ORDER_TYPE[request.order_type],
            "side": 1 if request.side == Side.BUY else -1,
            "productType": request.product.value,
            "limitPrice": request.price or 0,
            "stopPrice": request.trigger_price or 0,
            "validity": request.validity.value,
            "orderTag": request.tag or request.algo_id,
        }

    def _from_client_order(self, payload: dict[str, Any]) -> Order:
        broker_id = str(payload.get("id", ""))
        status_map = {
            1: OrderStatus.CANCELLED,
            2: OrderStatus.COMPLETE,
            4: OrderStatus.PENDING,
            5: OrderStatus.REJECTED,
            6: OrderStatus.OPEN,
        }
        status = status_map.get(int(payload.get("status", 4)), OrderStatus.PENDING)
        return Order(
            order_id=broker_id or _new_id("fyers"),
            request=OrderRequest(
                symbol=str(payload.get("symbol", "")),
                side=Side.BUY if int(payload.get("side", 1)) > 0 else Side.SELL,
                quantity=int(payload.get("qty", 0) or 0),
            ),
            status=status,
            filled_quantity=int(payload.get("filledQty", 0) or 0),
            average_price=float(payload.get("tradedPrice", 0.0) or 0.0),
            broker=self.name,
            broker_order_id=broker_id,
        )


__all__ = [
    "DhanBroker",
    "FyersBroker",
    "UpstoxBroker",
    "ZerodhaBroker",
    "_ensure_live_allowed",
]
