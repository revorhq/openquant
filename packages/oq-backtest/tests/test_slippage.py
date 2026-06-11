from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
from oq_backtest.slippage import (
    FixedBpsSlippage,
    SpreadSlippage,
    VolumeParticipationSlippage,
    resolve_slippage,
)


def test_fixed_bps_basic():
    slip = FixedBpsSlippage(bps=10.0)
    cost = slip.slippage_cost(
        date(2025, 1, 1), pd.Index(["A"]), np.array([100_000.0]), np.array([50_000.0])
    )
    assert cost == pytest.approx(150_000.0 * 10 / 10_000)


def test_fixed_bps_default_is_5():
    assert FixedBpsSlippage().bps == 5.0


def test_fixed_bps_zero_trade():
    slip = FixedBpsSlippage(20.0)
    cost = slip.slippage_cost(date(2025, 1, 1), pd.Index(["A"]), np.array([0.0]), np.array([0.0]))
    assert cost == 0.0


def test_fixed_bps_negative_rejected():
    with pytest.raises(ValueError):
        FixedBpsSlippage(-1.0)


def test_resolve_slippage_passthrough():
    s = FixedBpsSlippage(15.0)
    assert resolve_slippage(s) is s


def test_resolve_slippage_numeric():
    s = resolve_slippage(7.5)
    assert isinstance(s, FixedBpsSlippage)
    assert s.bps == 7.5


def test_resolve_slippage_bad_type():
    with pytest.raises(TypeError):
        resolve_slippage("ten")  # type: ignore[arg-type]


def test_volume_participation_sqrt_impact():
    adv = pd.DataFrame({"A": [10_000_000.0]}, index=pd.DatetimeIndex([pd.Timestamp("2025-01-01")]))
    slip = VolumeParticipationSlippage(adv_rupees=adv, impact_coeff=10.0, default_bps=10.0)
    buy = np.array([100_000.0])
    cost = slip.slippage_cost(date(2025, 1, 1), pd.Index(["A"]), buy, np.array([0.0]))
    participation = 100_000.0 / 10_000_000.0
    expected_bps = 10.0 * np.sqrt(participation) * 100.0
    assert cost == pytest.approx(100_000.0 * expected_bps / 10_000.0)


def test_volume_participation_missing_symbol_falls_back():
    adv = pd.DataFrame({"A": [10_000_000.0]}, index=pd.DatetimeIndex([pd.Timestamp("2025-01-01")]))
    slip = VolumeParticipationSlippage(adv_rupees=adv, default_bps=20.0)
    cost = slip.slippage_cost(
        date(2025, 1, 1), pd.Index(["B"]), np.array([50_000.0]), np.array([0.0])
    )
    assert cost == pytest.approx(50_000.0 * 20.0 / 10_000.0)


def test_volume_participation_date_before_history_uses_default():
    adv = pd.DataFrame({"A": [10_000_000.0]}, index=pd.DatetimeIndex([pd.Timestamp("2025-06-01")]))
    slip = VolumeParticipationSlippage(adv_rupees=adv, default_bps=5.0)
    cost = slip.slippage_cost(
        date(2025, 1, 1), pd.Index(["A"]), np.array([1_000.0]), np.array([0.0])
    )
    assert cost == pytest.approx(1_000.0 * 5.0 / 10_000.0)


def test_volume_participation_negative_args_rejected():
    adv = pd.DataFrame({"A": [1.0]}, index=pd.DatetimeIndex([pd.Timestamp("2025-01-01")]))
    with pytest.raises(ValueError):
        VolumeParticipationSlippage(adv_rupees=adv, impact_coeff=-1.0)
    with pytest.raises(ValueError):
        VolumeParticipationSlippage(adv_rupees=adv, default_bps=-1.0)


def test_spread_slippage_scalar():
    slip = SpreadSlippage(spread_bps=10.0)
    cost = slip.slippage_cost(
        date(2025, 1, 1), pd.Index(["A"]), np.array([50_000.0]), np.array([50_000.0])
    )
    assert cost == pytest.approx(100_000.0 * 5.0 / 10_000.0)


def test_spread_slippage_dataframe():
    spreads = pd.DataFrame(
        {"A": [4.0], "B": [10.0]},
        index=pd.DatetimeIndex([pd.Timestamp("2025-01-01")]),
    )
    slip = SpreadSlippage(spread_bps=spreads, default_bps=2.0)
    cost = slip.slippage_cost(
        date(2025, 1, 1),
        pd.Index(["A", "B"]),
        np.array([10_000.0, 10_000.0]),
        np.array([0.0, 0.0]),
    )
    assert cost == pytest.approx(10_000.0 * 2.0 / 10_000.0 + 10_000.0 * 5.0 / 10_000.0)


def test_spread_slippage_negative_scalar_rejected():
    with pytest.raises(ValueError):
        SpreadSlippage(spread_bps=-1.0)
