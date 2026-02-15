"""ATLAS Decision Explainability Layer modelleri.

Karar aciklanabilirligi veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ExplanationDepth(str, Enum):
    """Aciklama derinligi."""

    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    FULL = "full"


class ExplanationAudience(str, Enum):
    """Aciklama hedef kitlesi."""

    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    LEGAL = "legal"
    END_USER = "end_user"
    AUDITOR = "auditor"


class ReasoningType(str, Enum):
    """Akil yurutme tipi."""

    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    HEURISTIC = "heuristic"
    PROBABILISTIC = "probabilistic"


class FactorInfluence(str, Enum):
    """Faktor etkisi."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CRITICAL = "critical"
    NEGLIGIBLE = "negligible"


class AuditFormat(str, Enum):
    """Denetim formati."""

    COMPLIANCE = "compliance"
    LEGAL = "legal"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    CUSTOM = "custom"


class CacheStrategy(str, Enum):
    """Onbellek stratejisi."""

    ALWAYS = "always"
    ON_DEMAND = "on_demand"
    PATTERN_BASED = "pattern_based"
    NEVER = "never"
    TTL = "ttl"


class ExplanationRecord(BaseModel):
    """Aciklama kaydi."""

    explanation_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    decision_id: str = ""
    depth: ExplanationDepth = (
        ExplanationDepth.STANDARD
    )
    audience: ExplanationAudience = (
        ExplanationAudience.TECHNICAL
    )
    summary: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ReasoningStep(BaseModel):
    """Akil yurutme adimi."""

    step_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    decision_id: str = ""
    step_number: int = 0
    reasoning_type: ReasoningType = (
        ReasoningType.DEDUCTIVE
    )
    description: str = ""
    conclusion: str = ""
    confidence: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class FactorRecord(BaseModel):
    """Faktor kaydi."""

    factor_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    decision_id: str = ""
    name: str = ""
    weight: float = 0.0
    influence: FactorInfluence = (
        FactorInfluence.NEUTRAL
    )
    contribution: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ExplainabilitySnapshot(BaseModel):
    """Explainability snapshot."""

    total_explanations: int = 0
    decisions_explained: int = 0
    avg_factors_per_decision: float = 0.0
    cache_hit_rate: float = 0.0
    counterfactuals_generated: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
