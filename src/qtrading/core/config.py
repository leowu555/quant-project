from __future__ import annotations

from typing import Any, Literal


def _optional_pydantic_import() -> tuple[Any, Any]:
    try:
        from pydantic import BaseModel, Field  # type: ignore

        return BaseModel, Field
    except ModuleNotFoundError:  # pragma: no cover
        # Allow the contracts/config module to be imported in minimal
        # environments (like this sandbox) where runtime deps are not installed.
        BaseModel = object  # type: ignore

        def Field(
            default: Any = None,
            *,
            default_factory: Any = None,
            **_kwargs: Any,
        ) -> Any:  # type: ignore
            if default_factory is not None:
                return default_factory()
            return default

        return BaseModel, Field


BaseModel, Field = _optional_pydantic_import()


class DataSourceConfig(BaseModel):
    source: Literal["yfinance"] = "yfinance"
    cache_dir: str = "data/raw"


class UniverseConfig(BaseModel):
    # MVP: static membership (membership history is postponed).
    kind: Literal["sp500100_static"] = "sp500100_static"


class CostAssumptions(BaseModel):
    # MVP placeholders; execution/backtest engines will interpret these.
    commission_per_share: float = 0.0
    slippage_bps: float = 0.0


class PortfolioConstraints(BaseModel):
    max_positions: int = 25
    max_gross_exposure: float = 1.0
    allow_short: bool = False


class MVPConfig(BaseModel):
    """
    Step 1: daily-first MVP configuration.

    This config is designed to be loaded from YAML and validated.
    """

    experiment_name: str = "mvp_daily"

    # Data & sampling
    data: DataSourceConfig = Field(default_factory=DataSourceConfig)
    universe: UniverseConfig = Field(default_factory=UniverseConfig)
    frequency: Literal["1d"] = "1d"

    # Labeling / horizon semantics
    horizon_days: int = 5
    feature_lag_days: int = 1

    # Trading cadence
    rebalance_cadence_days: int = 5

    # Costs and portfolio constraints
    costs: CostAssumptions = Field(default_factory=CostAssumptions)
    constraints: PortfolioConstraints = Field(default_factory=PortfolioConstraints)

    # Arbitrary additional knobs for Step 1 stubs.
    model: dict[str, Any] = Field(default_factory=dict)

