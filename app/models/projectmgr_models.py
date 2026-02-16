"""ATLAS Project & Deadline Manager modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Proje durumu."""

    DRAFT = "draft"
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MilestoneStatus(str, Enum):
    """Kilometre taşı durumu."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    SKIPPED = "skipped"


class BlockerSeverity(str, Enum):
    """Engel ciddiyeti."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationLevel(str, Enum):
    """Eskalasyon seviyesi."""

    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"
    CRITICAL = "critical"


class ReportFormat(str, Enum):
    """Rapor formatı."""

    SUMMARY = "summary"
    DETAILED = "detailed"
    EXECUTIVE = "executive"
    BURNDOWN = "burndown"


class ResourceType(str, Enum):
    """Kaynak tipi."""

    DEVELOPER = "developer"
    DESIGNER = "designer"
    MANAGER = "manager"
    ANALYST = "analyst"
    TESTER = "tester"
    OTHER = "other"


class ProjectRecord(BaseModel):
    """Proje kaydı."""

    project_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    health_score: float = 100.0
    owner: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class MilestoneRecord(BaseModel):
    """Kilometre taşı kaydı."""

    milestone_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    project_id: str = ""
    name: str = ""
    status: MilestoneStatus = MilestoneStatus.PENDING
    progress: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class BlockerRecord(BaseModel):
    """Engel kaydı."""

    blocker_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    project_id: str = ""
    description: str = ""
    severity: BlockerSeverity = BlockerSeverity.MEDIUM
    resolved: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class EscalationRecord(BaseModel):
    """Eskalasyon kaydı."""

    escalation_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    level: EscalationLevel = EscalationLevel.WARNING
    reason: str = ""
    resolved: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
