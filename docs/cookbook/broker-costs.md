# Adding broker costs

Use a named preset, or roll your own.

## Presets

```python
from oq_backtest import backtest

result = backtest(signals, costs="zerodha")
# Also: "upstox", "fyers", "dhan", "full_service"
```

## Custom

```python
from oq_backtest.costs import CostModel

zerodha_like = CostModel(
    brokerage_bps=0.0,           # equity delivery is free at Zerodha
    intraday_brokerage_flat=20,  # ₹20 per executed order
    stt_buy_bps=0.0,
    stt_sell_bps=10.0,           # 0.1% sell-side equity delivery
    exchange_bps=0.325,          # NSE EQ
    gst_pct=18.0,
    stamp_duty_bps=1.5,
    sebi_fee_per_cr=10.0,
)
```

## Inspecting the breakdown

```python
result = backtest(signals, costs="zerodha")
print(result.cost_attribution)
#                       bps_of_aum
# stt                         12.4
# brokerage                    0.0
# exchange                     0.8
# gst                          0.2
# stamp_duty                   1.5
# slippage                    18.6
# total                       33.5
```

That `total` line is your alpha hurdle.
