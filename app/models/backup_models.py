"""ATLAS Backup & Disaster Recovery modelleri.

Yedekleme ve felaket kurtarma veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class BackupType(str, Enum):
    """Yedekleme tipi."""

    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"
    CONTINUOUS = "continuous"
    ARCHIVE = "archive"


class BackupStatus(str, Enum):
    """Yedekleme durumu."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    VERIFYING = "verifying"


class StorageType(str, Enum):
    """Depolama tipi."""

    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"
    REMOTE = "remote"
    NFS = "nfs"


class FailoverMode(str, Enum):
    """Yuk devri modu."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SEMI_AUTOMATIC = "semi_automatic"
    SCHEDULED = "scheduled"
    DNS_BASED = "dns_based"
    TRAFFIC_BASED = "traffic_based"


class DisasterSeverity(str, Enum):
    """Felaket ciddiyeti."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    CATASTROPHIC = "catastrophic"
    UNKNOWN = "unknown"


class ReplicationMode(str, Enum):
    """Replikasyon modu."""

    SYNC = "sync"
    ASYNC = "async"
    SEMI_SYNC = "semi_sync"
    BATCH = "batch"
    STREAMING = "streaming"
    SNAPSHOT = "snapshot"


class BackupRecord(BaseModel):
    """Yedekleme kaydi."""

    backup_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    backup_type: BackupType = BackupType.FULL
    status: BackupStatus = BackupStatus.PENDING
    size_bytes: int = 0
    duration_seconds: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class RestoreRecord(BaseModel):
    """Geri yukleme kaydi."""

    restore_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    source_backup_id: str = ""
    target: str = ""
    status: BackupStatus = BackupStatus.PENDING
    verified: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class DRPlanRecord(BaseModel):
    """DR plan kaydi."""

    plan_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    rto_minutes: int = 0
    rpo_minutes: int = 0
    severity: DisasterSeverity = (
        DisasterSeverity.MEDIUM
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class BackupSnapshot(BaseModel):
    """Backup snapshot."""

    total_backups: int = 0
    total_size_bytes: int = 0
    successful_restores: int = 0
    failed_restores: int = 0
    dr_plans: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
