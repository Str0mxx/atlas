"""Data Pipeline & ETL System veri modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Veri kaynak turu."""

    DATABASE = "database"
    API = "api"
    FILE = "file"
    WEB = "web"
    STREAM = "stream"


class PipelineStatus(str, Enum):
    """Pipeline durumu."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    """Pipeline adim turu."""

    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    VALIDATE = "validate"
    BRANCH = "branch"
    MERGE = "merge"


class ValidationLevel(str, Enum):
    """Dogrulama seviyesi."""

    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"


class WindowType(str, Enum):
    """Pencere turu."""

    TUMBLING = "tumbling"
    SLIDING = "sliding"
    SESSION = "session"
    GLOBAL = "global"


class JobFrequency(str, Enum):
    """Is zamanlama sikligi."""

    MINUTELY = "minutely"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"


class PipelineRecord(BaseModel):
    """Pipeline kaydi."""

    pipeline_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    status: PipelineStatus = PipelineStatus.PENDING
    steps: list[dict[str, Any]] = Field(
        default_factory=list,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class StepRecord(BaseModel):
    """Pipeline adim kaydi."""

    step_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    step_type: StepType = StepType.EXTRACT
    name: str = ""
    status: PipelineStatus = PipelineStatus.PENDING
    input_count: int = 0
    output_count: int = 0
    error: str = ""


class LineageEntry(BaseModel):
    """Soy kaydi."""

    entry_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    source: str = ""
    target: str = ""
    transformation: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class PipelineSnapshot(BaseModel):
    """Pipeline goruntusu."""

    total_pipelines: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    total_records_processed: int = 0
    avg_duration: float = 0.0
    active_jobs: int = 0
    lineage_entries: int = 0
