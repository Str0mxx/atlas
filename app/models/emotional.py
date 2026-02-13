"""ATLAS Emotional Intelligence veri modelleri.

Duygusal zeka ve empati icin enum ve Pydantic modelleri:
duygu analizi, empati, ruh hali takibi, iletisim stili,
catisma cozumu, motivasyon, kisilik adaptasyonu ve duygusal hafiza.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# === Enum'lar ===


class Sentiment(str, Enum):
    """Duygu polaritesi."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class Emotion(str, Enum):
    """Temel duygu sinifi."""

    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"


class MoodLevel(str, Enum):
    """Ruh hali seviyesi."""

    VERY_LOW = "very_low"
    LOW = "low"
    NEUTRAL = "neutral"
    HIGH = "high"
    VERY_HIGH = "very_high"


class CommunicationTone(str, Enum):
    """Iletisim tonu."""

    FORMAL = "formal"
    CASUAL = "casual"
    SUPPORTIVE = "supportive"
    ENTHUSIASTIC = "enthusiastic"
    EMPATHETIC = "empathetic"
    PROFESSIONAL = "professional"


class FormalityLevel(str, Enum):
    """Resmiyet seviyesi."""

    VERY_FORMAL = "very_formal"
    FORMAL = "formal"
    NEUTRAL = "neutral"
    CASUAL = "casual"
    VERY_CASUAL = "very_casual"


class ConflictLevel(str, Enum):
    """Catisma seviyesi."""

    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationAction(str, Enum):
    """Eskalasyon aksiyonu."""

    NONE = "none"
    ACKNOWLEDGE = "acknowledge"
    APOLOGIZE = "apologize"
    OFFER_ALTERNATIVE = "offer_alternative"
    ESCALATE_HUMAN = "escalate_human"


class MotivationType(str, Enum):
    """Motivasyon tipi."""

    ENCOURAGEMENT = "encouragement"
    CELEBRATION = "celebration"
    PROGRESS = "progress"
    GOAL_REMINDER = "goal_reminder"
    POSITIVE_REINFORCEMENT = "positive_reinforcement"


class RelationshipQuality(str, Enum):
    """Iliski kalitesi."""

    EXCELLENT = "excellent"
    GOOD = "good"
    NEUTRAL = "neutral"
    STRAINED = "strained"
    POOR = "poor"


# === Modeller ===


class SentimentResult(BaseModel):
    """Duygu analiz sonucu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str = ""
    sentiment: Sentiment = Sentiment.NEUTRAL
    emotion: Emotion = Emotion.TRUST
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    is_sarcastic: bool = False
    keywords: list[str] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserEmotionalState(BaseModel):
    """Kullanici duygusal durumu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    current_mood: MoodLevel = MoodLevel.NEUTRAL
    current_emotion: Emotion = Emotion.TRUST
    frustration_level: float = Field(default=0.0, ge=0.0, le=1.0)
    satisfaction_level: float = Field(default=0.5, ge=0.0, le=1.0)
    interaction_count: int = 0
    last_sentiment: Sentiment = Sentiment.NEUTRAL
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MoodEntry(BaseModel):
    """Ruh hali kaydi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    mood: MoodLevel = MoodLevel.NEUTRAL
    emotion: Emotion = Emotion.TRUST
    trigger: str = ""
    context: str = ""
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StyleProfile(BaseModel):
    """Iletisim stili profili."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    preferred_tone: CommunicationTone = CommunicationTone.PROFESSIONAL
    formality: FormalityLevel = FormalityLevel.NEUTRAL
    humor_receptive: bool = True
    preferred_length: str = "medium"
    cultural_context: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConflictEvent(BaseModel):
    """Catisma olayi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    level: ConflictLevel = ConflictLevel.NONE
    trigger: str = ""
    action_taken: EscalationAction = EscalationAction.NONE
    resolved: bool = False
    resolution_note: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MotivationMessage(BaseModel):
    """Motivasyon mesaji."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    motivation_type: MotivationType = MotivationType.ENCOURAGEMENT
    message: str = ""
    context: str = ""
    delivered: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PersonalityProfile(BaseModel):
    """Kisilik profili."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    communication_style: CommunicationTone = CommunicationTone.PROFESSIONAL
    humor_style: str = "light"
    formality_pref: FormalityLevel = FormalityLevel.NEUTRAL
    response_length_pref: str = "medium"
    patience_level: float = Field(default=0.5, ge=0.0, le=1.0)
    detail_preference: float = Field(default=0.5, ge=0.0, le=1.0)
    interactions_analyzed: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmotionalInteraction(BaseModel):
    """Duygusal etkilesim kaydi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    sentiment: Sentiment = Sentiment.NEUTRAL
    emotion: Emotion = Emotion.TRUST
    relationship_quality: RelationshipQuality = RelationshipQuality.NEUTRAL
    event_type: str = ""
    summary: str = ""
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EQAnalysis(BaseModel):
    """Duygusal zeka analiz sonucu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    input_text: str = ""
    sentiment: SentimentResult | None = None
    recommended_tone: CommunicationTone = CommunicationTone.PROFESSIONAL
    conflict_level: ConflictLevel = ConflictLevel.NONE
    motivation_needed: bool = False
    enhanced_response: str = ""
    processing_ms: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
