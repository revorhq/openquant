"""MCP server exposing OpenQuant India data and honest backtests."""

from __future__ import annotations

from oq_mcp.cache import TTLCache
from oq_mcp.screener import screen
from oq_mcp.server import build_server
from oq_mcp.tools import (
    get_fundamentals_basic,
    get_prices,
    get_universe,
    run_backtest,
    screen_stocks,
)

__version__ = "0.1.0"

__all__ = [
    "TTLCache",
    "__version__",
    "build_server",
    "get_fundamentals_basic",
    "get_prices",
    "get_universe",
    "run_backtest",
    "screen",
    "screen_stocks",
]
