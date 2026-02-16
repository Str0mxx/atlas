"""ATLAS Email Intelligence & Auto-Responder modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class EmailCategory(str, Enum):
    """Email kategorisi."""

    BUSINESS = "business"
    PERSONAL = "personal"
    MARKETING = "marketing"
    TRANSACTIONAL = "transactional"


class EmailPriority(str, Enum):
    """Email önceliği."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SpamVerdict(str, Enum):
    """Spam kararı."""

    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    SPAM = "spam"
    PHISHING = "phishing"


class ActionType(str, Enum):
    """Aksiyon tipi."""

    TASK = "task"
    DEADLINE = "deadline"
    REQUEST = "request"
    FOLLOWUP = "followup"


class ThreadStatus(str, Enum):
    """İş parçacığı durumu."""

    ACTIVE = "active"
    PENDING = "pending"
    RESOLVED = "resolved"
    STALE = "stale"


class ResponseTone(str, Enum):
    """Yanıt tonu."""

    FORMAL = "formal"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"


class EmailRecord(BaseModel):
    """Email kaydı."""

    email_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    sender: str = ""
    subject: str = ""
    category: str = "business"
    priority: str = "medium"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ActionRecord(BaseModel):
    """Aksiyon kaydı."""

    action_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    action_type: str = "task"
    description: str = ""
    deadline: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ThreadRecord(BaseModel):
    """İş parçacığı kaydı."""

    thread_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    subject: str = ""
    participants: list[str] = Field(
        default_factory=list,
    )
    status: str = "active"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class DigestRecord(BaseModel):
    """Özet kaydı."""

    digest_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    period: str = "daily"
    email_count: int = 0
    action_count: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
