"""ATLAS Streaming modelleri.

Akis isleme ve gercek zamanli analitik veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Kaynak tipi."""

    KAFKA = "kafka"
    WEBSOCKET = "websocket"
    FILE = "file"
    API = "api"
    GENERATOR = "generator"
    CUSTOM = "custom"


class WindowType(str, Enum):
    """Pencere tipi."""

    TUMBLING = "tumbling"
    SLIDING = "sliding"
    SESSION = "session"
    COUNT = "count"
    GLOBAL = "global"
    CUSTOM = "custom"


class JoinType(str, Enum):
    """Birlestirme tipi."""

    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    OUTER = "outer"
    TEMPORAL = "temporal"
    ENRICHMENT = "enrichment"


class SinkType(str, Enum):
    """Cikis tipi."""

    DATABASE = "database"
    KAFKA = "kafka"
    FILE = "file"
    API = "api"
    CONSOLE = "console"
    WEBHOOK = "webhook"


class ProcessingMode(str, Enum):
    """Isleme modu."""

    AT_LEAST_ONCE = "at_least_once"
    AT_MOST_ONCE = "at_most_once"
    EXACTLY_ONCE = "exactly_once"
    BEST_EFFORT = "best_effort"
    BATCH = "batch"
    MICRO_BATCH = "micro_batch"


class AlertLevel(str, Enum):
    """Alarm seviyesi."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"
    DEBUG = "debug"
    NOTICE = "notice"


class StreamRecord(BaseModel):
    """Akis kaydi."""

    stream_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    source_type: SourceType = SourceType.KAFKA
    name: str = ""
    events_processed: int = 0
    errors: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class WindowRecord(BaseModel):
    """Pencere kaydi."""

    window_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    window_type: WindowType = WindowType.TUMBLING
    size_seconds: int = 60
    events: int = 0
    aggregations: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CEPAlert(BaseModel):
    """CEP alarm kaydi."""

    alert_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    pattern: str = ""
    level: AlertLevel = AlertLevel.WARNING
    matched_events: int = 0
    details: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class StreamingSnapshot(BaseModel):
    """Streaming snapshot."""

    active_sources: int = 0
    active_sinks: int = 0
    total_events: int = 0
    active_windows: int = 0
    cep_alerts: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
