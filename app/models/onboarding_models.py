"""ATLAS Onboarding & Training Assistant modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SkillLevel(str, Enum):
    """Beceri seviyesi."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LearningStatus(str, Enum):
    """Öğrenme durumu."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"


class QuestionFormat(str, Enum):
    """Soru formatı."""

    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    CODE_EXERCISE = "code_exercise"


class CertificationStatus(str, Enum):
    """Sertifika durumu."""

    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class DifficultyLevel(str, Enum):
    """Zorluk seviyesi."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class TutorialType(str, Enum):
    """Eğitim tipi."""

    STEP_BY_STEP = "step_by_step"
    INTERACTIVE = "interactive"
    VIDEO_SCRIPT = "video_script"
    CODE_EXAMPLE = "code_example"


class SkillAssessmentRecord(BaseModel):
    """Beceri değerlendirme kaydı."""

    assessment_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    user_id: str = ""
    skill_name: str = ""
    level: str = "beginner"
    score: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class LearningPathRecord(BaseModel):
    """Öğrenme yolu kaydı."""

    path_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    user_id: str = ""
    title: str = ""
    status: str = "not_started"
    total_modules: int = 0
    completed_modules: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CertificationRecord(BaseModel):
    """Sertifika kaydı."""

    cert_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    user_id: str = ""
    certification_name: str = ""
    status: str = "pending"
    score: float = 0.0
    issued_at: datetime | None = None
    expires_at: datetime | None = None


class MentorAssignmentRecord(BaseModel):
    """Mentor atama kaydı."""

    assignment_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    mentor_id: str = ""
    mentee_id: str = ""
    skill_area: str = ""
    compatibility_score: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
