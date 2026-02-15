"""ATLAS Rate Limiting & Throttling modelleri.

Hiz sinirlama ve kisitlama veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class AlgorithmType(str, Enum):
    """Algoritma tipi."""

    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    LEAKY_BUCKET = "leaky_bucket"
    FIXED_WINDOW = "fixed_window"
    ADAPTIVE = "adaptive"


class QuotaPeriod(str, Enum):
    """Kota periyodu."""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class ThrottleMode(str, Enum):
    """Kisma modu."""

    NONE = "none"
    SOFT = "soft"
    HARD = "hard"
    ADAPTIVE = "adaptive"
    BACKPRESSURE = "backpressure"


class ViolationType(str, Enum):
    """Ihlal tipi."""

    RATE_EXCEEDED = "rate_exceeded"
    QUOTA_EXCEEDED = "quota_exceeded"
    BURST_EXCEEDED = "burst_exceeded"
    THROTTLED = "throttled"
    BANNED = "banned"


class PolicyTier(str, Enum):
    """Politika katmani."""

    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


class PenaltyAction(str, Enum):
    """Ceza aksiyonu."""

    WARN = "warn"
    DELAY = "delay"
    REJECT = "reject"
    THROTTLE = "throttle"
    BAN = "ban"
    NOTIFY = "notify"


class RateLimitRecord(BaseModel):
    """Hiz siniri kaydi."""

    record_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    key: str = ""
    algorithm: AlgorithmType = (
        AlgorithmType.TOKEN_BUCKET
    )
    limit: int = 100
    window_seconds: int = 60
    current_count: int = 0
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class QuotaRecord(BaseModel):
    """Kota kaydi."""

    quota_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    subject_id: str = ""
    period: QuotaPeriod = QuotaPeriod.DAY
    limit: int = 1000
    used: int = 0
    reset_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ViolationRecord(BaseModel):
    """Ihlal kaydi."""

    violation_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    subject_id: str = ""
    violation_type: ViolationType = (
        ViolationType.RATE_EXCEEDED
    )
    penalty: PenaltyAction = PenaltyAction.REJECT
    details: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class RateLimitSnapshot(BaseModel):
    """Rate limit snapshot."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    total_requests: int = 0
    allowed_requests: int = 0
    rejected_requests: int = 0
    active_limits: int = 0
    active_quotas: int = 0
    violations: int = 0
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
