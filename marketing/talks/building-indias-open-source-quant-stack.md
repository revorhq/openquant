---
marp: true
theme: default
paginate: true
backgroundColor: "#0b0f17"
color: "#e6e6e6"
title: "Building India's Open Source Quant Stack"
description: "OpenQuant India — honest, open source quant infrastructure for Indian markets."
author: "Shantanu Vishwanadha"
keywords: ["quant", "india", "nse", "sebi", "open source", "backtesting", "mcp"]
---

<!--
F5.6 — Conference talk deck (PRD §6 Phase 5).

Render with Marp CLI:
  npx @marp-team/marp-cli marketing/talks/building-indias-open-source-quant-stack.md --pdf
  npx @marp-team/marp-cli marketing/talks/building-indias-open-source-quant-stack.md --pptx
  npx @marp-team/marp-cli marketing/talks/building-indias-open-source-quant-stack.md --html

Target runtime: 25 minutes + 5 min Q&A. ~28 slides @ ~45-60s each.
Speaker notes live in HTML comments after each slide.
-->

# Building India's Open Source Quant Stack

### Honest infrastructure for a market that doesn't have any

**Shantanu Vishwanadha**
github.com/revorhq/openquant

<!--
Open with the punchline, not the agenda. India has algos doing 50%+ of
turnover and zero open source infrastructure. That is the whole talk.
-->

---

## The chart that started this project

Same strategy. Two backtests.

| | Gross | Net of everything |
|---|---:|---:|
| CAGR | **+22%** | **+9%** |
| Sharpe | 1.8 | 0.7 |
| Max DD | -12% | -19% |

> Most Indian backtests show you the left column.
> Live trading hands you the right one.

<!--
Lead with the gross-vs-net delta. This is the emotional hook. Mention
specifically: STT + brokerage + GST + stamp duty + SEBI fees + slippage
+ STCG taxes. Each of these is small. Together they eat 13 points of CAGR.
-->

---

## Who I am

- Built/scaled open source dev tools at Zencoder
- Indian retail quant for the last several years
- 1,500+ dev community, sit at the AI × fintech intersection
- This project is what I wish existed when I started

<!--
30 seconds. Establishes you have skin in the game on both sides:
infra builder AND retail trader who has been burned by dirty data.
-->

---

## The state of Indian quant tooling

- **US has:** zipline, vectorbt, Alpaca, polygon.io, QuantConnect
- **India has:** ???
- Existing open projects are **apps**, not **infrastructure**
- All built on **yfinance** — which silently lies about Indian data
- **Zero** open point-in-time index constituents

<!--
The killer question: name one open source piece of Indian quant
infrastructure that is not a wrapper around yfinance.
Pause. Wait for it. Nobody can.
-->

---

## Why now: April 1, 2026

**SEBI Retail Algo Framework — fully mandatory**

- Every algo order must carry a registered **Algo-ID**
- Strategy registration metadata required
- API security + immutable audit trail
- Kill switch in every retail algo system

> No open source library handles any of this today.

<!--
This is the regulatory forcing function. If you ship a retail algo
system in 2026 without these features, you are non-compliant. The
gap is wide open.
-->

---

## Four compounding problems

1. **Dirty data** — survivorship bias, no corp actions, HDFC merger breaks naive analysis
2. **Dishonest backtests** — no open tool models Indian frictions correctly
3. **Broker lock-in** — every broker API is different; SEBI 2026 adds compliance work
4. **No AI-native access** — you cannot do quant research conversationally

<!--
Each problem is a slide later. This is the table of contents disguised
as a problem statement.
-->

---

# Problem 1 — Dirty Data

---

## yfinance for Indian markets is a trap

- No corporate actions for India
- Survivorship bias built-in (delisted names disappear silently)
- Format-inconsistent across years
- One bad adjusted price kills a strategy

<!--
Show a concrete number: what HDFC Bank's price looks like in yfinance
vs the actual NSE bhavcopy across the merger date. The numbers don't
match. People built strategies on the wrong number.
-->

---

## The HDFC merger as a test fixture

- HDFC Ltd + HDFC Bank merger, **2023-07-01**
- Naive symbol-keyed lookup → broken time series
- ISIN-keyed mapping → correct continuation
- We ship this as a **test fixture** so regressions are loud

<!--
Story arc: a real merger, a real bug, a permanent test that prevents it.
This is how "data correctness is sacred" becomes a code artifact.
-->

---

## Point-in-time index universes

