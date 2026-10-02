from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _require_yaml() -> Any:
    try:
        import yaml
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "pyyaml is required to load config files. "
            "Install deps with: python -m pip install -r requirements.txt"
        ) from e
    return yaml


def _load_config(path: Path) -> dict[str, Any]:
    yaml = _require_yaml()
    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config at '{path}' must parse to a mapping/object.")
    return raw


def _default_symbols(universe_kind: str) -> list[str]:
    if universe_kind == "sp500100_static":
        return ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA"]
    return ["AAPL", "MSFT"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V1 data-stage runner: fetch, validate, fingerprint, and persist bars.",
    )
    parser.add_argument("--config", type=Path, default=Path("configs/base.yaml"))
    parser.add_argument("--start", type=str, default="2020-01-01")
    parser.add_argument("--end", type=str, default="2020-12-31")
    parser.add_argument("--symbols", nargs="*", default=None)
    parser.add_argument(
        "--store",
        type=Path,
        default=Path("data/processed/bars"),
        help="Directory for Parquet + metadata output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = _load_config(args.config)

    data_cfg = config.get("data", {})
    universe_cfg = config.get("universe", {})
    source = data_cfg.get("source", "yfinance")
    if source != "yfinance":
        raise NotImplementedError(
            f"Only yfinance is implemented in V1; got '{source}'."
        )

    cache_dir = Path(data_cfg.get("cache_dir", "data/raw")) / "yfinance"
    symbols = args.symbols or _default_symbols(universe_cfg.get("kind", ""))

    from qtrading.data import BarStore, YFinanceDataPipeline, build_metadata

    pipeline = YFinanceDataPipeline(cache_dir=cache_dir)
    bars = pipeline.load_bars(universe=symbols, start=args.start, end=args.end)
    bars.validate()

    metadata = build_metadata(
        data=bars.data,
        source="yfinance",
        extra={
            "config": str(args.config),
            "requested_start": args.start,
            "requested_end": args.end,
            "requested_symbols": symbols,
        },
    )
    store = BarStore(root=args.store)
    parquet_path = store.write(bars, metadata)

    print(f"rows={metadata.n_rows} symbols={metadata.n_symbols}")
    print(f"range={metadata.start} -> {metadata.end}")
    print(f"fingerprint={metadata.fingerprint}")
    print(f"parquet={parquet_path}")
    print(bars.data.head(5))
    print(
        "Data stage complete. Feature engineering and later V1 subsystems "
        "are not implemented yet."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
