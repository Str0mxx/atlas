"""ATLAS Scenario Planning & War Gaming modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ScenarioType(str, Enum):
    """Senaryo tipi."""

    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"
    REALISTIC = "realistic"
    EXPLORATORY = "exploratory"
    STRESS_TEST = "stress_test"


class ImpactLevel(str, Enum):
    """Etki seviyesi."""

    NEGLIGIBLE = "negligible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class StrategyType(str, Enum):
    """Strateji tipi."""

    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    BALANCED = "balanced"
    OPPORTUNISTIC = "opportunistic"
    CONSERVATIVE = "conservative"


class SimulationStatus(str, Enum):
    """Simülasyon durumu."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskTolerance(str, Enum):
    """Risk toleransı."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class GameOutcome(str, Enum):
    """Oyun sonucu."""

    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    PARTIAL_WIN = "partial_win"
    UNDETERMINED = "undetermined"


class ScenarioRecord(BaseModel):
    """Senaryo kaydı."""

    scenario_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    scenario_type: ScenarioType = (
        ScenarioType.REALISTIC
    )
    probability: float = 0.0
    impact_level: ImpactLevel = (
        ImpactLevel.MODERATE
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class SimulationRecord(BaseModel):
    """Simülasyon kaydı."""

    simulation_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    scenario_id: str = ""
    status: SimulationStatus = (
        SimulationStatus.PENDING
    )
    iterations: int = 0
    outcome: GameOutcome = (
        GameOutcome.UNDETERMINED
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class DecisionRecord(BaseModel):
    """Karar kaydı."""

    decision_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    scenario_id: str = ""
    strategy_type: StrategyType = (
        StrategyType.BALANCED
    )
    risk_tolerance: RiskTolerance = (
        RiskTolerance.MEDIUM
    )
    expected_value: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class WarGameRecord(BaseModel):
    """Savaş oyunu kaydı."""

    game_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    players: list[str] = Field(
        default_factory=list,
    )
    rounds: int = 0
    outcome: GameOutcome = (
        GameOutcome.UNDETERMINED
    )
    winner: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None
