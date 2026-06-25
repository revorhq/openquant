"""OpenQuant India meta-package.

Re-exports the most common entry points from the underlying packages so
``import openquant`` works for casual users.
"""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str):
    if name in {"core", "data", "backtest", "broker", "mcp", "zoo"}:
        import importlib

        return importlib.import_module(f"oq_{name}")
    raise AttributeError(f"module 'openquant' has no attribute {name!r}")


__all__ = ["__version__"]
