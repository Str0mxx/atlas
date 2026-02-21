"""OpenClaw beceri ekosistemi modelleri.

SKILL.md dosyalarindan beceri ithal etme,
guvenlik taramasi ve donusum icin veri modelleri.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OpenClawRiskLevel(str, Enum):
    """OpenClaw guvenlik risk seviyesi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    SKIP = "skip"


class ScanCategory(str, Enum):
    """Guvenlik tarama kategorisi."""

    PROMPT_INJECTION = "prompt_injection"
    CREDENTIAL_STEALING = "credential_stealing"
    MALICIOUS_CODE = "malicious_code"
    QUALITY = "quality"


class OpenClawFrontmatter(BaseModel):
    """SKILL.md YAML frontmatter verisi."""

    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = Field(default_factory=list)
    category: str = ""
    primary_env: str = ""
    os: list[str] = Field(default_factory=list)
    requires_env: list[str] = Field(
        default_factory=list,
    )
    requires_bins: list[str] = Field(
        default_factory=list,
    )
    requires_install: list[str] = Field(
        default_factory=list,
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
    )


class OpenClawSkillRaw(BaseModel):
    """Ham OpenClaw beceri verisi."""

    file_path: str
    frontmatter: OpenClawFrontmatter = Field(
        default_factory=OpenClawFrontmatter,
    )
    body: str = ""
    source_repo: str = ""
    parse_errors: list[str] = Field(
        default_factory=list,
    )


class ScanFinding(BaseModel):
    """Tek bir guvenlik bulgusu."""

    category: str
    pattern: str = ""
    description: str = ""
    severity: str = "low"
    deduction: int = 0
    line_number: int = 0
    context: str = ""


class SecurityScanResult(BaseModel):
    """Guvenlik taramasi sonucu."""

    skill_path: str = ""
    skill_name: str = ""
    score: int = 100
    risk_level: str = "low"
    findings: list[ScanFinding] = Field(
        default_factory=list,
    )
    passed: bool = True
    scan_time: float = 0.0


class ConversionResult(BaseModel):
    """Beceri donusum sonucu."""

    skill_id: str = ""
    skill_name: str = ""
    class_name: str = ""
    category: str = "basic_tools"
    source_repo: str = ""
    success: bool = True
    error: str = ""
    risk_level: str = "low"


class ImportStatistics(BaseModel):
    """Ithalat istatistikleri."""

    total_found: int = 0
    parsed_ok: int = 0
    passed_security: int = 0
    imported: int = 0
    failed: int = 0
    duplicates: int = 0
    skipped: int = 0
    avg_security_score: float = 0.0
    by_category: dict[str, int] = Field(
        default_factory=dict,
    )
    by_risk_level: dict[str, int] = Field(
        default_factory=dict,
    )
    by_repo: dict[str, int] = Field(
        default_factory=dict,
    )
    errors: list[str] = Field(
        default_factory=list,
    )


class AwesomeListEntry(BaseModel):
    """Awesome listesi girdisi."""

    name: str = ""
    url: str = ""
    description: str = ""
    category: str = ""
    is_curated: bool = True
    security_score: int = 0
    is_premium: bool = False
