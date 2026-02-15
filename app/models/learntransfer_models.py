"""ATLAS Cross-System Learning Transfer modelleri.

Sistemler arasi ogrenme transferi veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TransferStatus(str, Enum):
    """Transfer durumu."""

    pending = "pending"
    validating = "validating"
    adapting = "adapting"
    injecting = "injecting"
    completed = "completed"
    failed = "failed"
    rolled_back = "rolled_back"


class KnowledgeType(str, Enum):
    """Bilgi tipi."""

    pattern = "pattern"
    rule = "rule"
    heuristic = "heuristic"
    model = "model"
    strategy = "strategy"
    lesson = "lesson"


class SimilarityDimension(str, Enum):
    """Benzerlik boyutu."""

    domain = "domain"
    task = "task"
    structure = "structure"
    context = "context"
    semantic = "semantic"


class TransferRisk(str, Enum):
    """Transfer riski."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"
    unknown = "unknown"


class FeedbackType(str, Enum):
    """Geri bildirim tipi."""

    positive = "positive"
    negative = "negative"
    neutral = "neutral"
    mixed = "mixed"
    pending = "pending"


class AdaptationMethod(str, Enum):
    """Adaptasyon yontemi."""

    direct = "direct"
    scaled = "scaled"
    translated = "translated"
    constrained = "constrained"
    hybrid = "hybrid"


class KnowledgeRecord(BaseModel):
    """Bilgi kaydi."""

    knowledge_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    source_system: str = ""
    knowledge_type: KnowledgeType = (
        KnowledgeType.pattern
    )
    content: dict[str, Any] = Field(
        default_factory=dict,
    )
    confidence: float = 0.0
    tags: list[str] = Field(
        default_factory=list,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class TransferRecord(BaseModel):
    """Transfer kaydi."""

    transfer_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    source_system: str = ""
    target_system: str = ""
    knowledge_id: str = ""
    status: TransferStatus = (
        TransferStatus.pending
    )
    similarity_score: float = 0.0
    risk_level: TransferRisk = (
        TransferRisk.unknown
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class SimilarityResult(BaseModel):
    """Benzerlik sonucu."""

    source: str = ""
    target: str = ""
    overall_score: float = 0.0
    dimension_scores: dict[str, float] = Field(
        default_factory=dict,
    )
    transfer_potential: str = "low"
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class LearnTransferSnapshot(BaseModel):
    """Ogrenme transferi snapshot."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    total_knowledge: int = 0
    total_transfers: int = 0
    successful_transfers: int = 0
    success_rate: float = 0.0
    active_networks: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
