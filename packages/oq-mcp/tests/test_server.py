from __future__ import annotations

import pytest
from oq_data.config import DataPaths
from oq_mcp import tools
from oq_mcp.server import build_server


def test_build_server_registers_all_tools() -> None:
    server = build_server()
    tool_list = pytest.importorskip("asyncio").run(server.list_tools())
    names = {t.name for t in tool_list}
    assert names == {
        "get_prices",
        "get_universe",
        "screen_stocks",
        "get_fundamentals_basic",
        "run_backtest",
    }


def test_server_name_and_instructions() -> None:
    server = build_server(name="oq-test")
    assert server.name == "oq-test"
    assert "OpenQuant India" in server.instructions


async def test_call_get_universe_via_server(
    seeded_paths: DataPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENQUANT_DATA_DIR", str(seeded_paths.root))

    out = tools.get_universe("NIFTY 50", as_of="2024-06-01")
    assert out["count"] == 4
