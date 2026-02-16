"""ATLAS Reputation & Brand Monitor modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class MentionSource(str, Enum):
    """Bahsedilme kaynağı."""

    SOCIAL_MEDIA = "social_media"
    NEWS = "news"
    FORUM = "forum"
    REVIEW = "review"


class SentimentType(str, Enum):
    """Duygu tipi."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class CrisisLevel(str, Enum):
    """Kriz seviyesi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResponseTone(str, Enum):
    """Yanıt tonu."""

    APOLOGETIC = "apologetic"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    EMPATHETIC = "empathetic"


class HealthGrade(str, Enum):
    """Sağlık derecesi."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class TrackingStatus(str, Enum):
    """Takip durumu."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MentionRecord(BaseModel):
    """Bahsedilme kaydı."""

    mention_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    source: str = "social_media"
    sentiment: str = "neutral"
    content: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ReviewRecord(BaseModel):
    """Yorum kaydı."""

    review_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    platform: str = ""
    rating: float = 0.0
    content: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CrisisRecord(BaseModel):
    """Kriz kaydı."""

    crisis_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    level: str = "low"
    trigger: str = ""
    status: str = "active"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class BrandHealthRecord(BaseModel):
    """Marka sağlık kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    brand: str = ""
    score: float = 0.0
    grade: str = "fair"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
