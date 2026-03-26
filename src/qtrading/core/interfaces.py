from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Protocol

from .types import (
    BacktestResult,
    BarFrame,
    FeatureFrame,
    Fill,
    Order,
    PositionSnapshot,
    SignalFrame,
)


class DataPipeline(ABC):
    @abstractmethod
    def load_bars(
        self,
        *,
        universe: Iterable[str],
        start: Any,
        end: Any,
    ) -> BarFrame:
        raise NotImplementedError


class FeatureEngineer(ABC):
    @abstractmethod
    def make_features(self, *, bars: BarFrame, as_of: Any) -> FeatureFrame:
        raise NotImplementedError


class SignalModel(ABC):
    @abstractmethod
    def predict(self, *, features: FeatureFrame) -> SignalFrame:
        raise NotImplementedError


class SignalFusion(ABC):
    @abstractmethod
    def fuse(self, *, signals: SignalFrame) -> SignalFrame:
        raise NotImplementedError


class PortfolioConstructor(ABC):
    @abstractmethod
    def construct_orders(
        self,
        *,
        as_of: Any,
        fused_signals: SignalFrame,
        positions: PositionSnapshot,
        cash: float,
    ) -> list[Order]:
        raise NotImplementedError


class ExecutionSimulator(ABC):
    @abstractmethod
    def execute(
        self,
        *,
        as_of: Any,
        orders: list[Order],
        bars_at_execution: BarFrame,
    ) -> list[Fill]:
        raise NotImplementedError


class BacktestEngine(ABC):
    @abstractmethod
    def run(self, *, start: Any, end: Any, config: Any) -> BacktestResult:
        raise NotImplementedError


class Evaluator(ABC):
    @abstractmethod
    def evaluate(self, *, result: BacktestResult) -> dict[str, float]:
        raise NotImplementedError


class SupportsClose(Protocol):
    def close(self) -> None: ...

