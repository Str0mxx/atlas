"""ATLAS Deep Research Engine modelleri.

Çoklu kaynak tarama, sorgu genişletme,
kaynak sıralama, bilgi çıkarma,
çapraz doğrulama, sentez, raporlama.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Kaynak tipi."""

    web = "web"
    academic = "academic"
    news = "news"
    social = "social"
    database = "database"
    api = "api"


class CredibilityLevel(str, Enum):
    """Güvenilirlik seviyesi."""

    authoritative = "authoritative"
    high = "high"
    moderate = "moderate"
    low = "low"
    unknown = "unknown"
    unreliable = "unreliable"


class ResearchStatus(str, Enum):
    """Araştırma durumu."""

    queued = "queued"
    crawling = "crawling"
    extracting = "extracting"
    validating = "validating"
    synthesizing = "synthesizing"
    completed = "completed"


class ReportFormat(str, Enum):
    """Rapor formatı."""

    markdown = "markdown"
    html = "html"
    json = "json"
    pdf = "pdf"
    text = "text"
    executive = "executive"


class ValidationResult(str, Enum):
    """Doğrulama sonucu."""

    verified = "verified"
    likely_true = "likely_true"
    uncertain = "uncertain"
    contradicted = "contradicted"
    unverifiable = "unverifiable"
    false = "false"


class TrackingFrequency(str, Enum):
    """Takip sıklığı."""

    realtime = "realtime"
    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    on_change = "on_change"


class ResearchRecord(BaseModel):
    """Araştırma kaydı."""

    research_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    query: str = ""
    status: ResearchStatus = (
        ResearchStatus.queued
    )
    sources_found: int = 0
    facts_extracted: int = 0
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class SourceRecord(BaseModel):
    """Kaynak kaydı."""

    source_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    url: str = ""
    source_type: SourceType = SourceType.web
    credibility: CredibilityLevel = (
        CredibilityLevel.unknown
    )
    credibility_score: float = 0.5
    domain: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class FactRecord(BaseModel):
    """Tespit edilen gerçek kaydı."""

    fact_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    content: str = ""
    source_count: int = 0
    validation: ValidationResult = (
        ValidationResult.uncertain
    )
    confidence: float = 0.5
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ResearchSnapshot(BaseModel):
    """Araştırma sistem anlık görüntüsü."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    active_research: int = 0
    total_sources: int = 0
    total_facts: int = 0
    tracked_topics: int = 0
    reports_generated: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
