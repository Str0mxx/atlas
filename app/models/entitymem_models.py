"""ATLAS Unified Entity Memory modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Varlık tipi."""

    PERSON = "person"
    COMPANY = "company"
    PROJECT = "project"
    PRODUCT = "product"
    SERVICE = "service"


class RelationshipType(str, Enum):
    """İlişki tipi."""

    WORKS_FOR = "works_for"
    OWNS = "owns"
    COLLABORATES = "collaborates"
    MANAGES = "manages"
    SUPPLIES = "supplies"


class InteractionChannel(str, Enum):
    """Etkileşim kanalı."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    PHONE = "phone"
    MEETING = "meeting"
    API = "api"


class PrivacyLevel(str, Enum):
    """Gizlilik seviyesi."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PERSONAL = "personal"


class ConsentStatus(str, Enum):
    """Onay durumu."""

    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class EventType(str, Enum):
    """Olay tipi."""

    CREATED = "created"
    UPDATED = "updated"
    INTERACTION = "interaction"
    MILESTONE = "milestone"
    NOTE = "note"


class EntityRecord(BaseModel):
    """Varlık kaydı."""

    entity_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    entity_type: str = EntityType.PERSON
    aliases: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class InteractionRecord(BaseModel):
    """Etkileşim kaydı."""

    interaction_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    entity_id: str = ""
    channel: str = InteractionChannel.TELEGRAM
    content: str = ""
    sentiment: float = 0.0
    context: dict[str, Any] = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class RelationshipRecord(BaseModel):
    """İlişki kaydı."""

    source_id: str = ""
    target_id: str = ""
    relationship_type: str = (
        RelationshipType.COLLABORATES
    )
    strength: float = 0.5
    bidirectional: bool = False
    properties: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class EntityMemSnapshot(BaseModel):
    """Entity Memory snapshot."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    total_entities: int = 0
    total_interactions: int = 0
    total_relationships: int = 0
    privacy_mode: str = "standard"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
