"""Bildirim veri modelleri.

Pydantic schema'lari (API/validasyon) ve SQLAlchemy tablo modeli (DB).
Bildirim olaylari, gonderim kanallari ve durumlarini modeller.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationEventType(str, Enum):
    """Bildirim olay tipi."""

    SECURITY_ALERT = "security_alert"
    SERVER_ALERT = "server_alert"
    ADS_ALERT = "ads_alert"
    OPPORTUNITY_ALERT = "opportunity_alert"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SYSTEM_ERROR = "system_error"
    SCHEDULED_REPORT = "scheduled_report"


class NotificationPriority(str, Enum):
    """Bildirim onceligi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, Enum):
    """Bildirim gonderim durumu."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"


class NotificationChannel(str, Enum):
    """Bildirim kanali."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"


# === SQLAlchemy Tablo Modeli ===


class NotificationRecord(Base):
    """Bildirim veritabani tablosu.

    Attributes:
        id: Benzersiz bildirim kimlik numarasi (UUID).
        task_id: Iliskili gorev ID'si (opsiyonel).
        event_type: Olay tipi.
        priority: Bildirim onceligi.
        status: Gonderim durumu.
        message: Bildirim mesaji.
        details: Ek detaylar (JSON string veya metin).
        recipient: Alici bilgisi.
        channel: Gonderim kanali.
        sent_at: Gonderim zamani.
        acknowledged_at: Okunma/onaylama zamani.
        created_at: Olusturulma zamani.
    """

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    task_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=NotificationPriority.MEDIUM.value,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=NotificationStatus.PENDING.value,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    recipient: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=NotificationChannel.TELEGRAM.value,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def to_dict(self) -> dict:
        """Satiri sozluge donusturur."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "priority": self.priority,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "recipient": self.recipient,
            "channel": self.channel,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "acknowledged_at": (
                self.acknowledged_at.isoformat()
                if self.acknowledged_at else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }


# === Pydantic Schema'lari ===


class NotificationCreate(BaseModel):
    """Yeni bildirim olusturma schema'si.

    Attributes:
        task_id: Iliskili gorev ID'si.
        event_type: Olay tipi.
        priority: Bildirim onceligi.
        message: Bildirim mesaji.
        details: Ek detaylar.
        recipient: Alici bilgisi.
        channel: Gonderim kanali.
    """

    task_id: str | None = None
    event_type: str
    priority: str = NotificationPriority.MEDIUM.value
    message: str
    details: str | None = None
    recipient: str | None = None
    channel: str = NotificationChannel.TELEGRAM.value


class NotificationResponse(BaseModel):
    """Bildirim yanit schema'si.

    Attributes:
        id: Bildirim kimlik numarasi.
        task_id: Iliskili gorev ID'si.
        event_type: Olay tipi.
        priority: Bildirim onceligi.
        status: Gonderim durumu.
        message: Bildirim mesaji.
        details: Ek detaylar.
        recipient: Alici bilgisi.
        channel: Gonderim kanali.
        sent_at: Gonderim zamani.
        acknowledged_at: Okunma zamani.
        created_at: Olusturulma zamani.
    """

    id: str
    task_id: str | None = None
    event_type: str
    priority: str
    status: str
    message: str
    details: str | None = None
    recipient: str | None = None
    channel: str
    sent_at: datetime | None = None
    acknowledged_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
