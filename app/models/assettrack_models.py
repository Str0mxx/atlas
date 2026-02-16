"""ATLAS Physical Inventory & Asset Tracker modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AssetCategory(str, Enum):
    """Varlık kategorisi."""

    EQUIPMENT = "equipment"
    FURNITURE = "furniture"
    VEHICLE = "vehicle"
    ELECTRONICS = "electronics"
    SOFTWARE = "software"


class AssetStatus(str, Enum):
    """Varlık durumu."""

    ACTIVE = "active"
    IN_MAINTENANCE = "in_maintenance"
    RETIRED = "retired"
    DISPOSED = "disposed"
    RESERVED = "reserved"


class DepreciationMethod(str, Enum):
    """Amortisman yöntemi."""

    STRAIGHT_LINE = "straight_line"
    DECLINING_BALANCE = "declining_balance"
    UNITS_OF_PRODUCTION = "units_of_production"


class MovementType(str, Enum):
    """Stok hareket tipi."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"


class AuditStatus(str, Enum):
    """Denetim durumu."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BarcodeFormat(str, Enum):
    """Barkod formatı."""

    QR = "qr"
    CODE128 = "code128"
    EAN13 = "ean13"
    UPC = "upc"


class AssetRecord(BaseModel):
    """Varlık kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    asset_name: str = ""
    category: str = "equipment"
    status: str = "active"
    purchase_cost: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class StockRecord(BaseModel):
    """Stok kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    item_id: str = ""
    quantity: int = 0
    location: str = ""
    min_level: int = 0
    max_level: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class MaintenanceRecord(BaseModel):
    """Bakım kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    asset_id: str = ""
    maintenance_type: str = "preventive"
    vendor: str = ""
    cost: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class AuditRecord(BaseModel):
    """Denetim kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    audit_type: str = "full"
    status: str = "scheduled"
    discrepancies: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
