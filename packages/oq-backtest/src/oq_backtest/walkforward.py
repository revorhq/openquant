"""Walk-forward and out-of-sample split utilities.

Anti-overfitting guardrails for the backtest engine. Use these to slice your
``signals`` and ``prices`` DataFrames into expanding or rolling train/test
windows before calling :func:`oq_backtest.backtest` on each fold.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class Fold:
    """A single walk-forward train/test split."""

    fold: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def walk_forward(
    index: pd.DatetimeIndex,
    train_periods: int,
    test_periods: int,
    expanding: bool = False,
    step: int | None = None,
) -> Iterator[Fold]:
    """Yield successive train/test :class:`Fold` slices over ``index``.

    Parameters
    ----------
    index:
        Sorted date index to walk through.
    train_periods:
        Length of each training window in periods.
    test_periods:
        Length of each test window in periods.
    expanding:
        If True, train window grows; if False (default), it rolls.
    step:
        Number of periods to advance between folds. Defaults to
        ``test_periods`` (non-overlapping test windows).
    """
    if train_periods <= 0 or test_periods <= 0:
        raise ValueError("train_periods and test_periods must be > 0")
    if step is None:
        step = test_periods
    if step <= 0:
        raise ValueError("step must be > 0")
    n = len(index)
    if n < train_periods + test_periods:
        return
    start = 0
    fold = 0
    while start + train_periods + test_periods <= n:
        train_lo = 0 if expanding else start
        train_hi = start + train_periods
        test_lo = train_hi
        test_hi = test_lo + test_periods
        yield Fold(
            fold=fold,
            train_start=index[train_lo],
            train_end=index[train_hi - 1],
            test_start=index[test_lo],
            test_end=index[test_hi - 1],
        )
        fold += 1
        start += step


def train_test_split(
    index: pd.DatetimeIndex,
    test_size: float = 0.3,
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    """Single, contiguous train/test split.

    The split is chronological: the last ``test_size`` fraction of ``index``
    is the test set. Default 30% reserves a meaningful out-of-sample tail.
    """
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be in (0, 1)")
    n = len(index)
    if n < 2:
        raise ValueError("need at least 2 points to split")
    split = round(n * (1.0 - test_size))
    split = max(1, min(n - 1, split))
    return index[:split], index[split:]


__all__ = ["Fold", "train_test_split", "walk_forward"]
