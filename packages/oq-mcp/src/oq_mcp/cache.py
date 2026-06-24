"""In-process TTL cache for upstream rate-limit friendliness.

The cache is keyed on a hashable tuple and stores any picklable value.
Entries expire after ``ttl_seconds``; lookups for expired entries are
treated as misses. A small ``max_entries`` bound keeps memory predictable
under heavy tool traffic (oldest entries are evicted FIFO).
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Hashable
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float = 300.0, max_entries: int = 1024) -> None:
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must be >= 0")
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self._ttl = float(ttl_seconds)
        self._max = int(max_entries)
        self._data: OrderedDict[Hashable, tuple[float, T]] = OrderedDict()

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: Hashable) -> T | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return value

    def set(self, key: Hashable, value: T) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = (time.monotonic() + self._ttl, value)
        while len(self._data) > self._max:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()


__all__ = ["TTLCache"]
