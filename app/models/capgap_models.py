"""ATLAS Capability Gap Detection modelleri.

Yetenek eksikligi tespiti ve edinme veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class GapSeverity(str, Enum):
    """Eksiklik siddeti."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class AcquisitionStrategy(str, Enum):
    """Edinme stratejisi."""

    BUILD = "build"
    BUY = "buy"
    LEARN = "learn"
    INTEGRATE = "integrate"
    DELEGATE = "delegate"


class CapabilityStatus(str, Enum):
    """Yetenek durumu."""

    AVAILABLE = "available"
    PARTIAL = "partial"
    MISSING = "missing"
    DEPRECATED = "deprecated"
    IN_PROGRESS = "in_progress"


class ValidationResult(str, Enum):
    """Dogrulama sonucu."""

    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    PENDING = "pending"


class AcquisitionPhase(str, Enum):
    """Edinme asamasi."""

    DETECTION = "detection"
    PLANNING = "planning"
    ACQUISITION = "acquisition"
    VALIDATION = "validation"
    DEPLOYMENT = "deployment"


class SkillCategory(str, Enum):
    """Yetenek kategorisi."""

    API_INTEGRATION = "api_integration"
    DATA_PROCESSING = "data_processing"
    MACHINE_LEARNING = "machine_learning"
    COMMUNICATION = "communication"
    INFRASTRUCTURE = "infrastructure"


class GapRecord(BaseModel):
    """Eksiklik kaydi."""

    gap_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    task_id: str = ""
    capability: str = ""
    severity: GapSeverity = GapSeverity.MEDIUM
    status: CapabilityStatus = (
        CapabilityStatus.MISSING
    )
    priority: float = 0.0
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class AcquisitionPlan(BaseModel):
    """Edinme plani."""

    plan_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    gap_id: str = ""
    strategy: AcquisitionStrategy = (
        AcquisitionStrategy.BUILD
    )
    estimated_hours: float = 0.0
    estimated_cost: float = 0.0
    risk_level: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CapabilityRecord(BaseModel):
    """Yetenek kaydi."""

    capability_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    category: SkillCategory = (
        SkillCategory.API_INTEGRATION
    )
    version: str = "1.0.0"
    status: CapabilityStatus = (
        CapabilityStatus.AVAILABLE
    )
    coverage: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CapGapSnapshot(BaseModel):
    """CapGap snapshot."""

    total_capabilities: int = 0
    total_gaps: int = 0
    gaps_resolved: int = 0
    acquisitions_in_progress: int = 0
    avg_acquisition_time: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
