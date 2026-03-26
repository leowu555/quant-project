from __future__ import annotations

import numpy as np
import pandas as pd

from qtrading.validation.leakage_checks import (
    validate_forward_return_labels,
    validate_lagged_features,
)


def test_validate_lagged_features_pass() -> None:
    idx = pd.date_range("2020-01-01", periods=60, freq="D")
    raw = pd.Series(np.linspace(10.0, 20.0, num=len(idx)), index=idx)
    lag_days = 2

    # Correct: features(t) == raw(t - lag)
    features = pd.DataFrame(
        {"f": raw.shift(lag_days)},
        index=idx,
    )

    res = validate_lagged_features(raw=raw, features=features, lag_days=lag_days)
    assert res.ok, res.message


def test_validate_lagged_features_fail_on_lookahead() -> None:
    idx = pd.date_range("2020-01-01", periods=60, freq="D")
    raw = pd.Series(np.linspace(10.0, 20.0, num=len(idx)), index=idx)
    lag_days = 2

    # Incorrect: lookahead shift (raw(t + lag))
    features = pd.DataFrame(
        {"f": raw.shift(-lag_days)},
        index=idx,
    )

    res = validate_lagged_features(raw=raw, features=features, lag_days=lag_days)
    assert not res.ok


def test_validate_forward_return_labels_pass() -> None:
    idx = pd.date_range("2020-01-01", periods=60, freq="D")
    prices = pd.Series(np.linspace(100.0, 160.0, num=len(idx)), index=idx)
    horizon_days = 5

    # Correct: label(t) = forward_return over horizon
    labels = prices.shift(-horizon_days) / prices - 1.0

    res = validate_forward_return_labels(prices=prices, labels=labels, horizon_days=horizon_days)
    assert res.ok, res.message


def test_validate_forward_return_labels_fail_on_wrong_horizon_or_backwards() -> None:
    idx = pd.date_range("2020-01-01", periods=60, freq="D")
    prices = pd.Series(np.linspace(100.0, 160.0, num=len(idx)), index=idx)
    horizon_days = 5

    # Incorrect: backward return instead of forward
    labels = prices / prices.shift(horizon_days) - 1.0

    res = validate_forward_return_labels(prices=prices, labels=labels, horizon_days=horizon_days)
    assert not res.ok

