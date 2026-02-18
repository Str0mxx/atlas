"""
Security Incident Response & Forensics
veri modelleri.
"""

from enum import Enum

from pydantic import BaseModel, Field


class IncidentType(str, Enum):
    """Olay tipi."""

    MALWARE = "malware"
    PHISHING = "phishing"
    DATA_BREACH = "data_breach"
    UNAUTHORIZED = "unauthorized_access"
    DOS = "dos_attack"
    INSIDER = "insider_threat"
    RANSOMWARE = "ransomware"
    SUPPLY_CHAIN = "supply_chain"
    ZERO_DAY = "zero_day"
    SOCIAL_ENG = "social_engineering"


class SeverityLevel(str, Enum):
    """Ciddiyet seviyesi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(str, Enum):
    """Olay durumu."""

    ACTIVE = "active"
    CONTAINED = "contained"
    INVESTIGATING = "investigating"
    RECOVERING = "recovering"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ImpactLevel(str, Enum):
    """Etki seviyesi."""

    CATASTROPHIC = "catastrophic"
    SEVERE = "severe"
    MAJOR = "major"
    MODERATE = "moderate"
    MINOR = "minor"
    NEGLIGIBLE = "negligible"


class EvidenceType(str, Enum):
    """Kanit tipi."""

    LOG_FILE = "log_file"
    MEMORY_DUMP = "memory_dump"
    NETWORK_CAPTURE = "network_capture"
    DISK_IMAGE = "disk_image"
    CONFIGURATION = "configuration"
    PROCESS_LIST = "process_list"
    REGISTRY = "registry"
    FILE_ARTIFACT = "file_artifact"


class ContainmentAction(str, Enum):
    """Cevreleme aksiyonu."""

    NETWORK_ISOLATE = "network_isolate"
    ACCOUNT_SUSPEND = "account_suspend"
    SERVICE_SHUTDOWN = "service_shutdown"
    PORT_BLOCK = "port_block"
    IP_BLOCK = "ip_block"
    PROCESS_KILL = "process_kill"
    FILE_QUARANTINE = "file_quarantine"
    CREDENTIAL_REVOKE = "credential_revoke"


class PlaybookType(str, Enum):
    """Playbook tipi."""

    MALWARE = "malware_response"
    PHISHING = "phishing_response"
    DATA_BREACH = "data_breach"
    RANSOMWARE = "ransomware"
    DOS = "dos_attack"
    INSIDER = "insider_threat"
    UNAUTHORIZED = "unauthorized_access"
    GENERAL = "general_incident"


class CauseCategory(str, Enum):
    """Kok neden kategorisi."""

    HUMAN_ERROR = "human_error"
    SOFTWARE_BUG = "software_bug"
    CONFIGURATION = "configuration"
    VULNERABILITY = "vulnerability"
    SOCIAL_ENG = "social_engineering"
    INSIDER = "insider_threat"
    SUPPLY_CHAIN = "supply_chain"
    ZERO_DAY = "zero_day"
    POLICY = "policy_violation"
    INFRASTRUCTURE = "infrastructure"


class IncidentRecord(BaseModel):
    """Olay kaydi."""

    incident_id: str = ""
    title: str = ""
    incident_type: str = "malware"
    severity: str = "medium"
    status: str = "active"
    source: str = ""
    description: str = ""
    indicators: list[str] = Field(
        default_factory=list
    )
    affected_systems: list[str] = Field(
        default_factory=list
    )


class EvidenceRecord(BaseModel):
    """Kanit kaydi."""

    evidence_id: str = ""
    incident_id: str = ""
    evidence_type: str = "log_file"
    title: str = ""
    content: str = ""
    hash: str = ""
    integrity: str = "verified"


class ImpactAssessment(BaseModel):
    """Etki degerlendirmesi."""

    assessment_id: str = ""
    incident_id: str = ""
    impact_level: str = "moderate"
    impact_score: float = 0.0
    affected_users: int = 0
    financial_impact: float = 0.0
    categories: list[str] = Field(
        default_factory=list
    )


class RecoveryPlan(BaseModel):
    """Kurtarma plani."""

    plan_id: str = ""
    incident_id: str = ""
    title: str = ""
    priority: str = "high"
    status: str = "created"
    steps: list[dict] = Field(
        default_factory=list
    )


class PlaybookRecord(BaseModel):
    """Playbook kaydi."""

    playbook_id: str = ""
    name: str = ""
    playbook_type: str = (
        "general_incident"
    )
    severity_trigger: str = "high"
    version: int = 1
    status: str = "draft"
    auto_execute: bool = False


class LessonRecord(BaseModel):
    """Ders kaydi."""

    lesson_id: str = ""
    incident_id: str = ""
    title: str = ""
    category: str = "process"
    what_went_well: str = ""
    what_went_wrong: str = ""
    recommendations: list[str] = Field(
        default_factory=list
    )


class RootCauseAnalysis(BaseModel):
    """Kok neden analizi."""

    analysis_id: str = ""
    incident_id: str = ""
    title: str = ""
    status: str = "in_progress"
    root_causes: list[dict] = Field(
        default_factory=list
    )


class IncidentSummary(BaseModel):
    """Olay mudahale ozeti."""

    total_incidents: int = 0
    active_incidents: int = 0
    active_quarantines: int = 0
    evidence_count: int = 0
    lessons_learned: int = 0
    playbooks: int = 0
