"""Context-Aware Assistant veri modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ContextType(str, Enum):
    """Baglam turu."""
    USER = "user"
    CONVERSATION = "conversation"
    TASK = "task"
    ENVIRONMENT = "environment"
    TEMPORAL = "temporal"


class IntentCategory(str, Enum):
    """Niyet kategorisi."""
    QUERY = "query"
    COMMAND = "command"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"
    FEEDBACK = "feedback"


class ResponseFormat(str, Enum):
    """Yanit formati."""
    TEXT = "text"
    SUMMARY = "summary"
    DETAILED = "detailed"
    LIST = "list"
    TABLE = "table"


class ChannelType(str, Enum):
    """Kanal turu."""
    TELEGRAM = "telegram"
    EMAIL = "email"
    VOICE = "voice"
    API = "api"
    WEB = "web"


class PreferenceType(str, Enum):
    """Tercih turu."""
    COMMUNICATION = "communication"
    STYLE = "style"
    TOOL = "tool"
    TIME = "time"
    FORMAT = "format"


class ProactiveType(str, Enum):
    """Proaktif yardim turu."""
    SUGGESTION = "suggestion"
    REMINDER = "reminder"
    ALERT = "alert"
    PREVENTION = "prevention"
    OPPORTUNITY = "opportunity"


class ContextSnapshot(BaseModel):
    """Baglam goruntusu."""
    context_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    context_type: ContextType = ContextType.USER
    data: dict[str, Any] = Field(default_factory=dict)
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class IntentPrediction(BaseModel):
    """Niyet tahmini."""
    prediction_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    category: IntentCategory = IntentCategory.QUERY
    predicted_action: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class SmartResponse(BaseModel):
    """Akilli yanit."""
    response_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    content: str = ""
    format: ResponseFormat = ResponseFormat.TEXT
    tone: str = "neutral"
    detail_level: float = Field(default=0.5, ge=0.0, le=1.0)
    channel: ChannelType = ChannelType.TELEGRAM
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class UserPreference(BaseModel):
    """Kullanici tercihi."""
    preference_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    preference_type: PreferenceType = PreferenceType.COMMUNICATION
    key: str = ""
    value: Any = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    learned_from: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ConversationEntry(BaseModel):
    """Konusma girdisi."""
    entry_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    role: str = "user"
    content: str = ""
    topic: str = ""
    channel: ChannelType = ChannelType.TELEGRAM
    references: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ProactiveAction(BaseModel):
    """Proaktif aksiyon."""
    action_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    action_type: ProactiveType = ProactiveType.SUGGESTION
    title: str = ""
    description: str = ""
    urgency: float = Field(default=0.5, ge=0.0, le=1.0)
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class AssistantSnapshot(BaseModel):
    """Asistan goruntusu."""
    total_conversations: int = 0
    total_predictions: int = 0
    prediction_accuracy: float = 0.0
    preferences_learned: int = 0
    proactive_actions: int = 0
    active_channels: int = 0
    context_items: int = 0
    uptime_seconds: float = 0.0
