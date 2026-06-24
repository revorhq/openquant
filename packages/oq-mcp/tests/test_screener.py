from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from oq_mcp.screener import screen


def _prices() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    dates = pd.bdate_range("2024-01-02", periods=260)
    cols = ["UP", "DOWN", "FLAT", "TINY"]
    data = {
        "UP": 100 * np.cumprod(1 + rng.normal(0.002, 0.01, 260)),
        "DOWN": 100 * np.cumprod(1 + rng.normal(-0.002, 0.01, 260)),
        "FLAT": 100 * np.ones(260),
        "TINY": 0.5 * np.ones(260),
    }
    return pd.DataFrame(data, index=dates, columns=cols)


def test_numeric_filter() -> None:
    p = _prices()
    out = screen(p, ["returns_252d > 0.10"])
    assert "UP" in out
    assert "DOWN" not in out


def test_combine_and() -> None:
    p = _prices()
    out = screen(p, ["returns_252d > 0.05", "close > 5"], combine="and")
    assert "TINY" not in out


def test_combine_or() -> None:
    p = _prices()
    out = screen(p, ["close > 90", "close < 1"], combine="or")
    assert "TINY" in out


def test_boolean_field() -> None:
    p = _prices()
    out = screen(p, ["sma_50_above_sma_200"])
    assert isinstance(out, list)


def test_bad_expression_raises() -> None:
    p = _prices()
    with pytest.raises(ValueError):
        screen(p, ["not a thing"])
    with pytest.raises(ValueError):
        screen(p, [])


def test_empty_universe() -> None:
    out = screen(pd.DataFrame(), ["close > 1"])
    assert out == []


def test_pct_from_52w_high() -> None:
    p = _prices()
    out = screen(p, ["pct_from_52w_high <= 0.50"])
    assert isinstance(out, list)
