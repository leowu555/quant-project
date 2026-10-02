# Quant Project

A leakage-aware research stack. V1 is a local Python system: data → features →
labels → time-aware validation → models → portfolio → backtest → evaluation.

This repo is being built one subsystem at a time. **Only the data layer is
implemented as production-quality V1 so far.**

## V1 scope (in progress)

1. Multi-asset data pipeline — **done this round**
2. Leakage-safe feature engine
3. Forward-return labels
4. Walk-forward / purge / embargo validation
5. Momentum baseline, Elastic Net, XGBoost
6. Portfolio construction (including CVXPY)
7. Cost-aware backtest
8. Evaluation metrics
9. Research experiments
10. Final methodology docs with measured results

Not in V1: APIs, frontends, streaming, cloud, deep learning, order books.

## Data layer (current)

- `YFinanceDataPipeline`: daily OHLCV, UTC timestamps, deterministic sort
- `validate_bars`: schema, duplicates, OHLC consistency
- `fingerprint_bars` / `DatasetMetadata`: content hash for reproducibility
- `BarStore`: Parquet write/read + DuckDB queries

```bash
python -m pip install -r requirements.txt
pytest
python scripts/run_backtest.py --start 2020-01-01 --end 2020-03-31 --symbols AAPL MSFT
```

The runner stops after the data stage on purpose. Later stages should plug in
behind the existing interfaces without rewriting ingestion.

Details: `docs/data_pipeline.md`.
