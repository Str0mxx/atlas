"""Intelligent Heartbeat Engine modelleri."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HeartbeatStatus(str, Enum):
    """Heartbeat durum seviyeleri."""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    SILENT = "silent"
    SKIPPED = "skipped"


class ImportanceLevel(str, Enum):
    """Onem seviyesi siniflandirmasi."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HeartbeatResult(BaseModel):
    """Tek bir heartbeat kontrolunun sonucu."""
    heartbeat_id: str = ""
    timestamp: float = 0.0
    status: HeartbeatStatus = HeartbeatStatus.OK
    importance: ImportanceLevel = ImportanceLevel.NONE
    message: str = ""
    findings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    should_notify: bool = False
    suppressed: bool = False


class HeartbeatTemplate(BaseModel):
    """Heartbeat kontrol sablonu."""
    template_id: str = ""
    name: str = ""
    content: str = ""
    interval_minutes: int = 15
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuietHoursConfig(BaseModel):
    """Sessiz saat yapilandirmasi."""
    enabled: bool = False
    start_hour: int = 22
    end_hour: int = 8
    timezone: str = "UTC"
    override_critical: bool = True
    days: list[str] = Field(
        default_factory=lambda: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    )


class DigestEntry(BaseModel):
    """Ozet derlemesine eklenecek tek bir kayit."""
    entry_id: str = ""
    heartbeat_id: str = ""
    importance: ImportanceLevel = ImportanceLevel.LOW
    summary: str = ""
    timestamp: float = 0.0


class HeartbeatConfig(BaseModel):
    """Heartbeat Engine genel yapilandirmasi."""
    default_interval: int = 15
    template_dir: str = "heartbeat_templates"
    suppress_tool_errors: bool = False
    strip_response_prefix: bool = True
    ok_responses: list[str] = Field(
        default_factory=lambda: ["HEARTBEAT_OK", "OK", "ALL_CLEAR"]
    )
    max_digest_size: int = 50
    digest_interval_minutes: int = 60
    sender_metadata: dict[str, str] = Field(default_factory=dict)
