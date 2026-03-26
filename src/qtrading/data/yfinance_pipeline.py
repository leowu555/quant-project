from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from qtrading.core.interfaces import DataPipeline
from qtrading.core.types import BarFrame


def _require_pandas() -> Any:  # pragma: no cover
    try:
        import pandas as pd

        return pd
    except ModuleNotFoundError as e:  # pragma: no cover
        raise ModuleNotFoundError(
            "pandas is required for YFinanceDataPipeline. "
            "Install deps with: python -m pip install -r requirements.txt"
        ) from e


def _require_yfinance() -> Any:  # pragma: no cover
    try:
        import yfinance as yf

        return yf
    except ModuleNotFoundError as e:  # pragma: no cover
        raise ModuleNotFoundError(
            "yfinance is required for YFinanceDataPipeline. "
            "Install deps with: python -m pip install -r requirements.txt"
        ) from e


def _to_timestamp(x: Any) -> Any:
    pd = _require_pandas()
    return pd.Timestamp(x)


@dataclass(slots=True)
class YFinanceDataPipeline(DataPipeline):
    """
    Daily OHLCV downloader using yfinance, standardized into `BarFrame`.

    Output format:
    - Long-form DataFrame indexed by UTC timestamps.
    - Columns: `symbol`, `open`, `high`, `low`, `close`, `volume`

    Caching (MVP):
    - Per-symbol CSV cache under `cache_dir`.
    - If a cached file fully covers the requested date range, we slice it.
      Otherwise, we re-download the requested range and overwrite the cache.
    """

    cache_dir: str | Path = Path("data/raw/yfinance")
    auto_adjust: bool = False
    progress: bool = False

    def load_bars(self, *, universe: Iterable[str], start: Any, end: Any) -> BarFrame:
        pd = _require_pandas()

        symbols = sorted({s.strip().upper() for s in universe if str(s).strip()})
        if not symbols:
            raise ValueError("universe must contain at least one non-empty symbol")

        start_ts = _to_timestamp(start).normalize()
        end_ts = _to_timestamp(end).normalize()
        if end_ts < start_ts:
            raise ValueError("end must be >= start")

        frames: list[Any] = []
        for sym in symbols:
            df = self._load_symbol_daily(symbol=sym, start=start_ts, end=end_ts)
            frames.append(df)

        out = pd.concat(frames, axis=0, ignore_index=False)
        out.index.name = "timestamp"
        out = out.sort_values(["timestamp", "symbol"], kind="mergesort")

        bars = BarFrame(data=out, timezone="UTC")
        bars.validate()
        return bars

    def _cache_path(self, *, symbol: str) -> Path:
        cache_dir = Path(self.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{symbol}.daily.csv.gz"

    def _load_symbol_daily(self, *, symbol: str, start: Any, end: Any) -> Any:
        pd = _require_pandas()
        cache_path = self._cache_path(symbol=symbol)

        if cache_path.exists():
            cached = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            cached.index = self._ensure_utc_index(cached.index)
            cached = cached.sort_index()
            # If cache fully covers [start, end], slice.
            if (len(cached.index) > 0) and (cached.index.min() <= start) and (cached.index.max() >= end):
                sliced = cached.loc[(cached.index >= start) & (cached.index <= end)].copy()
                sliced["symbol"] = symbol
                return sliced

        downloaded = self._download_symbol_daily(symbol=symbol, start=start, end=end)
        # Cache the clean frame for future reads.
        downloaded.to_csv(cache_path, index=True, compression="gzip")
        return downloaded

    def _download_symbol_daily(self, *, symbol: str, start: Any, end: Any) -> Any:
        pd = _require_pandas()
        yf = _require_yfinance()

        # yfinance treats `end` as exclusive; add a day so the user's `end`
        # behaves as inclusive for daily bars.
        end_exclusive = pd.Timestamp(end) + pd.Timedelta(days=1)

        raw = yf.download(
            tickers=symbol,
            start=pd.Timestamp(start).to_pydatetime(),
            end=end_exclusive.to_pydatetime(),
            interval="1d",
            group_by="column",
            auto_adjust=self.auto_adjust,
            actions=False,
            progress=self.progress,
            threads=True,
        )

        if raw is None or len(raw) == 0:
            raise ValueError(f"No data returned by yfinance for symbol '{symbol}'")

        df = self._standardize_ohlcv(symbol=symbol, raw=raw)
        df = df.loc[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))].copy()
        return df

    def _standardize_ohlcv(self, *, symbol: str, raw: Any) -> Any:
        pd = _require_pandas()

        # yfinance returns columns like Open/High/Low/Close/Adj Close/Volume.
        cols = {c.lower().replace(" ", "_"): c for c in raw.columns}
        required_map = {
            "open": cols.get("open"),
            "high": cols.get("high"),
            "low": cols.get("low"),
            "close": cols.get("close"),
            "volume": cols.get("volume"),
        }
        missing = [k for k, v in required_map.items() if v is None]
        if missing:
            raise ValueError(f"yfinance data for '{symbol}' missing columns: {missing}")

        df = raw[[required_map["open"], required_map["high"], required_map["low"], required_map["close"], required_map["volume"]]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]

        df.index = self._ensure_utc_index(df.index)
        df = df.sort_index()

        # Basic MVP cleaning: drop malformed rows, enforce numeric types.
        df = df.replace([pd.NA], pd.NA)
        df = df.dropna(subset=["open", "high", "low", "close", "volume"])

        for c in ["open", "high", "low", "close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("float64")
        df = df.dropna(subset=["open", "high", "low", "close", "volume"])

        # Long-form output with symbol column for easy grouping downstream.
        df["symbol"] = symbol
        return df[["symbol", "open", "high", "low", "close", "volume"]]

    def _ensure_utc_index(self, idx: Any) -> Any:
        pd = _require_pandas()
        ts = pd.to_datetime(idx)
        # Ensure tz-aware UTC for consistent downstream semantics.
        if getattr(ts, "tz", None) is None:
            return ts.tz_localize("UTC")
        return ts.tz_convert("UTC")

