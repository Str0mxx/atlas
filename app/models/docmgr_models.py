"""ATLAS Smart Document Manager modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Doküman tipi."""

    CONTRACT = "contract"
    INVOICE = "invoice"
    REPORT = "report"
    PROPOSAL = "proposal"


class DocumentCategory(str, Enum):
    """Doküman kategorisi."""

    LEGAL = "legal"
    FINANCIAL = "financial"
    TECHNICAL = "technical"
    MARKETING = "marketing"


class AccessLevel(str, Enum):
    """Erişim seviyesi."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class VersionStatus(str, Enum):
    """Sürüm durumu."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class ExpiryStatus(str, Enum):
    """Süre durumu."""

    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    RENEWED = "renewed"


class TagSource(str, Enum):
    """Etiket kaynağı."""

    AUTO = "auto"
    MANUAL = "manual"
    ENTITY = "entity"
    TOPIC = "topic"


class DocumentRecord(BaseModel):
    """Doküman kaydı."""

    doc_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    title: str = ""
    doc_type: str = "report"
    category: str = "technical"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class VersionRecord(BaseModel):
    """Sürüm kaydı."""

    version_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    doc_id: str = ""
    version: str = "1.0"
    status: str = "draft"
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class TagRecord(BaseModel):
    """Etiket kaydı."""

    tag_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    tag: str = ""
    source: str = "auto"
    confidence: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ExpiryRecord(BaseModel):
    """Süre kaydı."""

    expiry_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    doc_id: str = ""
    status: str = "active"
    days_remaining: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
