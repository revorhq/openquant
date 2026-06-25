# OpenQuant India

> **Honest, open source quant infrastructure for Indian markets.**

*Your backtest is lying to you. We fix that.*

---

## What this actually is

If you're trading Indian stocks with code, this project is your toolkit.

- **The problem:** When you test a trading strategy on past data ("backtesting"),
  most free tools lie to you. They show fat profits because they ignore the
  fees, taxes, and friction that eat your returns in real life. A strategy
  that "made 22% a year" on paper often makes 9% or less once you pay
  brokerage, STT, GST, stamp duty, slippage, and taxes. Some lose money.
- **What we built:** A set of small, pip-installable Python packages that do
  the boring-but-critical work right:
  - **`oq-data`** — pulls clean, corporate-action-adjusted NSE price history
    so your tests aren't built on broken data (the HDFC merger alone breaks
    most free sources).
  - **`oq-backtest`** — tests your strategy with *all* the real Indian costs
    baked in (Zerodha/Dhan/Upstox/Fyers presets included) and shows you
    gross vs net side-by-side.
  - **`oq-broker`** — one common interface to place paper or live orders
    across major Indian brokers, with SEBI-2026 compliance (Algo-ID, audit
    log, kill switch) wired in by default.
  - **`oq-mcp`** — lets you ask an AI assistant like Claude to run an honest
    backtest in plain English.
  - **`oq-zoo`** — community strategies that *only* get accepted if they
    survive honest-cost testing.
- **Who it's for:** Retail algo traders, fintech builders, students, and
  researchers who want truthful numbers instead of marketing-deck CAGRs.
- **The one-liner:** Free tools tell you what you want to hear. This one tells
  you what you'll actually make.

---

## The hook

Indian retail quants run backtests that look like this:

> *"+22% CAGR. Sharpe 1.8. Strategy: 12-month momentum on Nifty 500."*

Then they go live and bleed money. Why? Because the backtest didn't model:

- **STT** (~0.1% sell-side on equity delivery)
- **Brokerage** (varies wildly: ₹0 to 0.5%)
- **Exchange transaction charges** (~0.00325% NSE EQ)
- **GST** on brokerage + exchange charges (18%)
- **SEBI fee** (~₹10 per crore)
- **Stamp duty** (varies by state, 0.003%–0.015%)
- **STCG / LTCG** (15% / 12.5% on equity)
- **Slippage and impact** on the close print
- **Survivorship bias** — the Nifty 500 of 2010 is not the Nifty 500 of 2024
- **The HDFC merger** and a hundred other corporate actions

Add all of that back and the "+22% CAGR" becomes a single-digit drag-fest. The
gap between gross and net is where retail quants get destroyed.

**OpenQuant India shows you the right number, by default.**

---

## What this is

A composable, pip-installable stack:

| Package | Status | What it does |
|---|---|---|
| [`oq-core`](./packages/oq-core) | Alpha (Phase 0) | Shared primitives: `Instrument`, NSE `TradingCalendar`. |
| `oq-data` | Planned (Phase 1) | NSE/BSE bhavcopy ingestion, corporate-action-adjusted prices, point-in-time index universes. |
| `oq-backtest` | Planned (Phase 2) | Vectorized portfolio backtester with an honest Indian cost engine. |
| `oq-mcp` | Planned (Phase 3) | MCP server exposing data and backtests to LLM clients (Claude Desktop, etc.). |
| `oq-broker` | Planned (Phase 4) | Unified async broker abstraction (Kite / Upstox / Fyers / Dhan) with a SEBI-2026-native paper engine, kill switch, and audit log. |

Each package is independently installable. Use one piece or all of them.

## What this is NOT

- **Not investment advice.** See [DISCLAIMER.md](./DISCLAIMER.md).
- **Not a trading bot.** It's the infrastructure underneath trading bots.
- **Not a signal-selling service.** We will never sell tips, signals, or
  "guaranteed returns" anything.
- **Not HFT.** Daily-frequency by default; intraday (1-min bars) is on the
  roadmap. No co-location ambitions, ever.
- **Not a black box.** Every cost calculation, every adjustment, every
  data transformation is documented and tested.

---

## 60-second quickstart (Phase 0)

Right now `oq-core` is the only published piece. The data, backtest, MCP, and
broker layers are coming in subsequent phases.

```bash
pip install oq-core
```

```python
from datetime import date
from oq_core import Instrument, Segment, TradingCalendar

reliance = Instrument(symbol="RELIANCE", isin="INE002A01018")
print(reliance)
# NSE:EQ:RELIANCE

cal = TradingCalendar()
cal.is_session(date(2024, 1, 26))          # False — Republic Day
cal.next_session(date(2024, 8, 14))         # date(2024, 8, 16) — skips Independence Day
cal.session_count(date(2024, 1, 1), date(2024, 12, 31))  # NSE sessions in 2024
```

