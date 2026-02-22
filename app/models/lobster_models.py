"""Lobster Workflow Engine modelleri."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    """Adim durumlari."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    """Is akisi durumlari."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    """Adim turleri."""
    ACTION = "action"
    APPROVAL = "approval"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    DELAY = "delay"


class PipelineStep(BaseModel):
    """Pipeline adim modeli."""
    step_id: str = ""
    name: str = ""
    step_type: StepType = StepType.ACTION
    action: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    requires_approval: bool = False
    approver: str = ""
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    condition: str = ""


class Workflow(BaseModel):
    """Is akisi modeli."""
    workflow_id: str = ""
    name: str = ""
    description: str = ""
    steps: list[PipelineStep] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    current_step: int = 0
    variables: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    recording: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    """Onay istegi modeli."""
    request_id: str = ""
    workflow_id: str = ""
    step_id: str = ""
    step_name: str = ""
    description: str = ""
    requested_at: float = 0.0
    expires_at: float = 0.0
    status: str = "pending"
    approver: str = ""
    response: str = ""
    responded_at: float = 0.0


class WorkflowExecution(BaseModel):
    """Is akisi yurutme modeli."""
    execution_id: str = ""
    workflow_id: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    status: WorkflowStatus = WorkflowStatus.RUNNING
    steps_completed: int = 0
    steps_total: int = 0
    output: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class LobsterConfig(BaseModel):
    """Lobster yapilandirma modeli."""
    max_steps: int = 100
    default_timeout: int = 300
    max_retries: int = 3
    approval_timeout: int = 3600
    enable_recording: bool = True
    workflow_store_dir: str = "workspace/workflows"
    path_based_execution: bool = True
    windows_wrapper_resolution: bool = True
