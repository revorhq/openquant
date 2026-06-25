"""Strategy registry. Each strategy declares itself once at import time."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class StrategyEntry:
    """A strategy registered in the zoo."""

    name: str
    category: str
    author: str
    description: str
    signal_fn: Callable[[pd.DataFrame], pd.DataFrame]
    benchmark: str
    universe: str
    cost_preset: str = "zerodha"
    rebalance: str = "ME"
    initial_capital: float = 1_000_000.0
    tags: tuple[str, ...] = field(default_factory=tuple)
    extras: dict[str, Any] = field(default_factory=dict)


REGISTRY: dict[str, StrategyEntry] = {}


def register(entry: StrategyEntry) -> StrategyEntry:
    """Register a strategy. Duplicate names raise."""
    if entry.name in REGISTRY:
        raise ValueError(f"strategy '{entry.name}' already registered")
    REGISTRY[entry.name] = entry
    return entry


__all__ = ["REGISTRY", "StrategyEntry", "register"]
