# Quant Project

A small (MVP) quant research framework that keeps the data/time semantics honest.
Strategies are built as a pipeline with explicit “what you can know when” rules, so
timing and leakage mistakes become testable failures.

## Architecture

The pipeline goes left-to-right:
`data -> features -> signals -> fusion -> portfolio -> execution -> backtest -> evaluation`.

Step 1’s goal is to define shared contracts between layers, via:
`DataPipeline`, `FeatureEngineer`, `SignalModel`, `SignalFusion`,
`PortfolioConstructor`, `ExecutionSimulator`, `BacktestEngine`, `Evaluator`.

## Repo layout

- `configs/`: YAML experiment configuration (the MVP lives here)
- `data/`: data staging (`raw/`, `interim/`, `processed/`, `artifacts/`)
- `docs/`: documentation (queued for deeper Step 1 write-ups)
- `notebooks/`: exploratory work
- `scripts/`: runnable entrypoints (runner stub planned for Step 1)
- `reports/`: outputs from backtests/evaluations
- `src/qtrading/`: the Python package
  - `core/`: shared schemas + abstract interfaces + MVP config models
  - `validation/`: timing/leakage validators with unit tests
  - `data/`, `features/`, `signals/`, `models/`, `portfolio/`, `execution/`,
    `backtest/`, `evaluation/`, `utils/`: placeholders for implementations
- `tests/`: unit tests

## What’s already implemented

Core contracts in `src/qtrading/core/`:
- `types.py`: dataclass “shapes” for bars/features/signals/orders/fills/positions/results
- `interfaces.py`: ABCs for each pipeline layer
- `clock.py`: MVP timestamp semantics helpers (horizon labeling + feature lag)

Config + YAML in `src/qtrading/core/config.py` + `configs/`:
- `MVPConfig`: validated MVP settings (horizon/lag, rebalance cadence, costs, constraints)
- `configs/base.yaml`: base MVP defaults
- `configs/experiments/mvp_daily_ls_wproxy.yaml`: an example experiment config

Timing/leakage validation in `src/qtrading/validation/`:
- `leakage_checks.py`: `validate_lagged_features` + `validate_forward_return_labels`
- `tests/test_timing_contracts.py`: synthetic tests to catch common alignment mistakes

## Quick start

1. Install deps:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Run tests:
   ```bash
   pytest
   ```
3. Lint (optional if `ruff` is installed):
   ```bash
   ruff check .
   ```