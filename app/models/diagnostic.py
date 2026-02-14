"""Self-Diagnostic & Auto-Repair veri modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Saglik durumu."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ErrorSeverity(str, Enum):
    """Hata ciddiyeti."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BottleneckType(str, Enum):
    """Darbogaz turu."""
    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    NETWORK = "network"
    LATENCY = "latency"


class FixType(str, Enum):
    """Duzeltme turu."""
    CONFIG = "config"
    CACHE_CLEAR = "cache_clear"
    RESTART = "restart"
    DATA_REPAIR = "data_repair"
    DEPENDENCY = "dependency"
    ROLLBACK = "rollback"


class MaintenanceType(str, Enum):
    """Bakim turu."""
    CLEANUP = "cleanup"
    OPTIMIZATION = "optimization"
    BACKUP = "backup"
    UPDATE = "update"
    HEALTH_CHECK = "health_check"


class DiagnosticPhase(str, Enum):
    """Teshis asamasi."""
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    FIXING = "fixing"
    RECOVERING = "recovering"
    REPORTING = "reporting"
    IDLE = "idle"


class HealthReport(BaseModel):
    """Saglik raporu."""
    report_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    component: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    metrics: dict[str, float] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ErrorRecord(BaseModel):
    """Hata kaydi."""
    error_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    error_type: str = ""
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    component: str = ""
    root_cause: str = ""
    frequency: int = 1
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class BottleneckRecord(BaseModel):
    """Darbogaz kaydi."""
    bottleneck_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    bottleneck_type: BottleneckType = BottleneckType.LATENCY
    component: str = ""
    metric_value: float = 0.0
    threshold: float = 0.0
    impact: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class FixRecord(BaseModel):
    """Duzeltme kaydi."""
    fix_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    fix_type: FixType = FixType.CONFIG
    target: str = ""
    description: str = ""
    success: bool = False
    rollback_available: bool = True
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class RecoveryRecord(BaseModel):
    """Kurtarma kaydi."""
    recovery_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    action: str = ""
    target: str = ""
    success: bool = False
    data_integrity: float = Field(default=1.0, ge=0.0, le=1.0)
    duration_seconds: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class DiagnosticSnapshot(BaseModel):
    """Teshis goruntusu."""
    overall_health: HealthStatus = HealthStatus.UNKNOWN
    health_score: float = 0.0
    components_scanned: int = 0
    errors_found: int = 0
    bottlenecks_found: int = 0
    fixes_applied: int = 0
    recoveries_performed: int = 0
    maintenance_runs: int = 0
    uptime_seconds: float = 0.0
