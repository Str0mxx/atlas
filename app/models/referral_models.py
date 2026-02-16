"""ATLAS Referral & Word-of-Mouth Engine modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ReferralStatus(str, Enum):
    """Referans durumu."""

    PENDING = "pending"
    CLICKED = "clicked"
    SIGNED_UP = "signed_up"
    CONVERTED = "converted"
    REWARDED = "rewarded"
    REJECTED = "rejected"


class RewardType(str, Enum):
    """Ödül tipi."""

    CASH = "cash"
    CREDIT = "credit"
    DISCOUNT = "discount"
    POINTS = "points"
    GIFT = "gift"


class AmbassadorTier(str, Enum):
    """Elçi seviyesi."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class FraudRisk(str, Enum):
    """Dolandırıcılık risk seviyesi."""

    CLEAN = "clean"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class IncentiveStrategy(str, Enum):
    """Teşvik stratejisi."""

    FIXED = "fixed"
    PERCENTAGE = "percentage"
    TIERED = "tiered"
    DYNAMIC = "dynamic"


class ViralPhase(str, Enum):
    """Viral aşama."""

    SEED = "seed"
    GROWTH = "growth"
    VIRAL = "viral"
    PLATEAU = "plateau"


class ReferralRecord(BaseModel):
    """Referans kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    referrer_id: str = ""
    referred_id: str = ""
    status: str = "pending"
    reward_amount: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class AmbassadorRecord(BaseModel):
    """Elçi kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    tier: str = "bronze"
    total_referrals: int = 0
    total_earnings: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class LinkRecord(BaseModel):
    """Takip linki kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    referrer_id: str = ""
    url: str = ""
    clicks: int = 0
    conversions: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class FraudRecord(BaseModel):
    """Dolandırıcılık kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    referral_id: str = ""
    risk_level: str = "clean"
    reason: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
