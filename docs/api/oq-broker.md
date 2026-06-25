# `oq-broker`

Unified async broker interface, paper engine, live adapters, SEBI-2026
compliance primitives, audit log, notifications.

## `AsyncBroker`

The common interface:

```python
class AsyncBroker:
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def place_order(self, request: OrderRequest) -> Order: ...
    async def cancel_order(self, order_id: str) -> Order: ...
    async def get_order(self, order_id: str) -> Order: ...
    async def list_orders(self) -> list[Order]: ...
    async def list_fills(self) -> list[Fill]: ...
    async def list_positions(self) -> list[Position]: ...
    async def list_holdings(self) -> list[Holding]: ...
    async def get_margin(self) -> Margin: ...
    async def get_quote(self, symbol: str) -> Quote: ...
    async def stream_quotes(self, symbols) -> AsyncIterator[Quote]: ...
```

Identical interface for paper and live.

## `PaperBroker`

Models: slippage, partial fills, circuit limits, freeze quantities,
lot sizes, tick rounding.

```python
from oq_broker import PaperBroker, PaperConfig, InstrumentSpec

broker = PaperBroker(
    registration=reg,
    config=PaperConfig(starting_cash=500_000, slippage_bps=5.0),
)
broker.register_instrument(InstrumentSpec(symbol="NIFTY24DECFUT", lot_size=50))
```

## Live adapters

| Adapter         | Status |
| --------------- | ------ |
| `ZerodhaBroker` | Stable |
| `DhanBroker`    | Stable |
| `UpstoxBroker`  | Stable |
| `FyersBroker`   | Stable |

All gated behind `OQ_LIVE_TRADING=1` + `i_accept_live_risk=True`.

## Compliance

```python
from oq_broker import StrategyRegistration, AuditLog, KillSwitch

reg = StrategyRegistration(
    algo_id="OPENQ001",     # SEBI broker-registered Algo-ID
    strategy_id="trend-200",
    strategy_name="Reliance trend",
    owner="you@example.com",
)

audit = AuditLog("./journal/audit.jsonl")
audit.verify()                            # True iff chain is intact

kill = KillSwitch(max_loss=10_000, audit=audit)
kill.engage("manual")
kill.reset("operator-you")
```

## Notifications

```python
from oq_broker import (
    NotificationBridge, TelegramNotifier, WebhookNotifier, CompositeNotifier,
)
import requests

tg = TelegramNotifier(bot_token="...", chat_id="...", client=requests)
hook = WebhookNotifier(url="https://example.com/oq", client=requests)

NotificationBridge(audit, CompositeNotifier([tg, hook]))
```

By default forwards: `order.placed`, `order.filled`, `order.cancelled`,
`order.rejected`, `kill_switch.engaged`.

## Journal export

```python
from oq_broker import export_journal

export_journal(broker, path="./journal/")
# Writes orders.csv, fills.csv, orders.parquet, fills.parquet
```
