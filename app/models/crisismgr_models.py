"""ATLAS Disaster & Crisis Management modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class CrisisLevel(str, Enum):
    """Kriz seviyesi."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class CrisisStatus(str, Enum):
    """Kriz durumu."""

    DETECTED = "detected"
    ESCALATED = "escalated"
    ACTIVE = "active"
    RECOVERING = "recovering"


class EscalationTier(str, Enum):
    """Eskalasyon katmanı."""

    TIER1 = "tier1"
    TIER2 = "tier2"
    TIER3 = "tier3"
    EXECUTIVE = "executive"


class NotificationChannel(str, Enum):
    """Bildirim kanalı."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"


class RecoveryPhase(str, Enum):
    """Kurtarma aşaması."""

    CONTAINMENT = "containment"
    MITIGATION = "mitigation"
    RESTORATION = "restoration"
    VERIFICATION = "verification"


class SimulationType(str, Enum):
    """Simülasyon tipi."""

    TABLETOP = "tabletop"
    FUNCTIONAL = "functional"
    FULL_SCALE = "full_scale"
    DRILL = "drill"


class CrisisRecord(BaseModel):
    """Kriz kaydı."""

    crisis_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    title: str = ""
    level: str = "moderate"
    status: str = "detected"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class EscalationRecord(BaseModel):
    """Eskalasyon kaydı."""

    escalation_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    crisis_id: str = ""
    tier: str = "tier1"
    responder: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ActionPlanRecord(BaseModel):
    """Aksiyon planı kaydı."""

    plan_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    crisis_id: str = ""
    task_count: int = 0
    status: str = "draft"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class RecoveryRecord(BaseModel):
    """Kurtarma kaydı."""

    recovery_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    crisis_id: str = ""
    phase: str = "containment"
    progress_pct: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
