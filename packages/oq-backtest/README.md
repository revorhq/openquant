# oq-backtest

Honest, vectorized backtester for Indian equities.

Models every cost an Indian retail trader actually pays — STT, brokerage,
exchange charges, GST, stamp duty, SEBI fees, slippage, and STCG/LTCG —
with broker presets for Zerodha, Upstox, Fyers, Dhan. Outputs gross vs net
equity curves side-by-side with a full cost attribution breakdown.

```bash
pip install oq-backtest
```

```python
import oq_backtest as ob
result = ob.backtest(signals, prices, costs="zerodha")
print(result.tearsheet())
```

Includes walk-forward / out-of-sample utilities and an intraday layer for
1–60 min bars with session square-off.

Part of [OpenQuant India](https://github.com/revorhq/openquant) — honest, open
source quant infrastructure for Indian markets. Apache 2.0.
