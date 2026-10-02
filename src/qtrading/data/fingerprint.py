from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


@dataclass(frozen=True, slots=True)
class DatasetMetadata:
    fingerprint: str
    source: str
    symbols: list[str]
    start: str
    end: str
    n_rows: int
    n_symbols: int
    timezone: str
    columns: list[str]
    created_at: str
    extra: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_pandas() -> Any:
    import pandas as pd

    return pd


def fingerprint_bars(data: Any) -> str:
    """
    Content hash of the canonical bar table.

    Same symbols/dates/values always produce the same fingerprint, independent
    of how the frame was assembled in memory.
    """
    pd = _require_pandas()
    canonical = data.reset_index()
    ts_col = canonical.columns[0]
    canonical = canonical.rename(columns={ts_col: "timestamp"})
    canonical["timestamp"] = pd.to_datetime(canonical["timestamp"], utc=True).dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    canonical["symbol"] = canonical["symbol"].astype(str)
    ordered = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]
    extra_cols = [c for c in canonical.columns if c not in ordered]
    canonical = canonical[ordered + extra_cols]
    canonical = canonical.sort_values(["timestamp", "symbol"], kind="mergesort")
    payload = canonical.to_csv(index=False, float_format="%.10g")
    return sha256(payload.encode("utf-8")).hexdigest()


def build_metadata(
    *,
    data: Any,
    source: str,
    extra: dict[str, Any] | None = None,
) -> DatasetMetadata:
    pd = _require_pandas()
    idx = pd.to_datetime(data.index, utc=True)
    symbols = sorted({str(s) for s in data["symbol"].tolist()})
    return DatasetMetadata(
        fingerprint=fingerprint_bars(data),
        source=source,
        symbols=symbols,
        start=idx.min().strftime("%Y-%m-%dT%H:%M:%SZ") if len(idx) else "",
        end=idx.max().strftime("%Y-%m-%dT%H:%M:%SZ") if len(idx) else "",
        n_rows=int(len(data)),
        n_symbols=len(symbols),
        timezone="UTC",
        columns=["timestamp", *list(data.columns)],
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        extra=extra or {},
    )
