"""Financial Dashboard veri modelleri."""

from enum import Enum

from pydantic import BaseModel, Field


class RevenueSource(str, Enum):
    """Gelir kaynagi turleri."""

    PRODUCT = "product"
    SERVICE = "service"
    SUBSCRIPTION = "subscription"
    ADVERTISING = "advertising"
    OTHER = "other"


class ExpenseCategory(str, Enum):
    """Gider kategorisi turleri."""

    INFRASTRUCTURE = "infrastructure"
    API = "api"
    PERSONNEL = "personnel"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    OTHER = "other"


class FlowType(str, Enum):
    """Nakit akis turleri."""

    INFLOW = "inflow"
    OUTFLOW = "outflow"


class ForecastMetric(str, Enum):
    """Tahmin metrik turleri."""

    REVENUE = "revenue"
    EXPENSE = "expense"
    PROFIT = "profit"


class BudgetStatus(str, Enum):
    """Butce durum turleri."""

    ON_BUDGET = "on_budget"
    UNDER_BUDGET = "under_budget"
    OVER_BUDGET = "over_budget"


class MarginStatus(str, Enum):
    """Marj durum turleri."""

    ABOVE_TARGET = "above_target"
    ACCEPTABLE = "acceptable"
    BELOW_MINIMUM = "below_minimum"


class RevenueRecord(BaseModel):
    """Gelir kaydi modeli."""

    amount: float = Field(
        default=0.0,
        description="Gelir tutari",
    )
    source: str = Field(
        default="overall",
        description="Gelir kaynagi",
    )
    period: str = Field(
        default="",
        description="Donem",
    )


class ExpenseRecord(BaseModel):
    """Gider kaydi modeli."""

    category: str = Field(
        default="",
        description="Gider kategorisi",
    )
    amount: float = Field(
        default=0.0,
        description="Gider tutari",
    )
    period: str = Field(
        default="",
        description="Donem",
    )
    description: str = Field(
        default="",
        description="Aciklama",
    )


class CashFlowEntry(BaseModel):
    """Nakit akis kaydi modeli."""

    flow_type: FlowType = Field(
        default=FlowType.INFLOW,
        description="Akis turu",
    )
    amount: float = Field(
        default=0.0,
        description="Tutar",
    )
    period: str = Field(
        default="",
        description="Donem",
    )
    category: str = Field(
        default="",
        description="Kategori",
    )


class BudgetEntry(BaseModel):
    """Butce kaydi modeli."""

    category: str = Field(
        default="",
        description="Kategori",
    )
    amount: float = Field(
        default=0.0,
        description="Butce tutari",
    )
    period: str = Field(
        default="",
        description="Donem",
    )


class ForecastDataPoint(BaseModel):
    """Tahmin veri noktasi modeli."""

    metric: ForecastMetric = Field(
        default=ForecastMetric.REVENUE,
        description="Metrik",
    )
    value: float = Field(
        default=0.0,
        description="Deger",
    )
    period: str = Field(
        default="",
        description="Donem",
    )


class InvestmentRecord(BaseModel):
    """Yatirim kaydi modeli."""

    name: str = Field(
        default="",
        description="Yatirim adi",
    )
    amount: float = Field(
        default=0.0,
        description="Yatirim tutari",
    )
    category: str = Field(
        default="technology",
        description="Kategori",
    )
    expected_return: float = Field(
        default=0.0,
        description="Beklenen getiri",
    )
    period_months: int = Field(
        default=12,
        description="Donem",
    )


class MarginRecord(BaseModel):
    """Kar marji kaydi modeli."""

    revenue: float = Field(
        default=0.0,
        description="Gelir",
    )
    cost: float = Field(
        default=0.0,
        description="Maliyet",
    )
    period: str = Field(
        default="",
        description="Donem",
    )
    category: str = Field(
        default="overall",
        description="Kategori",
    )
