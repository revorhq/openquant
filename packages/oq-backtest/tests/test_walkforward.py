from __future__ import annotations

import pandas as pd
import pytest
from oq_backtest import train_test_split, walk_forward


def test_walk_forward_yields_expected_count():
    idx = pd.bdate_range("2020-01-01", periods=100)
    folds = list(walk_forward(idx, train_periods=40, test_periods=20))
    assert len(folds) == 3


def test_walk_forward_rolling_advances_start():
    idx = pd.bdate_range("2020-01-01", periods=60)
    folds = list(walk_forward(idx, train_periods=20, test_periods=10))
    assert folds[0].train_start == idx[0]
    assert folds[1].train_start == idx[10]


def test_walk_forward_expanding_keeps_train_start():
    idx = pd.bdate_range("2020-01-01", periods=60)
    folds = list(walk_forward(idx, train_periods=20, test_periods=10, expanding=True))
    assert all(f.train_start == idx[0] for f in folds)


def test_walk_forward_train_test_no_overlap():
    idx = pd.bdate_range("2020-01-01", periods=50)
    folds = list(walk_forward(idx, train_periods=20, test_periods=10))
    for f in folds:
        assert f.train_end < f.test_start


def test_walk_forward_invalid_args():
    idx = pd.bdate_range("2020-01-01", periods=10)
    with pytest.raises(ValueError):
        list(walk_forward(idx, train_periods=0, test_periods=10))
    with pytest.raises(ValueError):
        list(walk_forward(idx, train_periods=5, test_periods=5, step=0))


def test_walk_forward_too_short_yields_nothing():
    idx = pd.bdate_range("2020-01-01", periods=5)
    assert list(walk_forward(idx, train_periods=10, test_periods=5)) == []


def test_train_test_split_default_30pct():
    idx = pd.bdate_range("2020-01-01", periods=100)
    train, test = train_test_split(idx)
    assert len(train) == 70
    assert len(test) == 30


def test_train_test_split_bad_size():
    idx = pd.bdate_range("2020-01-01", periods=10)
    with pytest.raises(ValueError):
        train_test_split(idx, test_size=0.0)
    with pytest.raises(ValueError):
        train_test_split(idx, test_size=1.0)


def test_train_test_split_short_index():
    with pytest.raises(ValueError):
        train_test_split(pd.DatetimeIndex([pd.Timestamp("2020-01-01")]))
