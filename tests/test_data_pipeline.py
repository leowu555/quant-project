from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from qtrading.core.types import BarFrame
from qtrading.data.fingerprint import build_metadata, fingerprint_bars
from qtrading.data.store import BarStore
from qtrading.data.validation import validate_bars
from qtrading.data.yfinance_pipeline import assemble_universe, standardize_ohlcv


def _bars() -> pd.DataFrame:
    idx = pd.to_datetime(
        ["2020-01-02", "2020-01-02", "2020-01-03", "2020-01-03"],
        utc=True,
    )
    return pd.DataFrame(
        {
            "symbol": ["AAPL", "MSFT", "AAPL", "MSFT"],
            "open": [10.0, 20.0, 11.0, 21.0],
            "high": [11.0, 21.0, 12.0, 22.0],
            "low": [9.0, 19.0, 10.0, 20.0],
            "close": [10.5, 20.5, 11.5, 21.5],
            "volume": [100.0, 200.0, 110.0, 210.0],
        },
        index=idx,
    )


def test_validate_bars_pass() -> None:
    result = validate_bars(_bars())
    assert result.ok, result.issues


def test_validate_bars_detects_ohlc_violation() -> None:
    data = _bars()
    data.iloc[0, data.columns.get_loc("high")] = 8.0
    result = validate_bars(data)
    assert not result.ok
    assert any("high" in issue for issue in result.issues)


def test_validate_bars_detects_unsorted_rows() -> None:
    data = _bars().iloc[::-1]
    result = validate_bars(data)
    assert not result.ok
    assert any("sorted" in issue for issue in result.issues)


def test_fingerprint_is_deterministic_and_order_invariant() -> None:
    a = _bars()
    b = a.iloc[::-1].copy()
    b = b.sort_values("symbol", kind="mergesort").sort_index(kind="mergesort")
    assert fingerprint_bars(a) == fingerprint_bars(b)
    mutated = a.copy()
    mutated.iloc[0, mutated.columns.get_loc("close")] = 99.0
    assert fingerprint_bars(a) != fingerprint_bars(mutated)


def test_standardize_ohlcv_and_assemble() -> None:
    idx = pd.to_datetime(["2020-01-02", "2020-01-03"])
    raw = pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [11.0, 12.0],
            "Low": [9.0, 10.0],
            "Close": [10.5, 11.5],
            "Volume": [100, 110],
        },
        index=idx,
    )
    aapl = standardize_ohlcv(symbol="AAPL", raw=raw)
    msft_raw = raw.copy()
    msft_raw += 1
    msft = standardize_ohlcv(symbol="MSFT", raw=msft_raw)
    out = assemble_universe([aapl, msft])
    result = validate_bars(out)
    assert result.ok, result.issues
    assert list(out["symbol"]) == ["AAPL", "MSFT", "AAPL", "MSFT"]


def test_bar_store_parquet_and_duckdb_roundtrip(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    pytest.importorskip("duckdb")

    data = _bars()
    bars = BarFrame(data=data, timezone="UTC")
    meta = build_metadata(data=data, source="synthetic")
    store = BarStore(root=tmp_path)
    store.write(bars, meta)

    loaded, loaded_meta = store.read()
    assert loaded_meta["fingerprint"] == meta.fingerprint
    assert fingerprint_bars(loaded.data) == meta.fingerprint

    queried = store.query(
        "SELECT symbol, COUNT(*) AS n FROM bars GROUP BY symbol ORDER BY symbol"
    )
    assert list(queried["symbol"]) == ["AAPL", "MSFT"]
    assert list(queried["n"]) == [2, 2]
