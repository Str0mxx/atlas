"""ATLAS Report & Insight Generator modelleri.

Rapor oluşturma, içgörü üretimi,
dışa aktarma, biçimlendirme modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ReportFormat(str, Enum):
    """Rapor formatı."""

    PDF = "pdf"
    WORD = "word"
    HTML = "html"
    MARKDOWN = "markdown"
    TELEGRAM = "telegram"
    JSON = "json"


class InsightType(str, Enum):
    """İçgörü tipi."""

    OPPORTUNITY = "opportunity"
    RISK = "risk"
    TREND = "trend"
    ANOMALY = "anomaly"
    RECOMMENDATION = "recommendation"
    WARNING = "warning"


class ReportStatus(str, Enum):
    """Rapor durumu."""

    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    EXPORTED = "exported"
    ARCHIVED = "archived"
    FAILED = "failed"


class ChartType(str, Enum):
    """Grafik tipi."""

    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    TABLE = "table"
    HEATMAP = "heatmap"


class PriorityLevel(str, Enum):
    """Öncelik seviyesi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScoringMethod(str, Enum):
    """Puanlama yöntemi."""

    WEIGHTED = "weighted"
    SIMPLE = "simple"
    NORMALIZED = "normalized"
    RANKED = "ranked"
    PERCENTILE = "percentile"


class ReportRecord(BaseModel):
    """Rapor kaydı."""

    report_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    title: str = ""
    format: ReportFormat = ReportFormat.MARKDOWN
    status: ReportStatus = ReportStatus.DRAFT
    sections: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class InsightRecord(BaseModel):
    """İçgörü kaydı."""

    insight_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    insight_type: InsightType = (
        InsightType.RECOMMENDATION
    )
    priority: PriorityLevel = PriorityLevel.MEDIUM
    description: str = ""
    action_items: list[str] = Field(
        default_factory=list,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ComparisonRecord(BaseModel):
    """Karşılaştırma kaydı."""

    comparison_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    items: list[str] = Field(
        default_factory=list,
    )
    criteria: list[str] = Field(
        default_factory=list,
    )
    method: ScoringMethod = ScoringMethod.WEIGHTED
    winner: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ReportGenSnapshot(BaseModel):
    """Rapor üretici anlık görüntü."""

    reports_generated: int = 0
    insights_extracted: int = 0
    exports_completed: int = 0
    comparisons_made: int = 0
    active_templates: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
