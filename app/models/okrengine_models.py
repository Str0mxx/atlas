"""ATLAS Goal Tracking & OKR Engine modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ObjectiveLevel(str, Enum):
    """Hedef seviyesi."""

    COMPANY = "company"
    DEPARTMENT = "department"
    TEAM = "team"
    INDIVIDUAL = "individual"


class OKRStatus(str, Enum):
    """OKR durumu."""

    DRAFT = "draft"
    ACTIVE = "active"
    AT_RISK = "at_risk"
    ON_TRACK = "on_track"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class CadenceType(str, Enum):
    """Kadans tipi."""

    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class AlignmentType(str, Enum):
    """Hizalama tipi."""

    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    CROSS_FUNCTIONAL = "cross_functional"


class ScoreMethod(str, Enum):
    """Puanlama yöntemi."""

    SIMPLE_AVERAGE = "simple_average"
    WEIGHTED = "weighted"
    BINARY = "binary"
    PERCENTAGE = "percentage"


class ReviewType(str, Enum):
    """İnceleme tipi."""

    CHECK_IN = "check_in"
    MONTHLY_REVIEW = "monthly_review"
    QUARTERLY_REVIEW = "quarterly_review"
    ANNUAL_REVIEW = "annual_review"


class ObjectiveRecord(BaseModel):
    """Hedef kaydı."""

    objective_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    title: str = ""
    level: ObjectiveLevel = (
        ObjectiveLevel.COMPANY
    )
    status: OKRStatus = OKRStatus.DRAFT
    owner: str = ""
    parent_id: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class KeyResultRecord(BaseModel):
    """Anahtar sonuç kaydı."""

    kr_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    objective_id: str = ""
    description: str = ""
    target_value: float = 100.0
    current_value: float = 0.0
    confidence: float = 0.5
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class CheckInRecord(BaseModel):
    """Check-in kaydı."""

    checkin_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    kr_id: str = ""
    value: float = 0.0
    note: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None


class ReviewRecord(BaseModel):
    """İnceleme kaydı."""

    review_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    review_type: ReviewType = (
        ReviewType.CHECK_IN
    )
    period: str = ""
    score: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] | None = None
