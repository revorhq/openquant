# Paper to live

The same strategy file runs paper and live. Mode is configuration.

## Paper

```python
from oq_broker import PaperBroker, PaperConfig, StrategyRegistration

reg = StrategyRegistration(
    algo_id="OPENQ001",
    strategy_id="trend-200d",
    strategy_name="Reliance trend",
    owner="you@example.com",
)

broker = PaperBroker(registration=reg, config=PaperConfig(starting_cash=500_000))
```

## Live (Zerodha)

Three things must all be true to enable live mode:

1. Environment variable: `OQ_LIVE_TRADING=1`
2. Explicit kwarg: `i_accept_live_risk=True`
3. A SEBI-registered `algo_id` on the strategy

```python
from kiteconnect import KiteConnect
from oq_broker import ZerodhaBroker, KillSwitch, AuditLog

kite = KiteConnect(api_key="...")
kite.set_access_token("...")

audit = AuditLog("./journal/audit.jsonl")
kill = KillSwitch(max_loss=10_000, audit=audit)

broker = ZerodhaBroker(
    client=kite,
    registration=reg,
    i_accept_live_risk=True,
    kill_switch=kill,
    audit=audit,
)
```

You will see a banner printed to stderr the moment the broker is
instantiated. That is intentional.

## Kill switch

```python
broker.kill_switch.engage("manual")   # halts all subsequent orders
broker.kill_switch.reset("operator-you")
```

It also auto-engages if realised + unrealised P&L breaches `max_loss`.

## Notifications

```python
from oq_broker import NotificationBridge, TelegramNotifier
import requests

tg = TelegramNotifier(bot_token="...", chat_id="...", client=requests)
NotificationBridge(audit, tg)  # forwards order.filled, kill_switch.engaged, ...
```

## Audit log

Every action is appended to a hash-chained JSON-lines file. Verify at
any time:

```python
assert audit.verify()
```

Tampering with any prior line breaks the chain.
