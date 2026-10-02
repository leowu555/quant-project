from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


REQUIRED_BAR_COLUMNS = ("symbol", "open", "high", "low", "close", "volume")


@dataclass(frozen=True, slots=True)
class BarValidationResult:
    ok: bool
    issues: list[str] = field(default_factory=list)


def _require_pandas() -> Any:
    import pandas as pd

    return pd


def validate_bars(data: Any, *, require_utc: bool = True) -> BarValidationResult:
    """
    Check that a multi-asset OHLCV frame is safe to persist and consume.

    Rules:
    - required columns exist
    - no duplicate (timestamp, symbol) rows
    - deterministic order: timestamp ascending, then symbol
    - prices are positive; volume is non-negative
    - high is the session high; low is the session low
    """
    pd = _require_pandas()
    issues: list[str] = []

    if not isinstance(data, pd.DataFrame):
        return BarValidationResult(ok=False, issues=["bars must be a pandas DataFrame"])

    missing = [c for c in REQUIRED_BAR_COLUMNS if c not in data.columns]
    if missing:
        return BarValidationResult(ok=False, issues=[f"missing columns: {missing}"])

    if data.empty:
        issues.append("frame is empty")

    idx = pd.to_datetime(data.index)
    if require_utc and getattr(idx, "tz", None) is None:
        issues.append("timestamp index must be timezone-aware (UTC)")
    elif require_utc:
        tz_name = str(idx.tz)
        if "UTC" not in tz_name and tz_name not in {"tzutc()", "datetime.timezone.utc"}:
            issues.append(f"timestamp index timezone must be UTC, got {idx.tz}")

    keys = pd.DataFrame(
        {"timestamp": idx, "symbol": data["symbol"].astype(str)}
    ).reset_index(drop=True)
    if keys.duplicated().any():
        n_dup = int(keys.duplicated().sum())
        issues.append(f"duplicate (timestamp, symbol) rows: {n_dup}")

    expected = keys.sort_values(["timestamp", "symbol"], kind="mergesort")
    if not keys.reset_index(drop=True).equals(expected.reset_index(drop=True)):
        issues.append("rows are not sorted by (timestamp, symbol)")

    numeric = data[["open", "high", "low", "close", "volume"]]
    if numeric.isna().any().any():
        issues.append("NaN values remain in OHLCV columns")

    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        issues.append("open/high/low/close must be strictly positive")
    if (data["volume"] < 0).any():
        issues.append("volume must be >= 0")

    high_ok = data["high"] + 1e-12 >= data[["open", "close", "low"]].max(axis=1)
    low_ok = data["low"] - 1e-12 <= data[["open", "close", "high"]].min(axis=1)
    if not bool(high_ok.all()):
        issues.append("high is below open/close/low on at least one row")
    if not bool(low_ok.all()):
        issues.append("low is above open/close/high on at least one row")

    return BarValidationResult(ok=len(issues) == 0, issues=issues)


def assert_valid_bars(data: Any, *, require_utc: bool = True) -> None:
    result = validate_bars(data, require_utc=require_utc)
    if not result.ok:
        detail = "; ".join(result.issues)
        raise ValueError(f"bar validation failed: {detail}")
