"""Unified async broker interface.

Every broker adapter (paper, Zerodha, Dhan, Upstox, Fyers) implements
:class:`AsyncBroker`. Strategy code is broker-agnostic: switching from
paper to live is a one-line config change, and the same code path runs
in both modes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from oq_broker.compliance import AuditLog, KillSwitch, StrategyRegistration
from oq_broker.models import (
    Fill,
    Holding,
    Margin,
    Order,
    OrderRequest,
    Position,
    Quote,
)


class BrokerError(RuntimeError):
    """Base class for all broker-side errors."""


class OrderRejected(BrokerError):
    """Raised when the broker rejects an order (pre- or post-submission)."""


class AsyncBroker(ABC):
    """Async broker interface.

    Implementations MUST:

    * apply the kill switch before any state-changing call,
    * record every order/fill/cancel through the audit log,
    * stamp ``algo_id`` + ``strategy_id`` from
      :class:`~oq_broker.compliance.StrategyRegistration` on every order.
    """

    name: str = "abstract"
    is_paper: bool = False

    def __init__(
        self,
        registration: StrategyRegistration,
        kill_switch: KillSwitch | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        self.registration = registration
        self.audit = audit or AuditLog()
        self.kill_switch = kill_switch or KillSwitch(audit=self.audit)
        if self.kill_switch.audit is None:
            self.kill_switch.audit = self.audit

    def _stamp(self, request: OrderRequest) -> OrderRequest:
        request.algo_id = self.registration.algo_id
        request.strategy_id = self.registration.strategy_id
        return request

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def place_order(self, request: OrderRequest) -> Order: ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> Order: ...

    @abstractmethod
    async def get_order(self, order_id: str) -> Order: ...

    @abstractmethod
    async def list_orders(self) -> list[Order]: ...

    @abstractmethod
    async def list_fills(self) -> list[Fill]: ...

    @abstractmethod
    async def list_positions(self) -> list[Position]: ...

    @abstractmethod
    async def list_holdings(self) -> list[Holding]: ...

    @abstractmethod
    async def get_margin(self) -> Margin: ...

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote: ...

    @abstractmethod
    async def stream_quotes(self, symbols: Iterable[str]) -> object: ...


__all__ = [
    "AsyncBroker",
    "BrokerError",
    "OrderRejected",
]
