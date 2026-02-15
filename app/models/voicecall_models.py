"""ATLAS Voice Call Interface modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CallDirection(str, Enum):
    """Arama yönü."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"
    EMERGENCY = "emergency"
    SCHEDULED = "scheduled"


class CallStatus(str, Enum):
    """Arama durumu."""

    RINGING = "ringing"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    FAILED = "failed"


class VoiceProvider(str, Enum):
    """Ses sağlayıcı."""

    TWILIO = "twilio"
    VONAGE = "vonage"
    LOCAL = "local"
    ELEVENLABS = "elevenlabs"
    AZURE = "azure"


class AuthMethod(str, Enum):
    """Doğrulama yöntemi."""

    VOICE_BIOMETRIC = "voice_biometric"
    PIN = "pin"
    CHALLENGE = "challenge"
    PASSPHRASE = "passphrase"
    NONE = "none"


class UrgencyLevel(str, Enum):
    """Aciliyet seviyesi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ROUTINE = "routine"


class RecordingConsent(str, Enum):
    """Kayıt onayı."""

    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"
    NOT_REQUIRED = "not_required"
    REVOKED = "revoked"


class CallRecord(BaseModel):
    """Arama kaydı."""

    call_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    direction: str = CallDirection.OUTBOUND
    status: str = CallStatus.RINGING
    caller: str = ""
    callee: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class TranscriptionRecord(BaseModel):
    """Transkripsiyon kaydı."""

    transcription_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    call_id: str = ""
    text: str = ""
    language: str = "en"
    confidence: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class VoiceProfile(BaseModel):
    """Ses profili."""

    profile_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    user_id: str = ""
    auth_method: str = AuthMethod.NONE
    enrolled: bool = False
    details: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class VoiceCallSnapshot(BaseModel):
    """VoiceCall snapshot."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    total_calls: int = 0
    total_recordings: int = 0
    total_transcriptions: int = 0
    total_authentications: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
