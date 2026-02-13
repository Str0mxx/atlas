"""ATLAS Self-Evolution veri modelleri.

Kendi kendini gelistiren otonom AI icin enum ve Pydantic modelleri:
performans izleme, zayiflik tespiti, iyilestirme planlama,
kod evrimi, guvenlik koruma, deney yonetimi, onay ve ogrenme.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# === Enum'lar ===


class ChangeSeverity(str, Enum):
    """Degisiklik siddeti."""

    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    """Onay durumu."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    AUTO_APPROVED = "auto_approved"


class EvolutionPhase(str, Enum):
    """Evrim asamasi."""

    OBSERVING = "observing"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    APPROVING = "approving"
    DEPLOYING = "deploying"
    COMPLETE = "complete"
    FAILED = "failed"
    PAUSED = "paused"


class WeaknessType(str, Enum):
    """Zayiflik tipi."""

    FAILURE = "failure"
    SLOW_OPERATION = "slow_operation"
    MISSING_CAPABILITY = "missing_capability"
    ERROR_HOTSPOT = "error_hotspot"
    USER_COMPLAINT = "user_complaint"
    RESOURCE_WASTE = "resource_waste"


class ExperimentStatus(str, Enum):
    """Deney durumu."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class ImprovementType(str, Enum):
    """Iyilestirme tipi."""

    BUG_FIX = "bug_fix"
    PERFORMANCE = "performance"
    NEW_CAPABILITY = "new_capability"
    REFACTOR = "refactor"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"


class EvolutionCycleType(str, Enum):
    """Evrim dongusu tipi."""

    DAILY = "daily"
    WEEKLY = "weekly"
    ON_DEMAND = "on_demand"
    EMERGENCY = "emergency"


class TrendDirection(str, Enum):
    """Trend yonu."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


# === Modeller ===


class PerformanceMetric(BaseModel):
    """Performans metrigi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str = ""
    task_type: str = ""
    success_count: int = 0
    failure_count: int = 0
    total_count: int = 0
    avg_response_ms: float = 0.0
    p95_response_ms: float = 0.0
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    period_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime | None = None
    trend: TrendDirection = TrendDirection.STABLE


class WeaknessReport(BaseModel):
    """Zayiflik raporu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    weakness_type: WeaknessType = WeaknessType.FAILURE
    component: str = ""
    description: str = ""
    severity: ChangeSeverity = ChangeSeverity.MINOR
    frequency: int = 1
    impact_score: float = Field(default=0.0, ge=0.0, le=10.0)
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    examples: list[str] = Field(default_factory=list)
    suggested_fix: str = ""


class ImprovementPlan(BaseModel):
    """Iyilestirme plani."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = ""
    improvement_type: ImprovementType = ImprovementType.BUG_FIX
    target_component: str = ""
    description: str = ""
    expected_impact: float = Field(default=0.0, ge=0.0, le=10.0)
    estimated_effort: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_level: ChangeSeverity = ChangeSeverity.MINOR
    dependencies: list[str] = Field(default_factory=list)
    priority_score: float = Field(default=0.0, ge=0.0, le=100.0)
    steps: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CodeChange(BaseModel):
    """Kod degisikligi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    file_path: str = ""
    change_type: str = ""
    diff: str = ""
    description: str = ""
    severity: ChangeSeverity = ChangeSeverity.MINOR
    version: int = 1
    rollback_data: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SafetyCheckResult(BaseModel):
    """Guvenlik kontrol sonucu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    change_id: str = ""
    severity: ChangeSeverity = ChangeSeverity.MINOR
    is_safe: bool = True
    requires_approval: bool = False
    issues: list[str] = Field(default_factory=list)
    resource_impact: dict[str, float] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExperimentResult(BaseModel):
    """Deney sonucu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    experiment_name: str = ""
    status: ExperimentStatus = ExperimentStatus.PENDING
    baseline_score: float = 0.0
    variant_score: float = 0.0
    improvement_pct: float = 0.0
    sample_size: int = 0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    """Onay istegi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    change_id: str = ""
    title: str = ""
    description: str = ""
    severity: ChangeSeverity = ChangeSeverity.MAJOR
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: datetime | None = None
    responder: str = ""
    timeout_hours: int = 24
    batch_id: str = ""


class LearnedPattern(BaseModel):
    """Ogrenilmis kalip."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    pattern_name: str = ""
    category: str = ""
    description: str = ""
    solution: str = ""
    success_count: int = 0
    applicability_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_components: list[str] = Field(default_factory=list)
    learned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_applied: datetime | None = None


class EvolutionCycle(BaseModel):
    """Evrim dongusu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    cycle_type: EvolutionCycleType = EvolutionCycleType.DAILY
    phase: EvolutionPhase = EvolutionPhase.OBSERVING
    weaknesses_found: int = 0
    improvements_planned: int = 0
    changes_applied: int = 0
    changes_auto_approved: int = 0
    changes_human_approved: int = 0
    changes_rejected: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    paused: bool = False
