"""ATLAS Regulatory & Constraint Engine modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RuleCategory(str, Enum):
    """Kural kategorisi."""

    LEGAL = "legal"
    FINANCIAL = "financial"
    PRIVACY = "privacy"
    OPERATIONAL = "operational"
    PLATFORM = "platform"


class ConstraintType(str, Enum):
    """Kısıt tipi."""

    HARD = "hard"
    SOFT = "soft"
    TEMPORAL = "temporal"
    CONDITIONAL = "conditional"
    RATE_LIMIT = "rate_limit"


class ViolationSeverity(str, Enum):
    """İhlal şiddeti."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class JurisdictionScope(str, Enum):
    """Yetki alanı kapsamı."""

    GLOBAL = "global"
    REGIONAL = "regional"
    NATIONAL = "national"
    INDUSTRY = "industry"
    PLATFORM = "platform"


class ExceptionStatus(str, Enum):
    """İstisna durumu."""

    REQUESTED = "requested"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ComplianceStatus(str, Enum):
    """Uyumluluk durumu."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    PENDING = "pending"
    EXEMPT = "exempt"


class RuleRecord(BaseModel):
    """Kural kaydı."""

    rule_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    category: str = RuleCategory.OPERATIONAL
    description: str = ""
    severity: str = ViolationSeverity.MEDIUM
    active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ConstraintRecord(BaseModel):
    """Kısıt kaydı."""

    constraint_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    constraint_type: str = ConstraintType.HARD
    condition: str = ""
    priority: int = 5
    properties: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ViolationRecord(BaseModel):
    """İhlal kaydı."""

    violation_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    rule_id: str = ""
    action: str = ""
    severity: str = ViolationSeverity.MEDIUM
    details: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class RegulatorySnapshot(BaseModel):
    """Regulatory snapshot."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    total_rules: int = 0
    total_violations: int = 0
    compliance_rate: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
