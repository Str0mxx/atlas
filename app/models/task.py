"""Gorev veri modelleri.

Pydantic schema'lari (API/validasyon) ve SQLAlchemy tablo modeli (DB).
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaskStatus(str, Enum):
    """Gorev durum tanimlari."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# === SQLAlchemy Tablo Modeli ===


class TaskRecord(Base):
    """Gorev veritabani tablosu.

    Attributes:
        id: Benzersiz gorev kimlik numarasi (UUID).
        description: Gorev aciklamasi.
        status: Mevcut gorev durumu.
        agent: Gorevi calistiran agent adi.
        risk: Risk seviyesi (low/medium/high).
        urgency: Aciliyet seviyesi (low/medium/high).
        result_message: Gorev sonuc mesaji.
        result_success: Gorev basarili mi.
        confidence: Guven skoru.
        created_at: Olusturulma zamani.
        updated_at: Son guncelleme zamani.
        completed_at: Tamamlanma zamani.
    """

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TaskStatus.PENDING.value
    )
    agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    result_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        """Satiri sozluge donusturur."""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "agent": self.agent,
            "risk": self.risk,
            "urgency": self.urgency,
            "result_message": self.result_message,
            "result_success": self.result_success,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# === Pydantic Schema'lari ===


class TaskCreate(BaseModel):
    """Yeni gorev olusturma schema'si.

    Attributes:
        description: Gorev aciklamasi.
        agent: Hedef agent adi (opsiyonel).
        risk: Risk seviyesi.
        urgency: Aciliyet seviyesi.
    """

    description: str
    agent: str | None = None
    risk: str | None = None
    urgency: str | None = None


class TaskResponse(BaseModel):
    """Gorev yanit schema'si.

    Attributes:
        id: Gorev kimlik numarasi.
        description: Gorev aciklamasi.
        status: Mevcut durum.
        agent: Atanan agent.
        risk: Risk seviyesi.
        urgency: Aciliyet seviyesi.
        result_message: Sonuc mesaji.
        result_success: Basari durumu.
        confidence: Guven skoru.
        created_at: Olusturulma zamani.
        updated_at: Son guncelleme zamani.
        completed_at: Tamamlanma zamani.
    """

    id: str
    description: str
    status: TaskStatus
    agent: str | None = None
    risk: str | None = None
    urgency: str | None = None
    result_message: str | None = None
    result_success: bool | None = None
    confidence: float | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
