# MCP with Claude Desktop

Run honest backtests by talking to an LLM.

## Install

```bash
pip install oq-mcp
```

## Wire into Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or the equivalent on your platform:

```json
{
  "mcpServers": {
    "openquant": {
      "command": "python",
      "args": ["-m", "oq_mcp"]
    }
  }
}
```

Restart Claude Desktop.

## Try it

> *Backtest a 12-1 momentum on the Nifty 500 with Zerodha costs since 2015. Show net of everything.*

Claude calls `run_backtest` under the hood, fills in costs, runs the
strategy, and hands you a tearsheet image plus the numbers.

## Available tools

| Tool                 | What it does |
| -------------------- | ------------ |
| `get_prices`         | Adjusted/unadjusted EOD series |
| `get_universe`       | Point-in-time index constituents |
| `screen_stocks`      | DSL-based screening |
| `get_fundamentals_basic` | Latest available basics |
| `run_backtest`       | NL-parameterized backtest with honest costs |

## Caching

The MCP server uses `TTLCache` against the underlying `oq-data` queries
to stay polite with upstream rate limits. Defaults are conservative;
tune via env vars `OQ_MCP_CACHE_TTL` and `OQ_MCP_CACHE_SIZE`.
