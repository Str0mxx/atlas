"""ATLAS Runtime Capability Factory modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CapabilityStatus(str, Enum):
    """Yetenek durumu."""

    DRAFT = "draft"
    BUILDING = "building"
    TESTING = "testing"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"


class ComplexityLevel(str, Enum):
    """Karmaşıklık seviyesi."""

    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXTREME = "extreme"


class DeploymentStage(str, Enum):
    """Dağıtım aşaması."""

    CANARY = "canary"
    STAGING = "staging"
    PARTIAL = "partial"
    FULL = "full"
    ROLLED_BACK = "rolled_back"


class TestType(str, Enum):
    """Test tipi."""

    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    EDGE_CASE = "edge_case"


class RollbackReason(str, Enum):
    """Geri alma nedeni."""

    TEST_FAILURE = "test_failure"
    HEALTH_CHECK = "health_check"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MANUAL = "manual"


class SandboxState(str, Enum):
    """Sandbox durumu."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CLEANED = "cleaned"


class CapabilityRecord(BaseModel):
    """Yetenek kaydı."""

    capability_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    status: str = CapabilityStatus.DRAFT
    complexity: str = ComplexityLevel.MODERATE
    version: str = "1.0.0"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class DeploymentRecord(BaseModel):
    """Dağıtım kaydı."""

    deployment_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    capability_id: str = ""
    stage: str = DeploymentStage.CANARY
    healthy: bool = True
    rollback_reason: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class TestResult(BaseModel):
    """Test sonucu."""

    test_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    test_type: str = TestType.UNIT
    passed: bool = True
    coverage: float = 0.0
    details: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CapFactorySnapshot(BaseModel):
    """CapFactory snapshot."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    total_capabilities: int = 0
    total_deployments: int = 0
    total_rollbacks: int = 0
    active_sandboxes: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
