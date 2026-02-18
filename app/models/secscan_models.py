"""Continuous Security Scanner modelleri."""

from enum import Enum

from pydantic import BaseModel, Field


class ScanType(str, Enum):
    """Tarama turu."""

    VULNERABILITY = "vulnerability"
    CODE_ANALYSIS = "code_analysis"
    DEPENDENCY = "dependency"
    CONFIG = "config"
    PORT = "port"
    SSL = "ssl"
    CVE = "cve"
    FULL = "full"


class SeverityLevel(str, Enum):
    """Ciddiyet seviyesi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class PatchStatus(str, Enum):
    """Yama durumu."""

    PENDING = "pending"
    TESTING = "testing"
    SCHEDULED = "scheduled"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"


class CertGrade(str, Enum):
    """Sertifika notu."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class PortState(str, Enum):
    """Port durumu."""

    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"


class ComplianceStatus(str, Enum):
    """Uyumluluk durumu."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"


class VulnerabilityRecord(BaseModel):
    """Zafiyet kaydi."""

    finding_id: str = ""
    name: str = ""
    severity: SeverityLevel = (
        SeverityLevel.MEDIUM
    )
    source: str = ""
    match_count: int = 0
    remediation: str = ""
    fixed: bool = False


class DependencyRecord(BaseModel):
    """Bagimlilik kaydi."""

    package_id: str = ""
    name: str = ""
    version: str = ""
    latest_version: str = ""
    license_type: str = ""
    outdated: bool = False
    vulnerable: bool = False


class ConfigIssueRecord(BaseModel):
    """Config sorunu kaydi."""

    issue_id: str = ""
    rule: str = ""
    severity: SeverityLevel = (
        SeverityLevel.MEDIUM
    )
    suggestion: str = ""
    source: str = ""
    resolved: bool = False


class PortRecord(BaseModel):
    """Port kaydi."""

    port: int = 0
    service: str = ""
    state: PortState = PortState.OPEN
    risky: bool = False


class CertificateRecord(BaseModel):
    """Sertifika kaydi."""

    cert_id: str = ""
    domain: str = ""
    issuer: str = ""
    expires_at: str = ""
    cipher_suite: str = ""
    key_size: int = Field(default=2048)
    grade: CertGrade = CertGrade.A
    auto_renew: bool = False


class CVERecord(BaseModel):
    """CVE kaydi."""

    cve_id: str = ""
    description: str = ""
    severity: SeverityLevel = (
        SeverityLevel.HIGH
    )
    cvss_score: float = Field(
        default=0.0, ge=0.0, le=10.0
    )
    affected_software: str = ""
    patched: bool = False


class PatchRecord(BaseModel):
    """Yama kaydi."""

    patch_id: str = ""
    name: str = ""
    version: str = ""
    target_software: str = ""
    severity: SeverityLevel = (
        SeverityLevel.MEDIUM
    )
    status: PatchStatus = PatchStatus.PENDING
    cve_ids: list[str] = Field(
        default_factory=list
    )


class SecurityPosture(BaseModel):
    """Guvenlik durumu."""

    score: int = Field(
        default=100, ge=0, le=100
    )
    grade: CertGrade = CertGrade.A
    total_vulnerabilities: int = 0
    unresolved_issues: int = 0
    critical_count: int = 0
    compliant: bool = True
