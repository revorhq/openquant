"""oq-data: NSE/BSE data pipeline for OpenQuant India.

Top-level convenience imports mirror the most-used public API:

    >>> from oq_data import prices, universe, wide_prices
"""

from __future__ import annotations

from oq_data.api import list_symbols, prices, resolve_symbol, universe, wide_prices
from oq_data.bhavcopy import build_url, download_bhavcopy, parse_bhavcopy_blob, sync_range
from oq_data.config import DataPaths, default_root, get_paths
from oq_data.corporate_actions import CorporateAction, add_actions, adjust_prices, load_actions
from oq_data.storage import coverage, query, read_prices, write_eod
from oq_data.symbols import SymbolMaster, add_mapping, load_master
from oq_data.universes import UniverseEntry, add_entries, load_universes, members_as_of

__version__ = "0.1.0"

__all__ = [
    "CorporateAction",
    "DataPaths",
    "SymbolMaster",
    "UniverseEntry",
    "__version__",
    "add_actions",
    "add_entries",
    "add_mapping",
    "adjust_prices",
    "build_url",
    "coverage",
    "default_root",
    "download_bhavcopy",
    "get_paths",
    "list_symbols",
    "load_actions",
    "load_master",
    "load_universes",
    "members_as_of",
    "parse_bhavcopy_blob",
    "prices",
    "query",
    "read_prices",
    "resolve_symbol",
    "sync_range",
    "universe",
    "wide_prices",
    "write_eod",
]
