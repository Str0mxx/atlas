"""ATLAS Investment & ROI Analyzer modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class InvestmentType(str, Enum):
    """Yatırım tipi."""

    EQUITY = "equity"
    DEBT = "debt"
    REAL_ESTATE = "real_estate"
    PROJECT = "project"
    ACQUISITION = "acquisition"


class RiskCategory(str, Enum):
    """Risk kategorisi."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class DDStatus(str, Enum):
    """Durum tespiti durumu."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FLAGGED = "flagged"
    APPROVED = "approved"


class ValuationMethod(str, Enum):
    """Değerleme yöntemi."""

    DCF = "dcf"
    COMPARABLE = "comparable"
    ASSET_BASED = "asset_based"
    EARNINGS_MULTIPLE = "earnings_multiple"
    BOOK_VALUE = "book_value"


class PortfolioStrategy(str, Enum):
    """Portföy stratejisi."""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    GROWTH = "growth"
    AGGRESSIVE = "aggressive"
    INCOME = "income"


class RecommendationAction(str, Enum):
    """Öneri aksiyonu."""

    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    WAIT = "wait"
    INVESTIGATE = "investigate"


class InvestmentRecord(BaseModel):
    """Yatırım kaydı."""

    investment_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    investment_type: InvestmentType = (
        InvestmentType.PROJECT
    )
    amount: float = 0.0
    risk_category: RiskCategory = (
        RiskCategory.MODERATE
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class PortfolioRecord(BaseModel):
    """Portföy kaydı."""

    portfolio_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    strategy: PortfolioStrategy = (
        PortfolioStrategy.BALANCED
    )
    total_value: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class DDRecord(BaseModel):
    """Durum tespiti kaydı."""

    dd_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    investment_id: str = ""
    status: DDStatus = (
        DDStatus.NOT_STARTED
    )
    findings: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class AnalysisRecord(BaseModel):
    """Analiz kaydı."""

    analysis_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    investment_id: str = ""
    method: ValuationMethod = (
        ValuationMethod.DCF
    )
    result: float = 0.0
    recommendation: RecommendationAction = (
        RecommendationAction.INVESTIGATE
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None
