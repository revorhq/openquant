---
hide:
  - navigation
  - toc
---

# OpenQuant India

> **Honest, open source quant infrastructure for Indian markets.**
>
> *Your backtest is lying to you. We fix that.*

<p align="center">
  <a href="https://pypi.org/project/oqstack/"><img alt="oqstack" src="https://img.shields.io/pypi/v/oqstack?label=oqstack"></a>
  <a href="https://github.com/revorhq/openquant/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/revorhq/openquant/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/revorhq/openquant/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache%202.0-blue.svg"></a>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue.svg"></a>
  <a href="https://github.com/revorhq/openquant"><img alt="Stars" src="https://img.shields.io/github/stars/revorhq/openquant?style=social"></a>
</p>

<p align="center">
  <a href="quickstart/" class="md-button md-button--primary">⚡ 60-second quickstart</a>
  <a href="https://github.com/revorhq/openquant" class="md-button">⭐ Star on GitHub</a>
  <a href="honest-backtesting/" class="md-button">📖 Honest backtesting guide</a>
</p>

---

## The hook

Same strategy. Two backtests.

|         | Gross    | Net of everything |
| ------- | -------: | ----------------: |
| CAGR    | **+22%** | **+9%**           |
| Sharpe  | 1.8      | 0.7               |
| Max DD  | -12%     | -19%              |

Most Indian backtests show you the left column.
Live trading hands you the right one.

**OpenQuant India shows you the right column, by default.**

---

## Install the whole stack in one line

```bash
pip install oqstack
```

Or pick just the pieces you need:

```bash
pip install oq-core oq-data oq-backtest oq-broker oq-mcp oq-zoo
```

---

## What's inside

| Package        | Install                | Purpose |
| -------------- | ---------------------- | ------- |
| **`oqstack`**  | `pip install oqstack`  | Meta-package — the whole stack in one go. |
| `oq-core`      | `pip install oq-core`  | Shared primitives — `Instrument`, NSE `TradingCalendar`. |
| `oq-data`      | `pip install oq-data`  | NSE bhavcopy ingestion, corporate-action adjustments, point-in-time index universes, F&O, delivery %, FII/DII flows, announcements. |
| `oq-backtest`  | `pip install oq-backtest` | Vectorized portfolio backtester with an honest Indian cost engine (STT, brokerage, exchange charges, GST, stamp duty, SEBI fees, STCG/LTCG) + intraday. |
| `oq-mcp`       | `pip install oq-mcp`   | MCP server exposing data + backtests to Claude Desktop and other LLM clients. |
| `oq-broker`    | `pip install oq-broker`| Unified async broker abstraction (Kite / Upstox / Fyers / Dhan) with a SEBI-2026-native paper engine, kill switch, hash-chained audit log, and notifications. |
| `oq-zoo`       | `pip install oq-zoo`   | Community strategy library, gated by an honesty test. |

Each package is independently installable. Use one piece or all of them.

---

## 60-second quickstart

```bash
pip install oqstack
oq sync --quick
```

```python
import oq_data as oq
from oq_backtest import backtest

prices  = oq.prices("RELIANCE", start="2015-01-01", adjusted=True)
signals = prices["close"].rolling(200).mean().lt(prices["close"]).astype(int)

result = backtest(signals, costs="zerodha")
result.tearsheet()      # gross vs net, side by side
```

See the [Quickstart](quickstart.md) for the full walkthrough.

---

## Drive it from Claude

After installing `oq-mcp` and wiring it into Claude Desktop, just ask:

> *"Backtest 12-month momentum on Nifty 500 with Zerodha delivery costs from 2015. Show me gross vs net."*

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

---

<p align="center">
  Apache 2.0 · Built in India · <a href="https://github.com/revorhq/openquant">github.com/revorhq/openquant</a>
</p>
