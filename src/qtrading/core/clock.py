from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class LabelSemantics:
    """
    Timestamp semantics for leakage avoidance.

    MVP daily-first contract:
    - features are computed from information available at `feature_as_of`
    - labels are aligned to a future horizon relative to that timestamp
    """

    horizon_days: int

    def label_time(self, *, feature_as_of: object) -> object:
        if self.horizon_days < 0:
            raise ValueError("horizon_days must be >= 0")
        # Works for both `datetime` and `pandas.Timestamp` (adds `timedelta`).
        return feature_as_of + timedelta(days=self.horizon_days)


def shift_as_of_for_features(
    *,
    observation_time: object,
    feature_lag_days: int,
) -> object:
    """
    Compute the safe `as_of` for features derived from an observation.

    Contract:
    - if data is observed at `observation_time`, and a `feature_lag_days` is
      required (e.g., to ensure we don't use same-day close when predicting),
      then features use `observation_time - feature_lag_days`.
    """

    if feature_lag_days < 0:
        raise ValueError("feature_lag_days must be >= 0")
    # Works for both `datetime` and `pandas.Timestamp` (subtracts `timedelta`).
    return observation_time - timedelta(days=feature_lag_days)

