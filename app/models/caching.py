"""ATLAS Caching & Performance Optimization modelleri.

Onbellekleme, sorgu optimizasyonu,
sikistirma, profilleme modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CacheStrategy(str, Enum):
    """Onbellek stratejisi."""

    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    FIFO = "fifo"


class CacheLayer(str, Enum):
    """Onbellek katmani."""

    MEMORY = "memory"
    DISTRIBUTED = "distributed"
    DISK = "disk"


class CompressionType(str, Enum):
    """Sikistirma turu."""

    NONE = "none"
    GZIP = "gzip"
    BROTLI = "brotli"
    ZLIB = "zlib"


class ProfileMetric(str, Enum):
    """Profil metrigi."""

    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    IO_WAIT = "io_wait"


class BatchStatus(str, Enum):
    """Toplu islem durumu."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LoadPriority(str, Enum):
    """Yukleme onceligI."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class CacheEntry(BaseModel):
    """Onbellek kaydi."""

    key: str = ""
    value: Any = None
    layer: CacheLayer = CacheLayer.MEMORY
    ttl: int = 0
    hits: int = 0
    size_bytes: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ProfileRecord(BaseModel):
    """Profil kaydi."""

    profile_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    operation: str = ""
    metric: ProfileMetric = (
        ProfileMetric.EXECUTION_TIME
    )
    value: float = 0.0
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class BatchRecord(BaseModel):
    """Toplu islem kaydi."""

    batch_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    status: BatchStatus = BatchStatus.PENDING
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    duration: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CachingSnapshot(BaseModel):
    """Onbellekleme sistemi goruntusu."""

    total_entries: int = 0
    total_hits: int = 0
    total_misses: int = 0
    hit_rate: float = 0.0
    total_size_bytes: int = 0
    active_profiles: int = 0
    pending_batches: int = 0
    compression_ratio: float = 0.0
