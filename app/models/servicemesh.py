"""ATLAS Service Mesh & Microservices modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    """Servis durumu."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAINING = "draining"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


class LoadBalancerAlgorithm(str, Enum):
    """Yuk dengeleme algoritmasi."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    RANDOM = "random"
    CONSISTENT_HASH = "consistent_hash"
    HEALTH_AWARE = "health_aware"


class CircuitState(str, Enum):
    """Devre durumu."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    FORCED_OPEN = "forced_open"
    FORCED_CLOSED = "forced_closed"
    DISABLED = "disabled"


class RetryStrategy(str, Enum):
    """Yeniden deneme stratejisi."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    JITTER = "jitter"
    FIBONACCI = "fibonacci"
    NONE = "none"


class TrafficPolicy(str, Enum):
    """Trafik politikasi."""

    NORMAL = "normal"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    AB_TEST = "ab_test"
    DARK_LAUNCH = "dark_launch"
    MIRROR = "mirror"


class ProxyMode(str, Enum):
    """Vekil modu."""

    SIDECAR = "sidecar"
    INGRESS = "ingress"
    EGRESS = "egress"
    PASSTHROUGH = "passthrough"
    INTERCEPT = "intercept"
    TRANSPARENT = "transparent"


class MeshServiceRecord(BaseModel):
    """Servis kaydi modeli."""

    service_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    status: ServiceStatus = ServiceStatus.ACTIVE
    instances: int = 0
    version: str = "1.0.0"
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CircuitRecord(BaseModel):
    """Devre kaydi modeli."""

    circuit_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    service: str = ""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class TrafficRecord(BaseModel):
    """Trafik kaydi modeli."""

    traffic_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    policy: TrafficPolicy = TrafficPolicy.NORMAL
    source: str = ""
    destination: str = ""
    weight: float = 100.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class MeshSnapshot(BaseModel):
    """Mesh snapshot modeli."""

    total_services: int = 0
    total_instances: int = 0
    active_circuits: int = 0
    open_circuits: int = 0
    active_routes: int = 0
    proxy_count: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