When Phase 1 lands, the next five lines will look like this:

```python
import oq_data as oq

oq.sync(quick=True)
prices = oq.prices("RELIANCE", "2015-01-01", "2024-12-31", adjusted=True)
universe = oq.universe("NIFTY500", as_of="2018-06-30")
```

And Phase 2:

```python
import oq_backtest as bt

result = bt.run(signals, costs="zerodha")
result.tearsheet()   # gross vs net, cost attribution, drawdowns, the works
```

## Product principles

1. **Honesty over excitement.** Net-of-cost numbers are the default. Gross
   requires an explicit flag.
2. **Data correctness is sacred.** A wrong adjusted price is a P0 bug.
3. **Paper-first, safety-default.** Live execution is opt-in, loud, and
   guarded.
4. **Compliance-native.** SEBI 2026 requirements (Algo-ID, audit logs, kill
   switch) are framework features, not afterthoughts.
5. **Composable, not monolithic.** Separate packages with a shared core.
6. **Community is the product.** See [CONTRIBUTING.md](./CONTRIBUTING.md).

## Roadmap

- **Phase 0 — Foundation** (in progress): `oq-core`, repo scaffolding, CI,
  license, manifesto.
- **Phase 1 — Data Layer**: NSE bhavcopy ingestion, corporate actions,
  point-in-time index universes.
- **Phase 2 — Backtester**: vectorized engine + honest cost engine + broker
  presets + tearsheet.
- **Phase 3 — MCP Server**: data + backtests exposed to LLM clients.
- **Phase 4 — Execution Layer**: paper + live broker abstraction with
  SEBI-2026 compliance built in.
- **Phase 5 — Ecosystem**: docs site, strategy zoo, Discord, cohorts.

### What's next — beyond v1.0

We've shipped the boring-but-critical foundation. Now we make it exciting.

**Near term**

- **OpenQuant Web** — a hosted web app for browser-based backtesting,
  tearsheet rendering, and strategy sharing. No `pip install` required.
- **REST + WebSocket API** — `api.openquant.in` exposing prices, universes,
  screeners, and `run_backtest` over HTTPS with API keys and rate limits.
- **Tearsheet GUI** — interactive Plotly/Streamlit app for equity curves,
  drawdown explorers, and per-trade cost attribution.
- **CLI dashboard** — `oq dash` opens a rich TUI for live paper-trading
  monitoring, P&L, and kill-switch control.
- **Options analytics** — Greeks, IV surface, OI heatmap, max-pain finder,
  SEBI F&O position-limit validator.
- **Intraday data feed** — 1-min/5-min bars across NSE EQ + F&O.
- **Strategy marketplace** — `oq-zoo` browsable in the web app with
  one-click clone-and-run.

**Mid term**

- **Live monitoring dashboard** — self-hosted Grafana-style panels for
  positions, slippage attribution, broker latency, and circuit-breaker
  alerts.
- **AI co-pilot in the GUI** — "Why did my strategy lose money on
  2024-03-12?" answered with a chart and a paragraph.
- **Mobile app** — read-only PnL + kill-switch on iOS/Android.
- **Mutual fund / ETF backtesting** module.
- **Event-study toolkit** — earnings, index inclusion, splits, mergers.
- **Factor library** — India-specific factors (momentum, low-vol, quality,
  monsoon-cyclical, election-cycle) with risk decomposition.
- **Notebook gallery** — JupyterLite-powered, runs in the browser.

**Far term**

- **Hosted backtest cloud** — burst your 5-year walk-forward across 100
  cores in seconds; free tier + paid intraday/realtime tier.
- **Strategy certification program** — `oq-zoo` strategies that pass
  walk-forward + out-of-sample get a verifiable badge.
- **Broker partnerships** — official "Works with OpenQuant" co-marketing
  with Zerodha, Dhan, Upstox, Fyers.
- **College curriculum** — course-in-a-box for IITs/IIMs/NITs.
- **Multi-asset** — bonds, commodities (MCX), currency (NSE CDS).
- **Plugin SDK** — third-party data feeds, custom cost models, alternative
  brokers.

**Permanent non-goals**

No signal selling. No "guaranteed returns" anything. No managing third-party
capital. No HFT/co-location. No closing the source on the core.

Want to help? Look for `good first issue` once we open the repo, or read
[CONTRIBUTING.md](./CONTRIBUTING.md).

## Community

Coming soon: Discord, docs site, "30 Days of OpenQuant" challenge. Watch the
repo to be the first to know.

## License

Apache License 2.0. See [LICENSE](./LICENSE) and [NOTICE](./NOTICE).

## Acknowledgments

Inspired by the open quant ecosystems of other markets — zipline, vectorbt,
backtrader, Alpaca, polygon.io — and by every Indian retail trader who has
ever discovered, the hard way, that their backtest was lying to them.
