# V1 data pipeline

This is the first production-quality subsystem. Later V1 work (features, labels,
models, portfolio, backtest) is not implemented yet.

## Why this exists

Downstream research is only as good as the bar table. The data layer therefore:

- downloads daily OHLCV from yfinance
- standardizes schema and timezone
- rejects malformed or unsorted panels
- persists a reproducible Parquet snapshot
- fingerprints the exact dataset that later stages would consume

## Contract

`YFinanceDataPipeline.load_bars(...)` returns a `BarFrame` whose `data` is:

- UTC `DatetimeIndex` named `timestamp`
- columns: `symbol`, `open`, `high`, `low`, `close`, `volume`
- sorted by `(timestamp, symbol)`
- unique `(timestamp, symbol)` keys
- positive prices, non-negative volume, consistent OHLC ranges

## Persistence

`BarStore` writes:

- `data/processed/bars/bars.parquet`
- `data/processed/bars/metadata.json` (includes SHA-256 content fingerprint)

DuckDB can query the parquet as table `bars` without copying it into a warehouse.

## Run

```bash
python scripts/run_backtest.py --start 2020-01-01 --end 2020-03-31 --symbols AAPL MSFT
pytest tests/test_data_pipeline.py tests/test_timing_contracts.py
```
