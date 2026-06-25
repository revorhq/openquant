# oq-data

NSE data pipeline for OpenQuant India.

Bhavcopy ingestion (EOD equity + F&O), corporate-action adjustments, point-in-time
index universes (Nifty 50/100/500), delivery %, FII/DII flows, and a Parquet +
DuckDB query layer. Symbol master keyed on ISIN with merger/symbol-change
mapping (HDFC merger included as a test fixture).

```bash
pip install oq-data
oq sync --quick
```

```python
import oq_data as oq
prices = oq.prices("RELIANCE", "2015-01-01", "2024-12-31", adjusted=True)
universe = oq.universe("NIFTY50", as_of="2018-06-30")
```

Part of [OpenQuant India](https://github.com/revorhq/openquant) — honest, open
source quant infrastructure for Indian markets. Apache 2.0.
