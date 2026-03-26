# Quant Project

Institutional quant research framework (MVP), structured around layered contracts
to make timing/leakage constraints explicit.

## Architecture (layered pipeline)

The framework is organized into responsibilities that compose left-to-right:
data -> features -> signals -> fusion -> portfolio -> execution -> backtest -> evaluation.

Concretely, the Step 1 contract layer defines these interfaces:
`DataPipeline`, `FeatureEngineer`, `SignalModel`, `SignalFusion`,
`PortfolioConstructor`, `ExecutionSimulator`, `BacktestEngine`, `Evaluator`.

## Repo Layout

- `configs/`: YAML experiment configuration (e.g. MVP daily-first)
- `data/`: data staging (`raw/`, `interim/`, `processed/`, `artifacts/`)
- `docs/`: architecture and timing/leakage documentation (planned in Step 1)
- `notebooks/`: exploratory analysis
- `scripts/`: runnable entrypoints (Step 1 runner stub planned)
- `reports/`: generated report outputs
- `src/qtrading/`: the Python package
  - `core/`: canonical schemas, abstract interfaces, and config models
  - `validation/`: unit-testable leakage/timing validators
  - `data/`, `features/`, `signals/`, `models/`, `portfolio/`, `execution/`,
    `backtest/`, `evaluation/`, `utils/`: package placeholders for future
    implementations
- `tests/`: unit tests (timing/leakage contracts)

## What’s Implemented So Far (Step 1)

### Core contracts (`src/qtrading/core/`)

- `types.py`: canonical dataclass schemas for bars/features/signals/orders/fills/
  positions/backtest results.
- `interfaces.py`: ABCs for each layer of the research/backtest pipeline.
- `clock.py`: MVP daily-first timestamp semantics helpers (horizon labeling and
  safe feature lag computation).

### Config layer (`src/qtrading/core/config.py` + YAML in `configs/`)

- `MVPConfig`: validated MVP settings (data source, universe kind, horizon/lag,
  rebalance cadence, costs, and constraints).
- `configs/base.yaml`: base defaults for the daily-first MVP.
- `configs/experiments/mvp_daily_ls_wproxy.yaml`: an example experiment config.

### Timing / leakage validation (`src/qtrading/validation/`)

- `leakage_checks.py`:
  - `validate_lagged_features(...)` checks feature alignment vs. a required lag.
  - `validate_forward_return_labels(...)` checks label alignment for a forward
    return horizon.
- `tests/test_timing_contracts.py`: synthetic unit tests that pass for correct
  alignment and fail for common lookahead mistakes.

## Quick start (dev)

1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Run tests:
   ```bash
   pytest
   ```
3. Lint:
   ```bash
   ruff check .
   ```

## Notes

Step 1 is about getting the repo layout + importable contracts right, and making
timing/leakage assumptions testable. The MVP runner stub (`scripts/run_backtest.py`)
is planned next.