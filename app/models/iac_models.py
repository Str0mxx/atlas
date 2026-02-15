"""ATLAS IaC modelleri.

Kod olarak altyapi veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ResourceStatus(str, Enum):
    """Kaynak durumu."""

    PENDING = "pending"
    CREATING = "creating"
    CREATED = "created"
    UPDATING = "updating"
    DELETING = "deleting"
    DELETED = "deleted"


class ChangeAction(str, Enum):
    """Degisiklik eylemi."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    REPLACE = "replace"
    NO_OP = "no_op"
    READ = "read"


class DriftSeverity(str, Enum):
    """Kayma ciddiyeti."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComplianceLevel(str, Enum):
    """Uyumluluk seviyesi."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    ERROR = "error"
    EXEMPTED = "exempted"
    NOT_ASSESSED = "not_assessed"


class StateBackend(str, Enum):
    """Durum arka ucu."""

    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"
    CONSUL = "consul"
    POSTGRESQL = "postgresql"


class ModuleStatus(str, Enum):
    """Modul durumu."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DRAFT = "draft"
    ARCHIVED = "archived"
    TESTING = "testing"
    PUBLISHED = "published"


class ResourceRecord(BaseModel):
    """Kaynak kaydi."""

    resource_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    resource_type: str = ""
    name: str = ""
    status: ResourceStatus = (
        ResourceStatus.PENDING
    )
    provider: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class PlanRecord(BaseModel):
    """Plan kaydi."""

    plan_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    creates: int = 0
    updates: int = 0
    deletes: int = 0
    estimated_cost: float = 0.0
    approved: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class DriftRecord(BaseModel):
    """Kayma kaydi."""

    drift_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    resource_type: str = ""
    resource_name: str = ""
    severity: DriftSeverity = DriftSeverity.NONE
    drifted_properties: int = 0
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class IaCSnapshot(BaseModel):
    """IaC snapshot."""

    total_resources: int = 0
    managed_resources: int = 0
    drifted_resources: int = 0
    compliance_score: float = 100.0
    modules_count: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
