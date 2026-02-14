"""Workflow & Automation Engine veri modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Dugum turu."""

    ACTION = "action"
    CONDITION = "condition"
    TRIGGER = "trigger"
    LOOP = "loop"
    MERGE = "merge"
    END = "end"


class TriggerType(str, Enum):
    """Tetikleyici turu."""

    EVENT = "event"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    MANUAL = "manual"
    CONDITIONAL = "conditional"


class WorkflowStatus(str, Enum):
    """Is akisi durumu."""

    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class ActionType(str, Enum):
    """Aksiyon turu."""

    BUILTIN = "builtin"
    CUSTOM = "custom"
    API_CALL = "api_call"
    SCRIPT = "script"
    AGENT = "agent"


class VariableScope(str, Enum):
    """Degisken kapsamı."""

    LOCAL = "local"
    WORKFLOW = "workflow"
    GLOBAL = "global"
    SECRET = "secret"


class LoopType(str, Enum):
    """Dongu turu."""

    FOR_EACH = "for_each"
    WHILE = "while"
    PARALLEL = "parallel"
    COUNT = "count"


class WorkflowRecord(BaseModel):
    """Is akisi kaydi."""

    workflow_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    status: WorkflowStatus = WorkflowStatus.DRAFT
    nodes: list[dict[str, Any]] = Field(
        default_factory=list,
    )
    connections: list[dict[str, Any]] = Field(
        default_factory=list,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ExecutionRecord(BaseModel):
    """Yurutme kaydi."""

    execution_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    workflow_id: str = ""
    status: WorkflowStatus = WorkflowStatus.RUNNING
    steps: list[dict[str, Any]] = Field(
        default_factory=list,
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    duration: float = 0.0


class TriggerRecord(BaseModel):
    """Tetikleyici kaydi."""

    trigger_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    trigger_type: TriggerType = TriggerType.MANUAL
    workflow_id: str = ""
    config: dict[str, Any] = Field(
        default_factory=dict,
    )
    enabled: bool = True


class WorkflowSnapshot(BaseModel):
    """Is akisi goruntusu."""

    total_workflows: int = 0
    active: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    total_executions: int = 0
    avg_duration: float = 0.0
    active_triggers: int = 0
