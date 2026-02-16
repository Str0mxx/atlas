"""ATLAS Market & Trend Intelligence modelleri.

Pazar istihbaratı, trend takibi, rakip analizi,
patent, akademik, düzenleme modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TrendStage(str, Enum):
    """Trend yaşam döngüsü aşaması."""

    EMERGING = "emerging"
    GROWING = "growing"
    MATURING = "maturing"
    DECLINING = "declining"
    STABLE = "stable"
    REVIVING = "reviving"


class SignalType(str, Enum):
    """Sinyal tipi."""

    MARKET = "market"
    COMPETITOR = "competitor"
    PATENT = "patent"
    ACADEMIC = "academic"
    REGULATION = "regulation"
    INVESTMENT = "investment"


class CompetitorThreat(str, Enum):
    """Rakip tehdit seviyesi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"
    UNKNOWN = "unknown"


class PatentStatus(str, Enum):
    """Patent durumu."""

    FILED = "filed"
    PENDING = "pending"
    GRANTED = "granted"
    EXPIRED = "expired"
    REJECTED = "rejected"
    ABANDONED = "abandoned"


class RegulationType(str, Enum):
    """Düzenleme tipi."""

    LAW = "law"
    REGULATION = "regulation"
    DIRECTIVE = "directive"
    GUIDELINE = "guideline"
    STANDARD = "standard"
    POLICY = "policy"


class MarketSegment(str, Enum):
    """Pazar segmenti."""

    TAM = "tam"
    SAM = "sam"
    SOM = "som"
    NICHE = "niche"
    ADJACENT = "adjacent"
    GLOBAL = "global"


class TrendRecord(BaseModel):
    """Trend kaydı."""

    trend_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    stage: TrendStage = TrendStage.EMERGING
    momentum: float = 0.0
    confidence: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class CompetitorRecord(BaseModel):
    """Rakip kaydı."""

    competitor_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    threat_level: CompetitorThreat = (
        CompetitorThreat.UNKNOWN
    )
    market_share: float = 0.0
    strengths: list[str] = Field(
        default_factory=list,
    )
    weaknesses: list[str] = Field(
        default_factory=list,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class SignalRecord(BaseModel):
    """Sinyal kaydı."""

    signal_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    signal_type: SignalType = (
        SignalType.MARKET
    )
    source: str = ""
    strength: float = 0.0
    actionable: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class MarketIntelSnapshot(BaseModel):
    """Pazar istihbaratı anlık görüntü."""

    trends_tracked: int = 0
    competitors_mapped: int = 0
    patents_scanned: int = 0
    signals_collected: int = 0
    regulations_monitored: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
