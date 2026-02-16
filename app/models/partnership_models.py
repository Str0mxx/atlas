"""ATLAS Network & Partnership Finder modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PartnerType(str, Enum):
    """Ortak tipi."""

    STRATEGIC = "strategic"
    TECHNOLOGY = "technology"
    DISTRIBUTION = "distribution"
    SUPPLIER = "supplier"
    INVESTOR = "investor"
    RESELLER = "reseller"


class DealStage(str, Enum):
    """Anlaşma aşaması."""

    PROSPECT = "prospect"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class PartnershipStatus(str, Enum):
    """Ortaklık durumu."""

    EXPLORING = "exploring"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    TERMINATED = "terminated"


class EventType(str, Enum):
    """Etkinlik tipi."""

    CONFERENCE = "conference"
    MEETUP = "meetup"
    WEBINAR = "webinar"
    TRADE_SHOW = "trade_show"


class InvestorType(str, Enum):
    """Yatırımcı tipi."""

    ANGEL = "angel"
    VC = "vc"
    PE = "pe"
    CORPORATE = "corporate"
    FAMILY_OFFICE = "family_office"


class CompatibilityLevel(str, Enum):
    """Uyumluluk seviyesi."""

    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    LOW = "low"


class PartnerRecord(BaseModel):
    """Ortak kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    partner_type: str = "strategic"
    industry: str = ""
    compatibility: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class DealRecord(BaseModel):
    """Anlaşma kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    partner_id: str = ""
    stage: str = "prospect"
    value: float = 0.0
    probability: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class EventRecord(BaseModel):
    """Etkinlik kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    event_type: str = "conference"
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


class InvestorRecord(BaseModel):
    """Yatırımcı kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    investor_type: str = "vc"
    thesis_match: float = 0.0
    portfolio_size: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
