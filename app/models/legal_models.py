"""ATLAS Legal & Contract Analyzer modelleri.

Sözleşme, madde, risk, uyumluluk,
son tarih, karşılaştırma modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ContractType(str, Enum):
    """Sözleşme tipi."""

    SERVICE = "service"
    NDA = "nda"
    EMPLOYMENT = "employment"
    LEASE = "lease"
    LICENSE = "license"
    OTHER = "other"


class ClauseType(str, Enum):
    """Madde tipi."""

    OBLIGATION = "obligation"
    RIGHT = "right"
    TERMINATION = "termination"
    PAYMENT = "payment"
    LIABILITY = "liability"
    OTHER = "other"


class RiskSeverity(str, Enum):
    """Risk ciddiyeti."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class ComplianceStatus(str, Enum):
    """Uyumluluk durumu."""

    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"
    PENDING = "pending"


class DeadlineType(str, Enum):
    """Son tarih tipi."""

    RENEWAL = "renewal"
    TERMINATION = "termination"
    NOTICE = "notice"
    PAYMENT = "payment"
    DELIVERY = "delivery"
    OTHER = "other"


class NegotiationPriority(str, Enum):
    """Müzakere önceliği."""

    MUST_HAVE = "must_have"
    IMPORTANT = "important"
    NICE_TO_HAVE = "nice_to_have"
    FLEXIBLE = "flexible"
    CONCESSION = "concession"


class ContractRecord(BaseModel):
    """Sözleşme kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    title: str = ""
    contract_type: str = "other"
    parties: list[str] = Field(
        default_factory=list,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ClauseRecord(BaseModel):
    """Madde kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    contract_id: str = ""
    clause_type: str = "other"
    text: str = ""
    key_terms: list[str] = Field(
        default_factory=list,
    )


class RiskRecord(BaseModel):
    """Risk kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    contract_id: str = ""
    severity: str = "medium"
    description: str = ""
    mitigation: str = ""


class DeadlineRecord(BaseModel):
    """Son tarih kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    contract_id: str = ""
    deadline_type: str = "other"
    date: str = ""
    notice_days: int = 0
