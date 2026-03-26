from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


InstrumentId = str
Side = Literal["buy", "sell"]
OrderType = Literal["market", "limit"]


@dataclass(frozen=True, slots=True)
class BarFrame:
    """
    Canonical bar container.

    Contract (MVP daily-first):
    - `data` is a DataFrame indexed by timestamp.
    - Columns are expected to contain at least:
      `open`, `high`, `low`, `close`, `volume`
    - Rows represent observations available at that timestamp.
    """

    # Keep runtime import requirements minimal (pandas is a dependency, but
    # should not be required just to import the contracts).
    data: Any
    timezone: str | None = None

    def validate(self) -> None:
        required = {"open", "high", "low", "close", "volume"}
        missing = required.difference(set(self.data.columns))
        if missing:
            raise ValueError(f"BarFrame missing columns: {sorted(missing)}")


@dataclass(frozen=True, slots=True)
class FeatureFrame:
    """
    Feature container aligned to an `as_of` timestamp.

    Contract:
    - `data` rows correspond to instruments observed at `as_of`.
    - Columns are feature names.
    """

    as_of: Any
    data: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SignalFrame:
    """
    Signal container aligned to an `as_of` timestamp.

    Contract:
    - `data` rows correspond to instruments.
    - Columns are signal names (e.g., "momentum", "value_score").
    """

    as_of: Any
    data: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    timestamp: Any
    instrument: InstrumentId
    side: Side
    quantity: float
    order_type: OrderType = "market"
    limit_price: float | None = None


@dataclass(frozen=True, slots=True)
class Fill:
    fill_id: str
    timestamp: Any
    order_id: str
    instrument: InstrumentId
    quantity_filled: float
    price: float
    fee: float = 0.0


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    """
    Position state at a specific timestamp.

    Contract (MVP):
    - `positions` maps instrument id -> quantity
    - `cash` is uninvested cash at `timestamp`
    """

    timestamp: Any
    positions: dict[InstrumentId, float]
    cash: float = 0.0


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """
    Output of a backtest run.

    Contract:
    - `equity_curve` indexed by timestamp, representing portfolio equity.
    - `metrics` contains evaluation outputs (sharpe, drawdown, etc.).
    """

    start: Any
    end: Any
    equity_curve: Any
    metrics: dict[str, float] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)