- **Survivorship bias = strategy's silent killer**
- You cannot rebuild Nifty 50 from today's constituents
- We reconstruct Nifty 50/100/500 from NSE change announcements
- `oq.universe("NIFTY500", as_of="2018-03-01")` → what was actually in it that day

<!--
This is the most under-appreciated piece. Reproducible research is
impossible without point-in-time universes. We're the first OSS
project to ship them for India.
-->

---

# Problem 2 — Dishonest Backtests

---

## What "net of everything" actually means

For a single equity intraday trade:

```
STT        0.025% sell  ←  flat tax
Brokerage  varies       ←  broker-dependent
Exchange   ~0.00345%    ←  NSE turnover charge
GST        18% on (broker + exchange)
Stamp duty 0.003% buy   ←  state-dependent
SEBI fee   ₹10/cr
STCG       15% on profits  ← if held < 1y
```

> Skip any one of these and your backtest lies.

<!--
Walk through each line. Note GST is 18% on top of brokerage+exchange,
so brokerage savings compound. STT is asymmetric (sell-side only for
equities). This is what every "free" backtester ignores.
-->

---

## The cost engine

```python
from oq_backtest import backtest

result = backtest(
    signals,
    costs="zerodha",   # or "upstox", "fyers", "dhan", custom
    slippage="vwap",   # or "fixed_bps", "spread"
)
result.tearsheet()     # gross + net side by side
result.cost_attribution()
```

- Pluggable cost models per broker
- Cost **attribution** breakdown — see where the money went
- Tax estimator with STCG/LTCG holding-period tracking

<!--
The API is one line. The output is honest. That is the entire pitch.
-->

---

## Walk-forward by default

- Single-shot backtest = overfit machine
- Walk-forward and OOS splits as first-class API
- Anti-overfitting guardrails the user has to opt OUT of
- "If your edge needs the test set, you don't have an edge"

<!--
This is a research-discipline statement disguised as a feature. We
make it harder to lie to yourself. That is the whole product.
-->

---

# Problem 3 — Broker Lock-in & Compliance

---

## The same strategy, two brokers, one file

```python
broker = PaperBroker(registration=reg)           # paper
broker = ZerodhaBroker(client=kite, registration=reg,
                       i_accept_live_risk=True)  # live
broker = DhanBroker(client=dhan, registration=reg,
                    i_accept_live_risk=True)     # live

await broker.place_order(OrderRequest(
    symbol="RELIANCE", side=Side.BUY, quantity=10
))
```

> Mode is **config**, not a code rewrite.

<!--
Show this slide for 20 seconds. Let it sink in. Strategy code is
broker-agnostic. Adapters absorb each broker's API quirks.
-->

---

## SEBI-2026 native — not bolted on

- `StrategyRegistration` validates Algo-ID (`[A-Z0-9]{4,32}`) at construction
- Every order **stamped** with `algo_id` + `strategy_id` automatically
- `AuditLog` is SHA-256 **hash-chained** JSON lines on disk
- `KillSwitch` lives in the framework core, mandatory
- `max_loss` auto-engages and **stays engaged** until manual reset

<!--
Hash-chained means tampering is detectable. This is what an exchange
auditor will want when they ask "show me your order trail." We ship
it on day one.
-->

---

## Paper engine that actually models NSE

| Reality | We model |
|---|---|
| Slippage | bps + VWAP + spread |
| Partial fills | displayed-size cap |
| Circuit limits | 5/10/20% bands → reject |
| Lot sizes | F&O multiple enforcement |
| Freeze quantities | per-instrument cap |

> Your paper PnL should approximate your live PnL.

<!--
A paper engine that always fills at last_price is a lying paper
engine. We don't ship a liar.
-->

---

## Live mode is loud

```python
ZerodhaBroker(client=kite, registration=reg,
              i_accept_live_risk=True)   # explicit kwarg
# Also requires: OQ_LIVE_TRADING=1 env var
# Also prints: a giant risk banner to stdout
```

- Live trading is **opt-in three ways**
- The library never accidentally trades your money
- Kill switch is one method call away

<!--
This is the "project must not be the reason a retail user blows up"
principle made concrete. Three independent toggles to go live.
-->

---

# Problem 4 — AI-Native Access

---

## Quant research is conversational now

> *"Claude, backtest Nifty 500 momentum with Zerodha costs since 2015"*

The MCP server exposes:

