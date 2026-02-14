"""External Integration Hub veri modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuthType(str, Enum):
    """Kimlik dogrulama turu."""

    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    JWT = "jwt"
    BASIC = "basic"
    BEARER = "bearer"
    NONE = "none"


class ProtocolType(str, Enum):
    """Protokol turu."""

    REST = "rest"
    GRAPHQL = "graphql"
    SOAP = "soap"
    WEBSOCKET = "websocket"
    GRPC = "grpc"


class SyncMode(str, Enum):
    """Senkronizasyon modu."""

    FULL = "full"
    DELTA = "delta"
    BIDIRECTIONAL = "bidirectional"
    PUSH = "push"
    PULL = "pull"


class ServiceStatus(str, Enum):
    """Servis durumu."""

    ACTIVE = "active"
    DEGRADED = "degraded"
    DOWN = "down"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class ErrorCategory(str, Enum):
    """Hata kategorisi."""

    NETWORK = "network"
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    SERVER = "server"
    CLIENT = "client"
    DATA = "data"


class WebhookDirection(str, Enum):
    """Webhook yonu."""

    INCOMING = "incoming"
    OUTGOING = "outgoing"


class ConnectionRecord(BaseModel):
    """Baglanti kaydi."""

    connection_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    service_name: str = ""
    protocol: ProtocolType = ProtocolType.REST
    base_url: str = ""
    auth_type: AuthType = AuthType.NONE
    status: ServiceStatus = ServiceStatus.UNKNOWN
    latency_ms: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class SyncRecord(BaseModel):
    """Senkronizasyon kaydi."""

    sync_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    source: str = ""
    target: str = ""
    mode: SyncMode = SyncMode.DELTA
    records_synced: int = 0
    conflicts: int = 0
    success: bool = True
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class WebhookRecord(BaseModel):
    """Webhook kaydi."""

    webhook_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    direction: WebhookDirection = WebhookDirection.INCOMING
    url: str = ""
    event_type: str = ""
    verified: bool = False
    retry_count: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class IntegrationError(BaseModel):
    """Entegrasyon hatasi."""

    error_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    service: str = ""
    category: ErrorCategory = ErrorCategory.NETWORK
    message: str = ""
    status_code: int = 0
    retryable: bool = True
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class CacheEntry(BaseModel):
    """Onbellek girdisi."""

    cache_key: str = ""
    service: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    ttl_seconds: int = 300
    hit_count: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class IntegrationSnapshot(BaseModel):
    """Entegrasyon goruntusu."""

    total_services: int = 0
    active_services: int = 0
    total_requests: int = 0
    total_errors: int = 0
    cache_hit_rate: float = 0.0
    avg_latency_ms: float = 0.0
    webhooks_processed: int = 0
    syncs_completed: int = 0
    uptime_seconds: float = 0.0
