from __future__ import annotations

import numpy as np
import pytest
from oq_backtest.costs import (
    PRESETS,
    ZERODHA_DELIVERY,
    ZERODHA_INTRADAY,
    CostBreakdown,
    CostConfig,
    compute_costs,
    resolve_config,
)


def test_default_config_is_zerodha_delivery_like():
    cfg = CostConfig()
    assert cfg.brokerage_rate == 0.0
    assert cfg.stt_buy_rate == 0.001
    assert cfg.stt_sell_rate == 0.001
    assert cfg.gst_rate == 0.18


def test_negative_rates_rejected():
    with pytest.raises(ValueError):
        CostConfig(brokerage_rate=-0.0001)
    with pytest.raises(ValueError):
        CostConfig(stt_buy_rate=-0.001)


def test_brokerage_max_must_be_ge_min():
    with pytest.raises(ValueError):
        CostConfig(brokerage_min=20.0, brokerage_max=10.0)


def test_resolve_config_known_preset():
    assert resolve_config("zerodha") is ZERODHA_DELIVERY
    assert resolve_config("ZERODHA") is ZERODHA_DELIVERY
    assert resolve_config("zerodha_intraday") is ZERODHA_INTRADAY


def test_resolve_config_unknown_preset_raises():
    with pytest.raises(KeyError):
        resolve_config("etrade")


def test_resolve_config_passes_through_instance():
    cfg = CostConfig(brokerage_rate=0.0005, brokerage_max=20.0)
    assert resolve_config(cfg) is cfg


def test_resolve_config_bad_type():
    with pytest.raises(TypeError):
        resolve_config(123)  # type: ignore[arg-type]


def test_zerodha_delivery_one_lakh_per_leg():
    bd = compute_costs(np.array([100_000.0]), np.array([100_000.0]), ZERODHA_DELIVERY)
    assert bd.brokerage == 0.0
    assert bd.stt == pytest.approx(0.001 * 100_000 + 0.001 * 100_000)
    assert bd.exchange == pytest.approx(0.0000297 * 200_000)
    assert bd.sebi == pytest.approx(1e-6 * 200_000)
    assert bd.stamp_duty == pytest.approx(0.00015 * 100_000)
    assert bd.gst == pytest.approx(0.18 * (bd.brokerage + bd.exchange + bd.sebi))
    assert bd.total > 0


def test_intraday_brokerage_capped_at_20():
    bd = compute_costs(np.array([1_000_000.0]), np.array([1_000_000.0]), ZERODHA_INTRADAY)
    assert bd.brokerage == pytest.approx(20.0 + 20.0)


def test_intraday_brokerage_uncapped_below_threshold():
    bd = compute_costs(np.array([10_000.0]), np.array([0.0]), ZERODHA_INTRADAY)
    assert bd.brokerage == pytest.approx(0.0003 * 10_000.0)


def test_breakdown_addition_components():
    a = CostBreakdown(brokerage=1.0, stt=2.0, exchange=3.0, sebi=0.5, gst=0.2, stamp_duty=0.1)
    b = CostBreakdown(brokerage=0.5, stt=1.0, exchange=1.5, sebi=0.5, gst=0.1, stamp_duty=0.05)
    s = a + b
    assert s.brokerage == 1.5
    assert s.stt == 3.0
    assert s.total == pytest.approx(a.total + b.total)


def test_breakdown_addition_with_non_breakdown():
    a = CostBreakdown(brokerage=1.0)
    with pytest.raises(TypeError):
        _ = a + 5  # type: ignore[operator]


def test_breakdown_as_dict_has_total():
    bd = CostBreakdown(brokerage=1.0, stt=2.0)
    d = bd.as_dict()
    assert d["brokerage"] == 1.0
    assert d["total"] == 3.0


def test_compute_costs_scalar_inputs():
    bd = compute_costs(50_000.0, 50_000.0, ZERODHA_DELIVERY)
    bd2 = compute_costs(np.array([50_000.0]), np.array([50_000.0]), ZERODHA_DELIVERY)
    assert bd.total == pytest.approx(bd2.total)


def test_compute_costs_zero_trade():
    bd = compute_costs(0.0, 0.0, ZERODHA_DELIVERY)
    assert bd.total == 0.0


def test_zero_preset_is_friction_free():
    bd = compute_costs(np.array([100_000.0]), np.array([100_000.0]), PRESETS["zero"])
    assert bd.total == 0.0


def test_full_service_brokerage_50bps():
    bd = compute_costs(np.array([100_000.0]), np.array([0.0]), PRESETS["full_service"])
    assert bd.brokerage == pytest.approx(0.005 * 100_000.0)


def test_brokerage_per_order_applies_min_floor():
    cfg = CostConfig(brokerage_rate=0.0003, brokerage_min=20.0, brokerage_max=20.0)
    bd = compute_costs(np.array([1_000.0, 1_000.0]), np.array([0.0, 0.0]), cfg)
    assert bd.brokerage == pytest.approx(40.0)
