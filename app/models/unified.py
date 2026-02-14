"""ATLAS Unified Intelligence Core modeli.

Bilinc, akil yurutme, dikkat, dunya modeli,
karar entegrasyonu, aksiyon koordinasyonu,
yansima ve kisilik modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ConsciousnessLevel(str, Enum):
    """Bilinc seviyesi."""

    DORMANT = "dormant"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PEAK = "peak"


class ReasoningType(str, Enum):
    """Akil yurutme turu."""

    LOGICAL = "logical"
    ANALOGICAL = "analogical"
    CAUSAL = "causal"
    ABDUCTIVE = "abductive"
    META = "meta"


class AttentionState(str, Enum):
    """Dikkat durumu."""

    FOCUSED = "focused"
    DISTRIBUTED = "distributed"
    BACKGROUND = "background"
    INTERRUPTED = "interrupted"
    SWITCHING = "switching"


class EntityType(str, Enum):
    """Varlik turu."""

    SYSTEM = "system"
    AGENT = "agent"
    RESOURCE = "resource"
    TASK = "task"
    USER = "user"
    EXTERNAL = "external"


class DecisionSource(str, Enum):
    """Karar kaynagi."""

    BDI = "bdi"
    PROBABILISTIC = "probabilistic"
    REINFORCEMENT = "reinforcement"
    EMOTIONAL = "emotional"
    RULE_BASED = "rule_based"
    CONSENSUS = "consensus"


class ReflectionType(str, Enum):
    """Yansima turu."""

    SELF_EVALUATION = "self_evaluation"
    PERFORMANCE = "performance"
    BIAS_CHECK = "bias_check"
    IMPROVEMENT = "improvement"
    CONSOLIDATION = "consolidation"


class AwarenessState(BaseModel):
    """Farkindalik durumu."""

    awareness_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    self_state: str = "operational"
    active_goals: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ReasoningChain(BaseModel):
    """Akil yurutme zinciri."""

    chain_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    reasoning_type: ReasoningType = ReasoningType.LOGICAL
    premises: list[str] = Field(default_factory=list)
    conclusion: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class AttentionFocus(BaseModel):
    """Dikkat odagi."""

    focus_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    target: str = ""
    priority: int = Field(default=5, ge=1, le=10)
    state: AttentionState = AttentionState.FOCUSED
    allocated_capacity: float = Field(default=0.5, ge=0.0, le=1.0)
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class WorldEntity(BaseModel):
    """Dunya modeli varligi."""

    entity_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    entity_type: EntityType = EntityType.SYSTEM
    state: str = "active"
    properties: dict[str, Any] = Field(default_factory=dict)
    relationships: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class IntegratedDecision(BaseModel):
    """Entegre karar."""

    decision_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    question: str = ""
    chosen_action: str = ""
    sources: list[DecisionSource] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = ""
    alternatives: list[str] = Field(default_factory=list)
    explanation: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ReflectionRecord(BaseModel):
    """Yansima kaydi."""

    record_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    reflection_type: ReflectionType = ReflectionType.SELF_EVALUATION
    subject: str = ""
    findings: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class PersonaProfile(BaseModel):
    """Kisilik profili."""

    persona_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = "ATLAS"
    traits: dict[str, float] = Field(default_factory=dict)
    values: list[str] = Field(default_factory=list)
    communication_style: str = "professional"
    formality: float = Field(default=0.5, ge=0.0, le=1.0)
    adaptability: float = Field(default=0.7, ge=0.0, le=1.0)


class UnifiedSnapshot(BaseModel):
    """Unified Core anlik goruntusu."""

    consciousness_level: str = "medium"
    active_focuses: int = 0
    world_entities: int = 0
    reasoning_chains: int = 0
    decisions_made: int = 0
    reflections: int = 0
    uptime_seconds: float = 0.0
    overall_health: float = Field(default=1.0, ge=0.0, le=1.0)
