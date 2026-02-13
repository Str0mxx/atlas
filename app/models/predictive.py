"""ATLAS Predictive Intelligence veri modelleri.

Tahmin ve ongoruler icin enum ve Pydantic modelleri:
oruntu tanima, trend analizi, tahmin motoru, risk
tahmini, talep tahmini, davranis tahmini, olay tahmini,
model yonetimi ve tahmin orkestratoru.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# === Enum'lar ===


class PatternType(str, Enum):
    """Oruntu tipi."""

    TIME_SERIES = "time_series"
    BEHAVIORAL = "behavioral"
    ANOMALY = "anomaly"
    CYCLICAL = "cyclical"
    TREND = "trend"
    SEASONAL = "seasonal"


class TrendDirection(str, Enum):
    """Trend yonu."""

    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    VOLATILE = "volatile"


class ForecastMethod(str, Enum):
    """Tahmin yontemi."""

    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    LINEAR_REGRESSION = "linear_regression"
    POLYNOMIAL_REGRESSION = "polynomial_regression"
    ENSEMBLE = "ensemble"


class RiskLevel(str, Enum):
    """Risk seviyesi."""

    NEGLIGIBLE = "negligible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DemandCategory(str, Enum):
    """Talep kategorisi."""

    SALES = "sales"
    RESOURCE = "resource"
    CAPACITY = "capacity"
    INVENTORY = "inventory"
    STAFFING = "staffing"


class BehaviorType(str, Enum):
    """Davranis tipi."""

    PURCHASE = "purchase"
    ENGAGEMENT = "engagement"
    CHURN = "churn"
    UPGRADE = "upgrade"
    REFERRAL = "referral"


class EventCategory(str, Enum):
    """Olay kategorisi."""

    SYSTEM_FAILURE = "system_failure"
    SECURITY_BREACH = "security_breach"
    MARKET_SHIFT = "market_shift"
    USER_MILESTONE = "user_milestone"
    OPPORTUNITY = "opportunity"
    THREAT = "threat"


class ModelStatus(str, Enum):
    """Model durumu."""

    TRAINING = "training"
    TRAINED = "trained"
    EVALUATING = "evaluating"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class EnsembleStrategy(str, Enum):
    """Ensemble stratejisi."""

    AVERAGE = "average"
    WEIGHTED = "weighted"
    BEST_PICK = "best_pick"
    STACKING = "stacking"


class ConfidenceLevel(str, Enum):
    """Guven seviyesi."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class SeasonType(str, Enum):
    """Mevsimsellik tipi."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class MetricType(str, Enum):
    """Metrik tipi."""

    MAE = "mae"
    RMSE = "rmse"
    MAPE = "mape"
    R_SQUARED = "r_squared"
    ACCURACY = "accuracy"


# === Modeller ===


class DataPoint(BaseModel):
    """Zaman serisi veri noktasi."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    value: float = 0.0
    label: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Pattern(BaseModel):
    """Tespit edilen oruntu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    pattern_type: PatternType = PatternType.TIME_SERIES
    name: str = ""
    description: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    data_points: list[DataPoint] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrendResult(BaseModel):
    """Trend analiz sonucu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    direction: TrendDirection = TrendDirection.STABLE
    slope: float = 0.0
    strength: float = Field(default=0.0, ge=0.0, le=1.0)
    start_value: float = 0.0
    end_value: float = 0.0
    change_rate: float = 0.0
    seasonality: SeasonType | None = None
    inflection_points: list[int] = Field(default_factory=list)
    moving_averages: list[float] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Forecast(BaseModel):
    """Tahmin sonucu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    method: ForecastMethod = ForecastMethod.MOVING_AVERAGE
    predictions: list[DataPoint] = Field(default_factory=list)
    confidence_lower: list[float] = Field(default_factory=list)
    confidence_upper: list[float] = Field(default_factory=list)
    confidence_level: float = Field(default=0.95, ge=0.0, le=1.0)
    error_metric: float = 0.0
    metric_type: MetricType = MetricType.MAE
    horizon: int = 7
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RiskAssessment(BaseModel):
    """Risk degerlendirmesi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    risk_level: RiskLevel = RiskLevel.LOW
    probability: float = Field(default=0.0, ge=0.0, le=1.0)
    impact: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    factors: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DemandForecast(BaseModel):
    """Talep tahmini."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    category: DemandCategory = DemandCategory.SALES
    current_demand: float = 0.0
    predicted_demand: float = 0.0
    change_percent: float = 0.0
    seasonal_factor: float = 1.0
    optimal_inventory: float = 0.0
    reorder_point: float = 0.0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    forecast_horizon_days: int = 30
    predicted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BehaviorPrediction(BaseModel):
    """Davranis tahmini."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    behavior_type: BehaviorType = BehaviorType.PURCHASE
    entity_id: str = ""
    probability: float = Field(default=0.0, ge=0.0, le=1.0)
    expected_time_days: float = 0.0
    lifetime_value: float = 0.0
    churn_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    next_actions: list[str] = Field(default_factory=list)
    engagement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    predicted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventPrediction(BaseModel):
    """Olay tahmini."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    event_category: EventCategory = EventCategory.SYSTEM_FAILURE
    description: str = ""
    likelihood: float = Field(default=0.0, ge=0.0, le=1.0)
    expected_time_hours: float = 0.0
    trigger_conditions: list[str] = Field(default_factory=list)
    cascade_effects: list[str] = Field(default_factory=list)
    prevention_actions: list[str] = Field(default_factory=list)
    impact_score: float = Field(default=0.0, ge=0.0, le=1.0)
    predicted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PredictionModel(BaseModel):
    """Tahmin modeli kaydi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    version: str = "1.0.0"
    model_type: str = ""
    status: ModelStatus = ModelStatus.TRAINING
    parameters: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    training_data_size: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PredictionResult(BaseModel):
    """Birlesik tahmin sonucu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    query: str = ""
    strategy: EnsembleStrategy = EnsembleStrategy.AVERAGE
    predictions: dict[str, float] = Field(default_factory=dict)
    combined_score: float = 0.0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    explanation: str = ""
    model_contributions: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
