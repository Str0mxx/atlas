"""
Learning & Self-Development Coach modelleri.

Beceri, kurs, okuma, podcast, öğrenme planı,
ilerleme, sertifika, mentor modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SkillLevel(str, Enum):
    """Beceri seviyeleri."""

    novice = "novice"
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"
    master = "master"


class ContentType(str, Enum):
    """İçerik türleri."""

    course = "course"
    book = "book"
    podcast = "podcast"
    article = "article"
    video = "video"
    workshop = "workshop"


class LearningStyle(str, Enum):
    """Öğrenme stilleri."""

    visual = "visual"
    auditory = "auditory"
    reading = "reading"
    kinesthetic = "kinesthetic"
    mixed = "mixed"


class CertDifficulty(str, Enum):
    """Sertifika zorluk seviyeleri."""

    entry = "entry"
    associate = "associate"
    professional = "professional"
    expert = "expert"
    architect = "architect"


class MentorStatus(str, Enum):
    """Mentor durumları."""

    available = "available"
    busy = "busy"
    on_leave = "on_leave"
    inactive = "inactive"
    matched = "matched"


class ProgressStatus(str, Enum):
    """İlerleme durumları."""

    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    paused = "paused"
    abandoned = "abandoned"
    certified = "certified"


class SkillRecord(BaseModel):
    """Beceri kaydı."""

    skill_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = ""
    level: str = "novice"
    target_level: str = "intermediate"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class CourseRecord(BaseModel):
    """Kurs kaydı."""

    course_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    title: str = ""
    platform: str = ""
    price: float = 0.0
    rating: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class ReadingRecord(BaseModel):
    """Okuma kaydı."""

    reading_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    title: str = ""
    author: str = ""
    status: str = "not_started"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class CertificationRecord(BaseModel):
    """Sertifika kaydı."""

    cert_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = ""
    provider: str = ""
    difficulty: str = "associate"
    status: str = "planned"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
