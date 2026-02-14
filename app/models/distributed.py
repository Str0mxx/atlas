"""ATLAS Distributed System Coordination modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class NodeStatus(str, Enum):
    """Dugum durumu."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPECT = "suspect"
    FAILED = "failed"
    JOINING = "joining"
    LEAVING = "leaving"


class LockState(str, Enum):
    """Kilit durumu."""

    FREE = "free"
    ACQUIRED = "acquired"
    WAITING = "waiting"
    EXPIRED = "expired"
    DEADLOCKED = "deadlocked"
    RELEASED = "released"


class ConsensusType(str, Enum):
    """Konsensus tipi."""

    MAJORITY = "majority"
    UNANIMITY = "unanimity"
    QUORUM = "quorum"
    WEIGHTED = "weighted"
    BYZANTINE = "byzantine"
    RAFT = "raft"


class ReplicationMode(str, Enum):
    """Replikasyon modu."""

    SYNC = "sync"
    ASYNC = "async"
    SEMI_SYNC = "semi_sync"
    CHAIN = "chain"
    QUORUM_WRITE = "quorum_write"
    EVENTUAL = "eventual"


class PartitionStrategy(str, Enum):
    """Bolum stratejisi."""

    HASH = "hash"
    RANGE = "range"
    LIST = "list"
    ROUND_ROBIN = "round_robin"
    CONSISTENT_HASH = "consistent_hash"
    GEOGRAPHIC = "geographic"


class QueuePriority(str, Enum):
    """Kuyruk onceligi."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"
    BULK = "bulk"


class NodeRecord(BaseModel):
    """Dugum kaydi modeli."""

    node_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    status: NodeStatus = NodeStatus.ACTIVE
    host: str = "localhost"
    port: int = 8000
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class LockRecord(BaseModel):
    """Kilit kaydi modeli."""

    lock_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    resource: str = ""
    owner: str = ""
    state: LockState = LockState.FREE
    ttl: int = 30
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ReplicationRecord(BaseModel):
    """Replikasyon kaydi modeli."""

    replica_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    source_node: str = ""
    target_node: str = ""
    mode: ReplicationMode = ReplicationMode.ASYNC
    lag_ms: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class DistributedSnapshot(BaseModel):
    """Dagitik sistem snapshot modeli."""

    total_nodes: int = 0
    active_nodes: int = 0
    total_locks: int = 0
    total_partitions: int = 0
    total_replicas: int = 0
    queue_depth: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
