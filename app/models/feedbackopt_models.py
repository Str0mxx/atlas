"""ATLAS Feedback Loop Optimizer modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class SatisfactionLevel(str, Enum):
    """Memnuniyet seviyesi."""

    DELIGHTED = "delighted"
    SATISFIED = "satisfied"
    NEUTRAL = "neutral"
    DISSATISFIED = "dissatisfied"
    FRUSTRATED = "frustrated"


class CorrelationStrength(str, Enum):
    """İlişki gücü."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


class ExperimentStatus(str, Enum):
    """Deney durumu."""

    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ImpactLevel(str, Enum):
    """Etki seviyesi."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class TuningAction(str, Enum):
    """Ayarlama eylemi."""

    INCREASE = "increase"
    DECREASE = "decrease"
    KEEP = "keep"
    ROLLBACK = "rollback"


class ImprovementStatus(str, Enum):
    """İyileştirme durumu."""

    IDENTIFIED = "identified"
    PRIORITIZED = "prioritized"
    IMPLEMENTING = "implementing"
    VERIFIED = "verified"
    DOCUMENTED = "documented"


class FeedbackRecord(BaseModel):
    """Geri bildirim kaydı."""

    feedback_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    source: str = ""
    score: float = 0.0
    sentiment: str = "neutral"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ExperimentRecord(BaseModel):
    """Deney kaydı."""

    experiment_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    hypothesis: str = ""
    status: str = "planned"
    result: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ImprovementRecord(BaseModel):
    """İyileştirme kaydı."""

    improvement_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    area: str = ""
    priority: int = 0
    status: str = "identified"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class LearningRecord(BaseModel):
    """Öğrenme kaydı."""

    learning_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    insight: str = ""
    source_system: str = ""
    applied: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
