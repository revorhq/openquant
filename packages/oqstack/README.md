# oqstack

The meta-package that installs the full **OpenQuant India** stack in one go.

```bash
pip install oqstack
```

This pulls in:

- [`oq-core`](https://pypi.org/project/oq-core/) — shared primitives (Instrument, TradingCalendar)
- [`oq-data`](https://pypi.org/project/oq-data/) — NSE data pipeline + PIT universes
- [`oq-backtest`](https://pypi.org/project/oq-backtest/) — honest-cost backtester
- [`oq-broker`](https://pypi.org/project/oq-broker/) — unified broker abstraction + paper engine
- [`oq-mcp`](https://pypi.org/project/oq-mcp/) — MCP server for LLM clients
- [`oq-zoo`](https://pypi.org/project/oq-zoo/) — community strategy library

Prefer to install only what you need? Each component is a separately
installable package — see the links above.

```python
import oqstack
# or, use sub-packages directly:
import oq_core, oq_data, oq_backtest, oq_broker, oq_mcp, oq_zoo
```

Repository: <https://github.com/revorhq/openquant>. Apache License 2.0.
