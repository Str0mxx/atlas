"""
Business Model Canvas & Pivot Detector modelleri.

İş modeli kanvas, gelir akışı, müşteri segmenti,
maliyet yapısı, değer önerisi, pivot sinyali modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CanvasSection(str, Enum):
    """Kanvas bölüm türleri."""

    key_partners = "key_partners"
    key_activities = "key_activities"
    key_resources = "key_resources"
    value_propositions = "value_propositions"
    customer_relationships = "customer_relationships"
    channels = "channels"
    customer_segments = "customer_segments"
    cost_structure = "cost_structure"
    revenue_streams = "revenue_streams"


class RevenueType(str, Enum):
    """Gelir türleri."""

    subscription = "subscription"
    transaction = "transaction"
    licensing = "licensing"
    advertising = "advertising"
    freemium = "freemium"
    marketplace = "marketplace"


class CostCategory(str, Enum):
    """Maliyet kategorileri."""

    fixed = "fixed"
    variable = "variable"
    semi_variable = "semi_variable"
    one_time = "one_time"
    recurring = "recurring"


class PivotType(str, Enum):
    """Pivot türleri."""

    customer_segment = "customer_segment"
    value_proposition = "value_proposition"
    revenue_model = "revenue_model"
    channel = "channel"
    technology = "technology"
    platform = "platform"


class CompetitivePosition(str, Enum):
    """Rekabet pozisyonu türleri."""

    leader = "leader"
    challenger = "challenger"
    follower = "follower"
    niche = "niche"
    new_entrant = "new_entrant"


class ModelMaturity(str, Enum):
    """Model olgunluk seviyeleri."""

    ideation = "ideation"
    validation = "validation"
    growth = "growth"
    maturity = "maturity"
    renewal = "renewal"


class CanvasRecord(BaseModel):
    """Kanvas kaydı modeli."""

    canvas_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = "Untitled Canvas"
    version: int = 1
    sections: dict[str, Any] = Field(
        default_factory=dict
    )
    maturity: str = "ideation"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class RevenueStreamRecord(BaseModel):
    """Gelir akışı kaydı modeli."""

    stream_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = "Default Stream"
    revenue_type: str = "subscription"
    amount: float = 0.0
    growth_rate: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class PivotSignalRecord(BaseModel):
    """Pivot sinyal kaydı modeli."""

    signal_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    signal_type: str = "market_feedback"
    severity: str = "medium"
    description: str = ""
    pivot_type: str = "value_proposition"
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class CompetitiveAnalysisRecord(BaseModel):
    """Rekabet analizi kaydı modeli."""

    analysis_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    competitor: str = ""
    position: str = "follower"
    moat_score: float = 0.0
    threat_level: str = "medium"
    analyzed_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
