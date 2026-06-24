"""oq-data — NSE/BSE data pipeline for OpenQuant India.

Top-level convenience imports mirror the most-used public API:

    >>> from oq_data import prices, universe, wide_prices
"""

from __future__ import annotations

from oq_data.announcements import (
    download_announcements,
    parse_announcements_blob,
    read_announcements,
    write_announcements,
)
from oq_data.api import list_symbols, prices, resolve_symbol, universe, wide_prices
from oq_data.bhavcopy import build_url, download_bhavcopy, parse_bhavcopy_blob, sync_range
from oq_data.config import DataPaths, default_root, get_paths
from oq_data.corporate_actions import CorporateAction, add_actions, adjust_prices, load_actions
from oq_data.delivery import (
    download_delivery,
    parse_delivery_blob,
    read_delivery,
    write_delivery,
)
from oq_data.flows import (
    download_flows,
    parse_flows_blob,
    read_flows,
    write_flows,
)
from oq_data.fno import (
    download_fno,
    parse_fno_blob,
)
from oq_data.storage import (
    coverage,
    query,
    read_fno,
    read_prices,
    write_eod,
    write_fno,
)
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
    "download_announcements",
    "download_bhavcopy",
    "download_delivery",
    "download_flows",
    "download_fno",
    "get_paths",
    "list_symbols",
    "load_actions",
    "load_master",
    "load_universes",
    "members_as_of",
    "parse_announcements_blob",
    "parse_bhavcopy_blob",
    "parse_delivery_blob",
    "parse_flows_blob",
    "parse_fno_blob",
    "prices",
    "query",
    "read_announcements",
    "read_delivery",
    "read_flows",
    "read_fno",
    "read_prices",
    "resolve_symbol",
    "sync_range",
    "universe",
    "wide_prices",
    "write_announcements",
    "write_delivery",
    "write_eod",
    "write_flows",
    "write_fno",
]
