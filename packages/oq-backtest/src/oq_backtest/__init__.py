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
from oq_backtest.intraday import (
    NSE_CLOSE,
    NSE_OPEN,
    IntradayConfig,
    apply_square_off,
    backtest_intraday,
    intraday_summary,
    is_intraday_preset,
)
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
    "NSE_CLOSE",
    "NSE_OPEN",
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
    "IntradayConfig",
    "SlippageModel",
    "SpreadSlippage",
    "TaxBreakdown",
    "TaxConfig",
    "VolumeParticipationSlippage",
    "__version__",
    "apply_square_off",
    "backtest",
    "backtest_intraday",
    "compute_costs",
    "equal_weight",
    "estimate_taxes",
    "intraday_summary",
    "is_intraday_preset",
    "mean_reversion_signal",
    "momentum_signal",
    "rebalance_dates",
    "resolve_config",
    "resolve_slippage",
    "synthetic_universe",
    "train_test_split",
    "walk_forward",
]
