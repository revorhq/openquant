"""``oq-zoo`` — the OpenQuant India community strategy zoo.

Every registered strategy must pass the honesty gate to be merged.
"""

from oq_zoo.gate import (
    GateReport,
    GateResult,
    HonestyGate,
    HonestyGateConfig,
    StrategySpec,
    run_gate,
)
from oq_zoo.registry import REGISTRY, StrategyEntry, register

__version__ = "0.1.0"

__all__ = [
    "REGISTRY",
    "GateReport",
    "GateResult",
    "HonestyGate",
    "HonestyGateConfig",
    "StrategyEntry",
    "StrategySpec",
    "__version__",
    "register",
    "run_gate",
]
