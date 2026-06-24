# `oq-mcp`

MCP server exposing `oq-data` and `oq-backtest` to LLM clients.

## Run

```bash
python -m oq_mcp
```

Or wire into Claude Desktop — see [Cookbook → MCP with Claude](../cookbook/mcp-claude.md).

## Tools

### `get_prices`

```json
{ "symbol": "RELIANCE", "start": "2020-01-01", "end": "2024-12-31", "adjusted": true }
```

Returns a compact JSON table of OHLCV.

### `get_universe`

```json
{ "index": "NIFTY500", "as_of": "2015-06-01" }
```

Point-in-time constituents.

### `screen_stocks`

```json
{ "dsl": "universe:nifty500 AND close/high_52w > 0.95 AND delivery_pct > delivery_pct.sma(20)" }
```

A small DSL for "Nifty 500 within 5% of 52w high with rising delivery"
style queries.

### `get_fundamentals_basic`

```json
{ "symbol": "RELIANCE" }
```

Latest available basics — market cap, sector, P/E, P/B.

### `run_backtest`

```json
{
  "strategy": "12-1 momentum on NIFTY500",
  "start": "2015-01-01",
  "rebalance": "ME",
  "costs": "zerodha"
}
```

Natural-language-parameterized backtest. Returns the tearsheet + a PNG.

## Caching

`TTLCache` against the underlying `oq-data` queries. Tunable:

| Env var             | Default |
| ------------------- | ------- |
| `OQ_MCP_CACHE_TTL`  | 900     |
| `OQ_MCP_CACHE_SIZE` | 1024    |
