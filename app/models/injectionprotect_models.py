"""Prompt Injection Protection veri modelleri.

Injection tespit, girdi temizleme,
beceri butunluk, cikti dogrulama
ve tehdit istihbarati modelleri.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DetectionLevel(str, Enum):
    """Tespit seviyesi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PARANOID = "paranoid"


class ThreatType(str, Enum):
    """Tehdit tipi."""

    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    DATA_EXFILTRATION = "data_exfiltration"
    COMMAND_INJECTION = "command_injection"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    ENCODING_ATTACK = "encoding_attack"
    SOCIAL_ENGINEERING = "social_engineering"
    OTHER = "other"


class SeverityLevel(str, Enum):
    """Ciddiyet seviyesi."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionTaken(str, Enum):
    """Alinan aksiyon."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    SANITIZED = "sanitized"
    FLAGGED = "flagged"
    LOGGED = "logged"


class IntegrityStatus(str, Enum):
    """Butunluk durumu."""

    VALID = "valid"
    INVALID = "invalid"
    TAMPERED = "tampered"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class DetectionResult(BaseModel):
    """Tespit sonucu."""

    result_id: str = ""
    input_text: str = ""
    is_threat: bool = False
    threat_type: ThreatType = (
        ThreatType.OTHER
    )
    severity: SeverityLevel = (
        SeverityLevel.INFO
    )
    confidence: float = 0.0
    patterns_matched: list[str] = Field(
        default_factory=list,
    )
    details: str = ""
    action_taken: ActionTaken = (
        ActionTaken.ALLOWED
    )
    timestamp: float = 0.0


class SanitizeResult(BaseModel):
    """Temizleme sonucu."""

    result_id: str = ""
    original: str = ""
    sanitized: str = ""
    changes_made: list[str] = Field(
        default_factory=list,
    )
    threat_removed: bool = False
    encoding_fixed: bool = False
    timestamp: float = 0.0


class IntegrityRecord(BaseModel):
    """Butunluk kaydi."""

    record_id: str = ""
    skill_name: str = ""
    expected_hash: str = ""
    actual_hash: str = ""
    status: IntegrityStatus = (
        IntegrityStatus.UNKNOWN
    )
    signature: str = ""
    verified_at: float = 0.0
    details: str = ""


class OutputScanResult(BaseModel):
    """Cikti tarama sonucu."""

    scan_id: str = ""
    output_text: str = ""
    contains_sensitive: bool = False
    sensitive_types: list[str] = Field(
        default_factory=list,
    )
    filtered_output: str = ""
    redactions: int = 0
    timestamp: float = 0.0


class ThreatPattern(BaseModel):
    """Tehdit kalibi."""

    pattern_id: str = ""
    pattern: str = ""
    threat_type: ThreatType = (
        ThreatType.OTHER
    )
    severity: SeverityLevel = (
        SeverityLevel.MEDIUM
    )
    description: str = ""
    source: str = ""
    enabled: bool = True
    hit_count: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
