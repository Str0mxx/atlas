"""ATLAS Cost-Per-Decision Engine modelleri.

Karar basina maliyet hesaplama veri modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class CostCategory(str, Enum):
    """Maliyet kategorisi."""

    API_CALL = "api_call"
    COMPUTE = "compute"
    STORAGE = "storage"
    TIME = "time"
    OPPORTUNITY = "opportunity"


class BudgetPeriod(str, Enum):
    """Butce donemi."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class SpendingAction(str, Enum):
    """Harcama aksiyonu."""

    ALLOW = "allow"
    WARN = "warn"
    PAUSE = "pause"
    BLOCK = "block"
    APPROVE = "approve"


class OptimizationType(str, Enum):
    """Optimizasyon tipi."""

    CACHING = "caching"
    BATCHING = "batching"
    DOWNGRADE = "downgrade"
    ELIMINATION = "elimination"
    SCHEDULING = "scheduling"


class ReportFormat(str, Enum):
    """Rapor formati."""

    SUMMARY = "summary"
    DETAILED = "detailed"
    BREAKDOWN = "breakdown"
    TREND = "trend"
    EXPORT = "export"


class PricingModel(str, Enum):
    """Fiyatlandirma modeli."""

    FIXED = "fixed"
    PER_UNIT = "per_unit"
    TIERED = "tiered"
    DYNAMIC = "dynamic"
    FREE = "free"


class CostRecord(BaseModel):
    """Maliyet kaydi."""

    cost_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    decision_id: str = ""
    category: CostCategory = CostCategory.API_CALL
    amount: float = 0.0
    currency: str = "USD"
    description: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class BudgetRecord(BaseModel):
    """Butce kaydi."""

    budget_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    period: BudgetPeriod = BudgetPeriod.DAILY
    limit: float = 0.0
    spent: float = 0.0
    remaining: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class OptimizationRecord(BaseModel):
    """Optimizasyon kaydi."""

    optimization_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    type: OptimizationType = (
        OptimizationType.CACHING
    )
    estimated_savings: float = 0.0
    description: str = ""
    applied: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class CostEngineSnapshot(BaseModel):
    """Cost engine snapshot."""

    total_spent: float = 0.0
    active_budgets: int = 0
    decisions_tracked: int = 0
    avg_cost_per_decision: float = 0.0
    optimization_savings: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
