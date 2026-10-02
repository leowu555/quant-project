# Quant Project

This is a daily, multi-asset research stack. The point is not a flashy dashboard. It is a pipeline that can load a universe of stocks, build features without peeking into the future, train models the way you actually would in time, turn scores into a portfolio, and measure the result with costs on.

Everything lives in one Python package (`qtrading`) with a shared contract between stages:

```
data → features → labels → validation → models → portfolio → backtest → evaluation
```

Config is YAML. Experiments should be repeatable: same universe, same dates, same bars, same fingerprint.

---

## How time is supposed to work

Most quant bugs are timing bugs. A feature at date `t` may only use prices that were known by `t`. A label at `t` is the *future* return over some horizon (for example, close[t+5] / close[t] − 1). Training folds cannot contain the test period, and overlapping labels need purge/embargo so the model is not graded on information that leaked across the cut.

That rule shows up in a few places:

- `src/qtrading/core/clock.py` — horizon and feature-lag helpers
- `src/qtrading/validation/leakage_checks.py` — checks that a lag or forward return is actually aligned
- later, walk-forward splits with purge and embargo around each test window

If those checks fail, the dataset is wrong. Do not tune models on top of it.

---

## Layout

```
configs/          YAML for universe, horizon, costs, constraints
data/raw/         yfinance cache (per symbol)
data/processed/   assembled bar panel (Parquet + metadata)
docs/             longer notes (start with docs/data_pipeline.md)
scripts/          CLI entrypoints
src/qtrading/     library
tests/            unit tests (synthetic data; no network required)
```

Interfaces for each stage sit in `src/qtrading/core/interfaces.py`. Types (`BarFrame`, `FeatureFrame`, `SignalFrame`, …) sit in `src/qtrading/core/types.py`. Implementations plug into those instead of growing one giant notebook.

---

## 1. Data

Daily OHLCV comes from yfinance, one symbol at a time, then gets stacked into a long panel.

The table looks like this:

| timestamp (UTC index) | symbol | open | high | low | close | volume |
|---|---|---|---|---|---|---|
| 2020-01-02 | AAPL | … | … | … | … | … |
| 2020-01-02 | MSFT | … | … | … | … | … |
| 2020-01-03 | AAPL | … | … | … | … | … |

Rows are sorted by `(timestamp, symbol)`. Duplicate keys are invalid. Prices must be positive, volume ≥ 0, high must actually be the high, low the low.

After a successful load, the panel is written to Parquet and hashed. The hash (fingerprint) is a SHA-256 of a canonical CSV of the table. If two runs produce the same fingerprint, they used the same bars. If a close ticks by a cent, the hash changes.

DuckDB reads that Parquet in place. You do not need a warehouse.

**Demo**

```bash
python -m pip install -r requirements.txt

python scripts/run_backtest.py \
  --config configs/base.yaml \
  --start 2020-01-01 \
  --end 2020-03-31 \
  --symbols AAPL MSFT
```

You should see row counts, the date range, a fingerprint, and a path like `data/processed/bars/bars.parquet`. Raw downloads cache under `data/raw/yfinance/` as per-symbol parquet files so a second run in the same window does not hit the network again.

From Python:

```python
from qtrading.data import BarStore, YFinanceDataPipeline, build_metadata

pipeline = YFinanceDataPipeline(cache_dir="data/raw/yfinance")
bars = pipeline.load_bars(
    universe=["AAPL", "MSFT"],
    start="2020-01-01",
    end="2020-03-31",
)
bars.validate()

meta = build_metadata(data=bars.data, source="yfinance")
store = BarStore(root="data/processed/bars")
store.write(bars, meta)

print(meta.fingerprint)
print(store.query("SELECT symbol, COUNT(*) AS n FROM bars GROUP BY 1 ORDER BY 1"))
```

Tests for this path (and the lag/label checks) do not call yfinance:

```bash
pytest tests/test_data_pipeline.py tests/test_timing_contracts.py
```

---

## 2. Features

Features are panel columns aligned to the same `(timestamp, symbol)` index as the bars. They are built only from history available at that timestamp.

The set:

