"""
Compliance & Regulatory Monitor modelleri.

Uyumluluk ve duzenleme izleyici
veri modelleri.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ComplianceFramework(str, Enum):
    """Uyumluluk cercevesi."""

    GDPR = "gdpr"
    KVKK = "kvkk"
    PCI_DSS = "pci_dss"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    ISO27001 = "iso27001"
    CCPA = "ccpa"


class PolicyType(str, Enum):
    """Politika tipi."""

    DATA_PROTECTION = "data_protection"
    ACCESS_CONTROL = "access_control"
    ENCRYPTION = "encryption"
    RETENTION = "retention"
    CONSENT = "consent"
    BREACH_RESPONSE = "breach_response"
    AUDIT = "audit"
    TRAINING = "training"


class DataCategory(str, Enum):
    """Veri kategorisi."""

    PERSONAL = "personal"
    SENSITIVE = "sensitive"
    FINANCIAL = "financial"
    HEALTH = "health"
    BIOMETRIC = "biometric"
    CHILDREN = "children"
    PUBLIC = "public"


class ConsentStatus(str, Enum):
    """Onay durumu."""

    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class GapSeverity(str, Enum):
    """Bosluk ciddiyeti."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class GapStatus(str, Enum):
    """Bosluk durumu."""

    IDENTIFIED = "identified"
    IN_PROGRESS = "in_progress"
    REMEDIATED = "remediated"
    ACCEPTED = "accepted"
    DEFERRED = "deferred"


class ReportType(str, Enum):
    """Rapor tipi."""

    COMPLIANCE_STATUS = (
        "compliance_status"
    )
    GAP_ANALYSIS = "gap_analysis"
    AUDIT_READY = "audit_ready"
    EXECUTIVE_SUMMARY = (
        "executive_summary"
    )
    INCIDENT_REPORT = "incident_report"
    DATA_PROTECTION = "data_protection"
    CONSENT_REPORT = "consent_report"


class RetentionType(str, Enum):
    """Saklama tipi."""

    FIXED = "fixed"
    EVENT_BASED = "event_based"
    INDEFINITE = "indefinite"
    REGULATORY = "regulatory"


class FrameworkInfo(BaseModel):
    """Cerceve bilgisi."""

    key: str = ""
    name: str = ""
    version: str = "1.0"
    region: str = ""
    requirements_count: int = 0
    is_active: bool = True


class PolicyRecord(BaseModel):
    """Politika kaydi."""

    policy_id: str = ""
    name: str = ""
    policy_type: PolicyType = (
        PolicyType.DATA_PROTECTION
    )
    framework_key: str = ""
    severity: str = "medium"
    is_active: bool = True


class DataFlowRecord(BaseModel):
    """Veri akis kaydi."""

    asset_id: str = ""
    name: str = ""
    category: DataCategory = (
        DataCategory.PERSONAL
    )
    country: str = ""
    is_cross_border: bool = False
    destination_country: str = ""


class ConsentRecord(BaseModel):
    """Onay kaydi."""

    consent_id: str = ""
    user_id: str = ""
    purpose_id: str = ""
    status: ConsentStatus = (
        ConsentStatus.GRANTED
    )
    source: str = ""


class GapRecord(BaseModel):
    """Bosluk kaydi."""

    gap_id: str = ""
    framework_key: str = ""
    title: str = ""
    severity: GapSeverity = (
        GapSeverity.MEDIUM
    )
    risk_score: float = Field(
        default=0.0, ge=0.0, le=1.0
    )
    status: GapStatus = (
        GapStatus.IDENTIFIED
    )


class ComplianceReport(BaseModel):
    """Uyumluluk raporu."""

    report_id: str = ""
    title: str = ""
    report_type: ReportType = (
        ReportType.COMPLIANCE_STATUS
    )
    framework_key: str = ""
    sections_count: int = 0
    status: str = "generated"


class RetentionPolicy(BaseModel):
    """Saklama politikasi."""

    policy_id: str = ""
    name: str = ""
    data_category: str = ""
    retention_type: RetentionType = (
        RetentionType.FIXED
    )
    retention_days: int = 365
    auto_delete: bool = False


class ComplianceStatus(BaseModel):
    """Uyumluluk durumu."""

    frameworks: int = 0
    violations: int = 0
    data_assets: int = 0
    access_logs: int = 0
    active_consents: int = 0
    open_gaps: int = 0
    reports: int = 0
