# Disclaimer

**Read this before you use OpenQuant India for anything that touches real money.**

## Not investment advice

OpenQuant India is open source **infrastructure** for research, education, and
software development. **Nothing in this project — code, documentation, example
strategies, backtest results, or any other artifact — constitutes investment
advice, a recommendation to buy or sell any security, or a solicitation of any
kind.** We are not a SEBI-registered Investment Adviser (RIA), Research
Analyst (RA), or Portfolio Manager.

If you need investment advice, consult a SEBI-registered professional.

## No guarantees, no warranty

The software is provided **"AS IS"**, without warranty of any kind, express or
implied. See the [LICENSE](LICENSE) for the full Apache 2.0 disclaimer of
warranty and limitation of liability.

**Past performance — backtested or live — is not indicative of future
results.** Backtests, even with realistic costs and slippage, are simulations.
They cannot fully capture market impact, liquidity shocks, regulatory changes,
or your own behavioural mistakes. Treat any backtested CAGR with deep
suspicion.

## Data correctness

We work hard to ship clean, corporate-action-adjusted, survivorship-bias-free
data. **We will still ship bugs.** If you act on data from this project
without verifying it for your own use case, you do so at your own risk. Always
cross-check critical numbers against the exchange's primary sources (NSE/BSE
bhavcopy, corporate action filings) before making a trading decision.

## Live trading is opt-in and risky

Trading real money — especially with automated strategies on F&O — can result
in losses that exceed your initial capital. Indian markets have circuit
limits, freeze quantities, margin calls, and regulatory halts that can cause
unexpected behaviour. **Always paper-trade first**, and treat the framework's
kill switch and risk limits as the floor, not the ceiling, of your safety
controls.

You are responsible for:

- Complying with SEBI's algorithmic trading framework (including the mandatory
  retail algo regime effective 1 April 2026), exchange circulars, and your
  broker's terms of service.
- Registering your algorithms where required and tagging orders with
  Algo-IDs as mandated.
- Reporting and paying taxes (STT, STCG, LTCG, GST on charges, etc.).
- Your own losses.

## Use of broker APIs

Each broker (Zerodha Kite Connect, Upstox, Fyers, Dhan, etc.) has its own
terms of service governing automation, rate limits, and personal/commercial
use. **You must use your own API credentials and comply with each broker's
terms.** This project does not bundle credentials and is not authorised to
trade on your behalf.

## NSE / BSE data

Exchange-published market data is the property of the respective exchange and
is subject to redistribution restrictions. This project ships the *pipeline*
to fetch data from official sources into your local environment — not bulk
redistributed datasets. You are responsible for ensuring your use of any
fetched data complies with the exchange's terms.

---

If any of the above gives you pause: that's the point. Use the tool with
clear eyes, or don't use it.
