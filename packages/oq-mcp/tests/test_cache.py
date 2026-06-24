from __future__ import annotations

import time

import pytest
from oq_mcp.cache import TTLCache


def test_set_and_get_roundtrip() -> None:
    c: TTLCache[int] = TTLCache(ttl_seconds=60.0, max_entries=8)
    c.set(("a", 1), 42)
    assert c.get(("a", 1)) == 42


def test_miss_returns_none() -> None:
    c: TTLCache[int] = TTLCache(ttl_seconds=60.0)
    assert c.get("missing") is None


def test_expiration() -> None:
    c: TTLCache[int] = TTLCache(ttl_seconds=0.05)
    c.set("k", 1)
    time.sleep(0.1)
    assert c.get("k") is None


def test_eviction_fifo() -> None:
    c: TTLCache[int] = TTLCache(ttl_seconds=60.0, max_entries=2)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_invalid_settings() -> None:
    with pytest.raises(ValueError):
        TTLCache(ttl_seconds=-1)
    with pytest.raises(ValueError):
        TTLCache(max_entries=0)


def test_clear() -> None:
    c: TTLCache[int] = TTLCache(ttl_seconds=60.0)
    c.set("k", 9)
    c.clear()
    assert c.get("k") is None
    assert len(c) == 0
