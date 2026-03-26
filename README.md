# Quant Project

Institutional quant research framework (MVP).

## Quick start

1. Create a virtual environment and install dependencies:
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

This repo is organized around layered institutional-style components (data, features, signals, fusion, portfolio, execution, backtesting, evaluation). Step 1 focuses on clean contracts and timing/leakage safety.