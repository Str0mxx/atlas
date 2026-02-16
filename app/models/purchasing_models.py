"""ATLAS Autonomous Purchasing Agent modelleri.

Otonom satın alma ajanı veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Sipariş durumu."""

    pending = "pending"
    approved = "approved"
    ordered = "ordered"
    shipped = "shipped"
    delivered = "delivered"
    canceled = "canceled"
    returned = "returned"


class SupplierTier(str, Enum):
    """Tedarikçi seviyesi."""

    platinum = "platinum"
    gold = "gold"
    silver = "silver"
    bronze = "bronze"
    new = "new"


class QualityGrade(str, Enum):
    """Kalite derecesi."""

    excellent = "excellent"
    good = "good"
    acceptable = "acceptable"
    poor = "poor"
    rejected = "rejected"


class BudgetStatus(str, Enum):
    """Bütçe durumu."""

    within = "within"
    warning = "warning"
    exceeded = "exceeded"
    frozen = "frozen"


class PurchasePriority(str, Enum):
    """Satın alma önceliği."""

    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    optional = "optional"


class ApprovalLevel(str, Enum):
    """Onay seviyesi."""

    auto = "auto"
    manager = "manager"
    director = "director"
    executive = "executive"


class OrderRecord(BaseModel):
    """Sipariş kaydı."""

    id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    item: str = ""
    supplier: str = ""
    quantity: int = 0
    unit_price: float = 0.0
    status: OrderStatus = OrderStatus.pending
    priority: PurchasePriority = (
        PurchasePriority.medium
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class SupplierRecord(BaseModel):
    """Tedarikçi kaydı."""

    id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    tier: SupplierTier = SupplierTier.new
    reliability: float = 0.0
    location: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class QualityRecord(BaseModel):
    """Kalite kaydı."""

    id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    order_id: str = ""
    grade: QualityGrade = (
        QualityGrade.acceptable
    )
    issues: list[str] = Field(
        default_factory=list,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class BudgetRecord(BaseModel):
    """Bütçe kaydı."""

    id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    category: str = ""
    limit_amount: float = 0.0
    spent_amount: float = 0.0
    status: BudgetStatus = (
        BudgetStatus.within
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
