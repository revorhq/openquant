"""``oq-backtest``: honest, vectorized backtester for Indian equities."""

from oq_backtest.costs import (
    DHAN_DELIVERY,
    DHAN_INTRADAY,
    FULL_SERVICE_DELIVERY,
    FYERS_DELIVERY,
    FYERS_INTRADAY,
    PRESETS,
    UPSTOX_DELIVERY,
    UPSTOX_INTRADAY,
    ZERODHA_DELIVERY,
    ZERODHA_INTRADAY,
    CostBreakdown,
    CostConfig,
    TaxConfig,
    compute_costs,
    resolve_config,
)
from oq_backtest.engine import backtest
from oq_backtest.result import BacktestResult
from oq_backtest.slippage import (
    FixedBpsSlippage,
    SlippageModel,
    SpreadSlippage,
    VolumeParticipationSlippage,
    resolve_slippage,
)
from oq_backtest.strategies import (
    equal_weight,
    mean_reversion_signal,
    momentum_signal,
    rebalance_dates,
    synthetic_universe,
)
from oq_backtest.tax import TaxBreakdown, estimate_taxes
from oq_backtest.walkforward import Fold, train_test_split, walk_forward

__version__ = "0.1.0"

__all__ = [
    "DHAN_DELIVERY",
    "DHAN_INTRADAY",
    "FULL_SERVICE_DELIVERY",
    "FYERS_DELIVERY",
    "FYERS_INTRADAY",
    "PRESETS",
    "UPSTOX_DELIVERY",
    "UPSTOX_INTRADAY",
    "ZERODHA_DELIVERY",
    "ZERODHA_INTRADAY",
    "BacktestResult",
    "CostBreakdown",
    "CostConfig",
    "FixedBpsSlippage",
    "Fold",
    "SlippageModel",
    "SpreadSlippage",
    "TaxBreakdown",
    "TaxConfig",
    "VolumeParticipationSlippage",
    "__version__",
    "backtest",
    "compute_costs",
    "equal_weight",
    "estimate_taxes",
    "mean_reversion_signal",
    "momentum_signal",
    "rebalance_dates",
    "resolve_config",
    "resolve_slippage",
    "synthetic_universe",
    "train_test_split",
    "walk_forward",
]
