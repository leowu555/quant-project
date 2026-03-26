from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _require_pandas() -> Any:  # pragma: no cover
    import pandas as pd

    return pd


def _require_numpy() -> Any:  # pragma: no cover
    import numpy as np

    return np


@dataclass(frozen=True, slots=True)
class LeakageCheckResult:
    ok: bool
    message: str = ""


def validate_lagged_features(
    *,
    raw: "Any",
    features: "Any",
    lag_days: int,
    tolerance: float = 1e-12,
) -> LeakageCheckResult:
    """
    Validate a "features are lagged by N days" contract.

    Contract tested (MVP daily-first):
    - features(t) must equal raw(t - lag_days) for all timestamps where both
      sides are defined.

    Note:
    This is a generic validator for lag/shift alignment. It can't prove
    feature engineering correctness if you provide features computed in
    other (model-specific) ways.
    """

    if lag_days < 0:
        return LeakageCheckResult(ok=False, message="lag_days must be >= 0")

    pd = _require_pandas()
    np = _require_numpy()

    if isinstance(features, pd.Series):
        features_df = features.to_frame(name="__feature__")
    elif isinstance(features, pd.DataFrame):
        features_df = features
    else:
        return LeakageCheckResult(ok=False, message="features must be a Series or DataFrame")

    expected = raw.shift(lag_days)
    expected_df = expected.to_frame(name="__expected__")
    expected_df = expected_df.reindex(features_df.index)

    # Compare only overlapping non-null rows.
    mask = features_df.notna()
    expected_values = expected_df.iloc[:, 0]

    # For each column, validate.
    for col in features_df.columns:
        feature_col = features_df[col]
        valid_idx = mask[col]
        if valid_idx.sum() == 0:
            continue
        diff = np.abs(feature_col[valid_idx] - expected_values[valid_idx])
        if float(diff.max()) > tolerance:
            return LeakageCheckResult(
                ok=False,
                message=f"Feature column '{col}' does not match raw shifted by lag_days={lag_days}.",
            )

    return LeakageCheckResult(ok=True, message="ok")


def validate_forward_return_labels(
    *,
    prices: "Any",
    labels: "Any",
    horizon_days: int,
    tolerance: float = 1e-12,
) -> LeakageCheckResult:
    """
    Validate the "label is forward return over horizon_days" contract.

    Contract tested:
    - labels(t) must equal (prices(t + horizon_days) / prices(t)) - 1
      for all timestamps where both future and current prices are defined.
    """

    if horizon_days < 0:
        return LeakageCheckResult(ok=False, message="horizon_days must be >= 0")
    pd = _require_pandas()
    np = _require_numpy()

    if not isinstance(labels, pd.Series):
        return LeakageCheckResult(ok=False, message="labels must be a pandas Series")

    expected = prices.shift(-horizon_days) / prices - 1.0
    expected = expected.reindex(labels.index)

    valid_idx = labels.notna()
    if valid_idx.sum() == 0:
        return LeakageCheckResult(ok=False, message="No overlapping, non-null label rows to validate.")

    diff = np.abs(labels[valid_idx] - expected[valid_idx])
    if float(diff.max()) > tolerance:
        return LeakageCheckResult(ok=False, message=f"Forward-return labels do not match horizon_days={horizon_days}.")

    return LeakageCheckResult(ok=True, message="ok")

