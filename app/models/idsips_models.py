"""Intrusion Detection & Prevention modelleri."""

from enum import Enum

from pydantic import BaseModel, Field


class DetectionMode(str, Enum):
    """Tespit modu."""

    PASSIVE = "passive"
    ACTIVE = "active"
    HYBRID = "hybrid"


class ThreatType(str, Enum):
    """Tehdit turu."""

    BRUTE_FORCE = "brute_force"
    INJECTION = "injection"
    XSS = "xss"
    SESSION_HIJACK = "session_hijack"
    NETWORK_ANOMALY = "network_anomaly"
    BLOCKED_IP = "blocked_ip"
    THREAT_INTEL = "threat_intel"


class IncidentSeverity(str, Enum):
    """Olay ciddiyeti."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, Enum):
    """Olay durumu."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    CLOSED = "closed"


class BlockReason(str, Enum):
    """Engelleme sebebi."""

    BRUTE_FORCE = "brute_force"
    INJECTION_ATTEMPT = "injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    THREAT_INTEL = "threat_intel"
    RATE_LIMIT = "rate_limit"
    GEO_BLOCK = "geo_block"
    MANUAL = "manual"


class IOCType(str, Enum):
    """IOC turu."""

    IP = "ip"
    DOMAIN = "domain"
    HASH = "hash"
    URL = "url"
    EMAIL = "email"


class NetworkThreatRecord(BaseModel):
    """Ag tehdit kaydi."""

    source_ip: str = ""
    dest_ip: str = ""
    protocol: str = ""
    port: int = 0
    threat_type: ThreatType = (
        ThreatType.NETWORK_ANOMALY
    )
    severity: IncidentSeverity = (
        IncidentSeverity.MEDIUM
    )
    description: str = ""
    blocked: bool = False


class BruteForceRecord(BaseModel):
    """Kaba kuvvet kaydi."""

    ip: str = ""
    username: str = ""
    service: str = ""
    attempt_count: int = 0
    alert_generated: bool = False
    blocked: bool = False


class InjectionRecord(BaseModel):
    """Enjeksiyon kaydi."""

    detection_id: str = ""
    injection_type: str = ""
    source: str = ""
    severity: IncidentSeverity = (
        IncidentSeverity.CRITICAL
    )
    pattern_count: int = 0
    sanitized: bool = False


class SessionAlertRecord(BaseModel):
    """Oturum uyari kaydi."""

    alert_id: str = ""
    session_id: str = ""
    alert_type: str = ""
    severity: IncidentSeverity = (
        IncidentSeverity.HIGH
    )
    forced_logout: bool = False


class BlockRecord(BaseModel):
    """Engelleme kaydi."""

    block_id: str = ""
    ip: str = ""
    reason: BlockReason = (
        BlockReason.MANUAL
    )
    duration_minutes: int = Field(
        default=60, ge=0
    )
    permanent: bool = False


class IOCRecord(BaseModel):
    """IOC kaydi."""

    ioc_id: str = ""
    ioc_type: IOCType = IOCType.IP
    value: str = ""
    severity: IncidentSeverity = (
        IncidentSeverity.HIGH
    )
    source: str = ""
    active: bool = True


class IncidentRecord(BaseModel):
    """Olay kaydi."""

    incident_id: str = ""
    incident_type: str = ""
    source_ip: str = ""
    target: str = ""
    severity: IncidentSeverity = (
        IncidentSeverity.MEDIUM
    )
    status: IncidentStatus = (
        IncidentStatus.OPEN
    )
    description: str = ""
    evidence_count: int = 0
    timeline_events: int = 0


class IDSIPSStatus(BaseModel):
    """IDS/IPS durum ozeti."""

    total_incidents: int = 0
    open_incidents: int = 0
    critical_incidents: int = 0
    blocked_ips: int = 0
    active_sessions: int = 0
    iocs_tracked: int = 0
    detection_mode: DetectionMode = (
        DetectionMode.ACTIVE
    )
