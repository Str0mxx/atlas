"""
Decision & Activity Log Dashboard modelleri.

Olay, karar, log, arama, nedensel zincir,
geri alma, uyumluluk, denetim modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Olay turleri."""

    action = "action"
    decision = "decision"
    alert = "alert"
    change = "change"
    system = "system"


class LogLevel(str, Enum):
    """Log seviyeleri."""

    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class RollbackStatus(str, Enum):
    """Geri alma durumlari."""

    initiated = "initiated"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ComplianceFormat(str, Enum):
    """Uyumluluk formatlari."""

    json = "json"
    csv = "csv"
    pdf = "pdf"
    xml = "xml"


class AuditResult(str, Enum):
    """Denetim sonuclari."""

    success = "success"
    failure = "failure"
    denied = "denied"
    error = "error"


class DecisionOutcome(str, Enum):
    """Karar sonuclari."""

    pending = "pending"
    success = "success"
    failure = "failure"
    partial = "partial"
    cancelled = "cancelled"


class ActivityEventRecord(BaseModel):
    """Aktivite olay kaydi."""

    event_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    event_type: str = "action"
    actor: str = ""
    description: str = ""
    category: str = "system"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class DecisionRecord(BaseModel):
    """Karar kaydi."""

    decision_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    title: str = ""
    actor: str = ""
    context: str = ""
    reasoning: str = ""
    outcome: str = "pending"
    confidence: float = 0.8
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class LogRecord(BaseModel):
    """Log kaydi."""

    log_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    source: str = ""
    action: str = ""
    actor: str = ""
    level: str = "info"
    category: str = "system"
    details: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class SearchEntry(BaseModel):
    """Arama kaydi."""

    entry_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    content: str = ""
    source: str = ""
    entry_type: str = "log"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class CausalEvent(BaseModel):
    """Nedensel olay."""

    event_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    name: str = ""
    event_type: str = "action"
    cause_id: str = ""
    actor: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class RollbackRecord(BaseModel):
    """Geri alma kaydi."""

    rollback_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    action_id: str = ""
    reason: str = ""
    status: str = "initiated"
    approved_by: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class ComplianceRecord(BaseModel):
    """Uyumluluk kaydi."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    record_type: str = "audit"
    source: str = ""
    action: str = ""
    actor: str = ""
    regulation: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class AuditEntry(BaseModel):
    """Denetim kaydi."""

    audit_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8]
    )
    actor: str = ""
    action: str = ""
    resource: str = ""
    permission: str = ""
    result: str = "success"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
