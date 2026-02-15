"""ATLAS ML Pipeline modelleri.

Makine ogrenmesi islem hatti veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ScalingMethod(str, Enum):
    """Olcekleme yontemi."""

    STANDARD = "standard"
    MINMAX = "minmax"
    ROBUST = "robust"
    MAXABS = "maxabs"
    NORMALIZE = "normalize"
    LOG = "log"


class ModelStatus(str, Enum):
    """Model durumu."""

    DRAFT = "draft"
    TRAINING = "training"
    TRAINED = "trained"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    RETIRED = "retired"


class DriftType(str, Enum):
    """Kayma tipi."""

    DATA = "data"
    CONCEPT = "concept"
    FEATURE = "feature"
    PREDICTION = "prediction"
    LABEL = "label"
    COVARIATE = "covariate"


class MetricType(str, Enum):
    """Metrik tipi."""

    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    AUC = "auc"
    MSE = "mse"


class ExperimentStatus(str, Enum):
    """Deney durumu."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class PipelineStage(str, Enum):
    """Pipeline asamasi."""

    PREPROCESSING = "preprocessing"
    FEATURE_ENGINEERING = "feature_engineering"
    TRAINING = "training"
    EVALUATION = "evaluation"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"


class ModelRecord(BaseModel):
    """Model kaydi."""

    model_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    version: str = "1.0.0"
    status: ModelStatus = ModelStatus.DRAFT
    metrics: dict[str, float] = Field(
        default_factory=dict,
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ExperimentRecord(BaseModel):
    """Deney kaydi."""

    experiment_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    status: ExperimentStatus = (
        ExperimentStatus.PENDING
    )
    runs: int = 0
    best_metric: float = 0.0
    parameters: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class DriftRecord(BaseModel):
    """Kayma kaydi."""

    drift_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    drift_type: DriftType = DriftType.DATA
    feature: str = ""
    score: float = 0.0
    threshold: float = 0.05
    detected: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class MLPipelineSnapshot(BaseModel):
    """Pipeline snapshot."""

    total_models: int = 0
    deployed_models: int = 0
    active_experiments: int = 0
    drift_alerts: int = 0
    pipeline_stage: PipelineStage = (
        PipelineStage.PREPROCESSING
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
