"""Order, position, holding, and quote primitives shared across brokers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class Product(StrEnum):
    CNC = "CNC"
    MIS = "MIS"
    NRML = "NRML"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class Validity(StrEnum):
    DAY = "DAY"
    IOC = "IOC"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass(slots=True)
class OrderRequest:
    symbol: str
    side: Side
    quantity: int
    order_type: OrderType = OrderType.MARKET
    product: Product = Product.CNC
    price: float | None = None
    trigger_price: float | None = None
    validity: Validity = Validity.DAY
    exchange: str = "NSE"
    tag: str | None = None
    algo_id: str | None = None
    strategy_id: str | None = None

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be > 0")
        if self.order_type in (OrderType.LIMIT, OrderType.SL) and self.price is None:
            raise ValueError(f"{self.order_type.value} order requires price")
        if self.order_type in (OrderType.SL, OrderType.SL_M) and self.trigger_price is None:
            raise ValueError(f"{self.order_type.value} order requires trigger_price")


@dataclass(slots=True)
class Order:
    order_id: str
    request: OrderRequest
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_price: float = 0.0
    placed_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    broker: str = ""
    broker_order_id: str | None = None
    rejection_reason: str | None = None

    @property
    def pending_quantity(self) -> int:
        return max(self.request.quantity - self.filled_quantity, 0)

    @property
    def is_terminal(self) -> bool:
        return self.status in (OrderStatus.COMPLETE, OrderStatus.CANCELLED, OrderStatus.REJECTED)


@dataclass(slots=True)
class Fill:
    fill_id: str
    order_id: str
    symbol: str
    side: Side
    quantity: int
    price: float
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: int
    average_price: float
    last_price: float = 0.0
    product: Product = Product.CNC
    realised_pnl: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.last_price

    @property
    def unrealised_pnl(self) -> float:
        return (self.last_price - self.average_price) * self.quantity


@dataclass(slots=True)
class Holding:
    symbol: str
    isin: str | None
    quantity: int
    average_price: float
    last_price: float = 0.0


@dataclass(slots=True)
class Quote:
    symbol: str
    last_price: float
    bid: float = 0.0
    ask: float = 0.0
    bid_qty: int = 0
    ask_qty: int = 0
    volume: int = 0
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass(slots=True)
class Margin:
    available: float
    used: float
    total: float


__all__ = [
    "Fill",
    "Holding",
    "Margin",
    "Order",
    "OrderRequest",
    "OrderStatus",
    "OrderType",
    "Position",
    "Product",
    "Quote",
    "Side",
    "Validity",
    "_new_id",
    "_utcnow",
]
