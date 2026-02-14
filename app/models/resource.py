"""Resource Management veri modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    """Kaynak turu."""

    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    API = "api"


class ResourceStatus(str, Enum):
    """Kaynak durumu."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


class AlertSeverity(str, Enum):
    """Uyari onem derecesi."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CostCategory(str, Enum):
    """Maliyet kategorisi."""

    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    API_CALL = "api_call"
    LICENSE = "license"


class ScaleDirection(str, Enum):
    """Olcekleme yonu."""

    UP = "up"
    DOWN = "down"
    NONE = "none"


class OptimizationAction(str, Enum):
    """Optimizasyon aksiyonu."""

    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    REBALANCE = "rebalance"
    CACHE = "cache"
    COMPRESS = "compress"
    EVICT = "evict"


class ResourceMetric(BaseModel):
    """Kaynak metrigi."""

    metric_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    resource_type: ResourceType = ResourceType.CPU
    name: str = ""
    value: float = 0.0
    unit: str = ""
    status: ResourceStatus = ResourceStatus.NORMAL
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class CostRecord(BaseModel):
    """Maliyet kaydi."""

    cost_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    category: CostCategory = CostCategory.COMPUTE
    amount: float = 0.0
    currency: str = "USD"
    resource: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class QuotaRecord(BaseModel):
    """Kota kaydi."""

    quota_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    service: str = ""
    limit: int = 0
    used: int = 0
    remaining: int = 0
    reset_at: str = ""


class ResourceAlert(BaseModel):
    """Kaynak uyarisi."""

    alert_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    resource_type: ResourceType = ResourceType.CPU
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    resolved: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ResourceSnapshot(BaseModel):
    """Kaynak goruntusu."""

    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    storage_usage: float = 0.0
    network_usage: float = 0.0
    api_quota_used: float = 0.0
    total_cost: float = 0.0
    active_alerts: int = 0
    optimizations_applied: int = 0
