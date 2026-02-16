"""ATLAS Content Generation modelleri.

İçerik üretimi, A/B test, marka sesi,
içerik takvimi modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """İçerik tipi."""

    AD_COPY = "ad_copy"
    HEADLINE = "headline"
    DESCRIPTION = "description"
    CTA = "cta"
    BLOG_POST = "blog_post"
    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    OTHER = "other"


class PlatformType(str, Enum):
    """Platform tipi."""

    GOOGLE_ADS = "google_ads"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    WEBSITE = "website"
    EMAIL = "email"
    OTHER = "other"


class ToneType(str, Enum):
    """Ton tipi."""

    PROFESSIONAL = "professional"
    CASUAL = "casual"
    HUMOROUS = "humorous"
    URGENT = "urgent"
    INSPIRATIONAL = "inspirational"
    INFORMATIVE = "informative"
    PERSUASIVE = "persuasive"
    OTHER = "other"


class ContentStatus(str, Enum):
    """İçerik durumu."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ABTestStatus(str, Enum):
    """A/B test durumu."""

    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELED = "canceled"


class PerformanceLevel(str, Enum):
    """Performans seviyesi."""

    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    BELOW_AVERAGE = "below_average"
    POOR = "poor"


class ContentRecord(BaseModel):
    """İçerik kaydı."""

    id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    title: str = ""
    content_type: ContentType = ContentType.OTHER
    platform: PlatformType = PlatformType.OTHER
    tone: ToneType = ToneType.PROFESSIONAL
    status: ContentStatus = ContentStatus.DRAFT
    language: str = "en"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ABTestRecord(BaseModel):
    """A/B test kaydı."""

    id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    test_name: str = ""
    variant_a: str = ""
    variant_b: str = ""
    status: ABTestStatus = ABTestStatus.PLANNED
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class BrandVoiceRecord(BaseModel):
    """Marka sesi kaydı."""

    id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    brand_name: str = ""
    tone: ToneType = ToneType.PROFESSIONAL
    guidelines: list[str] = Field(
        default_factory=list,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CalendarEntry(BaseModel):
    """İçerik takvimi girdisi."""

    id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    title: str = ""
    platform: PlatformType = PlatformType.OTHER
    scheduled_date: str = ""
    status: ContentStatus = ContentStatus.DRAFT
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
