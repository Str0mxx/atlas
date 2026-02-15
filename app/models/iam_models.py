"""ATLAS Identity & Access Management modelleri.

Kimlik ve erisim yonetimi veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class AuthMethod(str, Enum):
    """Kimlik dogrulama yontemi."""

    PASSWORD = "password"
    MFA = "mfa"
    OAUTH = "oauth"
    API_KEY = "api_key"
    CERTIFICATE = "certificate"
    SSO = "sso"


class UserStatus(str, Enum):
    """Kullanici durumu."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DELETED = "deleted"


class PermissionEffect(str, Enum):
    """Izin etkisi."""

    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL = "conditional"


class TokenType(str, Enum):
    """Token tipi."""

    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    AUTH_CODE = "auth_code"
    ID_TOKEN = "id_token"


class AuditAction(str, Enum):
    """Denetim aksiyonu."""

    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACCESS = "access"
    DENY = "deny"
    GRANT = "grant"
    REVOKE = "revoke"


class OAuthGrantType(str, Enum):
    """OAuth hibe tipi."""

    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"
    IMPLICIT = "implicit"
    DEVICE_CODE = "device_code"


class IdentityRecord(BaseModel):
    """Kimlik kaydi."""

    identity_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    username: str = ""
    email: str = ""
    status: UserStatus = UserStatus.ACTIVE
    auth_method: AuthMethod = AuthMethod.PASSWORD
    mfa_enabled: bool = False
    roles: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class RoleRecord(BaseModel):
    """Rol kaydi."""

    role_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    description: str = ""
    permissions: list[str] = Field(
        default_factory=list,
    )
    parent_role: str | None = None
    is_default: bool = False
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class PolicyRecord(BaseModel):
    """Politika kaydi."""

    policy_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    effect: PermissionEffect = PermissionEffect.ALLOW
    resources: list[str] = Field(
        default_factory=list,
    )
    actions: list[str] = Field(
        default_factory=list,
    )
    conditions: dict = Field(default_factory=dict)
    priority: int = 0
    enabled: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class IAMSnapshot(BaseModel):
    """IAM snapshot."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    users: int = 0
    roles: int = 0
    permissions: int = 0
    policies: int = 0
    groups: int = 0
    sessions: int = 0
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
