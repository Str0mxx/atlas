"""ATLAS Agent Spawner modelleri.

Dinamik agent olusturma, yasam dongusu yonetimi,
kaynak tahsisi, yetenek enjeksiyonu ve havuz yonetimi modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Agent durumu."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


class SpawnMethod(str, Enum):
    """Olusturma yontemi."""

    TEMPLATE = "template"
    SCRATCH = "scratch"
    CLONE = "clone"
    HYBRID = "hybrid"
    POOL = "pool"


class TerminationType(str, Enum):
    """Sonlandirma tipi."""

    GRACEFUL = "graceful"
    FORCE = "force"
    TIMEOUT = "timeout"
    ERROR = "error"
    IDLE = "idle"


class ResourceType(str, Enum):
    """Kaynak tipi."""

    MEMORY = "memory"
    CPU = "cpu"
    API_QUOTA = "api_quota"
    STORAGE = "storage"


class CapabilityAction(str, Enum):
    """Yetenek aksiyonu."""

    ADD = "add"
    REMOVE = "remove"
    UPGRADE = "upgrade"
    SWAP = "swap"


class PoolStrategy(str, Enum):
    """Havuz stratejisi."""

    FIXED = "fixed"
    ELASTIC = "elastic"
    ON_DEMAND = "on_demand"


class TemplateCategory(str, Enum):
    """Sablon kategorisi."""

    WORKER = "worker"
    SPECIALIST = "specialist"
    MONITOR = "monitor"
    COORDINATOR = "coordinator"
    CUSTOM = "custom"


class AgentTemplate(BaseModel):
    """Agent sablonu."""

    template_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    category: TemplateCategory = TemplateCategory.WORKER
    capabilities: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    resource_profile: dict[str, float] = Field(default_factory=dict)
    behavior_preset: str = "default"
    description: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class SpawnedAgent(BaseModel):
    """Olusturulmus agent."""

    agent_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    state: AgentState = AgentState.INITIALIZING
    spawn_method: SpawnMethod = SpawnMethod.TEMPLATE
    template_id: str = ""
    parent_agent_id: str = ""
    capabilities: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    resources: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    workload: float = Field(default=0.0, ge=0.0, le=1.0)
    error_count: int = 0
    restart_count: int = 0
    spawned_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    last_heartbeat: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ResourceAllocation(BaseModel):
    """Kaynak tahsisi."""

    allocation_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    agent_id: str = ""
    resource_type: ResourceType = ResourceType.MEMORY
    allocated: float = 0.0
    used: float = 0.0
    limit: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class CapabilityChange(BaseModel):
    """Yetenek degisikligi."""

    change_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    agent_id: str = ""
    action: CapabilityAction = CapabilityAction.ADD
    capability: str = ""
    old_version: str = ""
    new_version: str = ""
    success: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class TerminationRecord(BaseModel):
    """Sonlandirma kaydi."""

    record_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    agent_id: str = ""
    agent_name: str = ""
    termination_type: TerminationType = TerminationType.GRACEFUL
    reason: str = ""
    state_preserved: bool = False
    cleanup_done: bool = False
    terminated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class PoolStatus(BaseModel):
    """Havuz durumu."""

    pool_id: str = ""
    strategy: PoolStrategy = PoolStrategy.FIXED
    total_agents: int = 0
    active_agents: int = 0
    idle_agents: int = 0
    assigned_agents: int = 0
    target_size: int = 0


class SpawnerSnapshot(BaseModel):
    """Spawner anlık goruntusu."""

    total_agents: int = 0
    active_agents: int = 0
    paused_agents: int = 0
    error_agents: int = 0
    pool_size: int = 0
    total_spawned: int = 0
    total_terminated: int = 0
    avg_workload: float = 0.0
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
