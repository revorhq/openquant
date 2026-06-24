"""Notification sinks for broker lifecycle events (F4.9, P2).

Pluggable notifiers that broadcast order/fill/cancel/reject/kill-switch
events to Telegram, generic webhooks, or any user-supplied callable.
Transport is injected (HTTP client or send-callable) so the package
itself has no hard HTTP dependency.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol

from oq_broker.compliance import AuditEntry, AuditLog
from oq_broker.models import Fill, Order, OrderStatus


class _HttpClient(Protocol):
    def post(self, url: str, *, json: dict[str, Any] | None = ..., timeout: float = ...) -> Any: ...


class Notifier(Protocol):
    """A notifier consumes a structured event and side-effects it somewhere."""

    def notify(self, event: str, payload: dict[str, Any]) -> None: ...


@dataclass(slots=True)
class CallableNotifier:
    """Wraps any ``Callable[[event, payload], None]`` as a Notifier."""

    fn: Callable[[str, dict[str, Any]], None]

    def notify(self, event: str, payload: dict[str, Any]) -> None:
        self.fn(event, payload)


@dataclass(slots=True)
class WebhookNotifier:
    """POSTs ``{event, payload}`` JSON to ``url`` using an injected HTTP client.

    The client must expose ``post(url, json=..., timeout=...)`` — both
    ``requests`` and ``httpx`` satisfy this. Failures never propagate;
    they are swallowed so a flaky webhook can't crash a live strategy.
    """

    url: str
    client: _HttpClient
    timeout: float = 5.0
    headers: dict[str, str] = field(default_factory=dict)

    def notify(self, event: str, payload: dict[str, Any]) -> None:
        body = {"event": event, "payload": payload}
        try:
            self.client.post(self.url, json=body, timeout=self.timeout)
        except Exception:
            return


@dataclass(slots=True)
class TelegramNotifier:
    """Sends a formatted message to a Telegram chat via the Bot API.

    Provide your own HTTP client (``requests`` or ``httpx``); the package
    has no HTTP dependency. Errors are swallowed.
    """

    bot_token: str
    chat_id: str
    client: _HttpClient
    timeout: float = 5.0
    parse_mode: str = "Markdown"

    @property
    def url(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def _format(self, event: str, payload: dict[str, Any]) -> str:
        head = f"*{event}*"
        body = "\n".join(f"`{k}`: {v}" for k, v in payload.items())
        return f"{head}\n{body}"

    def notify(self, event: str, payload: dict[str, Any]) -> None:
        try:
            self.client.post(
                self.url,
                json={
                    "chat_id": self.chat_id,
                    "text": self._format(event, payload),
                    "parse_mode": self.parse_mode,
                },
                timeout=self.timeout,
            )
        except Exception:
            return


@dataclass(slots=True)
class CompositeNotifier:
    """Fan out a single event to multiple notifiers."""

    notifiers: list[Notifier] = field(default_factory=list)

    def add(self, notifier: Notifier) -> None:
        self.notifiers.append(notifier)

    def notify(self, event: str, payload: dict[str, Any]) -> None:
        for n in self.notifiers:
            try:
                n.notify(event, payload)
            except Exception:
                continue


DEFAULT_EVENTS: frozenset[str] = frozenset(
    {
        "order.placed",
        "order.filled",
        "order.cancelled",
        "order.rejected",
        "kill_switch.engaged",
    }
)


class NotificationBridge:
    """Subscribes to an ``AuditLog`` and forwards selected events to a Notifier.

    The audit log is the source of truth for lifecycle events — this
    bridge wraps :meth:`AuditLog.record` so that every recorded event
    flows through the notifier without changing the broker's call sites.
    """

    def __init__(
        self,
        audit: AuditLog,
        notifier: Notifier,
        events: Iterable[str] = DEFAULT_EVENTS,
    ) -> None:
        self.audit = audit
        self.notifier = notifier
        self.events = frozenset(events)
        self._original_record = audit.record
        audit.record = self._record  # type: ignore[method-assign]

    def _record(self, event: str, payload: dict[str, Any]) -> AuditEntry:
        entry = self._original_record(event, payload)
        if event in self.events:
            self.notifier.notify(event, payload)
        return entry

    def detach(self) -> None:
        self.audit.record = self._original_record  # type: ignore[method-assign]


def order_summary(order: Order) -> dict[str, Any]:
    req = order.request
    return {
        "order_id": order.order_id,
        "status": order.status.value,
        "symbol": req.symbol,
        "side": req.side.value,
        "qty": req.quantity,
        "filled": order.filled_quantity,
        "avg_price": order.average_price,
        "algo_id": req.algo_id,
        "strategy_id": req.strategy_id,
    }


def fill_summary(fill: Fill) -> dict[str, Any]:
    return {
        "fill_id": fill.fill_id,
        "order_id": fill.order_id,
        "symbol": fill.symbol,
        "side": fill.side.value,
        "qty": fill.quantity,
        "price": fill.price,
    }


def is_terminal(status: OrderStatus) -> bool:
    return status in (OrderStatus.COMPLETE, OrderStatus.CANCELLED, OrderStatus.REJECTED)


def json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str, sort_keys=True)


__all__ = [
    "DEFAULT_EVENTS",
    "CallableNotifier",
    "CompositeNotifier",
    "NotificationBridge",
    "Notifier",
    "TelegramNotifier",
    "WebhookNotifier",
    "fill_summary",
    "is_terminal",
    "json_dumps",
    "order_summary",
]
