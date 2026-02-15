"""ATLAS Closed-Loop Execution Tracking modelleri.

Aksiyon-sonuc-ogrenme dongusu veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ActionStatus(str, Enum):
    """Aksiyon durumu."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutcomeType(str, Enum):
    """Sonuc tipi."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class FeedbackSource(str, Enum):
    """Geri bildirim kaynagi."""

    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    SYSTEM = "system"
    EXTERNAL = "external"
    AUTOMATED = "automated"


class CausalConfidence(str, Enum):
    """Nedensellik guven seviyesi."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"
    NONE = "none"


class ExperimentStatus(str, Enum):
    """Deney durumu."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ImprovementPriority(str, Enum):
    """Iyilestirme onceligi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"


class ActionRecord(BaseModel):
    """Aksiyon kaydi."""

    action_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    status: ActionStatus = ActionStatus.PENDING
    context: dict = Field(default_factory=dict)
    parent_action_id: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class OutcomeRecord(BaseModel):
    """Sonuc kaydi."""

    outcome_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    action_id: str = ""
    outcome_type: OutcomeType = OutcomeType.UNKNOWN
    metrics: dict = Field(default_factory=dict)
    side_effects: list = Field(default_factory=list)
    confidence: float = 0.0
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ExperimentRecord(BaseModel):
    """Deney kaydi."""

    experiment_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    hypothesis: str = ""
    status: ExperimentStatus = ExperimentStatus.DRAFT
    variants: list = Field(default_factory=list)
    results: dict = Field(default_factory=dict)
    duration_hours: int = 24
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ClosedLoopSnapshot(BaseModel):
    """Kapali dongu snapshot."""

    total_actions: int = 0
    outcomes_detected: int = 0
    learnings_count: int = 0
    improvements_applied: int = 0
    active_experiments: int = 0
    avg_confidence: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
