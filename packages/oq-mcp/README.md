# oq-mcp

MCP server exposing OpenQuant India data, screeners, and honest backtests to
LLM clients like Claude Desktop.

Tools: `get_prices`, `get_universe`, `screen_stocks`, `get_fundamentals_basic`,
and the headline `run_backtest` tool — natural-language-parameterized
backtests with honest Indian-market costs.

```bash
pip install oq-mcp
```

Configure in Claude Desktop:

```json
{
  "mcpServers": {
    "openquant": { "command": "oq-mcp" }
  }
}
```

Then ask Claude: *"Backtest momentum on Nifty 500 with Zerodha costs since 2015."*

Part of [OpenQuant India](https://github.com/revorhq/openquant) — honest, open
source quant infrastructure for Indian markets. Apache 2.0.
