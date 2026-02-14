"""ATLAS Inter-System Bridge modelleri.

Sistemler arasi kopru, mesaj yolu, olay yonlendirme,
API gecidi, veri donusturme ve saglik birlestirme modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SystemState(str, Enum):
    """Sistem durumu."""

    REGISTERED = "registered"
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class MessagePriority(str, Enum):
    """Mesaj onceligi."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageState(str, Enum):
    """Mesaj durumu."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD = "dead"


class EventType(str, Enum):
    """Olay tipi."""

    SYSTEM = "system"
    DATA = "data"
    ERROR = "error"
    LIFECYCLE = "lifecycle"
    HEALTH = "health"


class HealthStatus(str, Enum):
    """Saglik durumu."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class WorkflowState(str, Enum):
    """Is akisi durumu."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class SystemInfo(BaseModel):
    """Sistem bilgisi."""

    system_id: str = ""
    name: str = ""
    state: SystemState = SystemState.REGISTERED
    version: str = "1.0.0"
    capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    registered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class BusMessage(BaseModel):
    """Mesaj yolu mesaji."""

    message_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    topic: str = ""
    source: str = ""
    target: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    state: MessageState = MessageState.PENDING
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class BridgeEvent(BaseModel):
    """Kopru olayi."""

    event_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    event_type: EventType = EventType.SYSTEM
    source: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class WorkflowRecord(BaseModel):
    """Is akisi kaydi."""

    workflow_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    state: WorkflowState = WorkflowState.PENDING
    steps: list[str] = Field(default_factory=list)
    completed_steps: list[str] = Field(default_factory=list)
    systems_involved: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class HealthReport(BaseModel):
    """Saglik raporu."""

    system_id: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    details: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class BridgeSnapshot(BaseModel):
    """Kopru anlik goruntusu."""

    total_systems: int = 0
    active_systems: int = 0
    total_messages: int = 0
    pending_messages: int = 0
    total_events: int = 0
    active_workflows: int = 0
    healthy_systems: int = 0
    avg_health: float = Field(default=1.0, ge=0.0, le=1.0)
