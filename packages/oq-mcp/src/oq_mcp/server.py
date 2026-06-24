"""FastMCP server wiring for the OpenQuant India tool set.

Run over stdio for desktop MCP clients::

    uv run oq-mcp

or programmatically::

    from oq_mcp.server import build_server
    server = build_server()
    server.run()

Every tool is a thin pass-through to :mod:`oq_mcp.tools` so the underlying
logic stays trivially testable without the MCP machinery.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from mcp.server.fastmcp import FastMCP

from oq_mcp import tools

logger = logging.getLogger(__name__)

SERVER_INSTRUCTIONS = (
    "OpenQuant India MCP server. Tools expose NSE EOD prices, "
    "point-in-time index universes, a screener DSL, basic fundamentals, "
    "and an honest, cost-aware backtester. All cost numbers are net of "
    "Indian frictions (STT, brokerage, exchange, SEBI, GST, stamp duty, "
    "slippage). Outputs are research artefacts, NOT investment advice."
)


def build_server(name: str = "openquant-india") -> FastMCP:
    """Build a FastMCP instance with every OpenQuant tool registered."""
    server = FastMCP(name=name, instructions=SERVER_INSTRUCTIONS)

    @server.tool(
        name="get_prices",
        description="Return adjusted EOD prices for a single NSE symbol.",
    )
    def _get_prices(
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        adjusted: bool = True,
    ) -> dict[str, Any]:
        return tools.get_prices(symbol, start=start, end=end, adjusted=adjusted)

    @server.tool(
        name="get_universe",
        description="Return point-in-time members of an NSE index (Nifty 50/100/500).",
    )
    def _get_universe(index_name: str, as_of: str) -> dict[str, Any]:
        return tools.get_universe(index_name, as_of=as_of)

    @server.tool(
        name="screen_stocks",
        description=(
            "Apply a list of screener expressions against the PIT universe. "
            "Expressions: 'returns_252d > 0.10', 'pct_from_52w_high <= 0.05', "
            "'sma_50_above_sma_200', 'close > 100'."
        ),
    )
    def _screen_stocks(
        expressions: Sequence[str],
        index_name: str | None = None,
        as_of: str | None = None,
        lookback_days: int = 300,
        combine: str = "and",
    ) -> dict[str, Any]:
        return tools.screen_stocks(
            expressions,
            index_name=index_name,
            as_of=as_of,
            lookback_days=lookback_days,
            combine=combine,
        )

    @server.tool(
        name="get_fundamentals_basic",
        description="Return basic reference info (ISIN, series, last close/volume) for a symbol.",
    )
    def _get_fundamentals_basic(symbol: str) -> dict[str, Any]:
        return tools.get_fundamentals_basic(symbol)

    @server.tool(
        name="run_backtest",
        description=(
            "Run an honest, cost-aware backtest. signals_source in "
            "{momentum, mean_reversion, equal_weight}; costs in "
            "{zerodha, upstox, fyers, dhan, full_service, zero}."
        ),
    )
    def _run_backtest(
        signals_source: str = "momentum",
        index_name: str | None = None,
        start: str | None = None,
        end: str | None = None,
        costs: str = "zerodha",
        slippage_bps: float = 5.0,
        initial_capital: float = 1_000_000.0,
        lookback: int = 252,
        top_k: int = 10,
        schedule: str = "monthly",
    ) -> dict[str, Any]:
        return tools.run_backtest(
            signals_source=signals_source,
            index_name=index_name,
            start=start,
            end=end,
            costs=costs,
            slippage_bps=slippage_bps,
            initial_capital=initial_capital,
            lookback=lookback,
            top_k=top_k,
            schedule=schedule,
        )

    return server


def main() -> None:
    """Console-script entry point: serve over stdio."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    server = build_server()
    server.run()


__all__ = ["SERVER_INSTRUCTIONS", "build_server", "main"]
