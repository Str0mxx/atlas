"""ATLAS Community & Audience Builder modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SegmentType(str, Enum):
    """Segment tipi."""

    DEMOGRAPHIC = "demographic"
    BEHAVIORAL = "behavioral"
    INTEREST = "interest"
    VALUE = "value"
    DYNAMIC = "dynamic"


class MemberStatus(str, Enum):
    """Üye durumu."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    AT_RISK = "at_risk"
    CHURNED = "churned"
    NEW = "new"


class EngagementLevel(str, Enum):
    """Etkileşim seviyesi."""

    LURKER = "lurker"
    CASUAL = "casual"
    ACTIVE = "active"
    POWER_USER = "power_user"
    CHAMPION = "champion"


class GrowthChannel(str, Enum):
    """Büyüme kanalı."""

    ORGANIC = "organic"
    REFERRAL = "referral"
    PAID = "paid"
    PARTNERSHIP = "partnership"


class RewardType(str, Enum):
    """Ödül tipi."""

    POINTS = "points"
    BADGE = "badge"
    LEVEL_UP = "level_up"
    DISCOUNT = "discount"
    ACCESS = "access"


class RetentionStrategy(str, Enum):
    """Tutundurma stratejisi."""

    RE_ENGAGEMENT = "re_engagement"
    WIN_BACK = "win_back"
    LOYALTY = "loyalty"
    PREVENTION = "prevention"


class MemberRecord(BaseModel):
    """Üye kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    segment: str = "general"
    engagement_level: str = "casual"
    points: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class SegmentRecord(BaseModel):
    """Segment kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    segment_type: str = "demographic"
    member_count: int = 0
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
    campaign_type: str = "retention"
    target_segment: str = ""
    status: str = "draft"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class RewardRecord(BaseModel):
    """Ödül kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    member_id: str = ""
    reward_type: str = "points"
    value: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
