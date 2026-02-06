"""Agent aktivite log veri modelleri.

Agent islemlerinin kalici kaydi icin Pydantic ve SQLAlchemy modelleri.
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# === SQLAlchemy Tablo Modeli ===


class AgentLogRecord(Base):
    """Agent log veritabani tablosu.

    Attributes:
        id: Benzersiz log kayit kimlik numarasi.
        agent_name: Agent adi.
        action: Gerceklestirilen islem.
        details: Islem detaylari (JSON string veya metin).
        status: Islem sonuc durumu (idle/running/error vb.).
        created_at: Log kayit zamani.
    """

    __tablename__ = "agent_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="idle")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def to_dict(self) -> dict:
        """Satiri sozluge donusturur."""
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "action": self.action,
            "details": self.details,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# === Pydantic Schema'lari ===


class AgentLogCreate(BaseModel):
    """Agent log olusturma schema'si.

    Attributes:
        agent_name: Agent adi.
        action: Gerceklestirilen islem.
        details: Islem detaylari.
        status: Islem durumu.
    """

    agent_name: str
    action: str
    details: str | None = None
    status: str = "idle"


class AgentLogResponse(BaseModel):
    """Agent log yanit schema'si."""

    id: str
    agent_name: str
    action: str
    details: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
