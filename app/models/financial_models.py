"""ATLAS Financial Intelligence modelleri.

Finansal istihbarat, gelir/gider takibi,
nakit akış, fatura, karlılık modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    """İşlem tipi."""

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    REFUND = "refund"
    INVESTMENT = "investment"
    TAX = "tax"


class InvoiceStatus(str, Enum):
    """Fatura durumu."""

    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class AlertSeverity(str, Enum):
    """Uyarı şiddeti."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    WARNING = "warning"


class ExpenseCategory(str, Enum):
    """Gider kategorisi."""

    SALARY = "salary"
    RENT = "rent"
    UTILITIES = "utilities"
    MARKETING = "marketing"
    SOFTWARE = "software"
    TRAVEL = "travel"


class TaxType(str, Enum):
    """Vergi tipi."""

    INCOME = "income"
    VAT = "vat"
    CORPORATE = "corporate"
    WITHHOLDING = "withholding"
    PROPERTY = "property"
    CUSTOMS = "customs"


class ReportPeriod(str, Enum):
    """Rapor dönemi."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class TransactionRecord(BaseModel):
    """İşlem kaydı."""

    transaction_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    transaction_type: TransactionType = (
        TransactionType.INCOME
    )
    amount: float = 0.0
    currency: str = "TRY"
    category: str = ""
    description: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class InvoiceRecord(BaseModel):
    """Fatura kaydı."""

    invoice_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    status: InvoiceStatus = (
        InvoiceStatus.DRAFT
    )
    amount: float = 0.0
    client: str = ""
    due_date: datetime | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class AlertRecord(BaseModel):
    """Uyarı kaydı."""

    alert_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    severity: AlertSeverity = (
        AlertSeverity.MEDIUM
    )
    alert_type: str = ""
    message: str = ""
    acknowledged: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class FinancialSnapshot(BaseModel):
    """Finansal anlık görüntü."""

    total_income: float = 0.0
    total_expense: float = 0.0
    net_profit: float = 0.0
    invoices_pending: int = 0
    alerts_active: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
