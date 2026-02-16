"""ATLAS External Communication Agent modelleri.

Dış iletişim, email, LinkedIn, kampanya,
takip, ton adaptasyonu modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ChannelType(str, Enum):
    """İletişim kanalı tipi."""

    EMAIL = "email"
    LINKEDIN = "linkedin"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    PHONE = "phone"


class ToneLevel(str, Enum):
    """Ton seviyesi."""

    FORMAL = "formal"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    URGENT = "urgent"
    EMPATHETIC = "empathetic"


class EmailStatus(str, Enum):
    """Email durumu."""

    DRAFT = "draft"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    FAILED = "failed"


class CampaignStatus(str, Enum):
    """Kampanya durumu."""

    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ResponseSentiment(str, Enum):
    """Yanıt duygu analizi."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    ANGRY = "angry"


class FollowUpPriority(str, Enum):
    """Takip önceliği."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


class ContactRecord(BaseModel):
    """İletişim kaydı."""

    contact_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    email: str = ""
    company: str = ""
    channel: ChannelType = ChannelType.EMAIL
    relationship_score: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class EmailRecord(BaseModel):
    """Email kaydı."""

    email_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    to: str = ""
    subject: str = ""
    status: EmailStatus = EmailStatus.DRAFT
    tone: ToneLevel = ToneLevel.PROFESSIONAL
    sent_at: datetime | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CampaignRecord(BaseModel):
    """Kampanya kaydı."""

    campaign_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    status: CampaignStatus = (
        CampaignStatus.PLANNING
    )
    total_contacts: int = 0
    sent_count: int = 0
    response_count: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ExtCommSnapshot(BaseModel):
    """Dış iletişim anlık görüntü."""

    emails_sent: int = 0
    campaigns_active: int = 0
    contacts_total: int = 0
    follow_ups_pending: int = 0
    responses_received: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
