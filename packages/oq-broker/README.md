# oq-broker

Unified async broker interface, realistic paper engine, and SEBI-2026 native
compliance for OpenQuant India.

One interface (`AsyncBroker`) for Zerodha Kite Connect, Dhan, Upstox, and
Fyers. Same strategy file runs paper or live — mode is config. Built-in
Algo-ID tracking, immutable audit log, mandatory kill switch, and max-loss
circuit breaker. Live mode is gated behind explicit opt-in.

```bash
pip install oq-broker
```

```python
from oq_broker import PaperBroker
broker = PaperBroker(initial_capital=1_000_000)
await broker.place_order(symbol="RELIANCE", qty=10, side="BUY")
```

Part of [OpenQuant India](https://github.com/revorhq/openquant) — honest, open
source quant infrastructure for Indian markets. Apache 2.0.
