"""ATLAS veri modelleri."""

from app.models.agent_log import AgentLogCreate, AgentLogRecord, AgentLogResponse
from app.models.decision import DecisionCreate, DecisionRecord, DecisionResponse
from app.models.research import (
    CompanyInfo,
    ReliabilityLevel,
    ResearchConfig,
    ResearchResult,
    ResearchType,
    ScrapedPage,
    SupplierScore,
    WebSearchResult,
)
from app.models.security import (
    BannedIPEntry,
    FailedLoginEntry,
    OpenPort,
    SecurityCheckType,
    SecurityScanConfig,
    SecurityScanResult,
    SSLCertInfo,
    SuspiciousProcess,
    ThreatLevel,
)
from app.models.server import (
    CpuMetrics,
    DiskMetrics,
    MetricStatus,
    MetricThresholds,
    RamMetrics,
    ServerConfig,
    ServerMetrics,
    ServiceStatus,
)
from app.models.task import TaskCreate, TaskRecord, TaskResponse, TaskStatus

__all__ = [
    # Server modelleri
    "CpuMetrics",
    "DiskMetrics",
    "MetricStatus",
    "MetricThresholds",
    "RamMetrics",
    "ServerConfig",
    "ServerMetrics",
    "ServiceStatus",
    # Guvenlik modelleri
    "BannedIPEntry",
    "FailedLoginEntry",
    "OpenPort",
    "SecurityCheckType",
    "SecurityScanConfig",
    "SecurityScanResult",
    "SSLCertInfo",
    "SuspiciousProcess",
    "ThreatLevel",
    # Arastirma modelleri
    "CompanyInfo",
    "ReliabilityLevel",
    "ResearchConfig",
    "ResearchResult",
    "ResearchType",
    "ScrapedPage",
    "SupplierScore",
    "WebSearchResult",
    # Gorev modelleri
    "TaskCreate",
    "TaskRecord",
    "TaskResponse",
    "TaskStatus",
    # Karar modelleri
    "DecisionCreate",
    "DecisionRecord",
    "DecisionResponse",
    # Agent log modelleri
    "AgentLogCreate",
    "AgentLogRecord",
    "AgentLogResponse",
]
