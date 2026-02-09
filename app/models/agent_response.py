"""Agent yanit veri modelleri.

Agent gorev sonuclarini standart bir formatta temsil eden
Pydantic modelleri. base_agent.TaskResult ile uyumlu calisir.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResponseStatus(str, Enum):
    """Agent yanit durumu."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"


class AgentAction(BaseModel):
    """Agent tarafindan gerceklestirilen tekil aksiyon.

    Attributes:
        action_type: Aksiyon turu (ornek: "email_sent", "ip_blocked").
        description: Aksiyonun kisa aciklamasi.
        autonomous: Otomatik mi (onaysiz) yoksa onayli mi gerceklesti.
        success: Aksiyon basarili mi.
    """

    action_type: str
    description: str = ""
    autonomous: bool = False
    success: bool = True


class AgentResponse(BaseModel):
    """Standart agent yanit modeli.

    Herhangi bir agent'in gorev sonucunu temsil eder.
    API uzerinden disariya donulen yanitlarda kullanilir.

    Attributes:
        agent_name: Yaniti ureten agent adi.
        status: Yanit durumu.
        summary: Sonuc ozeti.
        data: Tur-bazli detayli sonuc verisi.
        actions_taken: Gerceklestirilen aksiyonlar listesi.
        recommendations: Oneriler listesi.
        risk_level: Genel risk seviyesi.
        confidence: Guven skoru (0.0-1.0).
        errors: Hata mesajlari.
        timestamp: Yanit olusturulma zamani.
    """

    agent_name: str
    status: ResponseStatus = ResponseStatus.SUCCESS
    summary: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    actions_taken: list[AgentAction] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    errors: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @property
    def is_success(self) -> bool:
        """Yanit basarili mi kontrol eder."""
        return self.status in (ResponseStatus.SUCCESS, ResponseStatus.PARTIAL)

    @property
    def autonomous_actions(self) -> list[AgentAction]:
        """Otomatik gerceklestirilen aksiyonlari dondurur."""
        return [a for a in self.actions_taken if a.autonomous]
