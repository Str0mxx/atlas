"""ATLAS API Management & Gateway modelleri.

API kayit, yonlendirme, hiz siniri,
dogrulama, surumleme ve analitik modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class APIStatus(str, Enum):
    """API durumu."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    BETA = "beta"


class HTTPMethod(str, Enum):
    """HTTP metodu."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class RateLimitStrategy(str, Enum):
    """Hiz siniri stratejisi."""

    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


class VersioningStrategy(str, Enum):
    """Surumleme stratejisi."""

    URL = "url"
    HEADER = "header"
    QUERY = "query"


class ValidationLevel(str, Enum):
    """Dogrulama seviyesi."""

    STRICT = "strict"
    NORMAL = "normal"
    LENIENT = "lenient"


class ResponseFormat(str, Enum):
    """Yanit formati."""

    JSON = "json"
    XML = "xml"
    CSV = "csv"
    YAML = "yaml"


class APIRecord(BaseModel):
    """API kaydi."""

    api_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    version: str = "v1"
    base_path: str = ""
    status: APIStatus = APIStatus.ACTIVE
    endpoints: list[dict[str, Any]] = Field(
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


class RouteRecord(BaseModel):
    """Yonlendirme kaydi."""

    route_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    path: str = ""
    method: HTTPMethod = HTTPMethod.GET
    target: str = ""
    version: str = "v1"
    weight: int = 100
    active: bool = True


class AnalyticsRecord(BaseModel):
    """Analitik kaydi."""

    request_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    path: str = ""
    method: str = "GET"
    status_code: int = 200
    response_time_ms: float = 0.0
    client_id: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class APIGatewaySnapshot(BaseModel):
    """API Gateway goruntusu."""

    total_apis: int = 0
    total_routes: int = 0
    total_requests: int = 0
    avg_response_time: float = 0.0
    error_rate: float = 0.0
    active_rate_limits: int = 0
    documented_apis: int = 0
    api_versions: int = 0
