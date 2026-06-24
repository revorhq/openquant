"""Journal export round-trip tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from oq_broker import (
    OrderRequest,
    PaperBroker,
    Side,
    export_journal,
)


async def test_export_journal_csv(paper: PaperBroker, tmp_path: Path) -> None:
    await paper.place_order(OrderRequest(symbol="RELIANCE", side=Side.BUY, quantity=2))
    paths = export_journal(await paper.list_orders(), await paper.list_fills(), tmp_path, fmt="csv")
    assert paths["orders"].exists()
    assert paths["fills"].exists()
    odf = pd.read_csv(paths["orders"])
    fdf = pd.read_csv(paths["fills"])
    assert "algo_id" in odf.columns
    assert odf["algo_id"].iloc[0] == "OQTEST001"
    assert fdf["quantity"].iloc[0] == 2


async def test_export_journal_parquet(paper: PaperBroker, tmp_path: Path) -> None:
    await paper.place_order(OrderRequest(symbol="RELIANCE", side=Side.BUY, quantity=1))
    paths = export_journal(
        await paper.list_orders(), await paper.list_fills(), tmp_path, fmt="parquet"
    )
    assert paths["orders"].suffix == ".parquet"
    assert pd.read_parquet(paths["orders"]).shape[0] == 1


def test_export_journal_rejects_unknown_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        export_journal([], [], tmp_path, fmt="xml")
