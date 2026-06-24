"""Storage layout and environment configuration for oq-data.

The cache root is resolved in this order:

1. ``OPENQUANT_DATA_DIR`` environment variable, if set.
2. ``$XDG_DATA_HOME/openquant`` if ``XDG_DATA_HOME`` is set.
3. ``~/.openquant`` on every platform otherwise.

Sub-paths under the cache root are stable and form the storage contract
between the writers in :mod:`oq_data.storage` and the readers in
:mod:`oq_data.api` / :mod:`oq_data.cli`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DataPaths:
    """Resolved on-disk locations for every artifact oq-data writes."""

    root: Path

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def bhavcopy(self) -> Path:
        return self.raw / "bhavcopy"

    @property
    def parquet(self) -> Path:
        return self.root / "parquet"

    @property
    def eod_equity(self) -> Path:
        return self.parquet / "eod_equity"

    @property
    def reference(self) -> Path:
        return self.root / "reference"

    @property
    def symbols(self) -> Path:
        return self.reference / "symbols.parquet"

    @property
    def corporate_actions(self) -> Path:
        return self.reference / "corporate_actions.parquet"

    @property
    def universes(self) -> Path:
        return self.reference / "universes.parquet"

    def ensure(self) -> None:
        for path in (self.bhavcopy, self.eod_equity, self.reference):
            path.mkdir(parents=True, exist_ok=True)


def default_root() -> Path:
    env = os.environ.get("OPENQUANT_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg).expanduser().resolve() / "openquant"
    return Path.home() / ".openquant"


def get_paths(root: Path | str | None = None) -> DataPaths:
    """Resolve a :class:`DataPaths` from an explicit root or the environment."""
    if root is None:
        return DataPaths(default_root())
    return DataPaths(Path(root).expanduser().resolve())


__all__ = ["DataPaths", "default_root", "get_paths"]
