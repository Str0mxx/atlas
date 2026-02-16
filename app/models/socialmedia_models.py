"""ATLAS Social Media Intelligence & Automation modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SocialPlatform(str, Enum):
    """Sosyal medya platformu."""

    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class PostStatus(str, Enum):
    """Gönderi durumu."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class EngagementType(str, Enum):
    """Etkileşim tipi."""

    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    SAVE = "save"
    CLICK = "click"


class SentimentLevel(str, Enum):
    """Duygu seviyesi."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class CampaignStatus(str, Enum):
    """Kampanya durumu."""

    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class TrendStrength(str, Enum):
    """Trend gücü."""

    EMERGING = "emerging"
    GROWING = "growing"
    PEAK = "peak"
    DECLINING = "declining"


class SocialPostRecord(BaseModel):
    """Sosyal medya gönderi kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    platform: str = "instagram"
    content: str = ""
    status: str = "draft"
    engagement_count: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class EngagementRecord(BaseModel):
    """Etkileşim kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    platform: str = "instagram"
    post_id: str = ""
    engagement_type: str = "like"
    count: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class CampaignRecord(BaseModel):
    """Kampanya kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    platform: str = "instagram"
    status: str = "planning"
    budget: float = 0.0
    spent: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class MentionRecord(BaseModel):
    """Bahsetme kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    platform: str = "twitter"
    keyword: str = ""
    sentiment: str = "neutral"
    source_url: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
