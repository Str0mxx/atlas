"""ATLAS Multi-Channel Command Center modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ChannelType(str, Enum):
    """Kanal tipi."""

    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    VOICE = "voice"
    SMS = "sms"


class MessageDirection(str, Enum):
    """Mesaj yönü."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"
    BROADCAST = "broadcast"
    SYSTEM = "system"


class EscalationLevel(str, Enum):
    """Eskalasyon seviyesi."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PresenceStatus(str, Enum):
    """Varlık durumu."""

    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"
    DND = "dnd"


class CommandType(str, Enum):
    """Komut tipi."""

    QUERY = "query"
    ACTION = "action"
    REPORT = "report"
    CONFIG = "config"
    HELP = "help"


class FormatType(str, Enum):
    """Format tipi."""

    PLAIN = "plain"
    MARKDOWN = "markdown"
    HTML = "html"
    RICH = "rich"
    MINIMAL = "minimal"


class ChannelMessage(BaseModel):
    """Kanal mesajı."""

    message_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    channel: str = ChannelType.TELEGRAM
    direction: str = MessageDirection.INBOUND
    content: str = ""
    sender: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class SessionRecord(BaseModel):
    """Oturum kaydı."""

    session_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    user_id: str = ""
    channel: str = ChannelType.TELEGRAM
    active: bool = True
    context: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class EscalationRecord(BaseModel):
    """Eskalasyon kaydı."""

    escalation_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    from_channel: str = ""
    to_channel: str = ""
    level: str = EscalationLevel.LOW
    reason: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class MultiChannelSnapshot(BaseModel):
    """MultiChannel snapshot."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    total_messages: int = 0
    total_sessions: int = 0
    total_escalations: int = 0
    active_channels: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
