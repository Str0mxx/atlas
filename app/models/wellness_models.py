"""
Health & Wellness Tracker modelleri.

Wellness hatırlatma, egzersiz, uyku, öğün,
randevu, stres, rapor, ilaç modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ReminderType(str, Enum):
    """Hatırlatma türleri."""

    hydration = "hydration"
    posture = "posture"
    break_time = "break_time"
    stretch = "stretch"
    medication = "medication"
    custom = "custom"


class ExerciseLevel(str, Enum):
    """Egzersiz zorluk seviyeleri."""

    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class SleepQuality(str, Enum):
    """Uyku kalitesi seviyeleri."""

    excellent = "excellent"
    good = "good"
    fair = "fair"
    poor = "poor"
    very_poor = "very_poor"


class MealType(str, Enum):
    """Öğün türleri."""

    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"
    pre_workout = "pre_workout"
    post_workout = "post_workout"


class StressLevel(str, Enum):
    """Stres seviyeleri."""

    minimal = "minimal"
    low = "low"
    moderate = "moderate"
    high = "high"
    severe = "severe"


class MedicationFrequency(str, Enum):
    """İlaç sıklığı."""

    once_daily = "once_daily"
    twice_daily = "twice_daily"
    three_daily = "three_daily"
    weekly = "weekly"
    as_needed = "as_needed"
    monthly = "monthly"


class WellnessReminderRecord(BaseModel):
    """Wellness hatırlatma kaydı."""

    reminder_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    reminder_type: str = "hydration"
    interval_minutes: int = 60
    active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class SleepRecord(BaseModel):
    """Uyku kaydı."""

    sleep_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    hours: float = 0.0
    quality: str = "fair"
    deep_sleep_pct: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class AppointmentRecord(BaseModel):
    """Randevu kaydı."""

    appointment_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    doctor: str = ""
    specialty: str = ""
    status: str = "scheduled"
    notes: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class MedicationRecord(BaseModel):
    """İlaç kaydı."""

    medication_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = ""
    dosage: str = ""
    frequency: str = "once_daily"
    active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
