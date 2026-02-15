"""ATLAS Observability & Tracing modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TraceStatus(str, Enum):
    """İz durumu."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    SAMPLED_OUT = "sampled_out"


class MetricType(str, Enum):
    """Metrik tipi."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    RATE = "rate"
    DISTRIBUTION = "distribution"


class HealthStatus(str, Enum):
    """Saglik durumu."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"
    STARTING = "starting"


class AlertSeverity(str, Enum):
    """Uyari ciddiyeti."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"
    RESOLVED = "resolved"


class AnomalyType(str, Enum):
    """Anomali tipi."""

    SPIKE = "spike"
    DROP = "drop"
    TREND = "trend"
    SEASONAL = "seasonal"
    OUTLIER = "outlier"
    PATTERN_BREAK = "pattern_break"


class SLALevel(str, Enum):
    """SLA seviyesi."""

    PLATINUM = "platinum"
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    BASIC = "basic"
    CUSTOM = "custom"


class TraceRecord(BaseModel):
    """İz kaydi modeli."""

    trace_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    status: TraceStatus = TraceStatus.ACTIVE
    span_count: int = 0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class MetricRecord(BaseModel):
    """Metrik kaydi modeli."""

    metric_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    metric_type: MetricType = MetricType.COUNTER
    value: float = 0.0
    labels: dict[str, str] = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class AlertRecord(BaseModel):
    """Uyari kaydi modeli."""

    alert_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    acknowledged: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ObservabilitySnapshot(BaseModel):
    """İzlenebilirlik snapshot modeli."""

    total_traces: int = 0
    total_metrics: int = 0
    total_alerts: int = 0
    health_status: HealthStatus = HealthStatus.UNKNOWN
    active_anomalies: int = 0
    sla_compliance: float = 100.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
