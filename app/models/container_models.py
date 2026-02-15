"""ATLAS Container modelleri.

Konteyner ve orkestrasyon veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ContainerStatus(str, Enum):
    """Konteyner durumu."""

    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    RESTARTING = "restarting"
    FAILED = "failed"


class DeploymentStrategy(str, Enum):
    """Dagitim stratejisi."""

    ROLLING = "rolling"
    RECREATE = "recreate"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    AB_TESTING = "ab_testing"
    SHADOW = "shadow"


class ServiceType(str, Enum):
    """Servis tipi."""

    CLUSTER_IP = "ClusterIP"
    NODE_PORT = "NodePort"
    LOAD_BALANCER = "LoadBalancer"
    EXTERNAL_NAME = "ExternalName"
    HEADLESS = "Headless"
    INGRESS = "Ingress"


class ProbeType(str, Enum):
    """Probe tipi."""

    LIVENESS = "liveness"
    READINESS = "readiness"
    STARTUP = "startup"
    HTTP = "http"
    TCP = "tcp"
    EXEC = "exec"


class ResourceType(str, Enum):
    """Kaynak tipi."""

    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    GPU = "gpu"
    NETWORK = "network"
    EPHEMERAL = "ephemeral"


class ChartStatus(str, Enum):
    """Chart durumu."""

    DEPLOYED = "deployed"
    PENDING = "pending"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    UNINSTALLED = "uninstalled"
    UPGRADING = "upgrading"


class ContainerRecord(BaseModel):
    """Konteyner kaydi."""

    container_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    image: str = ""
    status: ContainerStatus = (
        ContainerStatus.CREATED
    )
    cpu_limit: str = ""
    memory_limit: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class DeploymentRecord(BaseModel):
    """Dagitim kaydi."""

    deployment_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    replicas: int = 1
    strategy: DeploymentStrategy = (
        DeploymentStrategy.ROLLING
    )
    revision: int = 1
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class HelmRelease(BaseModel):
    """Helm release kaydi."""

    release_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    chart: str = ""
    version: str = "0.1.0"
    status: ChartStatus = ChartStatus.DEPLOYED
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ContainerSnapshot(BaseModel):
    """Container snapshot."""

    total_containers: int = 0
    running_containers: int = 0
    total_deployments: int = 0
    total_services: int = 0
    total_images: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
