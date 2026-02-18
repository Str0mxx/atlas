"""
Zero Trust Access Controller modelleri.

Sifir guven erisim kontrolu icin
enum ve Pydantic modelleri.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VerificationMethod(str, Enum):
    """Dogrulama yontemi."""

    PASSWORD = "password"
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BIOMETRIC = "biometric"
    HARDWARE_KEY = "hardware_key"


class RiskLevel(str, Enum):
    """Risk seviyesi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SessionState(str, Enum):
    """Oturum durumu."""

    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class TokenType(str, Enum):
    """Token tipi."""

    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SERVICE = "service"
    TEMPORARY = "temporary"


class EscalationType(str, Enum):
    """Yetki yukseltme tipi."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    LATERAL = "lateral"
    ROLE_ABUSE = "role_abuse"
    PERMISSION_CREEP = "permission_creep"


class AlertSeverity(str, Enum):
    """Uyari ciddiyeti."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class TrustLevel(str, Enum):
    """Guven seviyesi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IdentityRecord(BaseModel):
    """Kimlik kaydi."""

    identity_id: str = ""
    user_id: str = ""
    methods: list[str] = Field(
        default_factory=list
    )
    risk_level: str = "low"
    verified: bool = False
    last_verified: str | None = None


class SessionRecord(BaseModel):
    """Oturum kaydi."""

    session_id: str = ""
    user_id: str = ""
    device_id: str = ""
    ip_address: str = ""
    state: str = "active"
    timeout_min: int = 30
    risk_level: str = "low"
    created_at: str = ""


class TokenRecord(BaseModel):
    """Token kaydi."""

    token_id: str = ""
    user_id: str = ""
    token_type: str = "access"
    scope: str = ""
    claims: dict[str, Any] = Field(
        default_factory=dict
    )
    active: bool = True
    ttl_min: int = 60
    issued_at: str = ""


class DeviceRecord(BaseModel):
    """Cihaz kaydi."""

    device_id: str = ""
    user_id: str = ""
    fingerprint: str = ""
    trust_score: float = 0.5
    trust_level: str = "medium"
    seen_count: int = 0
    revoked: bool = False


class EscalationAlert(BaseModel):
    """Yetki yukseltme uyarisi."""

    alert_id: str = ""
    user_id: str = ""
    action: str = ""
    severity: str = "warning"
    risk_score: float = 0.0
    detections: list[dict] = Field(
        default_factory=list
    )
    acknowledged: bool = False


class AccessCheckResult(BaseModel):
    """Erisim kontrol sonucu."""

    user_id: str = ""
    access: bool = False
    risk_score: float = 0.0
    issues: list[str] = Field(
        default_factory=list
    )
    steps: dict[str, Any] = Field(
        default_factory=dict
    )


class ZeroTrustStatus(BaseModel):
    """Zero Trust durum bilgisi."""

    health: str = "good"
    active_sessions: int = 0
    active_tokens: int = 0
    total_alerts: int = 0
    total_blocked: int = 0
    identities: int = 0
    devices: int = 0
