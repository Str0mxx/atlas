"""
Working MVP Core veri modelleri.

Cekirdek motor, olay dongusu, oturum,
WebSocket, gorev, yapilandirma,
saglik, kapanma modelleri.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Enum'lar ---


class EngineState(str, Enum):
    """Motor durumu."""

    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class EventPriority(str, Enum):
    """Olay onceligi."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class SessionState(str, Enum):
    """Oturum durumu."""

    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CLOSED = "closed"


class ConnectionState(str, Enum):
    """Baglanti durumu."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class TaskState(str, Enum):
    """Gorev durumu."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class HealthState(str, Enum):
    """Saglik durumu."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckType(str, Enum):
    """Kontrol tipi."""

    LIVENESS = "liveness"
    READINESS = "readiness"
    DEPENDENCY = "dependency"
    CUSTOM = "custom"


class ShutdownPhase(str, Enum):
    """Kapanma fazI."""

    RUNNING = "running"
    DRAINING = "draining"
    COMPLETING = "completing"
    CLEANING = "cleaning"
    PERSISTING = "persisting"
    STOPPED = "stopped"


class MergeStrategy(str, Enum):
    """Birlestirme stratejisi."""

    OVERRIDE = "override"
    MERGE_DEEP = "merge_deep"
    MERGE_SHALLOW = "merge_shallow"
    KEEP_EXISTING = "keep_existing"


class TaskPriority(str, Enum):
    """Gorev onceligi."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# --- Modeller ---


class EngineInfo(BaseModel):
    """Motor bilgisi."""

    app_name: str = ""
    state: EngineState = (
        EngineState.CREATED
    )
    components: int = 0
    started_at: str | None = None


class EventInfo(BaseModel):
    """Olay bilgisi."""

    event_id: str = ""
    event_type: str = ""
    priority: EventPriority = (
        EventPriority.NORMAL
    )
    data: Any = None
    dispatched_at: str = ""


class SessionInfo(BaseModel):
    """Oturum bilgisi."""

    session_id: str = ""
    user_id: str = ""
    state: SessionState = (
        SessionState.ACTIVE
    )
    timeout: int = 3600
    created_at: str = ""


class WebSocketInfo(BaseModel):
    """WebSocket bilgisi."""

    connection_id: str = ""
    state: ConnectionState = (
        ConnectionState.CONNECTED
    )
    host: str = "0.0.0.0"
    port: int = 8765


class TaskInfo(BaseModel):
    """Gorev bilgisi."""

    task_id: str = ""
    state: TaskState = TaskState.PENDING
    priority: TaskPriority = (
        TaskPriority.NORMAL
    )
    submitted_at: str = ""
    completed_at: str | None = None


class HealthCheckResult(BaseModel):
    """Saglik kontrol sonucu."""

    name: str = ""
    check_type: CheckType = (
        CheckType.CUSTOM
    )
    passed: bool = False
    elapsed: float = 0.0
    critical: bool = False


class ShutdownInfo(BaseModel):
    """Kapanma bilgisi."""

    phase: ShutdownPhase = (
        ShutdownPhase.RUNNING
    )
    handlers_run: int = 0
    resources_cleaned: int = 0
    tasks_completed: int = 0
    elapsed: float = 0.0


class ConfigInfo(BaseModel):
    """Yapilandirma bilgisi."""

    config_count: int = 0
    default_count: int = 0
    sources: int = 0
    validators: int = 0


class MVPCoreSummary(BaseModel):
    """MVP Core ozeti."""

    running: bool = False
    engine_state: EngineState = (
        EngineState.CREATED
    )
    event_loop_running: bool = False
    ws_connections: int = 0
    active_sessions: int = 0
    task_queue: int = 0
    health_status: HealthState = (
        HealthState.UNKNOWN
    )
