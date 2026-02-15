"""ATLAS Configuration Management modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ConfigFormat(str, Enum):
    """Konfigurasyon formati."""

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    ENV = "env"
    INI = "ini"
    PROPERTIES = "properties"


class ConfigScope(str, Enum):
    """Konfigurasyon kapsami."""

    GLOBAL = "global"
    ENVIRONMENT = "environment"
    SERVICE = "service"
    INSTANCE = "instance"
    USER = "user"
    TEMPORARY = "temporary"


class ValidationLevel(str, Enum):
    """Dogrulama seviyesi."""

    STRICT = "strict"
    NORMAL = "normal"
    LENIENT = "lenient"
    WARN = "warn"
    SKIP = "skip"
    CUSTOM = "custom"


class FlagStatus(str, Enum):
    """Bayrak durumu."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    GRADUAL = "gradual"
    AB_TEST = "ab_test"
    SCHEDULED = "scheduled"
    KILLED = "killed"


class SecretType(str, Enum):
    """Gizli veri tipi."""

    API_KEY = "api_key"
    PASSWORD = "password"
    CERTIFICATE = "certificate"
    TOKEN = "token"
    PRIVATE_KEY = "private_key"
    CONNECTION_STRING = "connection_string"


class EnvironmentType(str, Enum):
    """Ortam tipi."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"
    CI = "ci"
    LOCAL = "local"


class ConfigRecord(BaseModel):
    """Konfigurasyon kaydi modeli."""

    config_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    key: str = ""
    value: Any = None
    scope: ConfigScope = ConfigScope.GLOBAL
    version: int = 1
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class FlagRecord(BaseModel):
    """Bayrak kaydi modeli."""

    flag_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    status: FlagStatus = FlagStatus.DISABLED
    rollout_pct: float = 0.0
    targeting: dict[str, Any] = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class SecretRecord(BaseModel):
    """Gizli veri kaydi modeli."""

    secret_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    secret_type: SecretType = SecretType.API_KEY
    rotated_at: datetime | None = None
    access_count: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ConfigSnapshot(BaseModel):
    """Konfigurasyon snapshot modeli."""

    total_configs: int = 0
    total_secrets: int = 0
    total_flags: int = 0
    environments: int = 0
    pending_changes: int = 0
    validation_errors: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
