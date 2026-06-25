<div align="center">

# OpenQuant India

**Honest, open source quant infrastructure for Indian markets.**

*Your backtest is lying to you. We fix that.*

[![CI](https://github.com/revorhq/openquant/actions/workflows/ci.yml/badge.svg)](https://github.com/revorhq/openquant/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![PyPI - oqstack](https://img.shields.io/pypi/v/oqstack?label=oqstack)](https://pypi.org/project/oqstack/)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)
[![Code of Conduct](https://img.shields.io/badge/contributor%20covenant-2.1-blueviolet.svg)](./CODE_OF_CONDUCT.md)
[![Discord](https://img.shields.io/badge/discord-join-5865F2.svg)](https://discord.gg/openquant)

[Website](https://revorhq.github.io/openquant/) ·
[Docs](https://revorhq.github.io/openquant/) ·
[Quickstart](#-60-second-quickstart) ·
[Packages](#-the-stack) ·
[Roadmap](#-roadmap) ·
[Contribute](./CONTRIBUTING.md)

</div>

---

## ✨ TL;DR

If you trade Indian stocks with code, **free tools lie to you**. They show fat
profits because they ignore the fees, taxes, and friction that eat your
returns. A "+22% CAGR" strategy on paper is often **+9% net** — or negative.

**OpenQuant India** is a set of small, pip-installable Python packages that
get the boring-but-critical parts right: clean NSE data, honest cost
modelling, paper-first execution, and an MCP server so you can drive it all
from Claude.

```bash
pip install oqstack         # everything
# or pick & choose:
pip install oq-core oq-data oq-backtest oq-broker oq-mcp oq-zoo
```

---

## 📦 The stack

| Package | PyPI | Install | What it does |
|---|---|---|---|
| [**`oqstack`**](./packages/oqstack) | [![oqstack](https://img.shields.io/pypi/v/oqstack)](https://pypi.org/project/oqstack/) | `pip install oqstack` | **Meta-package** — installs the full OpenQuant India stack in one go. Use this if you just want everything. |
| [`oq-core`](./packages/oq-core) | [![oq-core](https://img.shields.io/pypi/v/oq-core)](https://pypi.org/project/oq-core/) | `pip install oq-core` | Shared primitives — `Instrument`, NSE `TradingCalendar`, config. |
| [`oq-data`](./packages/oq-data) | [![oq-data](https://img.shields.io/pypi/v/oq-data)](https://pypi.org/project/oq-data/) | `pip install oq-data` | NSE bhavcopy ingestion, corporate-action-adjusted prices, point-in-time index universes. |
| [`oq-backtest`](./packages/oq-backtest) | [![oq-backtest](https://img.shields.io/pypi/v/oq-backtest)](https://pypi.org/project/oq-backtest/) | `pip install oq-backtest` | Vectorized portfolio backtester with the full Indian cost engine + intraday module. |
| [`oq-broker`](./packages/oq-broker) | [![oq-broker](https://img.shields.io/pypi/v/oq-broker)](https://pypi.org/project/oq-broker/) | `pip install oq-broker` | Unified async broker abstraction (Kite/Dhan/Upstox/Fyers) + SEBI-2026 paper engine. |
| [`oq-mcp`](./packages/oq-mcp) | [![oq-mcp](https://img.shields.io/pypi/v/oq-mcp)](https://pypi.org/project/oq-mcp/) | `pip install oq-mcp` | MCP server — drive the stack from Claude Desktop and other LLM clients. |
| [`oq-zoo`](./packages/oq-zoo) | [![oq-zoo](https://img.shields.io/pypi/v/oq-zoo)](https://pypi.org/project/oq-zoo/) | `pip install oq-zoo` | Community strategy library, gated by an honesty test. |

Each package is independently installable. Use one piece, several, or all of
them via `oqstack`.

---

## 🪝 The hook

Indian retail quants run backtests that look like this:

> *"+22% CAGR. Sharpe 1.8. Strategy: 12-month momentum on Nifty 500."*

Then they go live and bleed money. Why? Because the backtest didn't model:

- **STT** (~0.1% sell-side on equity delivery)
- **Brokerage** (₹0 to 0.5%, broker-dependent)
- **Exchange transaction charges** (~0.00325% NSE EQ)
- **GST** on brokerage + exchange charges (18%)
- **SEBI fee** (~₹10 per crore)
- **Stamp duty** (0.003%–0.015%, state-dependent)
- **STCG / LTCG** (15% / 12.5% on equity)
- **Slippage and impact** on the close print
- **Survivorship bias** — the Nifty 500 of 2010 is not the Nifty 500 of 2024
- **The HDFC merger** and a hundred other corporate actions

Add them all back and that "+22% CAGR" becomes a single-digit drag-fest. The
gap between gross and net is where retail quants get destroyed.

**OpenQuant India shows you the right number, by default.**

---

## ⚡ 60-second quickstart

Install the whole stack:

```bash
pip install oqstack
```

Run a honest backtest:

```python
import oq_data as data
import oq_backtest as bt

prices  = data.prices("RELIANCE", "2015-01-01", "2024-12-31", adjusted=True)
signals = bt.momentum_signal(prices, lookback=126)

result = bt.backtest(signals, prices, costs="zerodha")
result.tearsheet()      # gross vs net, cost attribution, drawdowns, the works
```

Or just use the primitives:

```python
from datetime import date
from oq_core import Instrument, TradingCalendar

reliance = Instrument(symbol="RELIANCE", isin="INE002A01018")
print(reliance)                              # NSE:EQ:RELIANCE

cal = TradingCalendar()
cal.is_session(date(2024, 1, 26))            # False — Republic Day
cal.next_session(date(2024, 8, 14))          # date(2024, 8, 16)
cal.session_count(date(2024, 1, 1), date(2024, 12, 31))
```

Ask Claude to run a backtest for you (after installing `oq-mcp` and wiring
it into Claude Desktop):

> *"Backtest 12-month momentum on Nifty 500 with Zerodha delivery costs from 2015. Show me gross vs net."*

---

## 🧭 Product principles

1. **Honesty over excitement.** Net-of-cost numbers are the default. Gross
   requires an explicit flag.
2. **Data correctness is sacred.** A wrong adjusted price is a P0 bug.
3. **Paper-first, safety-default.** Live execution is opt-in, loud, and
   guarded — kill switch + max-loss circuit breaker in framework core.
4. **Compliance-native.** SEBI 2026 (Algo-ID, audit logs, registration
   metadata) is built in, not bolted on.
5. **Composable, not monolithic.** Separate packages with a shared core.
6. **Community is the product.** See [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## 🚫 What this is **NOT**

- **Not investment advice.** See [DISCLAIMER.md](./DISCLAIMER.md).
- **Not a trading bot.** It's the infrastructure underneath trading bots.
- **Not a signal-selling service.** No tips, no signals, no "guaranteed
  returns" anything — ever.
- **Not HFT.** Daily-frequency by default; 1-min intraday on the roadmap.
  No co-location ambitions.
- **Not a black box.** Every cost calculation, every adjustment, every data
  transformation is documented and tested.

---

## 🗺️ Roadmap

### Shipped (v0.1)

- ✅ **Phase 0** — `oq-core`, monorepo, CI, Apache-2.0
- ✅ **Phase 1** — `oq-data`: bhavcopy ingestion, corporate actions, PIT universes
- ✅ **Phase 2** — `oq-backtest`: honest cost engine, broker presets, walk-forward, intraday
- ✅ **Phase 3** — `oq-mcp`: MCP server, screener DSL, 5 tools for LLM clients
- ✅ **Phase 4** — `oq-broker`: 4 broker adapters, paper engine, SEBI-2026 compliance
- ✅ **Phase 5** — docs site, `oq-zoo` honesty gate, Discord/30-Days/cohort kits

### Near term

- **OpenQuant Web** — hosted web app for browser-based backtesting and strategy sharing
- **REST + WebSocket API** — `api.openquant.in` for prices, universes, screeners, backtests
- **Tearsheet GUI** — interactive Plotly/Streamlit equity-curve & cost-attribution explorer
- **CLI dashboard** — `oq dash` TUI for live paper-trading monitoring and kill-switch
- **Options analytics** — Greeks, IV surface, OI heatmap, max-pain, SEBI F&O limit validator
- **Intraday data feed** — 1-min / 5-min bars across NSE EQ + F&O
- **Strategy marketplace** — `oq-zoo` browsable in the web app with one-click clone-and-run

### Mid term

- **Live monitoring dashboard** — Grafana-style panels for positions, slippage, latency, alerts
- **AI co-pilot in the GUI** — "Why did my strategy lose money on 2024-03-12?" answered with chart + paragraph
- **Mobile app** — read-only PnL + kill-switch on iOS/Android
- **Mutual fund / ETF backtesting** module
- **Event-study toolkit** — earnings, index inclusion, splits, mergers
- **Factor library** — India-specific (momentum, low-vol, quality, monsoon, election-cycle)
- **Notebook gallery** — JupyterLite, runs in the browser

### Far term

- **Hosted backtest cloud** — 100-core walk-forward in seconds; free tier + paid intraday/realtime
- **Strategy certification program** — verifiable badge for `oq-zoo` strategies that pass walk-forward + OOS
- **Broker partnerships** — official "Works with OpenQuant" with Zerodha, Dhan, Upstox, Fyers
- **College curriculum** — course-in-a-box for IITs / IIMs / NITs
- **Multi-asset** — bonds, commodities (MCX), currency (NSE CDS)
- **Plugin SDK** — third-party data feeds, custom cost models, alt brokers

### Permanent non-goals

No signal selling · No "guaranteed returns" anything · No managing third-party
capital · No HFT/co-location · No closing the source on the core.

---

## 🤝 Contributing

We love contributors. Easy on-ramps:

- **Good first issues** — tagged on the issue tracker.
- **Strategy zoo** — submit a strategy; the honesty gate decides.
- **Docs** — typos, examples, cookbook recipes.
- **Broker adapters** — add your favourite broker.

Read [CONTRIBUTING.md](./CONTRIBUTING.md) and our
[Code of Conduct](./CODE_OF_CONDUCT.md) before opening a PR. All PRs need a
[DCO sign-off](https://developercertificate.org/) (`git commit -s`).

---

## 💬 Community

- **Discord** — chat, help, strategy show-and-tell *(invite link coming soon)*
- **Docs site** — [revorhq.github.io/openquant](https://revorhq.github.io/openquant/)
- **GitHub Discussions** — design proposals, questions
- **30 Days of OpenQuant** — daily challenge kit in [`community/`](./community/)

---

## 🏷️ Tags

`quant` · `algo-trading` · `india` · `nse` · `bse` · `backtesting` ·
`market-data` · `sebi` · `mcp` · `claude` · `fintech` · `open-source` ·
`python` · `pandas` · `duckdb` · `kite-connect` · `dhan` · `upstox` ·
`fyers`

---

## 📜 License

[Apache License 2.0](./LICENSE) — permissive, fintech-friendly, with an
explicit patent grant. See also [NOTICE](./NOTICE) and
[DISCLAIMER.md](./DISCLAIMER.md).

## 🙏 Acknowledgments

Inspired by the open quant ecosystems of other markets — zipline, vectorbt,
backtrader, Alpaca, polygon.io — and by every Indian retail trader who has
ever discovered, the hard way, that their backtest was lying to them.
