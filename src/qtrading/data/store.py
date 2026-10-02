from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qtrading.core.types import BarFrame
from qtrading.data.fingerprint import DatasetMetadata
from qtrading.data.validation import assert_valid_bars


def _require_pandas() -> Any:
    import pandas as pd

    return pd


def _require_duckdb() -> Any:
    try:
        import duckdb
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "duckdb is required for BarStore. "
            "Install deps with: python -m pip install -r requirements.txt"
        ) from e
    return duckdb


@dataclass(slots=True)
class BarStore:
    """
    Persist validated bars as Parquet and query them with DuckDB.

    Layout:
      <root>/bars.parquet
      <root>/metadata.json
    """

    root: str | Path = Path("data/processed/bars")

    @property
    def parquet_path(self) -> Path:
        return Path(self.root) / "bars.parquet"

    @property
    def metadata_path(self) -> Path:
        return Path(self.root) / "metadata.json"

    def write(self, bars: BarFrame, metadata: DatasetMetadata) -> Path:
        import json

        assert_valid_bars(bars.data)
        Path(self.root).mkdir(parents=True, exist_ok=True)

        frame = bars.data.copy()
        frame.index.name = "timestamp"
        try:
            frame.to_parquet(self.parquet_path, index=True)
        except ImportError as e:
            raise ModuleNotFoundError(
                "pyarrow (or fastparquet) is required to write Parquet. "
                "Install deps with: python -m pip install -r requirements.txt"
            ) from e

        self.metadata_path.write_text(json.dumps(metadata.to_dict(), indent=2) + "\n")
        return self.parquet_path

    def read(self) -> tuple[BarFrame, dict[str, Any]]:
        import json

        pd = _require_pandas()
        if not self.parquet_path.exists():
            raise FileNotFoundError(f"missing parquet dataset: {self.parquet_path}")

        data = pd.read_parquet(self.parquet_path)
        if "timestamp" in data.columns and data.index.name == "timestamp":
            data = data.drop(columns=["timestamp"])
        elif "timestamp" in data.columns:
            data = data.set_index("timestamp")
        data.index.name = "timestamp"
        data.index = pd.to_datetime(data.index, utc=True)
        data = data.sort_values("symbol", kind="mergesort").sort_index(kind="mergesort")
        assert_valid_bars(data)

        meta: dict[str, Any] = {}
        if self.metadata_path.exists():
            meta = json.loads(self.metadata_path.read_text())

        return BarFrame(data=data, timezone="UTC"), meta

    def query(self, sql: str) -> Any:
        """
        Run DuckDB SQL against the stored parquet.

        The parquet file is available as table `bars`.
        """
        duckdb = _require_duckdb()
        if not self.parquet_path.exists():
            raise FileNotFoundError(f"missing parquet dataset: {self.parquet_path}")
        con = duckdb.connect(database=":memory:")
        try:
            con.execute(
                f"CREATE VIEW bars AS SELECT * FROM read_parquet('{self.parquet_path.as_posix()}')"
            )
            return con.execute(sql).df()
        finally:
            con.close()
