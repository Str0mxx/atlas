"""ATLAS Event Sourcing & CQRS modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Olay tipi."""

    DOMAIN = "domain"
    INTEGRATION = "integration"
    SYSTEM = "system"
    SNAPSHOT = "snapshot"
    COMPENSATION = "compensation"
    NOTIFICATION = "notification"


class CommandStatus(str, Enum):
    """Komut durumu."""

    PENDING = "pending"
    VALIDATED = "validated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class SagaState(str, Enum):
    """Saga durumu."""

    STARTED = "started"
    RUNNING = "running"
    COMPENSATING = "compensating"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class ProjectionStatus(str, Enum):
    """Projeksiyon durumu."""

    ACTIVE = "active"
    REBUILDING = "rebuilding"
    PAUSED = "paused"
    ERROR = "error"
    STALE = "stale"
    DISABLED = "disabled"


class ConsistencyLevel(str, Enum):
    """Tutarlilik seviyesi."""

    STRONG = "strong"
    EVENTUAL = "eventual"
    CAUSAL = "causal"
    READ_YOUR_WRITES = "read_your_writes"
    MONOTONIC = "monotonic"
    SESSION = "session"


class AggregateStatus(str, Enum):
    """Aggregate durumu."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    LOCKED = "locked"
    MIGRATING = "migrating"
    CORRUPTED = "corrupted"


class EventRecord(BaseModel):
    """Olay kaydi modeli."""

    event_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    event_type: EventType = EventType.DOMAIN
    aggregate_id: str = ""
    aggregate_type: str = ""
    version: int = 1
    data: dict[str, Any] = Field(
        default_factory=dict,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CommandRecord(BaseModel):
    """Komut kaydi modeli."""

    command_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    command_type: str = ""
    status: CommandStatus = CommandStatus.PENDING
    payload: dict[str, Any] = Field(
        default_factory=dict,
    )
    result: dict[str, Any] = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class SagaRecord(BaseModel):
    """Saga kaydi modeli."""

    saga_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    saga_type: str = ""
    state: SagaState = SagaState.STARTED
    steps_completed: int = 0
    steps_total: int = 0
    compensations: list[str] = Field(
        default_factory=list,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ESSnapshot(BaseModel):
    """Event Sourcing snapshot modeli."""

    total_events: int = 0
    total_commands: int = 0
    active_sagas: int = 0
    active_projections: int = 0
    subscribers: int = 0
    aggregates: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
