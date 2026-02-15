"""ATLAS GraphQL modelleri.

GraphQL ve API federasyonu veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Alan tipi."""

    STRING = "String"
    INT = "Int"
    FLOAT = "Float"
    BOOLEAN = "Boolean"
    ID = "ID"
    CUSTOM = "Custom"


class OperationType(str, Enum):
    """Islem tipi."""

    QUERY = "query"
    MUTATION = "mutation"
    SUBSCRIPTION = "subscription"
    FRAGMENT = "fragment"
    INLINE_FRAGMENT = "inline_fragment"
    DIRECTIVE = "directive"


class ResolverType(str, Enum):
    """Cozumleyici tipi."""

    FIELD = "field"
    BATCH = "batch"
    DEFAULT = "default"
    COMPUTED = "computed"
    DELEGATE = "delegate"
    CUSTOM = "custom"


class SubscriptionStatus(str, Enum):
    """Abonelik durumu."""

    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ERROR = "error"
    PENDING = "pending"
    RECONNECTING = "reconnecting"


class FederationMode(str, Enum):
    """Federasyon modu."""

    STITCHING = "stitching"
    FEDERATION = "federation"
    STANDALONE = "standalone"
    GATEWAY = "gateway"
    SUBGRAPH = "subgraph"
    HYBRID = "hybrid"


class ComplexityLevel(str, Enum):
    """Karmasiklik seviyesi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    BLOCKED = "blocked"
    UNLIMITED = "unlimited"


class SchemaRecord(BaseModel):
    """Sema kaydi."""

    schema_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    types_count: int = 0
    queries_count: int = 0
    mutations_count: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class QueryRecord(BaseModel):
    """Sorgu kaydi."""

    query_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    operation: OperationType = OperationType.QUERY
    complexity: int = 0
    depth: int = 0
    duration_ms: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class SubscriptionRecord(BaseModel):
    """Abonelik kaydi."""

    subscription_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    event_type: str = ""
    status: SubscriptionStatus = (
        SubscriptionStatus.ACTIVE
    )
    events_received: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class GraphQLSnapshot(BaseModel):
    """GraphQL snapshot."""

    total_types: int = 0
    total_resolvers: int = 0
    active_subscriptions: int = 0
    queries_executed: int = 0
    federation_services: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
