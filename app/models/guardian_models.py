"""ATLAS Health & Uptime Guardian modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Sağlık durumu."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class IncidentSeverity(str, Enum):
    """Olay ciddiyeti."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SLAStatus(str, Enum):
    """SLA durumu."""

    COMPLIANT = "compliant"
    AT_RISK = "at_risk"
    BREACHED = "breached"


class ScaleDirection(str, Enum):
    """Ölçekleme yönü."""

    UP = "up"
    DOWN = "down"
    NONE = "none"


class RecoveryStatus(str, Enum):
    """Kurtarma durumu."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    PENDING = "pending"


class DegradationRisk(str, Enum):
    """Bozulma riski."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class HealthCheckRecord(BaseModel):
    """Sağlık kontrolü kaydı."""

    check_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    component: str = ""
    status: str = "unknown"
    response_time_ms: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class IncidentRecord(BaseModel):
    """Olay kaydı."""

    incident_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    severity: str = "medium"
    component: str = ""
    description: str = ""
    resolved: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class SLARecord(BaseModel):
    """SLA kaydı."""

    sla_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    service: str = ""
    target: float = 99.9
    actual: float = 100.0
    status: str = "compliant"
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
    incident_id: str = ""
    action: str = ""
    status: str = "pending"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
