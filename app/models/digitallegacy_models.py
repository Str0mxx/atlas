"""
Digital Legacy & Backup Manager modelleri.

Dijital varlık, yedekleme, şifreleme,
veraset, kurtarma, vasiyet modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """Dijital varlık türleri."""

    account = "account"
    document = "document"
    media = "media"
    credential = "credential"
    cryptocurrency = "cryptocurrency"
    subscription = "subscription"


class BackupStatus(str, Enum):
    """Yedekleme durumları."""

    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    verified = "verified"
    expired = "expired"


class EncryptionLevel(str, Enum):
    """Şifreleme seviyeleri."""

    none = "none"
    basic = "basic"
    standard = "standard"
    military = "military"
    quantum_safe = "quantum_safe"


class VerificationStatus(str, Enum):
    """Doğrulama durumları."""

    not_verified = "not_verified"
    passed = "passed"
    failed = "failed"
    partial = "partial"
    scheduled = "scheduled"
    overdue = "overdue"


class SuccessionTrigger(str, Enum):
    """Veraset tetikleyicileri."""

    inactivity = "inactivity"
    manual = "manual"
    date_based = "date_based"
    health_event = "health_event"
    legal_order = "legal_order"


class WillStatus(str, Enum):
    """Vasiyet durumları."""

    draft = "draft"
    active = "active"
    updated = "updated"
    executed = "executed"
    revoked = "revoked"
    archived = "archived"


class DigitalAssetRecord(BaseModel):
    """Dijital varlık kaydı."""

    asset_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = ""
    asset_type: str = "account"
    value_estimate: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class BackupRecord(BaseModel):
    """Yedekleme kaydı."""

    backup_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    source: str = ""
    destination: str = ""
    status: str = "pending"
    size_mb: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class SuccessionRecord(BaseModel):
    """Veraset kaydı."""

    succession_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    beneficiary: str = ""
    trigger: str = "inactivity"
    status: str = "active"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class DigitalWillRecord(BaseModel):
    """Dijital vasiyet kaydı."""

    will_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    title: str = ""
    status: str = "draft"
    version: int = 1
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
