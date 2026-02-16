"""ATLAS Autonomous Revenue Optimizer modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RevenueStream(str, Enum):
    """Gelir akışı tipi."""

    PRODUCT = "product"
    SERVICE = "service"
    SUBSCRIPTION = "subscription"
    ADVERTISING = "advertising"


class PricingStrategy(str, Enum):
    """Fiyatlandırma stratejisi."""

    COST_PLUS = "cost_plus"
    VALUE_BASED = "value_based"
    COMPETITIVE = "competitive"
    DYNAMIC = "dynamic"


class ChurnRisk(str, Enum):
    """Kayıp risk seviyesi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CampaignChannel(str, Enum):
    """Kampanya kanalı."""

    GOOGLE_ADS = "google_ads"
    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    ORGANIC = "organic"


class ForecastMethod(str, Enum):
    """Tahmin yöntemi."""

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    SEASONAL = "seasonal"
    ENSEMBLE = "ensemble"


class MonetizationType(str, Enum):
    """Monetizasyon tipi."""

    FREEMIUM = "freemium"
    PREMIUM = "premium"
    MARKETPLACE = "marketplace"
    LICENSING = "licensing"


class RevenueRecord(BaseModel):
    """Gelir kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    stream: str = "product"
    amount: float = 0.0
    period: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ChurnRecord(BaseModel):
    """Kayıp kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    customer_id: str = ""
    risk_level: str = "low"
    risk_score: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class LTVRecord(BaseModel):
    """Yaşam boyu değer kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    customer_id: str = ""
    segment: str = ""
    ltv_value: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ForecastRecord(BaseModel):
    """Tahmin kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    period: str = ""
    predicted_revenue: float = 0.0
    confidence: float = 0.95
    method: str = "linear"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
