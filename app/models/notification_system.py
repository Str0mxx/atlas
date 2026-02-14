"""Notification & Alert System veri modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class NotificationPriority(str, Enum):
    """Bildirim onceligi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, Enum):
    """Bildirim durumu."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    SUPPRESSED = "suppressed"


class NotificationChannel(str, Enum):
    """Bildirim kanali."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    LOG = "log"


class AlertType(str, Enum):
    """Uyari turu."""

    THRESHOLD = "threshold"
    PATTERN = "pattern"
    ANOMALY = "anomaly"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class EscalationLevel(str, Enum):
    """Eskalasyon seviyesi."""

    L1 = "l1"
    L2 = "l2"
    L3 = "l3"
    MANAGEMENT = "management"
    EMERGENCY = "emergency"


class DigestFrequency(str, Enum):
    """Ozet sikligi."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class NotificationRecord(BaseModel):
    """Bildirim kaydi."""

    notification_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    title: str = ""
    message: str = ""
    priority: NotificationPriority = NotificationPriority.MEDIUM
    status: NotificationStatus = NotificationStatus.PENDING
    channel: NotificationChannel = NotificationChannel.LOG
    category: str = "general"
    recipient: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class AlertRecord(BaseModel):
    """Uyari kaydi."""

    alert_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    alert_type: AlertType = AlertType.THRESHOLD
    source: str = ""
    message: str = ""
    severity: NotificationPriority = NotificationPriority.MEDIUM
    acknowledged: bool = False
    suppressed: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class DeliveryRecord(BaseModel):
    """Teslimat kaydi."""

    delivery_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    notification_id: str = ""
    channel: NotificationChannel = NotificationChannel.LOG
    status: NotificationStatus = NotificationStatus.PENDING
    attempts: int = 0
    last_error: str = ""


class NotificationSnapshot(BaseModel):
    """Bildirim goruntusu."""

    total_notifications: int = 0
    pending: int = 0
    sent: int = 0
    failed: int = 0
    active_alerts: int = 0
    suppressed: int = 0
    delivery_rate: float = 0.0
    escalations: int = 0
