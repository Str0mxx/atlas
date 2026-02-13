"""ATLAS Just-in-Time Capability veri modelleri.

Ihtiyac aninda yetenek olusturma icin enum ve Pydantic modelleri:
yetenek kontrolu, ihtiyac analizi, API kesfi, hizli insa,
canli entegrasyon, kimlik yonetimi, sandbox test ve orkestrasyon.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# === Enum'lar ===


class CapabilityStatus(str, Enum):
    """Yetenek durumu."""

    AVAILABLE = "available"
    BUILDING = "building"
    TESTING = "testing"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    FAILED = "failed"
    ROLLBACK = "rollback"


class EffortLevel(str, Enum):
    """Uygulama efor seviyesi."""

    TRIVIAL = "trivial"
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    COMPLEX = "complex"


class SecurityLevel(str, Enum):
    """Guvenlik seviyesi."""

    PUBLIC = "public"
    API_KEY = "api_key"
    OAUTH = "oauth"
    MUTUAL_TLS = "mutual_tls"
    CUSTOM = "custom"


class AuthMethod(str, Enum):
    """Kimlik dogrulama yontemi."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    CUSTOM = "custom"


class SandboxTestResult(str, Enum):
    """Test sonucu."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class BuildPhase(str, Enum):
    """Insa asamasi."""

    ANALYZING = "analyzing"
    DISCOVERING = "discovering"
    BUILDING = "building"
    TESTING = "testing"
    INTEGRATING = "integrating"
    DEPLOYING = "deploying"
    COMPLETE = "complete"
    FAILED = "failed"


class OutputFormat(str, Enum):
    """Cikti formati."""

    JSON = "json"
    TEXT = "text"
    HTML = "html"
    CSV = "csv"
    BINARY = "binary"
    STREAM = "stream"


class FeasibilityLevel(str, Enum):
    """Fizibilite seviyesi."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFEASIBLE = "infeasible"


# === Modeller ===


class CapabilityInfo(BaseModel):
    """Yetenek bilgisi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    effort: EffortLevel = EffortLevel.MODERATE
    dependencies: list[str] = Field(default_factory=list)
    apis_required: list[str] = Field(default_factory=list)
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    feasibility: FeasibilityLevel = FeasibilityLevel.MEDIUM
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RequirementSpec(BaseModel):
    """Ihtiyac spesifikasyonu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    raw_request: str = ""
    parsed_intent: str = ""
    required_apis: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    output_format: OutputFormat = OutputFormat.JSON
    security_level: SecurityLevel = SecurityLevel.API_KEY
    constraints: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)


class APIEndpoint(BaseModel):
    """API endpoint bilgisi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    base_url: str = ""
    method: str = "GET"
    path: str = ""
    auth_method: AuthMethod = AuthMethod.NONE
    rate_limit: int = 0
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    doc_url: str = ""
    response_format: OutputFormat = OutputFormat.JSON


class GeneratedCode(BaseModel):
    """Uretilen kod."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    module_name: str = ""
    code_type: str = ""  # client, agent, model, test
    source_code: str = ""
    dependencies: list[str] = Field(default_factory=list)
    line_count: int = 0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CredentialEntry(BaseModel):
    """Kimlik bilgisi kaydi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    service_name: str = ""
    auth_method: AuthMethod = AuthMethod.API_KEY
    key_name: str = ""
    is_set: bool = False
    expires_at: datetime | None = None
    last_rotated: datetime | None = None


class SandboxResult(BaseModel):
    """Sandbox test sonucu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    test_name: str = ""
    result: SandboxTestResult = SandboxTestResult.PASSED
    execution_time_ms: float = 0.0
    output: str = ""
    error: str = ""
    security_issues: list[str] = Field(default_factory=list)


class BuildProgress(BaseModel):
    """Insa ilerleme durumu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    capability_name: str = ""
    phase: BuildPhase = BuildPhase.ANALYZING
    progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    message: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    errors: list[str] = Field(default_factory=list)


class JITResult(BaseModel):
    """JIT orkestrasyon sonucu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    request: str = ""
    capability_name: str = ""
    status: CapabilityStatus = CapabilityStatus.ACTIVE
    phases_completed: list[str] = Field(default_factory=list)
    build_time_ms: float = 0.0
    tests_passed: int = 0
    tests_total: int = 0
    cached: bool = False
    rollback_available: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
