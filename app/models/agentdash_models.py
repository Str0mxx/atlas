"""Agent Performance Dashboard modelleri."""

from enum import Enum

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent durum."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    RETIRED = "retired"


class MetricType(str, Enum):
    """Metrik turu."""

    TASK = "task"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    SPEED = "speed"
    COST = "cost"


class TaskStatus(str, Enum):
    """Gorev durumu."""

    COMPLETED = "completed"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"


class RankingMetric(str, Enum):
    """Siralama metrigi."""

    OVERALL = "overall"
    SUCCESS_RATE = "success_rate"
    QUALITY = "quality"
    SPEED = "speed"
    COST_EFFICIENCY = "cost_efficiency"


class HealthLevel(str, Enum):
    """Saglik seviyesi."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class TrendDirection(str, Enum):
    """Trend yonu."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    INSUFFICIENT = "insufficient_data"


class AgentMetricRecord(BaseModel):
    """Agent metrik kaydi."""

    metric_id: str = ""
    agent_id: str = ""
    metric_type: MetricType = (
        MetricType.TASK
    )
    success: bool = True
    quality_score: float = Field(
        default=0.0, ge=0.0, le=100.0
    )
    duration_ms: int = Field(
        default=0, ge=0
    )
    period: str = ""


class TaskRecord(BaseModel):
    """Gorev kaydi."""

    task_id: str = ""
    agent_id: str = ""
    task_type: str = "general"
    status: TaskStatus = TaskStatus.COMPLETED
    duration_ms: int = Field(
        default=0, ge=0
    )
    failure_reason: str = ""
    period: str = ""


class ConfidenceRecord(BaseModel):
    """Guven kaydi."""

    confidence_id: str = ""
    agent_id: str = ""
    predicted_confidence: float = Field(
        default=0.0, ge=0.0, le=100.0
    )
    actual_outcome: bool = True
    task_type: str = "general"
    period: str = ""


class CostRecord(BaseModel):
    """Maliyet kaydi."""

    cost_id: str = ""
    agent_id: str = ""
    task_id: str = ""
    api_cost: float = Field(
        default=0.0, ge=0.0
    )
    compute_cost: float = Field(
        default=0.0, ge=0.0
    )
    total_cost: float = Field(
        default=0.0, ge=0.0
    )
    duration_ms: int = Field(
        default=0, ge=0
    )
    success: bool = True
    period: str = ""


class ImprovementRecord(BaseModel):
    """Iyilestirme kaydi."""

    improvement_id: str = ""
    agent_id: str = ""
    metric: str = "performance"
    before_value: float = 0.0
    after_value: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    action_taken: str = ""
    period: str = ""


class AgentLifecycleRecord(BaseModel):
    """Agent yasam dongusu kaydi."""

    agent_id: str = ""
    agent_name: str = ""
    agent_type: str = "general"
    status: AgentStatus = AgentStatus.ACTIVE
    version: str = "1.0.0"
    health_score: float = Field(
        default=100.0, ge=0.0, le=100.0
    )
    health_level: HealthLevel = (
        HealthLevel.HEALTHY
    )
