"""ATLAS Autonomous Negotiation Engine modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class NegotiationPhase(str, Enum):
    """Müzakere fazı."""

    PLANNING = "planning"
    OPENING = "opening"
    BARGAINING = "bargaining"
    CLOSING = "closing"
    SETTLED = "settled"
    FAILED = "failed"


class OfferStatus(str, Enum):
    """Teklif durumu."""

    DRAFT = "draft"
    SENT = "sent"
    RECEIVED = "received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COUNTERED = "countered"


class ConcessionType(str, Enum):
    """Taviz tipi."""

    PRICE = "price"
    TERMS = "terms"
    TIMELINE = "timeline"
    SCOPE = "scope"
    WARRANTY = "warranty"
    VOLUME = "volume"


class NegotiationStrategy(str, Enum):
    """Müzakere stratejisi."""

    COMPETITIVE = "competitive"
    COLLABORATIVE = "collaborative"
    COMPROMISING = "compromising"
    ACCOMMODATING = "accommodating"
    AVOIDING = "avoiding"


class DealOutcome(str, Enum):
    """Anlaşma sonucu."""

    WON = "won"
    LOST = "lost"
    DRAW = "draw"
    PENDING = "pending"
    CANCELLED = "cancelled"


class PartyRole(str, Enum):
    """Taraf rolü."""

    BUYER = "buyer"
    SELLER = "seller"
    MEDIATOR = "mediator"
    PARTNER = "partner"


class NegotiationRecord(BaseModel):
    """Müzakere kaydı."""

    negotiation_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    parties: list[str] = Field(
        default_factory=list,
    )
    phase: NegotiationPhase = (
        NegotiationPhase.PLANNING
    )
    strategy: NegotiationStrategy = (
        NegotiationStrategy.COLLABORATIVE
    )
    outcome: DealOutcome = DealOutcome.PENDING
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class OfferRecord(BaseModel):
    """Teklif kaydı."""

    offer_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    negotiation_id: str = ""
    amount: float = 0.0
    terms: dict[str, str] | None = None
    status: OfferStatus = OfferStatus.DRAFT
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ConcessionRecord(BaseModel):
    """Taviz kaydı."""

    concession_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    concession_type: ConcessionType = (
        ConcessionType.PRICE
    )
    original_value: float = 0.0
    conceded_value: float = 0.0
    party: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class DealScore(BaseModel):
    """Anlaşma puanı."""

    score_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    overall_score: float = 0.0
    risk_score: float = 0.0
    value_score: float = 0.0
    recommendation: str = "evaluate"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
