"""ATLAS Event & Conference Intelligence modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventCategory(str, Enum):
    """Etkinlik kategorisi."""

    CONFERENCE = "conference"
    SUMMIT = "summit"
    WORKSHOP = "workshop"
    MEETUP = "meetup"
    WEBINAR = "webinar"
    TRADE_SHOW = "trade_show"


class RegistrationStatus(str, Enum):
    """Kayıt durumu."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"
    ATTENDED = "attended"


class SpeakerTier(str, Enum):
    """Konuşmacı seviyesi."""

    KEYNOTE = "keynote"
    FEATURED = "featured"
    REGULAR = "regular"
    PANELIST = "panelist"
    LIGHTNING = "lightning"


class FollowUpStatus(str, Enum):
    """Takip durumu."""

    PENDING = "pending"
    SENT = "sent"
    RESPONDED = "responded"
    MEETING_SET = "meeting_set"
    CLOSED = "closed"


class NetworkingPriority(str, Enum):
    """Ağ kurma önceliği."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ROICategory(str, Enum):
    """ROI kategorisi."""

    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"


class EventRecord(BaseModel):
    """Etkinlik kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    category: str = "conference"
    location: str = ""
    relevance: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class SpeakerRecord(BaseModel):
    """Konuşmacı kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    tier: str = "regular"
    topics: list[str] = Field(
        default_factory=list,
    )
    rating: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class ContactRecord(BaseModel):
    """İletişim kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    event_id: str = ""
    followup_status: str = "pending"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class ROIRecord(BaseModel):
    """ROI kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    event_id: str = ""
    total_cost: float = 0.0
    total_revenue: float = 0.0
    roi_pct: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
