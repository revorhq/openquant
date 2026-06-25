"""The honesty gate.

A strategy is accepted into the zoo only if:

1. Its net-of-cost CAGR strictly beats the declared benchmark CAGR
   (or, if tagged ``educational``, the maintainer has explicitly opted
   into a documented honest loser).
2. Walk-forward out-of-sample Sharpe is non-negative.
3. The cost preset and universe construction are declared upfront.
4. The reference backtest runs to completion without errors.

The gate is intentionally strict. Honest losers are still welcome but
must be tagged ``educational`` so readers don't mistake them for alpha.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from oq_backtest import BacktestResult, backtest
from oq_backtest.walkforward import walk_forward

from oq_zoo.registry import StrategyEntry


@dataclass(frozen=True, slots=True)
class HonestyGateConfig:
    """Tunables for the honesty gate."""

    min_alpha_bps: float = 0.0
    require_walk_forward: bool = True
    min_oos_sharpe: float = 0.0
    walk_forward_train_periods: int = 252 * 3
    walk_forward_test_periods: int = 252
    walk_forward_step: int | None = None


@dataclass(frozen=True, slots=True)
class StrategySpec:
    """Inputs the gate needs to evaluate a strategy."""

    entry: StrategyEntry
    prices: pd.DataFrame
    benchmark_returns: pd.Series


@dataclass(slots=True)
class GateReport:
    """Per-check results for a single strategy."""

    strategy: str
    ran_backtest: bool = False
    ran_walk_forward: bool = False
    net_cagr: float = float("nan")
    benchmark_cagr: float = float("nan")
    alpha_bps: float = float("nan")
    oos_sharpe: float = float("nan")
    is_educational: bool = False
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass(slots=True)
class GateResult:
    """Aggregate gate report across many strategies."""

    reports: list[GateReport] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.reports)

    def failures(self) -> list[GateReport]:
        return [r for r in self.reports if not r.passed]

    def summary(self) -> str:
        lines = [f"OpenQuant Zoo - Honesty Gate ({len(self.reports)} strategies)"]
        lines.append("=" * 60)
        for r in self.reports:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"[{status}] {r.strategy}  alpha={r.alpha_bps:+.0f} bps")
            for f in r.failures:
                lines.append(f"        - {f}")
        return "\n".join(lines)


def _cagr_from_returns(returns: pd.Series) -> float:
    if returns.empty:
        return float("nan")
    cumulative = (1.0 + returns.fillna(0.0)).prod()
    if cumulative <= 0:
        return float("nan")
    idx = pd.DatetimeIndex(returns.index)
    years = max((idx[-1] - idx[0]).days / 365.25, 1e-9)
    return float(cumulative ** (1.0 / years) - 1.0)


def _check_declarations(entry: StrategyEntry, report: GateReport) -> None:
    if not entry.benchmark:
        report.failures.append("no benchmark declared")
    if not entry.universe:
        report.failures.append("no universe declared")
    if not entry.cost_preset:
        report.failures.append("no cost preset declared")


def _run_reference_backtest(
    spec: StrategySpec,
    report: GateReport,
    config: HonestyGateConfig,
    backtest_fn: Callable[..., BacktestResult],
) -> None:
    entry = spec.entry
    try:
        signals = entry.signal_fn(spec.prices)
        if not isinstance(signals, pd.DataFrame):
            raise TypeError(f"signal_fn must return a DataFrame, got {type(signals).__name__}")
        result = backtest_fn(
            signals=signals,
            prices=spec.prices,
            costs=entry.cost_preset,
            initial_capital=entry.initial_capital,
        )
        report.ran_backtest = True
        report.net_cagr = float(result.summary()["net_cagr"])
    except Exception as exc:
        report.failures.append(f"backtest failed: {exc}")
        return

    report.benchmark_cagr = _cagr_from_returns(spec.benchmark_returns)
    report.alpha_bps = (report.net_cagr - report.benchmark_cagr) * 10_000.0
    if not report.is_educational and report.alpha_bps < config.min_alpha_bps:
        report.failures.append(
            f"net CAGR ({report.net_cagr * 100:.2f}%) does not beat benchmark "
            f"({report.benchmark_cagr * 100:.2f}%) by required margin"
        )


def _run_walk_forward(
    spec: StrategySpec,
    report: GateReport,
    config: HonestyGateConfig,
    backtest_fn: Callable[..., BacktestResult],
) -> None:
    entry = spec.entry
    try:
        index = pd.DatetimeIndex(spec.prices.index)
        folds = list(
            walk_forward(
                index=index,
                train_periods=config.walk_forward_train_periods,
                test_periods=config.walk_forward_test_periods,
                step=config.walk_forward_step,
            )
        )
        oos_returns: list[float] = []
        for fold in folds:
            prices_oos = spec.prices.loc[fold.test_start : fold.test_end]
            if prices_oos.shape[0] < 5:
                continue
            signals_oos = entry.signal_fn(prices_oos)
            if signals_oos.empty:
                continue
            fold_result = backtest_fn(
                signals=signals_oos,
                prices=prices_oos,
                costs=entry.cost_preset,
                initial_capital=entry.initial_capital,
            )
            r = fold_result.net_returns.dropna()
            if not r.empty:
                oos_returns.extend(r.tolist())
        report.ran_walk_forward = True
        if oos_returns:
            arr = np.asarray(oos_returns, dtype=float)
            std = float(arr.std(ddof=1)) if arr.size > 1 else 0.0
            report.oos_sharpe = float(arr.mean() / std * np.sqrt(252)) if std > 0 else 0.0
            if not report.is_educational and report.oos_sharpe < config.min_oos_sharpe:
                report.failures.append(
                    f"walk-forward OOS Sharpe ({report.oos_sharpe:.2f}) below "
                    f"required minimum ({config.min_oos_sharpe:.2f})"
                )
        else:
            report.failures.append("walk-forward produced no OOS returns")
    except Exception as exc:
        report.failures.append(f"walk-forward failed: {exc}")


def _evaluate(
    spec: StrategySpec,
    config: HonestyGateConfig,
    backtest_fn: Callable[..., BacktestResult],
) -> GateReport:
    entry = spec.entry
    report = GateReport(strategy=entry.name, is_educational="educational" in entry.tags)
    _run_reference_backtest(spec, report, config, backtest_fn)
    if config.require_walk_forward and report.ran_backtest:
        _run_walk_forward(spec, report, config, backtest_fn)
    _check_declarations(entry, report)
    return report


@dataclass(slots=True)
class HonestyGate:
    """Runs the gate across one or more strategies."""

    config: HonestyGateConfig = field(default_factory=HonestyGateConfig)
    backtest_fn: Callable[..., BacktestResult] = backtest

    def run(self, specs: list[StrategySpec]) -> GateResult:
        return GateResult(reports=[_evaluate(s, self.config, self.backtest_fn) for s in specs])


def run_gate(
    specs: list[StrategySpec],
    config: HonestyGateConfig | None = None,
) -> GateResult:
    return HonestyGate(config=config or HonestyGateConfig()).run(specs)


__all__ = [
    "GateReport",
    "GateResult",
    "HonestyGate",
    "HonestyGateConfig",
    "StrategySpec",
    "run_gate",
]
