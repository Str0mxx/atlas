"""ATLAS veri modelleri."""

from app.models.agent_log import AgentLogCreate, AgentLogRecord, AgentLogResponse
from app.models.coding import (
    CodeAnalysisResult,
    CodeIssue,
    CodeLanguage,
    CodeQualityMetrics,
    CodeTaskType,
    CodingConfig,
    SecurityVulnerability,
    SeverityLevel,
    VulnerabilityType,
)
from app.models.decision import DecisionCreate, DecisionRecord, DecisionResponse
from app.models.marketing import (
    AdCheckType,
    AdDisapproval,
    BudgetRecommendation,
    CampaignMetrics,
    KeywordMetrics,
    MarketingAnalysisResult,
    MarketingConfig,
    PerformanceLevel,
)
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
    # Coding modelleri
    "CodeAnalysisResult",
    "CodeIssue",
    "CodeLanguage",
    "CodeQualityMetrics",
    "CodeTaskType",
    "CodingConfig",
    "SecurityVulnerability",
    "SeverityLevel",
    "VulnerabilityType",
    # Marketing modelleri
    "AdCheckType",
    "AdDisapproval",
    "BudgetRecommendation",
    "CampaignMetrics",
    "KeywordMetrics",
    "MarketingAnalysisResult",
    "MarketingConfig",
    "PerformanceLevel",
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
