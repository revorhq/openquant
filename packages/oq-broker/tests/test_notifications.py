"""Tests for the notifications module (F4.9)."""

from __future__ import annotations

from typing import Any

from oq_broker import (
    AuditLog,
    CallableNotifier,
    CompositeNotifier,
    NotificationBridge,
    OrderRequest,
    PaperBroker,
    Side,
    TelegramNotifier,
    WebhookNotifier,
)


class FakeHttp:
    def __init__(self, raise_on_post: bool = False) -> None:
        self.calls: list[dict[str, Any]] = []
        self.raise_on_post = raise_on_post

    def post(self, url: str, *, json: dict[str, Any] | None = None, timeout: float = 5.0) -> Any:
        if self.raise_on_post:
            raise RuntimeError("boom")
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        return {"ok": True}


def test_callable_notifier_invokes_function() -> None:
    received: list[tuple[str, dict[str, Any]]] = []
    n = CallableNotifier(fn=lambda e, p: received.append((e, p)))
    n.notify("order.placed", {"symbol": "RELIANCE"})
    assert received == [("order.placed", {"symbol": "RELIANCE"})]


def test_webhook_notifier_posts_event_and_payload() -> None:
    http = FakeHttp()
    n = WebhookNotifier(url="https://example.com/hook", client=http)
    n.notify("order.filled", {"qty": 10})
    assert http.calls[0]["url"] == "https://example.com/hook"
    assert http.calls[0]["json"] == {"event": "order.filled", "payload": {"qty": 10}}


def test_webhook_notifier_swallows_errors() -> None:
    http = FakeHttp(raise_on_post=True)
    n = WebhookNotifier(url="https://example.com/hook", client=http)
    n.notify("order.placed", {"x": 1})  # must not raise


def test_telegram_notifier_uses_bot_api_url() -> None:
    http = FakeHttp()
    n = TelegramNotifier(bot_token="ABC:123", chat_id="42", client=http)
    n.notify("order.rejected", {"reason": "circuit"})
    call = http.calls[0]
    assert call["url"] == "https://api.telegram.org/botABC:123/sendMessage"
    assert call["json"]["chat_id"] == "42"
    assert "order.rejected" in call["json"]["text"]
    assert "reason" in call["json"]["text"]


def test_composite_fans_out_to_all_notifiers() -> None:
    seen: list[str] = []
    a = CallableNotifier(fn=lambda e, _: seen.append(f"a:{e}"))
    b = CallableNotifier(fn=lambda e, _: seen.append(f"b:{e}"))
    c = CompositeNotifier(notifiers=[a, b])
    c.notify("order.placed", {})
    assert seen == ["a:order.placed", "b:order.placed"]


def test_composite_isolates_failing_notifier() -> None:
    seen: list[str] = []

    def explode(_e: str, _p: dict[str, Any]) -> None:
        raise RuntimeError("boom")

    c = CompositeNotifier(
        notifiers=[
            CallableNotifier(fn=explode),
            CallableNotifier(fn=lambda e, _: seen.append(e)),
        ]
    )
    c.notify("order.filled", {})
    assert seen == ["order.filled"]


def test_bridge_forwards_default_events_only() -> None:
    audit = AuditLog()
    seen: list[str] = []
    NotificationBridge(audit=audit, notifier=CallableNotifier(fn=lambda e, _: seen.append(e)))
    audit.record("order.placed", {"x": 1})
    audit.record("broker.connect", {"x": 1})  # not in DEFAULT_EVENTS
    audit.record("order.filled", {"x": 1})
    assert seen == ["order.placed", "order.filled"]
    assert audit.verify()


def test_bridge_preserves_audit_chain() -> None:
    audit = AuditLog()
    NotificationBridge(audit=audit, notifier=CallableNotifier(fn=lambda *_: None))
    audit.record("order.placed", {"x": 1})
    audit.record("order.filled", {"x": 2})
    assert len(audit) == 2
    assert audit.verify()


def test_bridge_detach_restores_original_record() -> None:
    audit = AuditLog()
    bridge = NotificationBridge(
        audit=audit, notifier=CallableNotifier(fn=lambda *_: None), events={"order.placed"}
    )
    bridge.detach()
    assert audit.record.__func__ is AuditLog.record  # type: ignore[attr-defined]


async def test_bridge_with_paper_broker_emits_on_real_fill(paper: PaperBroker) -> None:
    events: list[str] = []
    NotificationBridge(
        audit=paper.audit, notifier=CallableNotifier(fn=lambda e, _: events.append(e))
    )
    await paper.connect()
    await paper.place_order(OrderRequest(symbol="RELIANCE", side=Side.BUY, quantity=1))
    assert "order.placed" in events
    assert "order.filled" in events
    assert paper.audit.verify()


def test_webhook_via_bridge_end_to_end() -> None:
    audit = AuditLog()
    http = FakeHttp()
    NotificationBridge(
        audit=audit,
        notifier=WebhookNotifier(url="https://hook.example/x", client=http),
        events={"order.placed"},
    )
    audit.record("order.placed", {"symbol": "RELIANCE", "qty": 5})
    audit.record("broker.disconnect", {})
    assert len(http.calls) == 1
    assert http.calls[0]["json"]["payload"]["symbol"] == "RELIANCE"
