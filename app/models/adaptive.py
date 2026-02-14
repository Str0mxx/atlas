"""Adaptive Learning Engine veri modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ExperienceType(str, Enum):
    """Deneyim turu."""

    INTERACTION = "interaction"
    TASK = "task"
    DECISION = "decision"
    ERROR = "error"
    FEEDBACK = "feedback"


class OutcomeType(str, Enum):
    """Sonuc turu."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class PatternType(str, Enum):
    """Oruntu turu."""

    SUCCESS = "success"
    FAILURE = "failure"
    CORRELATION = "correlation"
    TREND = "trend"
    CLUSTER = "cluster"


class StrategyStatus(str, Enum):
    """Strateji durumu."""

    ACTIVE = "active"
    TESTING = "testing"
    RETIRED = "retired"
    CANDIDATE = "candidate"


class FeedbackType(str, Enum):
    """Geri bildirim turu."""

    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    CORRECTION = "correction"
    PREFERENCE = "preference"


class SkillLevel(str, Enum):
    """Yetenek seviyesi."""

    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ExperienceRecord(BaseModel):
    """Deneyim kaydi."""

    experience_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    experience_type: ExperienceType = ExperienceType.INTERACTION
    outcome: OutcomeType = OutcomeType.UNKNOWN
    context: dict[str, Any] = Field(default_factory=dict)
    action: str = ""
    reward: float = 0.0
    tags: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class PatternRecord(BaseModel):
    """Oruntu kaydi."""

    pattern_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    pattern_type: PatternType = PatternType.SUCCESS
    description: str = ""
    confidence: float = 0.0
    support: int = 0
    features: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class StrategyRecord(BaseModel):
    """Strateji kaydi."""

    strategy_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    status: StrategyStatus = StrategyStatus.CANDIDATE
    fitness: float = 0.0
    generation: int = 0
    parameters: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class KnowledgeRule(BaseModel):
    """Bilgi kurali."""

    rule_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    condition: str = ""
    action: str = ""
    confidence: float = 0.0
    usage_count: int = 0
    valid: bool = True
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class AdaptiveSnapshot(BaseModel):
    """Adaptif ogrenme goruntusu."""

    total_experiences: int = 0
    patterns_discovered: int = 0
    active_strategies: int = 0
    knowledge_rules: int = 0
    skills_tracked: int = 0
    feedback_processed: int = 0
    transfer_count: int = 0
    avg_learning_rate: float = 0.0
