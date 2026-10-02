from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from qtrading.core.interfaces import DataPipeline
from qtrading.core.types import BarFrame
from qtrading.data.validation import assert_valid_bars


def _require_pandas() -> Any:
    try:
        import pandas as pd
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "pandas is required for YFinanceDataPipeline. "
            "Install deps with: python -m pip install -r requirements.txt"
        ) from e
    return pd


def _require_yfinance() -> Any:
    try:
        import yfinance as yf
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "yfinance is required for YFinanceDataPipeline. "
            "Install deps with: python -m pip install -r requirements.txt"
        ) from e
    return yf


def _to_timestamp(x: Any) -> Any:
    pd = _require_pandas()
    return pd.Timestamp(x)


def flatten_ohlcv_columns(columns: Any) -> list[str]:
    """Normalize yfinance single- or multi-index columns to lowercase names."""
    known = {"open", "high", "low", "close", "adj_close", "volume"}
    flat: list[str] = []
    for col in columns:
        parts = col if isinstance(col, tuple) else (col,)
        mapped = None
        for part in parts:
            key = str(part).lower().replace(" ", "_")
            if key in known:
                mapped = key
                break
        flat.append(mapped or str(parts[-1]).lower().replace(" ", "_"))
    return flat


def _utc_day(value: Any) -> Any:
    ts = _to_timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.normalize()


def _naive_datetime(value: Any) -> Any:
    pd = _require_pandas()
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.to_pydatetime()


def standardize_ohlcv(*, symbol: str, raw: Any) -> Any:
    """Turn a yfinance-like OHLCV frame into the project bar schema."""
    pd = _require_pandas()
    if raw is None or len(raw) == 0:
        raise ValueError(f"No data returned for symbol '{symbol}'")

    work = raw.copy()
    work.columns = flatten_ohlcv_columns(work.columns)
    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in work.columns]
    if missing:
        raise ValueError(f"yfinance data for '{symbol}' missing columns: {missing}")

    df = work[required].copy()
    df.index = ensure_utc_index(df.index)
    df = df[~df.index.duplicated(keep="last")].sort_index()

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required)

    invalid_range = (df["high"] + 1e-12 < df[["open", "close", "low"]].max(axis=1)) | (
        df["low"] - 1e-12 > df[["open", "close", "high"]].min(axis=1)
    )
    df = df.loc[~invalid_range]
    df = df.loc[(df[["open", "high", "low", "close"]] > 0).all(axis=1)]
    df = df.loc[df["volume"] >= 0]

    df["symbol"] = symbol
    return df[["symbol", *required]]


def ensure_utc_index(idx: Any) -> Any:
    pd = _require_pandas()
    ts = pd.to_datetime(idx)
    if getattr(ts, "tz", None) is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def assemble_universe(frames: list[Any]) -> Any:
    pd = _require_pandas()
    if not frames:
        raise ValueError("no symbol frames to assemble")
    out = pd.concat(frames, axis=0, ignore_index=False)
    out.index = ensure_utc_index(out.index)
    out.index.name = "timestamp"
    out = out.reset_index()
    out["symbol"] = out["symbol"].astype(str)
    out = out.sort_values(["timestamp", "symbol"], kind="mergesort")
    return out.set_index("timestamp")


@dataclass(slots=True)
class YFinanceDataPipeline(DataPipeline):
    """
    Daily multi-asset OHLCV downloader using yfinance.

    Output:
    - DatetimeIndex named `timestamp` in UTC
    - columns: symbol, open, high, low, close, volume
    - sorted by (timestamp, symbol)

    Raw cache is per-symbol Parquet under `cache_dir`. Processed assembly is
    left to BarStore so fingerprints are computed on the validated universe.
    """

    cache_dir: str | Path = Path("data/raw/yfinance")
    auto_adjust: bool = False
    progress: bool = False

    def load_bars(self, *, universe: Iterable[str], start: Any, end: Any) -> BarFrame:
        symbols = sorted({s.strip().upper() for s in universe if str(s).strip()})
        if not symbols:
            raise ValueError("universe must contain at least one non-empty symbol")

        start_ts = _utc_day(start)
        end_ts = _utc_day(end)
        if end_ts < start_ts:
            raise ValueError("end must be >= start")

        frames = [self._load_symbol_daily(symbol=sym, start=start_ts, end=end_ts) for sym in symbols]
        out = assemble_universe(frames)
        assert_valid_bars(out)
        return BarFrame(data=out, timezone="UTC")

    def _cache_path(self, *, symbol: str) -> Path:
        cache_dir = Path(self.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{symbol}.daily.parquet"

    def _load_symbol_daily(self, *, symbol: str, start: Any, end: Any) -> Any:
        pd = _require_pandas()
        cache_path = self._cache_path(symbol=symbol)

        if cache_path.exists():
            cached = pd.read_parquet(cache_path)
            cached.index = ensure_utc_index(cached.index)
            cached = cached.sort_index()
            start_cmp = pd.Timestamp(start)
            end_cmp = pd.Timestamp(end)
            if len(cached.index) > 0 and cached.index.min() <= start_cmp and cached.index.max() >= end_cmp:
                sliced = cached.loc[(cached.index >= start_cmp) & (cached.index <= end_cmp)].copy()
                sliced["symbol"] = symbol
                return sliced[["symbol", "open", "high", "low", "close", "volume"]]

        downloaded = self._download_symbol_daily(symbol=symbol, start=start, end=end)
        try:
            downloaded.to_parquet(cache_path, index=True)
        except ImportError:
            downloaded.to_csv(cache_path.with_suffix(".csv.gz"), index=True, compression="gzip")
        return downloaded

    def _download_symbol_daily(self, *, symbol: str, start: Any, end: Any) -> Any:
        pd = _require_pandas()
        yf = _require_yfinance()

        # yfinance treats `end` as exclusive; add a day so caller `end` is inclusive.
        end_exclusive = pd.Timestamp(end) + pd.Timedelta(days=1)
        raw = yf.download(
            tickers=symbol,
            start=_naive_datetime(start),
            end=_naive_datetime(end_exclusive),
            interval="1d",
            group_by="column",
            auto_adjust=self.auto_adjust,
            actions=False,
            progress=self.progress,
            threads=True,
        )
        df = standardize_ohlcv(symbol=symbol, raw=raw)
        start_cmp = pd.Timestamp(start)
        end_cmp = pd.Timestamp(end)
        return df.loc[(df.index >= start_cmp) & (df.index <= end_cmp)].copy()
