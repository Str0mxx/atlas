"""ATLAS Self-Benchmarking Framework modelleri.

Kendi kendini olcme ve degerlendirme veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class KPICategory(str, Enum):
    """KPI kategorisi."""

    SYSTEM = "system"
    AGENT = "agent"
    BUSINESS = "business"
    QUALITY = "quality"
    CUSTOM = "custom"


class MetricType(str, Enum):
    """Metrik tipi."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"
    PERCENTAGE = "percentage"


class TrendDirection(str, Enum):
    """Trend yonu."""

    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    ANOMALY = "anomaly"
    INSUFFICIENT = "insufficient"


class AlertSeverity(str, Enum):
    """Uyari ciddiyeti."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    IMPROVEMENT = "improvement"
    DEGRADATION = "degradation"


class ReportType(str, Enum):
    """Rapor tipi."""

    PERFORMANCE = "performance"
    TREND = "trend"
    COMPARISON = "comparison"
    EXECUTIVE = "executive"
    DETAILED = "detailed"


class ExperimentPhase(str, Enum):
    """Deney asamasi."""

    SETUP = "setup"
    RUNNING = "running"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class KPIRecord(BaseModel):
    """KPI kaydi."""

    kpi_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    category: KPICategory = KPICategory.CUSTOM
    target: float = 0.0
    threshold: float = 0.0
    unit: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class BenchmarkResult(BaseModel):
    """Benchmark sonucu."""

    result_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    kpi_id: str = ""
    score: float = 0.0
    target_met: bool = False
    period: str = ""
    metadata: dict = Field(default_factory=dict)
    measured_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class AlertRecord(BaseModel):
    """Uyari kaydi."""

    alert_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    kpi_id: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    acknowledged: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class BenchmarkSnapshot(BaseModel):
    """Benchmark snapshot."""

    total_kpis: int = 0
    targets_met: int = 0
    active_experiments: int = 0
    active_alerts: int = 0
    avg_score: float = 0.0
    trend: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
