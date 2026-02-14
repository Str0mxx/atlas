"""Security Hardening veri modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ThreatLevel(str, Enum):
    """Tehdit seviyesi."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(str, Enum):
    """Tehdit turu."""

    BRUTE_FORCE = "brute_force"
    INJECTION = "injection"
    XSS = "xss"
    INTRUSION = "intrusion"
    ANOMALY = "anomaly"
    DDOS = "ddos"
    DATA_LEAK = "data_leak"


class AccessAction(str, Enum):
    """Erisim aksiyonu."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class AuditEventType(str, Enum):
    """Denetim olay turu."""

    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS = "access"
    CHANGE = "change"
    THREAT = "threat"
    ERROR = "error"
    POLICY = "policy"


class SessionStatus(str, Enum):
    """Oturum durumu."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    LOCKED = "locked"


class FirewallAction(str, Enum):
    """Guvenlik duvari aksiyonu."""

    ALLOW = "allow"
    BLOCK = "block"
    RATE_LIMIT = "rate_limit"
    LOG = "log"


class ThreatRecord(BaseModel):
    """Tehdit kaydi."""

    threat_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    threat_type: ThreatType = ThreatType.ANOMALY
    level: ThreatLevel = ThreatLevel.LOW
    source: str = ""
    target: str = ""
    description: str = ""
    blocked: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class AccessRecord(BaseModel):
    """Erisim kaydi."""

    access_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    user: str = ""
    role: str = ""
    resource: str = ""
    action: AccessAction = AccessAction.READ
    granted: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class AuditEntry(BaseModel):
    """Denetim girdisi."""

    entry_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    event_type: AuditEventType = AuditEventType.ACCESS
    actor: str = ""
    action: str = ""
    resource: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    severity: ThreatLevel = ThreatLevel.NONE
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class SessionRecord(BaseModel):
    """Oturum kaydi."""

    session_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    user: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    ip_address: str = ""
    user_agent: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class SecuritySnapshot(BaseModel):
    """Guvenlik goruntusu."""

    total_threats: int = 0
    blocked_threats: int = 0
    active_sessions: int = 0
    access_denials: int = 0
    audit_entries: int = 0
    firewall_blocks: int = 0
    encryption_operations: int = 0
    secrets_managed: int = 0
    uptime_seconds: float = 0.0
