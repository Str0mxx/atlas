"""
API Key & Credential Lifecycle Manager modelleri.

Anahtar envanter, rotasyon, kullanim,
yetki, sizinti, iptal, saglik,
dogrulama modelleri.
"""

from enum import Enum

from pydantic import BaseModel, Field


class KeyType(str, Enum):
    """Anahtar tipi."""

    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"
    SERVICE_ACCOUNT = "service_account"
    SSH_KEY = "ssh_key"
    TLS_CERT = "tls_cert"
    JWT_SECRET = "jwt_secret"
    ENCRYPTION_KEY = "encryption_key"


class KeyStatus(str, Enum):
    """Anahtar durumu."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ROTATING = "rotating"


class RotationStrategy(str, Enum):
    """Rotasyon stratejisi."""

    TIME_BASED = "time_based"
    USAGE_BASED = "usage_based"
    EVENT_BASED = "event_based"
    MANUAL = "manual"


class LeakSource(str, Enum):
    """Sizinti kaynagi."""

    GITHUB_PUBLIC = "github_public"
    GIT_HISTORY = "git_history"
    DARK_WEB = "dark_web"
    PASTE_SITE = "paste_site"
    LOG_FILE = "log_file"
    CONFIG_FILE = "config_file"
    ENVIRONMENT = "environment"


class RevocationReason(str, Enum):
    """Iptal nedeni."""

    LEAKED = "leaked"
    COMPROMISED = "compromised"
    EXPIRED = "expired"
    OVER_PERMISSIONED = "over_permissioned"
    UNUSED = "unused"
    POLICY_VIOLATION = "policy_violation"
    MANUAL = "manual"
    ROTATION = "rotation"


class HealthGrade(str, Enum):
    """Saglik derecesi."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class VerificationStatus(str, Enum):
    """Dogrulama durumu."""

    PENDING = "pending"
    TESTING = "testing"
    PASSED = "passed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class KeyRecord(BaseModel):
    """Anahtar kaydi."""

    key_id: str = ""
    name: str = ""
    key_type: KeyType = KeyType.API_KEY
    owner: str = ""
    service: str = ""
    scopes: list[str] = Field(
        default_factory=list,
    )
    status: KeyStatus = KeyStatus.ACTIVE
    expires_days: int = 90
    usage_count: int = 0


class RotationSchedule(BaseModel):
    """Rotasyon zamanlama."""

    schedule_id: str = ""
    key_id: str = ""
    policy_name: str = ""
    rotation_days: int = 90
    strategy: RotationStrategy = (
        RotationStrategy.TIME_BASED
    )
    status: str = "scheduled"


class UsageLog(BaseModel):
    """Kullanim kaydi."""

    key_id: str = ""
    action: str = ""
    source_ip: str = ""
    user_agent: str = ""
    endpoint: str = ""
    response_code: int = 200


class LeakAlert(BaseModel):
    """Sizinti uyarisi."""

    alert_id: str = ""
    leak_id: str = ""
    severity: str = "critical"
    source: LeakSource = (
        LeakSource.GITHUB_PUBLIC
    )
    message: str = ""
    auto_revoked: bool = False


class RevocationRecord(BaseModel):
    """Iptal kaydi."""

    revocation_id: str = ""
    key_id: str = ""
    reason: RevocationReason = (
        RevocationReason.MANUAL
    )
    revoked_by: str = "system"
    cascade: bool = False
    replacement_id: str | None = None


class HealthReport(BaseModel):
    """Saglik raporu."""

    key_id: str = ""
    overall_score: float = 0.0
    grade: HealthGrade = (
        HealthGrade.GOOD
    )
    age_score: float = 0.0
    usage_score: float = 0.0
    permission_score: float = 0.0
    rotation_score: float = 0.0
    anomaly_score: float = 0.0


class VerificationResult(BaseModel):
    """Dogrulama sonucu."""

    verification_id: str = ""
    key_id: str = ""
    rotation_id: str = ""
    status: VerificationStatus = (
        VerificationStatus.PENDING
    )
    tests_passed: int = 0
    tests_failed: int = 0
    rolled_back: bool = False


class CredLifeStatus(BaseModel):
    """Genel durum."""

    total_keys: int = 0
    active_keys: int = 0
    total_schedules: int = 0
    total_leaks: int = 0
    total_revocations: int = 0
    average_health: float = 0.0
