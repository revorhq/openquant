# Point-in-time universes

The HDFC merger broke half the naive Indian backtests on the internet.
Don't be one of them.

```python
import oq_data as oq

# Universe as it existed on a specific date.
nifty50_2010 = oq.universe("NIFTY50", as_of="2010-01-01")
nifty50_2024 = oq.universe("NIFTY50", as_of="2024-01-01")

# These are different sets. That's the point.
print(len(set(nifty50_2010) - set(nifty50_2024)), "names dropped out")
```

## Why this matters

A fixed-modern-universe backtest:

> "Buy the current Nifty 50 in 2010, hold to 2024."

silently filters out everything that *would have been* in the index in
2010 but has since been removed (typically the losers). Your "buy and
hold the Nifty" returns get an unrealistic boost.

## Index change history

```python
changes = oq.universe_changes("NIFTY50", start="2010-01-01")
# DataFrame: date, added, removed, reason
```

Reconstructed from NSE change-announcement archives.

## Supported indices

- NIFTY50, NIFTY100, NIFTY200, NIFTY500
- NIFTYBANK, NIFTYIT, NIFTYAUTO (and other sectorals)
- NIFTYNEXT50, NIFTYMIDCAP100, NIFTYSMALLCAP100

## The HDFC fixture

We carry a regression test that walks through the entire HDFC Bank /
HDFC Ltd merger (July 2023) to ensure the symbol mapping, ISIN
continuity, and corporate-action chain don't silently break. If you
think you've found an adjusted-price bug around July 2023, file an
issue with the data correctness template.
