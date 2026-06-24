"""SEBI compliance primitives: AlgoID, audit chain, kill switch."""

from __future__ import annotations

from pathlib import Path

import pytest
from oq_broker import (
    AuditLog,
    KillSwitch,
    KillSwitchTriggered,
    MaxLossBreached,
    StrategyRegistration,
)


def test_registration_validates_algo_id() -> None:
    with pytest.raises(ValueError):
        StrategyRegistration(
            algo_id="bad id!",
            strategy_id="s1",
            strategy_name="n",
            owner="o",
        )


def test_registration_requires_owner() -> None:
    with pytest.raises(ValueError):
        StrategyRegistration(
            algo_id="OQ001",
            strategy_id="s1",
            strategy_name="n",
            owner="",
        )


def test_audit_log_hash_chain(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.record("order.placed", {"id": "1"})
    log.record("order.filled", {"id": "1"})
    log.record("order.cancelled", {"id": "1"})
    assert len(log) == 3
    assert log.verify()


def test_audit_log_detects_tampering(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.record("a", {})
    log.record("b", {})
    log.entries()[0].payload["x"] = "tampered"
    assert not log.verify()


def test_audit_log_persists(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log1 = AuditLog(path)
    log1.record("a", {"k": 1})
    log1.record("b", {"k": 2})
    log2 = AuditLog(path)
    assert len(log2) == 2
    assert log2.verify()


def test_kill_switch_blocks_after_engage() -> None:
    k = KillSwitch()
    k.check()
    k.engage("manual")
    with pytest.raises(KillSwitchTriggered):
        k.check()
    k.reset("admin")
    k.check()


def test_kill_switch_max_loss_engages() -> None:
    k = KillSwitch(max_loss=1000.0)
    k.check_loss(-500.0)
    with pytest.raises(MaxLossBreached):
        k.check_loss(-1500.0)
    assert k.engaged
