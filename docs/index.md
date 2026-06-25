# OpenQuant India

> **Honest, open source quant infrastructure for Indian markets.**
>
> *Your backtest is lying to you. We fix that.*

---

## The hook

Same strategy. Two backtests.

|         | Gross   | Net of everything |
| ------- | ------: | ----------------: |
| CAGR    | **+22%** | **+9%**         |
| Sharpe  | 1.8     | 0.7               |
| Max DD  | -12%    | -19%              |

Most Indian backtests show you the left column.
Live trading hands you the right one.

**OpenQuant India shows you the right column, by default.**

---

## What this is

A composable, pip-installable stack:

| Package        | Status | Purpose |
| -------------- | ------ | ------- |
| `oq-core`      | Stable | Shared primitives — `Instrument`, NSE `TradingCalendar`. |
| `oq-data`      | Stable | NSE bhavcopy ingestion, corporate-action adjustments, point-in-time index universes, F&O, delivery %, FII/DII flows, announcements. |
| `oq-backtest`  | Stable | Vectorized portfolio backtester with an honest Indian cost engine (STT, brokerage, exchange charges, GST, stamp duty, SEBI fees, STCG/LTCG). |
| `oq-mcp`       | Stable | MCP server exposing data + backtests to Claude Desktop and other LLM clients. |
| `oq-broker`    | Stable | Unified async broker abstraction (Kite / Upstox / Fyers / Dhan) with a SEBI-2026-native paper engine, kill switch, hash-chained audit log, and notifications. |

Each package is independently installable. Use one piece or all of them.

---

## 60-second quickstart

```bash
pip install oq-data oq-backtest
oq sync --quick
```

```python
import oq_data as oq
from oq_backtest import backtest

prices = oq.prices("RELIANCE", start="2015-01-01", adjusted=True)
signals = prices["close"].rolling(200).mean().lt(prices["close"]).astype(int)

result = backtest(signals, costs="zerodha")
result.tearsheet()  # gross vs net side by side
```

See [Quickstart](quickstart.md) for the full walkthrough.

---

## What this is NOT

- **Not investment advice.** See [Disclaimer](compliance/disclaimer.md).
- **Not a trading bot.** It's the infrastructure underneath trading bots.
- **Not a signal-selling service.** No tips, ever.
- **Not HFT.** Daily-frequency by default; intraday is on the roadmap.
- **Not a black box.** Every cost calculation, every adjustment, every transformation is documented and tested.

---

## Get involved

- [Contributing guide](community/contributing.md)
- [Good first issues](community/good-first-issues.md)
- [Strategy zoo](community/zoo.md) — community strategies that pass the honesty gate
- [30 Days of OpenQuant](community/30-days.md) — daily challenge
- [Cohort program](community/cohorts.md)
