"""
Fine-Tuning & Custom Model Manager modelleri.

Enum ve Pydantic modeller.
"""

from enum import Enum

from pydantic import BaseModel, Field


class FTProvider(str, Enum):
    """Fine-tune saglayicilari."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    CUSTOM = "custom"


class FTJobStatus(str, Enum):
    """Fine-tune is durumlari."""

    CREATED = "created"
    VALIDATING = "validating"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FTModelStage(str, Enum):
    """Model asamalari."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class FTDeployStrategy(str, Enum):
    """Dagitim stratejileri."""

    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    IMMEDIATE = "immediate"


class FTDriftType(str, Enum):
    """Kayma tipleri."""

    DATA_DRIFT = "data_drift"
    MODEL_DRIFT = "model_drift"
    PERFORMANCE_DRIFT = "performance_drift"
    CONCEPT_DRIFT = "concept_drift"


class FTAlertSeverity(str, Enum):
    """Uyari ciddiyetleri."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class FTDataFormat(str, Enum):
    """Veri format tipleri."""

    CHAT = "chat"
    COMPLETION = "completion"
    INSTRUCTION = "instruction"
    PREFERENCE = "preference"


class SamplingStrategy(str, Enum):
    """Ornekleme stratejileri."""

    RANDOM = "random"
    STRATIFIED = "stratified"
    BALANCED = "balanced"
    DIVERSE = "diverse"
    QUALITY_WEIGHTED = "quality_weighted"


class AugmentationType(str, Enum):
    """Artirma tipleri."""

    PARAPHRASE = "paraphrase"
    BACK_TRANSLATION = "back_translation"
    SYNONYM_REPLACE = "synonym_replace"
    NOISE_INJECTION = "noise_injection"
    TEMPLATE_FILL = "template_fill"


class FTMetricType(str, Enum):
    """Metrik tipleri."""

    ACCURACY = "accuracy"
    PERPLEXITY = "perplexity"
    BLEU = "bleu"
    ROUGE = "rouge"
    F1 = "f1"
    LATENCY = "latency"


class TrainingDataset(BaseModel):
    """Egitim veri seti."""

    dataset_id: str = ""
    name: str = ""
    format_type: str = "chat"
    total_samples: int = 0
    validation_split: float = 0.1
    avg_quality: float = 0.0


class FineTuneJob(BaseModel):
    """Fine-tune isi."""

    job_id: str = ""
    name: str = ""
    base_model: str = ""
    provider: str = "openai"
    status: str = "created"
    progress: float = 0.0
    cost_estimate: float = 0.0
    actual_cost: float = 0.0


class FTHyperparameters(BaseModel):
    """Hiperparametreler."""

    epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 2e-5
    warmup_steps: int = 100
    weight_decay: float = 0.01


class FTModelVersion(BaseModel):
    """Model versiyonu."""

    version_id: str = ""
    model_id: str = ""
    version: int = 1
    stage: str = "development"
    job_id: str = ""
    dataset_id: str = ""


class FTEvaluation(BaseModel):
    """Degerlendirme sonucu."""

    eval_id: str = ""
    model_id: str = ""
    metrics: dict[str, float] = Field(
        default_factory=dict
    )
    avg_quality: float = 0.0
    passed: bool = False


class FTBenchmarkResult(BaseModel):
    """Benchmark sonucu."""

    benchmark_id: str = ""
    suite_id: str = ""
    model_id: str = ""
    avg_score: float = 0.0
    test_count: int = 0


class FTDeployment(BaseModel):
    """Dagitim bilgisi."""

    deployment_id: str = ""
    endpoint_id: str = ""
    model_id: str = ""
    version_id: str = ""
    strategy: str = "blue_green"
    status: str = "deploying"
    traffic_pct: float = 0.0


class FTEndpoint(BaseModel):
    """Endpoint bilgisi."""

    endpoint_id: str = ""
    name: str = ""
    model_id: str = ""
    status: str = "active"
    health: str = "healthy"
    requests_total: int = 0


class FTDriftAlert(BaseModel):
    """Drift uyarisi."""

    alert_id: str = ""
    monitor_id: str = ""
    model_id: str = ""
    drift_type: str = "data_drift"
    severity: str = "warning"
    change_pct: float = 0.0


class FTSummary(BaseModel):
    """Genel ozet."""

    datasets: int = 0
    jobs: int = 0
    evaluations: int = 0
    models: int = 0
    deployments: int = 0
    drift_monitors: int = 0
