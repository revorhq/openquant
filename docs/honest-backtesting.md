# Honest backtesting

The single most important page in these docs.

## The gap

A "+22% CAGR" backtest on Indian equities almost always becomes a
single-digit number once you subtract:

| Friction              | Typical drag |
| --------------------- | ------------ |
| STT (sell-side equity delivery) | ~10 bps |
| Brokerage             | 0 – 50 bps   |
| Exchange charges      | ~0.325 bps   |
| GST (18% on brokerage + exchange) | derived |
| SEBI fee              | ~₹10 / crore |
| Stamp duty            | 0.3 – 1.5 bps |
| Slippage on close print | 5 – 25 bps |
| STCG (15%) / LTCG (12.5%) | depends on holding period |
| Survivorship bias     | strategy-dependent |

For a monthly-rebalanced Nifty 500 strategy with 30% turnover, those
costs alone are **10 – 15 percentage points of CAGR**.

## Our defaults

In `oq-backtest`, *net of everything* is the default. To see gross,
you must pass `gross=True` explicitly. We chose this default because
the alternative ships lies as a service.

```python
from oq_backtest import backtest

# Honest. Net of STT, brokerage, GST, stamp duty, SEBI fees, slippage.
result = backtest(signals, costs="zerodha")

# Gross — for diagnostics only.
gross = backtest(signals, costs="zerodha", gross=True)
```

## Cost presets

| Preset      | Brokerage model |
| ----------- | --------------- |
| `zerodha`   | Discount: ₹0 delivery, ₹20/trade intraday |
| `upstox`    | Discount: ₹20/trade flat |
| `fyers`     | Discount: ₹20/trade flat |
| `dhan`      | Discount: ₹20/trade flat |
| `full_service` | Generic 30 bps |

Roll your own:

```python
from oq_backtest.costs import CostModel

model = CostModel(
    brokerage_bps=2.0,
    stt_buy_bps=0.0,
    stt_sell_bps=10.0,
    exchange_bps=0.325,
    gst_pct=18.0,
    stamp_duty_bps=1.5,
    sebi_fee_per_cr=10.0,
)
result = backtest(signals, costs=model)
```

## Slippage

Three models out of the box:

- **Fixed bps** — `Slippage(bps=5)`
- **Volume participation** — `VolumeParticipation(pct=0.05)`
- **Spread-based** — `SpreadSlippage(spread_bps=10)`

## Anti-overfitting

```python
from oq_backtest.walk_forward import walk_forward

result = walk_forward(strategy_fn, prices, train="3y", test="1y", step="1y")
```

Out-of-sample windows are the merge gate for the
[strategy zoo](community/zoo.md). If your strategy only works in-sample,
the zoo rejects it.

## Survivorship bias

Use point-in-time universes. Never a fixed modern index:

```python
constituents = oq.universe("NIFTY50", as_of="2010-01-01")
# Returns the Nifty 50 as it stood on 2010-01-01,
# including the names that have since dropped out.
```

## The honesty pledge

If you publish a backtest using OpenQuant India:

1. Quote the **net** number.
2. State the **cost preset** used.
3. Show the **out-of-sample** result, not just in-sample.
4. Describe the **universe construction** (point-in-time, not "current Nifty 500 since 2010").

This is the bar. The strategy zoo enforces it; we hope the wider
community adopts it.
