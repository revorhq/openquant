from __future__ import annotations

import pytest
from oq_data.config import DataPaths
from oq_mcp import tools


def test_get_prices_returns_rows(seeded_paths: DataPaths) -> None:
    out = tools.get_prices("AAA", data_dir=str(seeded_paths.root))
    assert out["symbol"] == "AAA"
    assert out["rows"] > 0
    assert out["adjusted"] is True
    assert all("date" in r and "close" in r for r in out["data"][:3])


def test_get_prices_caches(seeded_paths: DataPaths) -> None:
    from oq_mcp.cache import TTLCache

    cache: TTLCache = TTLCache(ttl_seconds=60.0)
    out1 = tools.get_prices("AAA", data_dir=str(seeded_paths.root), cache=cache)
    out2 = tools.get_prices("AAA", data_dir=str(seeded_paths.root), cache=cache)
    assert out1 is out2


def test_get_universe(seeded_paths: DataPaths) -> None:
    out = tools.get_universe("NIFTY 50", as_of="2024-06-01", data_dir=str(seeded_paths.root))
    assert out["index"] == "NIFTY 50"
    assert out["count"] == 4
    assert set(out["symbols"]) == {"AAA", "BBB", "CCC", "DDD"}


def test_get_fundamentals_basic_found(seeded_paths: DataPaths) -> None:
    out = tools.get_fundamentals_basic("BBB", data_dir=str(seeded_paths.root))
    assert out["found"] is True
    assert out["symbol"] == "BBB"
    assert out["series"] == "EQ"
    assert out["last_close"] > 0


def test_get_fundamentals_basic_missing(seeded_paths: DataPaths) -> None:
    out = tools.get_fundamentals_basic("ZZZ", data_dir=str(seeded_paths.root))
    assert out["found"] is False


def test_screen_stocks_runs(seeded_paths: DataPaths) -> None:
    out = tools.screen_stocks(
        ["close > 0"],
        index_name="NIFTY 50",
        as_of="2024-06-01",
        data_dir=str(seeded_paths.root),
    )
    assert out["count"] >= 1
    assert out["universe_size"] == 4


def test_run_backtest_momentum(seeded_paths: DataPaths) -> None:
    out = tools.run_backtest(
        signals_source="momentum",
        index_name="NIFTY 50",
        start="2023-06-01",
        costs="zerodha",
        lookback=60,
        top_k=2,
        data_dir=str(seeded_paths.root),
    )
    assert out["signals_source"] == "momentum"
    assert out["universe_size"] == 4
    assert "net_cagr" in out["summary"]
    assert "tearsheet" in out
    assert isinstance(out["cost_attribution_inr"], dict)


def test_run_backtest_equal_weight(seeded_paths: DataPaths) -> None:
    out = tools.run_backtest(
        signals_source="equal_weight",
        index_name="NIFTY 50",
        data_dir=str(seeded_paths.root),
    )
    assert out["summary"]["final_net_value"] > 0


def test_run_backtest_unknown_source(seeded_paths: DataPaths) -> None:
    with pytest.raises(ValueError):
        tools.run_backtest(
            signals_source="nope",
            index_name="NIFTY 50",
            data_dir=str(seeded_paths.root),
        )


def test_run_backtest_no_data(tmp_path) -> None:
    with pytest.raises(ValueError):
        tools.run_backtest(
            signals_source="momentum",
            index_name="NIFTY 50",
            data_dir=str(tmp_path),
        )
