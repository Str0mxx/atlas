"""ATLAS A/B Testing & Experiment Platform modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ExperimentStatus(str, Enum):
    """Deney durumu."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class VariantType(str, Enum):
    """Varyant tipi."""

    CONTROL = "control"
    TREATMENT = "treatment"
    HOLDOUT = "holdout"
    BASELINE = "baseline"


class SignificanceLevel(str, Enum):
    """Anlamlılık seviyesi."""

    P90 = "0.10"
    P95 = "0.05"
    P99 = "0.01"
    P999 = "0.001"


class RolloutStage(str, Enum):
    """Yayılım aşaması."""

    CANARY = "canary"
    PARTIAL = "partial"
    MAJORITY = "majority"
    FULL = "full"


class MetricType(str, Enum):
    """Metrik tipi."""

    CONVERSION = "conversion"
    REVENUE = "revenue"
    ENGAGEMENT = "engagement"
    RETENTION = "retention"


class DesignType(str, Enum):
    """Tasarım tipi."""

    AB = "ab"
    MULTIVARIATE = "multivariate"
    FACTORIAL = "factorial"
    SEQUENTIAL = "sequential"


class ExperimentRecord(BaseModel):
    """Deney kaydı."""

    experiment_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    status: str = "draft"
    design_type: str = "ab"
    confidence: float = 0.95
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class VariantRecord(BaseModel):
    """Varyant kaydı."""

    variant_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    variant_type: str = "treatment"
    traffic_pct: float = 50.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ResultRecord(BaseModel):
    """Sonuç kaydı."""

    result_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    experiment_id: str = ""
    winner: str = ""
    p_value: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class RolloutRecord(BaseModel):
    """Yayılım kaydı."""

    rollout_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    experiment_id: str = ""
    stage: str = "canary"
    percentage: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
