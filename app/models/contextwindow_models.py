"""Context Window Management modelleri.

Token limiti yonetimi icin
veri modelleri.
"""

from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class OverflowStrategy(str, Enum):
    """Tasma stratejisi."""

    TRUNCATE = "truncate"
    SUMMARIZE = "summarize"
    DROP_OLDEST = "drop_oldest"
    DROP_LOWEST = "drop_lowest"


class MessagePriority(str, Enum):
    """Mesaj onceligi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DISPOSABLE = "disposable"


class SummaryLevel(str, Enum):
    """Ozet seviyesi."""

    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"


class WindowStatus(str, Enum):
    """Pencere durumu."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OVERFLOW = "overflow"


class TokenUsage(BaseModel):
    """Token kullanim kaydi."""

    usage_id: str = Field(
        default_factory=lambda: str(
            uuid4(),
        )[:8],
    )
    role: str = ""
    content_hash: str = ""
    token_count: int = 0
    timestamp: float = 0.0
    priority: MessagePriority = (
        MessagePriority.MEDIUM
    )
    is_system: bool = False
    is_pinned: bool = False
    metadata: dict = Field(
        default_factory=dict,
    )


class WindowSnapshot(BaseModel):
    """Pencere anlık goruntusi."""

    snapshot_id: str = Field(
        default_factory=lambda: str(
            uuid4(),
        )[:8],
    )
    total_tokens: int = 0
    max_tokens: int = 0
    used_ratio: float = 0.0
    status: WindowStatus = (
        WindowStatus.HEALTHY
    )
    message_count: int = 0
    system_tokens: int = 0
    reserved_tokens: int = 0
    available_tokens: int = 0
    timestamp: float = 0.0


class SummaryResult(BaseModel):
    """Ozet sonucu."""

    summary_id: str = Field(
        default_factory=lambda: str(
            uuid4(),
        )[:8],
    )
    original_tokens: int = 0
    summary_tokens: int = 0
    compression_ratio: float = 0.0
    summary_text: str = ""
    key_points: list[str] = Field(
        default_factory=list,
    )
    preserved_count: int = 0
    dropped_count: int = 0
    level: SummaryLevel = (
        SummaryLevel.STANDARD
    )


class RetentionRule(BaseModel):
    """Saklama kurali."""

    rule_id: str = Field(
        default_factory=lambda: str(
            uuid4(),
        )[:8],
    )
    name: str = ""
    priority: MessagePriority = (
        MessagePriority.MEDIUM
    )
    pattern: str = ""
    role: str = ""
    is_pinned: bool = False
    max_age_seconds: float = 0.0
    enabled: bool = True


class SystemPromptConfig(BaseModel):
    """Sistem prompt yapilandirmasi."""

    config_id: str = Field(
        default_factory=lambda: str(
            uuid4(),
        )[:8],
    )
    prompt_text: str = ""
    token_count: int = 0
    reserved_tokens: int = 0
    is_protected: bool = True
    version: int = 1
    fallback_text: str = ""
    fallback_tokens: int = 0
