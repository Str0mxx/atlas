"""ATLAS Task Memory & Command Learning modelleri.

Görev hafızası, komut öğrenme, tercih takibi,
şablon, kişiselleştirme modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PatternType(str, Enum):
    """Örüntü tipi."""

    COMMAND = "command"
    SEQUENCE = "sequence"
    SHORTCUT = "shortcut"
    ALIAS = "alias"
    WORKFLOW = "workflow"
    HABIT = "habit"


class FeedbackType(str, Enum):
    """Geri bildirim tipi."""

    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    CORRECTION = "correction"
    RATING = "rating"
    SUGGESTION = "suggestion"
    COMPLAINT = "complaint"


class QualityLevel(str, Enum):
    """Kalite seviyesi."""

    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    FAILING = "failing"
    UNKNOWN = "unknown"


class PersonalizationMode(str, Enum):
    """Kişiselleştirme modu."""

    AGGRESSIVE = "aggressive"
    MODERATE = "moderate"
    CONSERVATIVE = "conservative"
    MINIMAL = "minimal"
    OFF = "off"
    AUTO = "auto"


class TemplateStatus(str, Enum):
    """Şablon durumu."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"
    TESTING = "testing"
    APPROVED = "approved"


class PredictionConfidence(str, Enum):
    """Tahmin güven seviyesi."""

    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"
    UNCERTAIN = "uncertain"


class PatternRecord(BaseModel):
    """Örüntü kaydı."""

    pattern_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    pattern_type: PatternType = (
        PatternType.COMMAND
    )
    name: str = ""
    frequency: int = 0
    confidence: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class FeedbackRecord(BaseModel):
    """Geri bildirim kaydı."""

    feedback_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    feedback_type: FeedbackType = (
        FeedbackType.EXPLICIT
    )
    score: float = 0.0
    message: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class TemplateRecord(BaseModel):
    """Şablon kaydı."""

    template_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    status: TemplateStatus = (
        TemplateStatus.DRAFT
    )
    version: int = 1
    usage_count: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class TaskMemSnapshot(BaseModel):
    """Görev hafızası anlık görüntü."""

    patterns_learned: int = 0
    templates_created: int = 0
    feedbacks_received: int = 0
    predictions_made: int = 0
    quality_score: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
