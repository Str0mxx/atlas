"""ATLAS Version Control & Rollback modelleri.

Surum kontrolu, snapshot, degisiklik takibi,
geri alma ve migrasyon modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class VersionStatus(str, Enum):
    """Surum durumu."""

    DRAFT = "draft"
    RELEASED = "released"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ChangeType(str, Enum):
    """Degisiklik turu."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class SnapshotType(str, Enum):
    """Snapshot turu."""

    FULL = "full"
    INCREMENTAL = "incremental"
    CONFIGURATION = "configuration"
    DATA = "data"


class MigrationStatus(str, Enum):
    """Migrasyon durumu."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RollbackType(str, Enum):
    """Geri alma turu."""

    FULL = "full"
    SELECTIVE = "selective"
    STAGED = "staged"
    POINT_IN_TIME = "point_in_time"


class BranchStatus(str, Enum):
    """Dal durumu."""

    ACTIVE = "active"
    MERGED = "merged"
    CLOSED = "closed"
    STALE = "stale"


class VersionRecord(BaseModel):
    """Surum kaydi."""

    version_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    version: str = "0.1.0"
    status: VersionStatus = VersionStatus.DRAFT
    description: str = ""
    author: str = ""
    changes: list[dict[str, Any]] = Field(
        default_factory=list,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class SnapshotRecord(BaseModel):
    """Snapshot kaydi."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    snapshot_type: SnapshotType = SnapshotType.FULL
    source: str = ""
    data: dict[str, Any] = Field(
        default_factory=dict,
    )
    size_bytes: int = 0
    compressed: bool = False
    parent_id: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class MigrationRecord(BaseModel):
    """Migrasyon kaydi."""

    migration_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    status: MigrationStatus = MigrationStatus.PENDING
    direction: str = "forward"
    changes: list[dict[str, Any]] = Field(
        default_factory=list,
    )
    duration: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class VersioningSnapshot(BaseModel):
    """Surumleme sistemi goruntusu."""

    total_versions: int = 0
    total_snapshots: int = 0
    total_changes: int = 0
    total_migrations: int = 0
    total_rollbacks: int = 0
    active_branches: int = 0
    current_version: str = "0.1.0"
    latest_release: str = ""