- `get_prices` — clean OHLCV by symbol and date range
- `get_universe` — PIT index constituents
- `screen_stocks` — DSL screener
- `get_fundamentals_basic`
- **`run_backtest`** — natural-language parameterized, honest costs

<!--
This is the demo moment. Run the actual MCP demo here if it's working.
30 seconds. Audience reaction is the slide.
-->

---

## Demo

*(live MCP demo — 30s)*

```
You: backtest Nifty 500 momentum with Zerodha costs since 2015
Claude: → run_backtest(...)
        Gross CAGR: 24%  |  Net CAGR: 11%
        Cost drag: 13pp  (STT 4.2, brokerage 1.1, GST 0.9, ...)
```

<!--
Have a backup video clip in case wifi dies. The clip is also a
shipping artifact — F3.6 in the PRD.
-->

---

# What we ship

---

## The package layout

```
openquant/                  monorepo
├── oq-core        primitives: Instrument, NSE calendar
├── oq-data        bhavcopy ingestion, corp actions, PIT universes
├── oq-backtest    honest-cost vectorized engine
├── oq-mcp         MCP server for Claude Desktop & friends
├── oq-broker      paper + Zerodha/Dhan/Upstox/Fyers adapters
└── oq-zoo         community strategy library (separate repo)
```

- Apache 2.0
- All pip-installable, composable, take one piece or all
- One shared core, no monolith

<!--
Six packages, one principle: use one piece or all of them. The "use
one piece" path is critical for adoption — devs hate "all or nothing"
frameworks.
-->

---

## Why Apache 2.0

- Permissive — fintechs and brokers can adopt without legal review
- **Explicit patent grant** — the edge over MIT; fintech is patent-noisy
- Open-core sustainability path stays open
- GPL/AGPL would have killed adoption on day one

<!--
Indian fintechs WILL ask their legal team about your license. AGPL
is an immediate "no." Apache 2.0 is "fine, ship it." Choose the
license that lets brokers say yes.
-->

---

# What this is NOT

---

## The honest limitations slide

- **Not a signal service** — we will never tell you what to buy
- **Not investment advice** — reference strategies are research reproductions
- **Not for HFT** — daily and intraday, retail-grade
- **Not a managed account product** — regulatory line we never cross
- **Not closed-sourcing the core** — ever

<!--
This slide builds more trust than every feature in the previous decks.
Tell people what you won't do and they believe what you will.
-->

---

# Where we are

---

## What's already shipped

- ✅ **Phase 0** — `oq-core`, monorepo, CI
- ✅ **Phase 1** — `oq-data` with HDFC merger fixture
- ✅ **Phase 2** — `oq-backtest` with broker cost presets
- ✅ **Phase 3** — `oq-mcp` server
- ✅ **Phase 4** — `oq-broker` paper + 4 live adapters, SEBI-2026 native
- 🚧 **Phase 5** — docs site, strategy zoo, community

<!--
Update this slide before every talk. Phase numbers are tracking the
PRD exactly. Show the merged PRs as proof.
-->

---

## The metrics we care about

- An external project depends on `oq-data` in production
- "Check it net of costs" becomes a community phrase
- A stranger ships a strategy to the zoo that passes the honesty gate
- This demo works live on a conference stage

> If those four happen, v1.0 was worth it.

<!--
These are the success criteria from PRD §12. They are stranger-built,
community-built, and craft-built. Stars and downloads are not on the
list on purpose.
-->

---

# How to help

---

## Contribute

- `good-first-issue` pipeline → label + mentorship
- Strategy zoo merge gate = passes honest-cost backtest + walk-forward
- DCO sign-off, no heavyweight CLA
- Cohort program through GDG / college clubs
- Discord: structured channels, no spam

> The README is a recruiting document. Read it.

<!--
End with concrete asks. People in the audience will literally open
GitHub during the talk. Give them somewhere to land.
-->

---

## Resources

- **Code:** github.com/revorhq/openquant
- **Docs:** *(Phase 5 — landing this quarter)*
- **Discord:** *(launching with v1.0)*
- **License:** Apache 2.0
- **Talks page:** `marketing/talks/` in the repo

<!--
Last slide stays on screen for Q&A. URLs visible the whole time.
-->

---

# Questions?

### *Your backtest is lying to you. We fix that.*

**Shantanu Vishwanadha**
github.com/revorhq/openquant

<!--
Closing line is the tagline. Repeat it. That's what they walk out
remembering. If anyone asks "is this investment advice?" — point at
the §10 disclaimer slide and the README.
-->
