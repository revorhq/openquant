"""SEBI-2026 compliance primitives: AlgoID, strategy registration, audit log, kill switch.

The SEBI Retail Algo framework (mandatory from April 1, 2026) requires every
algorithmic order to carry a registered strategy/algo identifier, and brokers
must keep an immutable audit trail. This module provides the data model and a
file-backed append-only audit log used by every broker adapter.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ALGO_ID_RE = re.compile(r"^[A-Z0-9]{4,32}$")


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class StrategyRegistration:
    """SEBI-mandated metadata that must accompany every algo order."""

    algo_id: str
    strategy_id: str
    strategy_name: str
    owner: str
    description: str = ""
    approved_at: str = field(default_factory=_utcnow_iso)
    version: str = "0.1.0"

    def __post_init__(self) -> None:
        if not _ALGO_ID_RE.match(self.algo_id):
            raise ValueError(
                "algo_id must be 4-32 uppercase alphanumeric chars (SEBI broker-registered Algo-ID)"
            )
        if not self.strategy_id:
            raise ValueError("strategy_id is required")
        if not self.strategy_name:
            raise ValueError("strategy_name is required")
        if not self.owner:
            raise ValueError("owner is required (SEBI requires identifiable strategy owner)")

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class AuditEntry:
    timestamp: str
    event: str
    payload: dict[str, Any]
    prev_hash: str
    hash: str = ""

    def compute_hash(self) -> str:
        body = json.dumps(
            {
                "timestamp": self.timestamp,
                "event": self.event,
                "payload": self.payload,
                "prev_hash": self.prev_hash,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(body.encode("utf-8")).hexdigest()


class AuditLog:
    """Append-only, hash-chained audit log persisted as JSON lines."""

    GENESIS = "0" * 64

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self._entries: list[AuditEntry] = []
        if self.path and self.path.exists():
            self._load()

    def _load(self) -> None:
        assert self.path is not None
        for line in self.path.read_text().splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            self._entries.append(AuditEntry(**data))

    def _write(self, entry: AuditEntry) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as fh:
            fh.write(json.dumps(asdict(entry), default=str) + "\n")

    def record(self, event: str, payload: dict[str, Any]) -> AuditEntry:
        with self._lock:
            prev = self._entries[-1].hash if self._entries else self.GENESIS
            entry = AuditEntry(
                timestamp=_utcnow_iso(),
                event=event,
                payload=payload,
                prev_hash=prev,
            )
            entry.hash = entry.compute_hash()
            self._entries.append(entry)
            self._write(entry)
            return entry

    def verify(self) -> bool:
        prev = self.GENESIS
        for entry in self._entries:
            if entry.prev_hash != prev:
                return False
            if entry.compute_hash() != entry.hash:
                return False
            prev = entry.hash
        return True

    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)


class KillSwitchTriggered(RuntimeError):
    """Raised when the kill switch is engaged and a new order is attempted."""


class MaxLossBreached(RuntimeError):
    """Raised when the realised+unrealised loss exceeds the configured cap."""


@dataclass(slots=True)
class KillSwitch:
    """Mandatory framework-level circuit breaker.

    Engaging the switch (manually or via ``check_loss``) blocks all
    subsequent order placement until ``reset`` is called explicitly.
    """

    max_loss: float | None = None
    engaged: bool = False
    reason: str | None = None
    audit: AuditLog | None = None

    def engage(self, reason: str) -> None:
        self.engaged = True
        self.reason = reason
        if self.audit is not None:
            self.audit.record("kill_switch.engaged", {"reason": reason})

    def reset(self, operator: str) -> None:
        self.engaged = False
        self.reason = None
        if self.audit is not None:
            self.audit.record("kill_switch.reset", {"operator": operator})

    def check(self) -> None:
        if self.engaged:
            raise KillSwitchTriggered(self.reason or "kill switch engaged")

    def check_loss(self, pnl: float) -> None:
        if self.max_loss is not None and pnl <= -abs(self.max_loss):
            reason = f"max_loss breached: pnl={pnl:.2f}, cap={-abs(self.max_loss):.2f}"
            self.engage(reason)
            raise MaxLossBreached(reason)


def aggregate_pnl(positions: Iterable[Any]) -> float:
    return float(sum(p.realised_pnl + p.unrealised_pnl for p in positions))


__all__ = [
    "AuditEntry",
    "AuditLog",
    "KillSwitch",
    "KillSwitchTriggered",
    "MaxLossBreached",
    "StrategyRegistration",
    "aggregate_pnl",
]
