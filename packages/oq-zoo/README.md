# oq-zoo

Community strategy library for OpenQuant India.

Every strategy in the zoo has to pass the **honesty gate** — an honest-cost
backtest plus walk-forward validation. No "92% win rate" tips, no hidden
parameter tuning.

```bash
pip install oq-zoo
oq-zoo list
oq-zoo run buy_and_hold_equal_weight
```

Contribute your own — see [STRATEGY_TEMPLATE.md](./STRATEGY_TEMPLATE.md).

Part of [OpenQuant India](https://github.com/revorhq/openquant) — honest, open
source quant infrastructure for Indian markets. Apache 2.0.
