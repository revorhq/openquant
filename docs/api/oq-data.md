# `oq-data`

NSE/BSE pipeline: bhavcopy ingestion, corporate-action adjustments,
point-in-time index universes, F&O, delivery, FII/DII flows,
corporate announcements.

## CLI

```bash
oq sync                 # full historical sync
oq sync --quick         # last 2 years
oq sync --segment FNO   # futures + options EOD
oq universe --date 2020-01-01 --index NIFTY50
oq snapshot             # build derived-metadata snapshot
```

## Python

```python
import oq_data as oq

# EOD prices
prices = oq.prices("RELIANCE", start="2015-01-01", adjusted=True)

# Universe at a point in time
constituents = oq.universe("NIFTY50", as_of="2010-01-01")

# Index change history
changes = oq.universe_changes("NIFTY500", start="2010-01-01")

# Corporate actions
ca = oq.corporate_actions("RELIANCE")

# F&O EOD
fno = oq.fno_bhavcopy(date(2024, 1, 15))

# Delivery %
deliv = oq.delivery("RELIANCE", start="2024-01-01")

# FII/DII flows
flows = oq.fii_dii_flows(start="2024-01-01")

# Announcements
ann = oq.announcements("RELIANCE", start="2024-01-01")
```

## Storage layout

```
~/.openquant/data/
├── equity/
│   └── year=2024/
│       └── *.parquet
├── fno/
│   └── year=2024/
├── corporate_actions/
├── universes/
├── delivery/
├── flows/
└── announcements/
```

All Parquet, year-partitioned, queryable via DuckDB:

```python
import duckdb
con = duckdb.connect()
df = con.execute("""
    SELECT symbol, date, close
    FROM '~/.openquant/data/equity/year=*/*.parquet'
    WHERE symbol = 'RELIANCE'
""").df()
```
