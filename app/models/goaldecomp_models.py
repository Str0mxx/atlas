"""ATLAS Goal Decomposition & Self-Tasking modelleri.

Hedef ayristirma ve kendine gorev atama veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class GoalStatus(str, Enum):
    """Hedef durumu."""

    draft = "draft"
    parsed = "parsed"
    decomposed = "decomposed"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class TaskPriority(str, Enum):
    """Gorev onceligi."""

    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    optional = "optional"


class DecompositionType(str, Enum):
    """Ayristirma tipi."""

    and_node = "and"
    or_node = "or"
    sequential = "sequential"
    parallel = "parallel"
    conditional = "conditional"


class AssignmentStrategy(str, Enum):
    """Atama stratejisi."""

    capability_match = "capability_match"
    load_balance = "load_balance"
    priority_first = "priority_first"
    fastest = "fastest"
    cheapest = "cheapest"


class ReplanReason(str, Enum):
    """Yeniden planlama nedeni."""

    failure = "failure"
    scope_change = "scope_change"
    resource_change = "resource_change"
    opportunity = "opportunity"
    timeout = "timeout"


class ValidationResult(str, Enum):
    """Dogrulama sonucu."""

    valid = "valid"
    invalid = "invalid"
    partial = "partial"
    needs_clarification = "needs_clarification"
    infeasible = "infeasible"


class GoalRecord(BaseModel):
    """Hedef kaydi."""

    goal_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    description: str = ""
    status: GoalStatus = GoalStatus.draft
    intent: str = ""
    success_criteria: list[str] = Field(
        default_factory=list,
    )
    constraints: list[str] = Field(
        default_factory=list,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class DecompositionNode(BaseModel):
    """Ayristirma dugumu."""

    node_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    goal_id: str = ""
    parent_id: str | None = None
    node_type: DecompositionType = (
        DecompositionType.and_node
    )
    description: str = ""
    children: list[str] = Field(
        default_factory=list,
    )
    dependencies: list[str] = Field(
        default_factory=list,
    )
    is_leaf: bool = False
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class TaskSpec(BaseModel):
    """Gorev spesifikasyonu."""

    task_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    goal_id: str = ""
    node_id: str = ""
    title: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.medium
    acceptance_criteria: list[str] = Field(
        default_factory=list,
    )
    estimated_hours: float = 0.0
    assigned_to: str = ""
    status: str = "pending"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class GoalDecompSnapshot(BaseModel):
    """Hedef ayristirma snapshot."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    total_goals: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    completion_pct: float = 0.0
    active_assignments: int = 0
    replans: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
