"""ATLAS Voice Command & Smart Speaker Bridge modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SpeakerPlatform(str, Enum):
    """Hoparlör platformu."""

    ALEXA = "alexa"
    GOOGLE = "google"
    SIRI = "siri"
    CUSTOM = "custom"


class CommandIntent(str, Enum):
    """Komut niyeti."""

    CONTROL = "control"
    QUERY = "query"
    AUTOMATION = "automation"
    MEDIA = "media"
    COMMUNICATION = "communication"


class ResponseType(str, Enum):
    """Yanıt tipi."""

    SPEECH = "speech"
    CARD = "card"
    AUDIO = "audio"
    VISUAL = "visual"
    SSML = "ssml"


class DeviceSyncStatus(str, Enum):
    """Cihaz senkronizasyon durumu."""

    SYNCED = "synced"
    PENDING = "pending"
    CONFLICT = "conflict"
    OFFLINE = "offline"


class WakeWordState(str, Enum):
    """Uyandırma kelimesi durumu."""

    LISTENING = "listening"
    ACTIVATED = "activated"
    IDLE = "idle"
    DISABLED = "disabled"


class ConversationState(str, Enum):
    """Konuşma durumu."""

    ACTIVE = "active"
    WAITING = "waiting"
    ENDED = "ended"
    TIMEOUT = "timeout"


class VoiceCommandRecord(BaseModel):
    """Sesli komut kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    platform: str = "alexa"
    raw_text: str = ""
    intent: str = ""
    confidence: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class SpeakerDeviceRecord(BaseModel):
    """Hoparlör cihaz kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    device_name: str = ""
    platform: str = "alexa"
    location: str = ""
    status: str = "synced"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class ConversationRecord(BaseModel):
    """Konuşma kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    session_id: str = ""
    platform: str = "alexa"
    turns: int = 0
    state: str = "active"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class ResponseRecord(BaseModel):
    """Yanıt kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    response_type: str = "speech"
    platform: str = "alexa"
    content: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
