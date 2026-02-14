"""ATLAS GitHub Project Integrator modelleri.

Repo kesfi, analiz, uyumluluk, klonlama,
kurulum, sarmalama ve guvenlik modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RepoStatus(str, Enum):
    """Repo durumu."""

    DISCOVERED = "discovered"
    ANALYZED = "analyzed"
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    CLONED = "cloned"
    INSTALLED = "installed"
    WRAPPED = "wrapped"
    REGISTERED = "registered"
    FAILED = "failed"


class InstallMethod(str, Enum):
    """Kurulum yontemi."""

    PIP = "pip"
    NPM = "npm"
    DOCKER = "docker"
    MAKE = "make"
    SETUP_PY = "setup_py"
    POETRY = "poetry"
    CARGO = "cargo"
    MANUAL = "manual"


class LicenseType(str, Enum):
    """Lisans tipi."""

    MIT = "mit"
    APACHE_2 = "apache-2.0"
    GPL_3 = "gpl-3.0"
    BSD_2 = "bsd-2-clause"
    BSD_3 = "bsd-3-clause"
    LGPL = "lgpl"
    ISC = "isc"
    UNLICENSE = "unlicense"
    PROPRIETARY = "proprietary"
    UNKNOWN = "unknown"


class QualityGrade(str, Enum):
    """Kalite notu."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"


class SecurityRisk(str, Enum):
    """Guvenlik risk seviyesi."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WrapperType(str, Enum):
    """Sarmalayici tipi."""

    AGENT = "agent"
    TOOL = "tool"
    LIBRARY = "library"
    CLI = "cli"
    API = "api"


class RepoInfo(BaseModel):
    """Repo bilgisi."""

    repo_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    full_name: str = ""
    url: str = ""
    description: str = ""
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    language: str = ""
    topics: list[str] = Field(default_factory=list)
    license_type: LicenseType = LicenseType.UNKNOWN
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    is_archived: bool = False
    activity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class TechStackInfo(BaseModel):
    """Teknoloji stack bilgisi."""

    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    python_version: str = ""
    node_version: str = ""


class DependencyInfo(BaseModel):
    """Bagimlilik bilgisi."""

    name: str = ""
    version: str = ""
    required: bool = True
    available: bool = True
    conflict: bool = False
    conflict_reason: str = ""


class RepoAnalysis(BaseModel):
    """Repo analiz sonucu."""

    repo_id: str = ""
    repo_name: str = ""
    tech_stack: TechStackInfo = Field(default_factory=TechStackInfo)
    dependencies: list[DependencyInfo] = Field(default_factory=list)
    has_tests: bool = False
    has_docs: bool = False
    has_ci: bool = False
    has_api: bool = False
    install_methods: list[InstallMethod] = Field(default_factory=list)
    quality_grade: QualityGrade = QualityGrade.UNKNOWN
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    readme_summary: str = ""
    api_endpoints: list[str] = Field(default_factory=list)


class CompatibilityResult(BaseModel):
    """Uyumluluk sonucu."""

    compatible: bool = True
    python_compatible: bool = True
    deps_compatible: bool = True
    os_compatible: bool = True
    license_compatible: bool = True
    resource_ok: bool = True
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    overall_score: float = Field(default=1.0, ge=0.0, le=1.0)


class CloneResult(BaseModel):
    """Klonlama sonucu."""

    clone_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    repo_name: str = ""
    local_path: str = ""
    branch: str = "main"
    commit_hash: str = ""
    sparse: bool = False
    size_mb: float = 0.0
    success: bool = True
    error: str = ""


class InstallResult(BaseModel):
    """Kurulum sonucu."""

    install_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    repo_name: str = ""
    method: InstallMethod = InstallMethod.PIP
    success: bool = True
    steps_completed: list[str] = Field(default_factory=list)
    steps_failed: list[str] = Field(default_factory=list)
    installed_packages: list[str] = Field(default_factory=list)
    config_generated: bool = False
    error: str = ""


class WrapperConfig(BaseModel):
    """Sarmalayici konfigurasyonu."""

    wrapper_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    repo_name: str = ""
    wrapper_type: WrapperType = WrapperType.TOOL
    agent_name: str = ""
    entry_point: str = ""
    input_mapping: dict[str, str] = Field(default_factory=dict)
    output_mapping: dict[str, str] = Field(default_factory=dict)
    error_handlers: list[str] = Field(default_factory=list)
    registered: bool = False


class SecurityScanResult(BaseModel):
    """Guvenlik tarama sonucu."""

    scan_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    repo_name: str = ""
    risk_level: SecurityRisk = SecurityRisk.LOW
    malware_detected: bool = False
    suspicious_patterns: list[str] = Field(default_factory=list)
    permissions_required: list[str] = Field(default_factory=list)
    network_access: bool = False
    file_system_access: bool = False
    requires_sandbox: bool = False
    safe_to_install: bool = True
    findings: list[str] = Field(default_factory=list)


class IntegrationReport(BaseModel):
    """Entegrasyon raporu."""

    report_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    repo_name: str = ""
    status: RepoStatus = RepoStatus.DISCOVERED
    repo_info: RepoInfo | None = None
    analysis: RepoAnalysis | None = None
    compatibility: CompatibilityResult | None = None
    clone_result: CloneResult | None = None
    install_result: InstallResult | None = None
    security_scan: SecurityScanResult | None = None
    wrapper: WrapperConfig | None = None
    processing_ms: float = 0.0
    recommendation: str = ""
