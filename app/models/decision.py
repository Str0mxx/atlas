"""Karar kayit veri modelleri.

Karar matrisi sonuclarinin kalici kaydi icin Pydantic ve SQLAlchemy modelleri.
Denetim izi, onay is akisi, eskalasyon ve kural degisikligi modellerini icerir.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

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


# === Enum Tanimlari ===


class ApprovalStatus(str, Enum):
    """Onay durumu tanimlari.

    Attributes:
        PENDING: Onay bekliyor.
        APPROVED: Onaylandi.
        REJECTED: Reddedildi.
        TIMEOUT: Zaman asimi.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class EscalationLevel(str, Enum):
    """Eskalasyon seviyesi tanimlari.

    Attributes:
        NONE: Eskalasyon yok.
        RETRY_SAME: Ayni agent ile tekrar dene.
        ALTERNATE_AGENT: Farkli agent'a yonlendir.
        NOTIFY_HUMAN: Insan mudahalesi gerekli.
    """

    NONE = "none"
    RETRY_SAME = "retry_same"
    ALTERNATE_AGENT = "alternate_agent"
    NOTIFY_HUMAN = "notify_human"


# === Denetim ve Is Akisi Modelleri ===


class DecisionAuditEntry(BaseModel):
    """Karar denetim izi kaydi.

    Her karar icin olusturulan detayli denetim kaydi. Gorev bilgileri,
    karar sonucu, agent secimi ve sonuc takibi icerir.

    Attributes:
        id: Benzersiz kayit kimlik numarasi.
        task_description: Gorev aciklamasi.
        risk: Risk seviyesi.
        urgency: Aciliyet seviyesi.
        action: Belirlenen aksiyon tipi.
        confidence: Guven skoru (0.0 - 1.0).
        reason: Karar aciklamasi.
        agent_selected: Secilen agent adi.
        agent_selection_method: Secim yontemi (explicit/keyword/fallback/none).
        outcome_success: Gorev sonucu (None = henuz bitmedi).
        escalated_from: Eskalasyon kaynagi aksiyon (opsiyonel).
        timestamp: Karar zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str = ""
    risk: str = ""
    urgency: str = ""
    action: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    agent_selected: str | None = None
    agent_selection_method: str = "explicit"
    outcome_success: bool | None = None
    escalated_from: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalRequest(BaseModel):
    """Onay istegi modeli.

    Otonom aksiyon oncesi insan onayi gerektiren durumlar icin
    kullanilir. Telegram uzerinden onay/red butonu gonderilir.

    Attributes:
        id: Benzersiz istek kimlik numarasi.
        task: Onay bekleyen gorev verisi.
        action: Onerilen aksiyon tipi.
        decision: Iliskili karar bilgisi.
        status: Mevcut onay durumu.
        requested_at: Istek zamani.
        responded_at: Yanit zamani.
        timeout_seconds: Zaman asimi suresi (saniye).
        auto_execute_on_timeout: Zaman asiminda otomatik calistir.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: dict[str, Any] = Field(default_factory=dict)
    action: str = ""
    decision: DecisionCreate | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: datetime | None = None
    timeout_seconds: int = Field(default=300, ge=0)
    auto_execute_on_timeout: bool = False


class EscalationRecord(BaseModel):
    """Eskalasyon kaydi.

    Basarisiz gorev sonrasi uygulanan eskalasyon adiminin kaydi.
    Orijinal ve eskalasyon sonrasi aksiyon/agent bilgilerini icerir.

    Attributes:
        id: Benzersiz kayit kimlik numarasi.
        original_action: Orijinal aksiyon tipi.
        escalated_action: Eskalasyon sonrasi aksiyon.
        original_agent: Basarisiz olan agent.
        escalated_agent: Eskalasyon sonrasi atanan agent.
        level: Eskalasyon seviyesi.
        reason: Eskalasyon nedeni.
        timestamp: Eskalasyon zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_action: str = ""
    escalated_action: str = ""
    original_agent: str | None = None
    escalated_agent: str | None = None
    level: EscalationLevel = EscalationLevel.NONE
    reason: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RuleChangeRecord(BaseModel):
    """Kural degisikligi kaydi.

    Karar matrisi kurallarindaki degisikliklerin denetim kaydi.
    Eski ve yeni degerleri, degisikligi yapani kaydeder.

    Attributes:
        risk: Degisen kuralin risk seviyesi.
        urgency: Degisen kuralin aciliyet seviyesi.
        old_action: Eski aksiyon tipi.
        new_action: Yeni aksiyon tipi.
        old_confidence: Eski guven skoru.
        new_confidence: Yeni guven skoru.
        changed_by: Degisikligi yapan (system/user/learning).
        timestamp: Degisiklik zamani.
    """

    risk: str
    urgency: str
    old_action: str
    new_action: str
    old_confidence: float
    new_confidence: float
    changed_by: str = "system"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
