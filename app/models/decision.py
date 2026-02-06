"""Karar kayit veri modelleri.

Karar matrisi sonuclarinin kalici kaydi icin Pydantic ve SQLAlchemy modelleri.
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# === SQLAlchemy Tablo Modeli ===


class DecisionRecord(Base):
    """Karar kayit veritabani tablosu.

    Attributes:
        id: Benzersiz kayit kimlik numarasi.
        task_id: Iliskili gorev kimlik numarasi.
        risk: Risk seviyesi.
        urgency: Aciliyet seviyesi.
        action: Secilen aksiyon tipi.
        confidence: Guven skoru (0.0 - 1.0).
        reason: Karar gerekce metni.
        created_at: Karar zamani.
    """

    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    risk: Mapped[str] = mapped_column(String(20), nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        """Satiri sozluge donusturur."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "risk": self.risk,
            "urgency": self.urgency,
            "action": self.action,
            "confidence": self.confidence,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# === Pydantic Schema'lari ===


class DecisionCreate(BaseModel):
    """Karar kaydi olusturma schema'si.

    Attributes:
        task_id: Iliskili gorev ID'si (opsiyonel).
        risk: Risk seviyesi.
        urgency: Aciliyet seviyesi.
        action: Secilen aksiyon tipi.
        confidence: Guven skoru.
        reason: Karar gerekce metni.
    """

    task_id: str | None = None
    risk: str
    urgency: str
    action: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class DecisionResponse(BaseModel):
    """Karar yanit schema'si."""

    id: str
    task_id: str | None = None
    risk: str
    urgency: str
    action: str
    confidence: float
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}
