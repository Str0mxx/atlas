"""
System Health Dashboard modelleri.

Sistem durumu, ısı haritası, kaynak,
kota, gecikme, uptime, uyarı modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class SystemStatus(str, Enum):
    """Sistem durumları."""

    healthy = "healthy"
    degraded = "degraded"
    down = "down"
    maintenance = "maintenance"
    unknown = "unknown"


class ResourceType(str, Enum):
    """Kaynak türleri."""

    cpu = "cpu"
    memory = "memory"
    disk = "disk"
    network = "network"
    gpu = "gpu"


class AlertSeverity(str, Enum):
    """Uyarı ciddiyet düzeyleri."""

    info = "info"
    warning = "warning"
    critical = "critical"
    emergency = "emergency"


class HeatmapColor(str, Enum):
    """Isı haritası renkleri."""

    green = "green"
    yellow = "yellow"
    orange = "orange"
    red = "red"


class RiskLevel(str, Enum):
    """Risk düzeyleri."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TrendDirection(str, Enum):
    """Trend yönleri."""

    improving = "improving"
    stable = "stable"
    declining = "declining"
    volatile = "volatile"


class SystemRecord(BaseModel):
    """Sistem kaydı."""

    system_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    name: str = ""
    category: str = "core"
    status: str = "healthy"
    health_score: float = 100.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class HeatmapCell(BaseModel):
    """Isı haritası hücresi."""

    cell_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    system_name: str = ""
    metric_name: str = ""
    value: float = 0.0
    color: str = "green"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class ResourceReading(BaseModel):
    """Kaynak okuma kaydı."""

    reading_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    resource_type: str = "cpu"
    value: float = 0.0
    status: str = "normal"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class QuotaRecord(BaseModel):
    """API kota kaydı."""

    quota_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    api_name: str = ""
    daily_limit: int = 1000
    daily_used: int = 0
    monthly_limit: int = 30000
    monthly_used: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class LatencyRecord(BaseModel):
    """Gecikme kaydı."""

    endpoint_name: str = ""
    response_ms: float = 0.0
    baseline_ms: float = 100.0
    status_code: int = 200
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class UptimeRecord(BaseModel):
    """Uptime kaydı."""

    service_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    name: str = ""
    uptime_percent: float = 100.0
    sla_target: float = 99.9
    sla_met: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class AlertRecord(BaseModel):
    """Uyarı kaydı."""

    alert_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    source: str = ""
    message: str = ""
    severity: str = "warning"
    status: str = "active"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class PredictionRecord(BaseModel):
    """Tahmin kaydı."""

    prediction_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    system_name: str = ""
    current_value: float = 100.0
    risk_level: str = "low"
    risk_score: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
