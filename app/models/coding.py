"""Coding agent'i veri modelleri.

Kod analizi, bug tespiti, guvenlik taramasi, optimizasyon onerileri
ve kod uretimi sonuclarini modellar.
"""

from enum import Enum

from pydantic import BaseModel, Field


class CodeTaskType(str, Enum):
    """Kod gorevi tipleri."""

    ANALYZE = "analyze"
    BUG_DETECT = "bug_detect"
    OPTIMIZE = "optimize"
    SECURITY_SCAN = "security_scan"
    GENERATE = "generate"
    REVIEW = "review"


class CodeLanguage(str, Enum):
    """Desteklenen programlama dilleri."""

    PYTHON = "python"
    PHP = "php"
    JAVASCRIPT = "javascript"
    SQL = "sql"
    BASH = "bash"


class SeverityLevel(str, Enum):
    """Bulgu ciddiyet seviyesi."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class VulnerabilityType(str, Enum):
    """Guvenlik acigi tipleri."""

    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    HARDCODED_SECRET = "hardcoded_secret"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    INSECURE_HASH = "insecure_hash"
    OPEN_REDIRECT = "open_redirect"
    OTHER = "other"


class CodingConfig(BaseModel):
    """Coding agent yapilandirmasi.

    Attributes:
        model: Kullanilacak Anthropic modeli.
        max_tokens: LLM yanit uzunlugu limiti.
        supported_languages: Desteklenen diller.
        static_analysis_enabled: Regex tabanli statik analiz aktif mi.
    """

    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    supported_languages: list[CodeLanguage] = Field(
        default_factory=lambda: list(CodeLanguage),
    )
    static_analysis_enabled: bool = True


class CodeIssue(BaseModel):
    """Kod sorunu / bulgu.

    Attributes:
        line: Satir numarasi (biliniyorsa).
        severity: Ciddiyet seviyesi.
        category: Bulgu kategorisi (bug, style, performance, vb.).
        message: Sorun aciklamasi.
        suggestion: Duzeltme onerisi.
    """

    line: int = 0
    severity: SeverityLevel = SeverityLevel.INFO
    category: str = ""
    message: str = ""
    suggestion: str = ""


class SecurityVulnerability(BaseModel):
    """Guvenlik acigi bulgusu.

    Attributes:
        vuln_type: Acik tipi.
        line: Satir numarasi (biliniyorsa).
        severity: Ciddiyet seviyesi.
        description: Acik aciklamasi.
        fix: Duzeltme onerisi.
        snippet: Sorunlu kod parcasi.
    """

    vuln_type: VulnerabilityType = VulnerabilityType.OTHER
    line: int = 0
    severity: SeverityLevel = SeverityLevel.WARNING
    description: str = ""
    fix: str = ""
    snippet: str = ""


class CodeQualityMetrics(BaseModel):
    """Kod kalite metrikleri.

    Attributes:
        complexity: Karmasiklik puani (1-10, dusuk=iyi).
        readability: Okunabilirlik puani (1-10, yuksek=iyi).
        maintainability: Bakimlanabilirlik puani (1-10, yuksek=iyi).
        overall_score: Genel kalite puani (1-10).
    """

    complexity: float = 5.0
    readability: float = 5.0
    maintainability: float = 5.0
    overall_score: float = 5.0


class CodeAnalysisResult(BaseModel):
    """Kod analiz genel sonucu.

    Attributes:
        task_type: Yapilan gorev tipi.
        language: Tespit edilen veya belirtilen dil.
        issues: Tespit edilen sorunlar.
        vulnerabilities: Guvenlik aciklari.
        quality: Kalite metrikleri.
        suggestions: Genel iyilestirme onerileri.
        generated_code: Uretilen kod (generate gorevi icin).
        explanation: Kod aciklamasi (analyze gorevi icin).
        summary: Analiz ozeti.
    """

    task_type: CodeTaskType = CodeTaskType.ANALYZE
    language: CodeLanguage = CodeLanguage.PYTHON
    issues: list[CodeIssue] = Field(default_factory=list)
    vulnerabilities: list[SecurityVulnerability] = Field(default_factory=list)
    quality: CodeQualityMetrics = Field(default_factory=CodeQualityMetrics)
    suggestions: list[str] = Field(default_factory=list)
    generated_code: str = ""
    explanation: str = ""
    summary: str = ""
