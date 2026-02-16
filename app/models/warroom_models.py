"""ATLAS Competitive War Room modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CompetitorStatus(str, Enum):
    """Rakip durumu."""

    ACTIVE = "active"
    EMERGING = "emerging"
    DECLINING = "declining"
    DORMANT = "dormant"
    ACQUIRED = "acquired"


class ThreatLevel(str, Enum):
    """Tehdit seviyesi."""

    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class PriceAction(str, Enum):
    """Fiyat aksiyonu."""

    INCREASE = "increase"
    DECREASE = "decrease"
    STABLE = "stable"
    PROMOTIONAL = "promotional"
    DISCONTINUED = "discontinued"


class LaunchPhase(str, Enum):
    """Lansman aşaması."""

    RUMOR = "rumor"
    ANNOUNCED = "announced"
    BETA = "beta"
    LAUNCHED = "launched"
    MATURE = "mature"


class IntelSource(str, Enum):
    """İstihbarat kaynağı."""

    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    JOB_POSTINGS = "job_postings"
    PATENT_FILINGS = "patent_filings"
    WEBSITE_CHANGES = "website_changes"


class SignalStrength(str, Enum):
    """Sinyal gücü."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    CONFIRMED = "confirmed"
    VERIFIED = "verified"


class CompetitorRecord(BaseModel):
    """Rakip kaydı."""

    competitor_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    status: CompetitorStatus = (
        CompetitorStatus.ACTIVE
    )
    threat_level: ThreatLevel = (
        ThreatLevel.MODERATE
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class PriceRecord(BaseModel):
    """Fiyat kaydı."""

    price_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    competitor_id: str = ""
    product: str = ""
    price: float = 0.0
    action: PriceAction = (
        PriceAction.STABLE
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class IntelRecord(BaseModel):
    """İstihbarat kaydı."""

    intel_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    source: IntelSource = (
        IntelSource.NEWS
    )
    signal_strength: SignalStrength = (
        SignalStrength.MODERATE
    )
    content: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class PatentRecord(BaseModel):
    """Patent kaydı."""

    patent_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    competitor_id: str = ""
    title: str = ""
    technology: str = ""
    filed_year: int = 2024
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None
