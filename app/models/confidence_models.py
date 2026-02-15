"""ATLAS Confidence-Based Autonomy modelleri.

Guven tabanli otonom karar veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Guven seviyesi."""

    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class AutonomyAction(str, Enum):
    """Otonomi aksiyonu."""

    AUTO_EXECUTE = "auto_execute"
    SUGGEST = "suggest"
    ASK_HUMAN = "ask_human"
    REJECT = "reject"
    ESCALATE = "escalate"


class TrustLevel(str, Enum):
    """Guven duzeyi."""

    FULL = "full"
    HIGH = "high"
    MODERATE = "moderate"
    LIMITED = "limited"
    NONE = "none"


class EscalationUrgency(str, Enum):
    """Eskalasyon aciliyeti."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class CalibrationStatus(str, Enum):
    """Kalibrasyon durumu."""

    WELL_CALIBRATED = "well_calibrated"
    OVERCONFIDENT = "overconfident"
    UNDERCONFIDENT = "underconfident"
    INSUFFICIENT_DATA = "insufficient_data"
    NEEDS_RECALIBRATION = "needs_recalibration"


class FeedbackType(str, Enum):
    """Geri bildirim tipi."""

    APPROVAL = "approval"
    REJECTION = "rejection"
    CORRECTION = "correction"
    PREFERENCE = "preference"
    OVERRIDE = "override"
    IGNORE = "ignore"


class ConfidenceRecord(BaseModel):
    """Guven kaydi."""

    record_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    action_id: str = ""
    score: float = 0.0
    level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    factors: dict = Field(default_factory=dict)
    domain: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class TrustRecord(BaseModel):
    """Guven kaydi."""

    trust_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    domain: str = ""
    level: TrustLevel = TrustLevel.MODERATE
    score: float = 0.5
    history_count: int = 0
    metadata: dict = Field(default_factory=dict)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class EscalationRecord(BaseModel):
    """Eskalasyon kaydi."""

    escalation_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    action_id: str = ""
    urgency: EscalationUrgency = (
        EscalationUrgency.MEDIUM
    )
    target: str = ""
    reason: str = ""
    status: str = "pending"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ConfidenceSnapshot(BaseModel):
    """Guven snapshot."""

    total_decisions: int = 0
    auto_executed: int = 0
    suggested: int = 0
    asked_human: int = 0
    avg_confidence: float = 0.0
    avg_accuracy: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
