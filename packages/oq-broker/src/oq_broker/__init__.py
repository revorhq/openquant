"""OpenQuant India broker abstraction, paper engine, and SEBI-2026 compliance."""

from __future__ import annotations

from oq_broker.adapters import DhanBroker, FyersBroker, UpstoxBroker, ZerodhaBroker
from oq_broker.base import AsyncBroker, BrokerError, OrderRejected
from oq_broker.compliance import (
    AuditEntry,
    AuditLog,
    KillSwitch,
    KillSwitchTriggered,
    MaxLossBreached,
    StrategyRegistration,
    aggregate_pnl,
)
from oq_broker.journal import export_journal, fills_to_frame, orders_to_frame
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
    Validity,
)
from oq_broker.paper import InstrumentSpec, PaperBroker, PaperConfig

__version__ = "0.1.0"

__all__ = [
    "AsyncBroker",
    "AuditEntry",
    "AuditLog",
    "BrokerError",
    "DhanBroker",
    "Fill",
    "FyersBroker",
    "Holding",
    "InstrumentSpec",
    "KillSwitch",
    "KillSwitchTriggered",
    "Margin",
    "MaxLossBreached",
    "Order",
    "OrderRejected",
    "OrderRequest",
    "OrderStatus",
    "OrderType",
    "PaperBroker",
    "PaperConfig",
    "Position",
    "Product",
    "Quote",
    "Side",
    "StrategyRegistration",
    "UpstoxBroker",
    "Validity",
    "ZerodhaBroker",
    "__version__",
    "aggregate_pnl",
    "export_journal",
    "fills_to_frame",
    "orders_to_frame",
]
