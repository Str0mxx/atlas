"""ATLAS Hierarchical Agent Controller modelleri.

Agent hiyerarsisi, kume yonetimi, yetki devri,
denetim, raporlama, komut zinciri ve otonomi modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuthorityLevel(str, Enum):
    """Yetki seviyesi."""

    MASTER = "master"
    SUPERVISOR = "supervisor"
    LEAD = "lead"
    WORKER = "worker"
    OBSERVER = "observer"


class ClusterType(str, Enum):
    """Kume tipi."""

    BUSINESS = "business"
    TECHNICAL = "technical"
    COMMUNICATION = "communication"
    SECURITY = "security"
    ANALYTICS = "analytics"
    CUSTOM = "custom"


class DelegationStatus(str, Enum):
    """Yetki devri durumu."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class AutonomyLevel(str, Enum):
    """Otonomi seviyesi."""

    FULL = "full"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class CommandType(str, Enum):
    """Komut tipi."""

    DIRECTIVE = "directive"
    BROADCAST = "broadcast"
    TARGETED = "targeted"
    EMERGENCY = "emergency"
    FEEDBACK = "feedback"


class ConflictType(str, Enum):
    """Catisma tipi."""

    RESOURCE = "resource"
    PRIORITY = "priority"
    DECISION = "decision"
    DEADLOCK = "deadlock"
    AUTHORITY = "authority"


class ResolutionStrategy(str, Enum):
    """Cozum stratejisi."""

    PRIORITY_BASED = "priority_based"
    AUTHORITY_BASED = "authority_based"
    CONSENSUS = "consensus"
    ESCALATION = "escalation"
    RANDOM = "random"


class ReportType(str, Enum):
    """Rapor tipi."""

    STATUS = "status"
    PROGRESS = "progress"
    EXCEPTION = "exception"
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class AgentNode(BaseModel):
    """Agent dugumu."""

    agent_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    authority: AuthorityLevel = AuthorityLevel.WORKER
    autonomy: AutonomyLevel = AutonomyLevel.MEDIUM
    cluster_id: str = ""
    parent_id: str = ""
    children_ids: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    workload: float = Field(default=0.0, ge=0.0, le=1.0)
    active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ClusterInfo(BaseModel):
    """Kume bilgisi."""

    cluster_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    cluster_type: ClusterType = ClusterType.CUSTOM
    leader_id: str = ""
    member_ids: list[str] = Field(default_factory=list)
    max_members: int = 10
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    active: bool = True


class DelegationRecord(BaseModel):
    """Yetki devri kaydi."""

    delegation_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    task_id: str = ""
    from_agent: str = ""
    to_agent: str = ""
    priority: int = Field(default=5, ge=1, le=10)
    deadline_minutes: int = 0
    status: DelegationStatus = DelegationStatus.PENDING
    result: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class SupervisionEvent(BaseModel):
    """Denetim olayi."""

    event_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    agent_id: str = ""
    event_type: str = ""
    details: str = ""
    severity: str = "info"
    requires_intervention: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class CommandMessage(BaseModel):
    """Komut mesaji."""

    command_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    command_type: CommandType = CommandType.DIRECTIVE
    from_agent: str = ""
    to_agents: list[str] = Field(default_factory=list)
    content: str = ""
    priority: int = Field(default=5, ge=1, le=10)
    acknowledged_by: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ConflictRecord(BaseModel):
    """Catisma kaydi."""

    conflict_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    conflict_type: ConflictType = ConflictType.RESOURCE
    agents_involved: list[str] = Field(default_factory=list)
    resource: str = ""
    description: str = ""
    resolution: ResolutionStrategy = ResolutionStrategy.PRIORITY_BASED
    resolved: bool = False
    winner: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class HierarchyReport(BaseModel):
    """Hiyerarsi raporu."""

    report_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    report_type: ReportType = ReportType.STATUS
    agent_id: str = ""
    title: str = ""
    content: dict[str, Any] = Field(default_factory=dict)
    period_start: datetime | None = None
    period_end: datetime | None = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class HierarchySnapshot(BaseModel):
    """Hiyerarsi anlık goruntusu."""

    snapshot_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    total_agents: int = 0
    active_agents: int = 0
    total_clusters: int = 0
    pending_delegations: int = 0
    active_conflicts: int = 0
    avg_workload: float = 0.0
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
