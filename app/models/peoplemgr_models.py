"""ATLAS People & Relationship Manager modelleri.

Kişi profili, etkileşim, ilişki puanı,
takip, duygu, ağ haritası modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ContactCategory(str, Enum):
    """Kişi kategorisi."""

    CLIENT = "client"
    SUPPLIER = "supplier"
    PARTNER = "partner"
    COLLEAGUE = "colleague"
    PROSPECT = "prospect"
    OTHER = "other"


class InteractionChannel(str, Enum):
    """Etkileşim kanalı."""

    EMAIL = "email"
    PHONE = "phone"
    MEETING = "meeting"
    TELEGRAM = "telegram"
    SOCIAL = "social"
    OTHER = "other"


class SentimentLevel(str, Enum):
    """Duygu seviyesi."""

    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class RelationshipStrength(str, Enum):
    """İlişki gücü."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    DORMANT = "dormant"
    NEW = "new"


class FollowUpPriority(str, Enum):
    """Takip önceliği."""

    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    OPTIONAL = "optional"


class NetworkRole(str, Enum):
    """Ağ rolü."""

    HUB = "hub"
    BRIDGE = "bridge"
    PERIPHERAL = "peripheral"
    ISOLATE = "isolate"
    INFLUENCER = "influencer"


class ContactRecord(BaseModel):
    """Kişi kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    category: str = "other"
    tags: list[str] = Field(
        default_factory=list,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class InteractionRecord(BaseModel):
    """Etkileşim kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    contact_id: str = ""
    channel: str = "other"
    sentiment: str = "neutral"
    summary: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class RelationshipRecord(BaseModel):
    """İlişki kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    contact_id: str = ""
    score: float = 0.0
    strength: str = "new"
    trend: str = "stable"
    last_interaction: datetime | None = None


class FollowUpRecord(BaseModel):
    """Takip kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    contact_id: str = ""
    action: str = ""
    priority: str = "normal"
    scheduled_at: datetime | None = None
    completed: bool = False
