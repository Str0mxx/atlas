"""
AI Safety & Hallucination Guard modelleri.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk seviyesi."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionType(str, Enum):
    """Tespit tipi."""

    FACTUAL_ERROR = "factual_error"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    CONTRADICTION = "contradiction"
    FABRICATION = "fabrication"
    EXAGGERATION = "exaggeration"
    MISATTRIBUTION = "misattribution"


class VerdictType(str, Enum):
    """Karar tipi."""

    TRUE = "true"
    MOSTLY_TRUE = "mostly_true"
    MIXED = "mixed"
    MOSTLY_FALSE = "mostly_false"
    FALSE = "false"
    UNVERIFIABLE = "unverifiable"


class AuthorityLevel(str, Enum):
    """Otorite seviyesi."""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXPERT = "expert"


class BiasType(str, Enum):
    """Onyargi tipi."""

    NONE = "none"
    POLITICAL = "political"
    COMMERCIAL = "commercial"
    IDEOLOGICAL = "ideological"
    CULTURAL = "cultural"
    SELECTION = "selection"


class CalibrationState(str, Enum):
    """Kalibrasyon durumu."""

    WELL_CALIBRATED = "well_calibrated"
    OVERCONFIDENT = "overconfident"
    UNDERCONFIDENT = "underconfident"
    UNCALIBRATED = "uncalibrated"


class FlagType(str, Enum):
    """Isaret tipi."""

    HEDGING = "hedging"
    SPECULATION = "speculation"
    KNOWLEDGE_GAP = "knowledge_gap"
    VAGUE_CLAIM = "vague_claim"
    UNVERIFIED = "unverified"
    APPROXIMATION = "approximation"


class EscalationPriority(str, Enum):
    """Eskalasyon onceligi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class EscalationStatus(str, Enum):
    """Eskalasyon durumu."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class BoundaryAction(str, Enum):
    """Sinir aksiyonu."""

    ALLOW = "allow"
    WARN = "warn"
    MODIFY = "modify"
    BLOCK = "block"
    ESCALATE = "escalate"


class HallucinationDetection(BaseModel):
    """Halusinasyon tespiti."""

    detection_id: str = ""
    response_text: str = ""
    has_hallucination: bool = False
    risk_score: float = 0.0
    risk_level: str = "none"
    confidence: float = 1.0
    findings_count: int = 0
    findings: list[dict[str, Any]] = (
        Field(default_factory=list)
    )


class FactCheckResult(BaseModel):
    """Gercek kontrol sonucu."""

    check_id: str = ""
    claims_found: int = 0
    overall_score: float = 1.0
    results: list[dict[str, Any]] = (
        Field(default_factory=list)
    )


class SourceVerification(BaseModel):
    """Kaynak dogrulama."""

    verification_id: str = ""
    source_name: str = ""
    overall_score: float = 0.0
    is_reliable: bool = False
    authority_level: str = "unknown"
    bias_type: str = "none"


class ConsistencyResult(BaseModel):
    """Tutarlilik sonucu."""

    analysis_id: str = ""
    consistency_score: float = 1.0
    issue_count: int = 0
    is_consistent: bool = True
    issues: list[dict[str, Any]] = (
        Field(default_factory=list)
    )


class CalibrationResult(BaseModel):
    """Kalibrasyon sonucu."""

    calibration_id: str = ""
    ece: float = 0.0
    state: str = "well_calibrated"
    brier_score: float | None = None
    bin_count: int = 0


class UncertaintyFlag(BaseModel):
    """Belirsizlik isareti."""

    flag_id: str = ""
    uncertainty_score: float = 0.0
    level: str = "info"
    finding_count: int = 0
    needs_warning: bool = False


class EscalationRecord(BaseModel):
    """Eskalasyon kaydi."""

    escalation_id: str = ""
    reason: str = ""
    priority: str = "medium"
    status: str = "pending"
    description: str = ""
    route_to: str = ""


class SafetyCheckResult(BaseModel):
    """Guvenlik kontrol sonucu."""

    enforcement_id: str = ""
    action: str = "allow"
    violation_count: int = 0
    is_safe: bool = True
    violations: list[dict[str, Any]] = (
        Field(default_factory=list)
    )


class AISafetySummary(BaseModel):
    """AI guvenlik ozeti."""

    hallucination_check: bool = True
    fact_checking: bool = True
    auto_escalate: bool = True
    safety_threshold: float = 0.5
    total_checks: int = 0
    total_escalations: int = 0
