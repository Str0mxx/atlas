"""ATLAS Otonom Hedef Takip modeli.

Hedef uretimi, deger tahmini, secim,
girisim baslatma ve ilerleme izleme modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class GoalState(str, Enum):
    """Hedef durumu."""

    CANDIDATE = "candidate"
    EVALUATING = "evaluating"
    APPROVED = "approved"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    FAILED = "failed"


class GoalPriority(str, Enum):
    """Hedef onceligi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPPORTUNISTIC = "opportunistic"


class InitiativeState(str, Enum):
    """Girisim durumu."""

    PLANNED = "planned"
    LAUNCHING = "launching"
    RUNNING = "running"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    ABORTED = "aborted"


class OpportunityType(str, Enum):
    """Firsat turu."""

    MARKET = "market"
    COST_SAVING = "cost_saving"
    EFFICIENCY = "efficiency"
    GROWTH = "growth"
    RISK_MITIGATION = "risk_mitigation"
    INNOVATION = "innovation"


class LearningType(str, Enum):
    """Ogrenme turu."""

    SUCCESS_PATTERN = "success_pattern"
    FAILURE_ANALYSIS = "failure_analysis"
    STRATEGY_INSIGHT = "strategy_insight"
    BEST_PRACTICE = "best_practice"
    ANTI_PATTERN = "anti_pattern"


class AlignmentLevel(str, Enum):
    """Hizalama seviyesi."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NEUTRAL = "neutral"
    MISALIGNED = "misaligned"


class GoalCandidate(BaseModel):
    """Hedef adayi."""

    candidate_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    title: str = ""
    description: str = ""
    opportunity_type: OpportunityType = OpportunityType.GROWTH
    source: str = ""
    expected_value: float = 0.0
    feasibility: float = Field(default=0.5, ge=0.0, le=1.0)
    alignment: AlignmentLevel = AlignmentLevel.NEUTRAL
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class GoalDefinition(BaseModel):
    """Hedef tanimi."""

    goal_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    title: str = ""
    description: str = ""
    state: GoalState = GoalState.CANDIDATE
    priority: GoalPriority = GoalPriority.MEDIUM
    success_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    estimated_value: float = 0.0
    estimated_cost: float = 0.0
    roi: float = 0.0
    deadline: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ValueEstimate(BaseModel):
    """Deger tahmini."""

    estimate_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    goal_id: str = ""
    expected_benefit: float = 0.0
    estimated_cost: float = 0.0
    roi_projection: float = 0.0
    risk_adjusted_value: float = 0.0
    time_horizon_days: int = 30
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    factors: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class Initiative(BaseModel):
    """Girisim kaydi."""

    initiative_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    goal_id: str = ""
    name: str = ""
    state: InitiativeState = InitiativeState.PLANNED
    resources: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    success_metrics: dict[str, float] = Field(default_factory=dict)
    timeline_days: int = 30
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    launched_at: datetime | None = None
    completed_at: datetime | None = None


class LearningRecord(BaseModel):
    """Ogrenme kaydi."""

    record_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    goal_id: str = ""
    learning_type: LearningType = LearningType.SUCCESS_PATTERN
    title: str = ""
    description: str = ""
    insights: list[str] = Field(default_factory=list)
    applicability: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class OpportunityScan(BaseModel):
    """Firsat taramasi."""

    scan_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    opportunity_type: OpportunityType = OpportunityType.GROWTH
    title: str = ""
    description: str = ""
    estimated_value: float = 0.0
    urgency: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = ""
    recommendations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class GoalPursuitSnapshot(BaseModel):
    """Hedef takip anlık goruntusu."""

    total_goals: int = 0
    active_goals: int = 0
    completed_goals: int = 0
    abandoned_goals: int = 0
    total_initiatives: int = 0
    active_initiatives: int = 0
    total_learnings: int = 0
    total_scans: int = 0
    avg_roi: float = 0.0
    success_rate: float = 0.0
