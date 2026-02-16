"""ATLAS Knowledge Base & Wiki Engine modelleri."""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class PageStatus(str, Enum):
    """Sayfa durumu."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ContentType(str, Enum):
    """İçerik tipi."""

    WIKI = "wiki"
    FAQ = "faq"
    GUIDE = "guide"
    REFERENCE = "reference"


class ReviewStatus(str, Enum):
    """İnceleme durumu."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION = "revision"


class GapSeverity(str, Enum):
    """Boşluk şiddeti."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LinkType(str, Enum):
    """Bağlantı tipi."""

    RELATED = "related"
    PARENT = "parent"
    CHILD = "child"
    REFERENCE = "reference"


class ContributionType(str, Enum):
    """Katkı tipi."""

    CREATE = "create"
    EDIT = "edit"
    REVIEW = "review"
    DELETE = "delete"


class PageRecord(BaseModel):
    """Sayfa kaydı."""

    page_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    title: str = ""
    content_type: str = "wiki"
    status: str = "draft"
    author: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class FAQRecord(BaseModel):
    """SSS kaydı."""

    faq_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    question: str = ""
    answer: str = ""
    category: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class GapRecord(BaseModel):
    """Boşluk kaydı."""

    gap_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    topic: str = ""
    severity: str = "medium"
    description: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ContributionRecord(BaseModel):
    """Katkı kaydı."""

    contribution_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    contributor: str = ""
    contribution_type: str = "edit"
    page_id: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
