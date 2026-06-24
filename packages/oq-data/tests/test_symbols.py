from __future__ import annotations

from datetime import date

from oq_data import symbols
from oq_data.config import DataPaths


def test_load_master_seeds_defaults(tmp_paths: DataPaths) -> None:
    master = symbols.load_master(paths=tmp_paths)
    assert not master.df.empty
    assert "HDFC" in master.df["old_symbol"].tolist()


def test_resolve_as_of_returns_old_symbol_pre_merger(tmp_paths: DataPaths) -> None:
    master = symbols.load_master(paths=tmp_paths)
    pre = master.resolve_as_of("HDFCBANK", date(2023, 7, 12))
    assert pre == "HDFC"


def test_resolve_as_of_returns_new_symbol_post_merger(tmp_paths: DataPaths) -> None:
    master = symbols.load_master(paths=tmp_paths)
    post = master.resolve_as_of("HDFCBANK", date(2023, 7, 14))
    assert post == "HDFCBANK"


def test_canonical_walks_forward(tmp_paths: DataPaths) -> None:
    master = symbols.load_master(paths=tmp_paths)
    assert master.canonical("HDFC") == "HDFCBANK"


def test_add_mapping_appends(tmp_paths: DataPaths) -> None:
    symbols.add_mapping(
        isin="INE999X01010",
        old_symbol="OLDCO",
        new_symbol="NEWCO",
        effective_date="2024-01-15",
        reason="rename",
        paths=tmp_paths,
    )
    master = symbols.load_master(paths=tmp_paths)
    assert master.canonical("OLDCO") == "NEWCO"
    assert master.resolve_as_of("NEWCO", date(2024, 1, 14)) == "OLDCO"
