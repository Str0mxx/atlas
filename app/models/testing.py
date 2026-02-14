"""ATLAS Testing & Quality Assurance modelleri.

Test uretimi, calistirma, kapsam analizi,
mutasyon testi, regresyon ve kalite modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TestType(str, Enum):
    """Test tipi."""

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    LOAD = "load"
    MUTATION = "mutation"
    REGRESSION = "regression"


class TestStatus(str, Enum):
    """Test durumu."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class CoverageLevel(str, Enum):
    """Kapsam seviyesi."""

    LINE = "line"
    BRANCH = "branch"
    FUNCTION = "function"
    PATH = "path"


class MutationType(str, Enum):
    """Mutasyon tipi."""

    ARITHMETIC = "arithmetic"
    RELATIONAL = "relational"
    LOGICAL = "logical"
    BOUNDARY = "boundary"
    REMOVAL = "removal"


class QualityGate(str, Enum):
    """Kalite kapisi."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class ReportFormat(str, Enum):
    """Rapor formati."""

    HTML = "html"
    JSON = "json"
    XML = "xml"
    MARKDOWN = "markdown"


class TestRecord(BaseModel):
    """Test kaydi."""

    test_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    test_type: TestType = TestType.UNIT
    status: TestStatus = TestStatus.PENDING
    duration_ms: float = 0.0
    error_message: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CoverageRecord(BaseModel):
    """Kapsam kaydi."""

    coverage_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    module: str = ""
    level: CoverageLevel = CoverageLevel.LINE
    covered: int = 0
    total: int = 0
    percentage: float = 0.0


class MutationRecord(BaseModel):
    """Mutasyon kaydi."""

    mutation_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    mutation_type: MutationType = MutationType.ARITHMETIC
    original: str = ""
    mutated: str = ""
    killed: bool = False


class QASnapshot(BaseModel):
    """QA goruntusu."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    coverage_pct: float = 0.0
    mutation_score: float = 0.0
    quality_score: float = 0.0
    gate_status: QualityGate = QualityGate.PASSED
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
