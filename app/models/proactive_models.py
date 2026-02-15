"""ATLAS Always-On Proactive Brain modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ScanSource(str, Enum):
    """Tarama kaynağı."""

    SYSTEM = "system"
    MARKET = "market"
    SECURITY = "security"
    PERFORMANCE = "performance"
    USER = "user"


class OpportunityType(str, Enum):
    """Fırsat tipi."""

    COST_SAVING = "cost_saving"
    REVENUE = "revenue"
    EFFICIENCY = "efficiency"
    RISK_MITIGATION = "risk_mitigation"
    GROWTH = "growth"


class AnomalySeverity(str, Enum):
    """Anomali şiddeti."""

    CRITICAL = "critical"
    WARNING = "warning"
    NOTICE = "notice"
    INFO = "info"
    NORMAL = "normal"


class ActionType(str, Enum):
    """Aksiyon tipi."""

    AUTO_HANDLE = "auto_handle"
    NOTIFY = "notify"
    ESCALATE = "escalate"
    DEFER = "defer"
    IGNORE = "ignore"


class NotificationChannel(str, Enum):
    """Bildirim kanalı."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    LOG = "log"
    DASHBOARD = "dashboard"
    SMS = "sms"


class ReportFrequency(str, Enum):
    """Rapor sıklığı."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ScanResult(BaseModel):
    """Tarama sonucu."""

    scan_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    source: str = ScanSource.SYSTEM
    findings: list[dict[str, Any]] = Field(
        default_factory=list,
    )
    anomaly_count: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class OpportunityRecord(BaseModel):
    """Fırsat kaydı."""

    opportunity_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    title: str = ""
    opportunity_type: str = (
        OpportunityType.EFFICIENCY
    )
    score: float = 0.0
    urgency: float = 0.5
    feasibility: float = 0.5
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ActionDecision(BaseModel):
    """Aksiyon kararı."""

    decision_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    action_type: str = ActionType.NOTIFY
    confidence: float = 0.5
    risk_level: str = "low"
    details: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ProactiveSnapshot(BaseModel):
    """Proactive snapshot."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    total_scans: int = 0
    total_opportunities: int = 0
    total_anomalies: int = 0
    total_actions: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