- **returns** — 1-day and multi-day
- **momentum** — trailing return over a lookback
- **volatility** — rolling std of returns
- **rolling z-score** — (x − rolling mean) / rolling std
- **rolling beta** — vs a market or equal-weight basket
- **volume features** — relative volume, volume z-score
- **cross-sectional ranks** — rank of a feature across names *on that day only*

Cross-sectional ranks are easy to get wrong: ranking using the whole sample (including later days) is leakage. Ranks happen date by date.

---

## 3. Labels

Labels are configurable forward returns. If `horizon_days = 5` in `configs/base.yaml`, the label at `t` is the return from `t` to `t+5`.

Prediction time and label time are not the same object. You score with information as of `t`; the outcome realizes at `t + horizon`. That split is what the leakage tests enforce.

---

## 4. Validation (research, not just unit tests)

Random K-fold CV on a price panel is usually cheating: adjacent days are dependent, and a “test” fold can sit in the middle of training.

The intended splitters:

- **expanding walk-forward** — train on everything up to a cut, test the next window, then grow the train set
- **rolling walk-forward** — fixed-length train window that slides
- **purging** — drop train observations whose labels overlap the test period
- **embargo** — leave a gap after the test window before the next train sample

Those sit next to the existing lag/forward-return unit tests.

---

## 5. Models

Three approaches, same features and labels, same splits, so the comparison is actually a comparison:

1. **Momentum baseline** — no fitting; the signal *is* a momentum feature. This is the “did we beat something dumb?” line.
2. **Elastic Net** — linear, regularized, readable coefficients.
3. **XGBoost** — non-linear, still tabular, still trained only inside each walk-forward fold.

No deep learning in this version. The interesting question is whether extra flexibility survives costs and a honest split, not whether a bigger model can overfit 2015–2019.

---

## 6. Portfolio

Signals are not trades. The portfolio layer turns a cross-section of scores into weights.

- equal weight among names that pass a simple long/short or long-only rule
- signal weighting (score / sum of abs scores)
- **CVXPY** optimization with covariance, max position, leverage, and a turnover penalty so the book does not thrash

`configs/base.yaml` already carries `max_positions`, `max_gross_exposure`, `allow_short`, and cost assumptions. Those are the knobs the optimizer and the backtest should read.

---

## 7. Backtest

Daily (or rebalance-cadence) accounting:

- apply target weights
- charge **transaction costs** and a **simple slippage** model (bps in config)
- track **turnover**
- mark cash and positions to close

This is not a limit-order simulator. It is enough to stop a research result that only exists with zero costs.

---

## 8. Evaluation

Reported numbers, computed from the backtest — not typed in by hand:

- IC and rank IC (signal vs subsequent return)
- Sharpe, volatility, max drawdown
- turnover
- cumulative / total return

If a chart or table shows up in `reports/` or `docs/`, it should come from a command you can rerun.

---

## 9. Experiments

The same machinery, different questions:

- random CV vs walk-forward (how much of the “edge” was leakage)
- momentum vs Elastic Net vs XGBoost on the same panel
- cost sensitivity (0 bps vs 5 vs 10)
- feature ablation (drop volume, drop beta, …)

Configs under `configs/experiments/` are the place to pin those runs. Example: `configs/experiments/mvp_daily_ls_wproxy.yaml`.

---

## Config

`configs/base.yaml` is the default. It names the data source, a static universe kind, daily frequency, a 5-day label horizon, a 1-day feature lag, a 5-day rebalance, 5 bps slippage, and position limits.

Override symbols and dates on the CLI without editing YAML:

```bash
python scripts/run_backtest.py \
  --config configs/experiments/mvp_daily_ls_wproxy.yaml \
  --start 2018-01-01 \
  --end 2019-12-31 \
  --symbols AAPL MSFT AMZN GOOGL NVDA \
  --store data/processed/bars
```

---

## What this is not

This is a local research codebase. It is not a REST API, a React app, a streaming stack, or a cloud deployment. Those would be a different product. The depth here is in the panel, the clock, and the backtest.

---

## More detail

Data contract and on-disk layout: [`docs/data_pipeline.md`](docs/data_pipeline.md)
