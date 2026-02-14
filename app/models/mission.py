"""ATLAS Mission Control modelleri.

Buyuk gorev yonetimi, faz kontrolu, kaynak komutanligi,
ilerleme takibi, durum odasi ve raporlama modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MissionState(str, Enum):
    """Gorev durumu."""

    DRAFT = "draft"
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETING = "completing"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class PhaseState(str, Enum):
    """Faz durumu."""

    PENDING = "pending"
    READY = "ready"
    ACTIVE = "active"
    REVIEW = "review"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class MilestoneState(str, Enum):
    """Kilometre tasi durumu."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MISSED = "missed"
    DEFERRED = "deferred"


class AlertSeverity(str, Enum):
    """Uyari siddet seviyesi."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ContingencyType(str, Enum):
    """Olasilik plani tipi."""

    PLAN_B = "plan_b"
    RECOVERY = "recovery"
    ABORT = "abort"
    DEGRADATION = "degradation"
    ESCALATION = "escalation"


class ReportType(str, Enum):
    """Rapor tipi."""

    STATUS = "status"
    EXECUTIVE = "executive"
    DETAILED = "detailed"
    POST_MISSION = "post_mission"
    MILESTONE = "milestone"


class MissionDefinition(BaseModel):
    """Gorev tanimi."""

    mission_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    description: str = ""
    state: MissionState = MissionState.DRAFT
    goal: str = ""
    success_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    priority: int = Field(default=5, ge=1, le=10)
    timeline_hours: float = 0.0
    budget: float = 0.0
    budget_used: float = 0.0
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PhaseDefinition(BaseModel):
    """Faz tanimi."""

    phase_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    mission_id: str = ""
    name: str = ""
    description: str = ""
    state: PhaseState = PhaseState.PENDING
    order: int = 0
    dependencies: list[str] = Field(default_factory=list)
    gate_criteria: list[str] = Field(default_factory=list)
    assigned_agents: list[str] = Field(default_factory=list)
    parallel: bool = False
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class MilestoneDefinition(BaseModel):
    """Kilometre tasi tanimi."""

    milestone_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    mission_id: str = ""
    phase_id: str = ""
    name: str = ""
    state: MilestoneState = MilestoneState.PENDING
    target_date: datetime | None = None
    completed_at: datetime | None = None


class ResourceAssignment(BaseModel):
    """Kaynak atamasi."""

    assignment_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    mission_id: str = ""
    resource_id: str = ""
    resource_type: str = "agent"
    allocated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    released_at: datetime | None = None
    utilization: float = Field(default=0.0, ge=0.0, le=1.0)


class MissionAlert(BaseModel):
    """Gorev uyarisi."""

    alert_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    mission_id: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    source: str = ""
    acknowledged: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ContingencyPlan(BaseModel):
    """Olasilik plani."""

    plan_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    mission_id: str = ""
    contingency_type: ContingencyType = ContingencyType.PLAN_B
    trigger_condition: str = ""
    actions: list[str] = Field(default_factory=list)
    activated: bool = False
    activated_at: datetime | None = None


class MissionReport(BaseModel):
    """Gorev raporu."""

    report_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    mission_id: str = ""
    report_type: ReportType = ReportType.STATUS
    title: str = ""
    content: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class MissionSnapshot(BaseModel):
    """Gorev kontrol anlik goruntusu."""

    total_missions: int = 0
    active_missions: int = 0
    completed_missions: int = 0
    total_phases: int = 0
    active_phases: int = 0
    total_milestones: int = 0
    completed_milestones: int = 0
    active_alerts: int = 0
    avg_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
