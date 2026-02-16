"""ATLAS Scheduling & Calendar Intelligence modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class MeetingType(str, Enum):
    """Toplantı tipi."""

    STANDUP = "standup"
    REVIEW = "review"
    PLANNING = "planning"
    ONEONONE = "one_on_one"


class MeetingPriority(str, Enum):
    """Toplantı önceliği."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConflictSeverity(str, Enum):
    """Çakışma şiddeti."""

    HARD = "hard"
    SOFT = "soft"
    OVERLAP = "overlap"
    ADJACENT = "adjacent"


class SlotStatus(str, Enum):
    """Zaman dilimi durumu."""

    FREE = "free"
    BUSY = "busy"
    TENTATIVE = "tentative"
    BLOCKED = "blocked"


class FollowUpStatus(str, Enum):
    """Takip durumu."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class AnalysisPeriod(str, Enum):
    """Analiz dönemi."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class MeetingRecord(BaseModel):
    """Toplantı kaydı."""

    meeting_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    title: str = ""
    meeting_type: str = "review"
    priority: str = "medium"
    duration_minutes: int = 60
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ConflictRecord(BaseModel):
    """Çakışma kaydı."""

    conflict_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    severity: str = "soft"
    meeting_a: str = ""
    meeting_b: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class AgendaRecord(BaseModel):
    """Gündem kaydı."""

    agenda_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    meeting_id: str = ""
    topics: list[str] = Field(
        default_factory=list,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CalendarAnalysisRecord(BaseModel):
    """Takvim analiz kaydı."""

    analysis_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    period: str = "weekly"
    meeting_hours: float = 0.0
    free_hours: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
