"""ATLAS Simulation & Scenario Testing modelleri.

Dunya modelleme, aksiyon simulasyonu, senaryo uretimi,
sonuc tahmini, risk simulasyonu ve geri alma planlama modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ScenarioType(str, Enum):
    """Senaryo tipi."""

    BEST_CASE = "best_case"
    WORST_CASE = "worst_case"
    MOST_LIKELY = "most_likely"
    EDGE_CASE = "edge_case"
    RANDOM = "random"


class SimulationStatus(str, Enum):
    """Simulasyon durumu."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    """Risk seviyesi."""

    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OutcomeType(str, Enum):
    """Sonuc tipi."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class RollbackStatus(str, Enum):
    """Geri alma durumu."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_NEEDED = "not_needed"


class ResourceType(str, Enum):
    """Kaynak tipi."""

    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    API_CALLS = "api_calls"
    DATABASE = "database"


class SensitivityLevel(str, Enum):
    """Hassasiyet seviyesi."""

    INSENSITIVE = "insensitive"
    LOW_SENSITIVITY = "low_sensitivity"
    MODERATE = "moderate"
    HIGH_SENSITIVITY = "high_sensitivity"
    CRITICAL_SENSITIVITY = "critical_sensitivity"


class EntityState(BaseModel):
    """Varlik durumu."""

    entity_id: str = ""
    entity_type: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ResourceState(BaseModel):
    """Kaynak durumu."""

    resource_type: ResourceType = ResourceType.CPU
    current_usage: float = Field(default=0.0, ge=0.0, le=1.0)
    capacity: float = 100.0
    available: float = 100.0
    unit: str = ""


class Constraint(BaseModel):
    """Kisitlama."""

    name: str = ""
    description: str = ""
    constraint_type: str = "hard"
    expression: str = ""
    is_satisfied: bool = True


class Assumption(BaseModel):
    """Varsayim."""

    assumption_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    description: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = ""
    is_validated: bool = False


class WorldSnapshot(BaseModel):
    """Dunya anlık goruntusu."""

    snapshot_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    entities: list[EntityState] = Field(default_factory=list)
    resources: list[ResourceState] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    relationships: dict[str, list[str]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SideEffect(BaseModel):
    """Yan etki."""

    description: str = ""
    affected_entity: str = ""
    severity: RiskLevel = RiskLevel.LOW
    probability: float = Field(default=0.5, ge=0.0, le=1.0)
    reversible: bool = True


class ActionOutcome(BaseModel):
    """Aksiyon sonucu."""

    action_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    action_name: str = ""
    outcome_type: OutcomeType = OutcomeType.UNKNOWN
    success_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    side_effects: list[SideEffect] = Field(default_factory=list)
    resource_cost: dict[str, float] = Field(default_factory=dict)
    estimated_duration_seconds: float = 0.0
    dependencies: list[str] = Field(default_factory=list)
    error_message: str = ""


class Scenario(BaseModel):
    """Senaryo."""

    scenario_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    scenario_type: ScenarioType = ScenarioType.MOST_LIKELY
    name: str = ""
    description: str = ""
    probability: float = Field(default=0.5, ge=0.0, le=1.0)
    outcomes: list[ActionOutcome] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    impact_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    parameters: dict[str, Any] = Field(default_factory=dict)


class FailureMode(BaseModel):
    """Basarisizlik modu."""

    mode_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    description: str = ""
    probability: float = Field(default=0.1, ge=0.0, le=1.0)
    severity: RiskLevel = RiskLevel.MEDIUM
    mitigation: str = ""
    cascading_effects: list[str] = Field(default_factory=list)


class OutcomePrediction(BaseModel):
    """Sonuc tahmini."""

    prediction_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    action_name: str = ""
    success_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    failure_modes: list[FailureMode] = Field(default_factory=list)
    cascading_effects: list[str] = Field(default_factory=list)
    long_term_impact: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    recommended: bool = True


class RiskEvent(BaseModel):
    """Risk olayi."""

    event_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    description: str = ""
    probability: float = Field(default=0.1, ge=0.0, le=1.0)
    impact: RiskLevel = RiskLevel.MEDIUM
    affected_components: list[str] = Field(default_factory=list)
    propagation_path: list[str] = Field(default_factory=list)
    recovery_time_seconds: float = 0.0
    mitigation_strategy: str = ""


class RollbackCheckpoint(BaseModel):
    """Geri alma kontrol noktasi."""

    checkpoint_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    state_snapshot: dict[str, Any] = Field(default_factory=dict)
    rollback_steps: list[str] = Field(default_factory=list)
    validation_checks: list[str] = Field(default_factory=list)
    status: RollbackStatus = RollbackStatus.PLANNED
    estimated_duration_seconds: float = 0.0


class WhatIfResult(BaseModel):
    """Ne olur analiz sonucu."""

    parameter: str = ""
    original_value: Any = None
    varied_value: Any = None
    outcome_change: float = 0.0
    sensitivity: SensitivityLevel = SensitivityLevel.MODERATE
    threshold: float | None = None
    tipping_point: bool = False
    recommendation: str = ""


class DryRunResult(BaseModel):
    """Kuru calistirma sonucu."""

    run_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    action_name: str = ""
    would_succeed: bool = True
    steps_log: list[str] = Field(default_factory=list)
    prerequisites_met: bool = True
    missing_prerequisites: list[str] = Field(default_factory=list)
    permissions_ok: bool = True
    missing_permissions: list[str] = Field(default_factory=list)
    resources_available: bool = True
    resource_shortages: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SimulationReport(BaseModel):
    """Simulasyon raporu."""

    report_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    action_name: str = ""
    status: SimulationStatus = SimulationStatus.PENDING
    scenarios: list[Scenario] = Field(default_factory=list)
    prediction: OutcomePrediction | None = None
    risk_events: list[RiskEvent] = Field(default_factory=list)
    rollback_plan: RollbackCheckpoint | None = None
    dry_run: DryRunResult | None = None
    what_if_results: list[WhatIfResult] = Field(default_factory=list)
    overall_risk: RiskLevel = RiskLevel.LOW
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    recommendation: str = ""
    processing_ms: float = 0.0
