"""ATLAS Logging & Audit Trail modelleri.

Log yonetimi, denetim izi, uyumluluk
ve analiz modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Log seviyesi."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogFormat(str, Enum):
    """Log formati."""

    JSON = "json"
    PLAIN = "plain"
    CSV = "csv"
    SYSLOG = "syslog"


class AuditAction(str, Enum):
    """Denetim aksiyonu."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"


class ComplianceStandard(str, Enum):
    """Uyumluluk standardi."""

    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"


class ExportTarget(str, Enum):
    """Disa aktarim hedefi."""

    FILE = "file"
    CLOUD = "cloud"
    SIEM = "siem"
    ARCHIVE = "archive"


class RetentionPolicy(str, Enum):
    """Saklama politikasi."""

    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    PERMANENT = "permanent"


class LogRecord(BaseModel):
    """Log kaydi."""

    log_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    level: LogLevel = LogLevel.INFO
    message: str = ""
    source: str = ""
    context: dict[str, Any] = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class AuditRecord(BaseModel):
    """Denetim kaydi."""

    audit_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    action: AuditAction = AuditAction.READ
    actor: str = ""
    resource: str = ""
    before_state: dict[str, Any] = Field(
        default_factory=dict,
    )
    after_state: dict[str, Any] = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ComplianceRecord(BaseModel):
    """Uyumluluk kaydi."""

    record_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    standard: ComplianceStandard = ComplianceStandard.GDPR
    status: str = "compliant"
    findings: list[str] = Field(
        default_factory=list,
    )


class LoggingSnapshot(BaseModel):
    """Loglama goruntusu."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    total_logs: int = 0
    total_audits: int = 0
    error_count: int = 0
    export_count: int = 0
