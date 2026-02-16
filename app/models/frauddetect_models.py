"""ATLAS Anomaly & Fraud Detector modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class AnomalyType(str, Enum):
    """Anomali tipi."""

    STATISTICAL = "statistical"
    BEHAVIORAL = "behavioral"
    TEMPORAL = "temporal"
    STRUCTURAL = "structural"


class FraudSeverity(str, Enum):
    """Dolandırıcılık ciddiyeti."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertPriority(str, Enum):
    """Uyarı önceliği."""

    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class DetectionMethod(str, Enum):
    """Tespit yöntemi."""

    RULE_BASED = "rule_based"
    ML_BASED = "ml_based"
    STATISTICAL = "statistical"
    HYBRID = "hybrid"


class RiskLevel(str, Enum):
    """Risk seviyesi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class IncidentStatus(str, Enum):
    """Olay durumu."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"


class AnomalyRecord(BaseModel):
    """Anomali kaydı."""

    anomaly_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    source: str = ""
    anomaly_type: str = "statistical"
    severity: str = "medium"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class FraudAlertRecord(BaseModel):
    """Dolandırıcılık uyarı kaydı."""

    alert_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    priority: str = "p3"
    pattern: str = ""
    risk_score: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class FraudIncidentRecord(BaseModel):
    """Dolandırıcılık olay kaydı."""

    incident_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    severity: str = "medium"
    status: str = "open"
    description: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class RiskScoreRecord(BaseModel):
    """Risk puanı kaydı."""

    score_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    entity: str = ""
    score: float = 0.0
    level: str = "low"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
