"""ATLAS Contextual Availability & Priority modelleri.

Müsaitlik öğrenme, öncelik puanlama,
mesaj tamponlama, kesme kararı,
rutin tespiti, sessiz saat yönetimi.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AvailabilityState(str, Enum):
    """Müsaitlik durumu."""

    available = "available"
    busy = "busy"
    away = "away"
    dnd = "dnd"
    sleeping = "sleeping"
    offline = "offline"


class PriorityLevel(str, Enum):
    """Öncelik seviyesi."""

    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    informational = "informational"
    deferred = "deferred"


class InterruptAction(str, Enum):
    """Kesme aksiyonu."""

    deliver_now = "deliver_now"
    buffer = "buffer"
    digest = "digest"
    escalate = "escalate"
    discard = "discard"
    schedule = "schedule"


class RoutineType(str, Enum):
    """Rutin tipi."""

    daily = "daily"
    weekly = "weekly"
    workday = "workday"
    weekend = "weekend"
    custom = "custom"
    exception = "exception"


class DigestFrequency(str, Enum):
    """Özet sıklığı."""

    hourly = "hourly"
    every_4h = "every_4h"
    daily = "daily"
    twice_daily = "twice_daily"
    weekly = "weekly"
    on_available = "on_available"


class OverrideReason(str, Enum):
    """Geçersiz kılma nedeni."""

    emergency = "emergency"
    security = "security"
    financial = "financial"
    deadline = "deadline"
    user_request = "user_request"
    system_critical = "system_critical"


class AvailabilityRecord(BaseModel):
    """Müsaitlik kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    user_id: str = ""
    state: AvailabilityState = (
        AvailabilityState.available
    )
    confidence: float = 0.5
    source: str = "system"
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class BufferedMessage(BaseModel):
    """Tamponlanmış mesaj."""

    message_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    content: str = ""
    priority: PriorityLevel = PriorityLevel.medium
    source: str = ""
    action: InterruptAction = InterruptAction.buffer
    expires_at: datetime | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class RoutineRecord(BaseModel):
    """Rutin kaydı."""

    routine_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    routine_type: RoutineType = RoutineType.daily
    start_hour: int = 0
    end_hour: int = 23
    days: list[int] = Field(
        default_factory=list,
    )
    confidence: float = 0.5
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class AvailabilitySnapshot(BaseModel):
    """Müsaitlik sistem anlık görüntüsü."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    current_state: AvailabilityState = (
        AvailabilityState.available
    )
    buffered_count: int = 0
    routines_detected: int = 0
    overrides_active: int = 0
    quiet_hours_active: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
