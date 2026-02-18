"""
Payment & Financial Data Protector modelleri.

Odeme ve finansal veri koruma
veri modelleri.
"""

from enum import Enum

from pydantic import BaseModel, Field


class CardType(str, Enum):
    """Kart tipi."""

    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    DISCOVER = "discover"
    DINERS = "diners"
    JCB = "jcb"
    UNKNOWN = "unknown"


class TokenStatus(str, Enum):
    """Token durumu."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ComplianceLevel(str, Enum):
    """PCI uyum seviyesi."""

    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    LEVEL_4 = "level_4"


class LimitType(str, Enum):
    """Limit tipi."""

    SINGLE_AMOUNT = "single_amount"
    DAILY_AMOUNT = "daily_amount"
    WEEKLY_AMOUNT = "weekly_amount"
    MONTHLY_AMOUNT = "monthly_amount"
    DAILY_COUNT = "daily_count"
    HOURLY_COUNT = "hourly_count"


class RiskLevel(str, Enum):
    """Risk seviyesi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    """Onay durumu."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    OVERRIDDEN = "overridden"


class DisputeStatus(str, Enum):
    """Itiraz durumu."""

    OPENED = "opened"
    EVIDENCE_SUBMITTED = (
        "evidence_submitted"
    )
    UNDER_REVIEW = "under_review"
    WON = "won"
    LOST = "lost"
    EXPIRED = "expired"


class TransactionStatus(str, Enum):
    """Islem durumu."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class TokenRecord(BaseModel):
    """Token kaydi."""

    token_id: str = ""
    card_type: CardType = CardType.UNKNOWN
    masked_pan: str = ""
    last_four: str = ""
    holder_name: str = ""
    status: TokenStatus = (
        TokenStatus.ACTIVE
    )
    usage_count: int = 0


class ComplianceCheck(BaseModel):
    """Uyumluluk kontrolu."""

    data_type: str = ""
    is_encrypted: bool = False
    is_tokenized: bool = False
    compliant: bool = False
    violations: int = 0


class TransactionLimit(BaseModel):
    """Islem limiti."""

    name: str = ""
    limit_type: LimitType = (
        LimitType.SINGLE_AMOUNT
    )
    max_value: float = 0.0
    currency: str = "TRY"
    active: bool = True


class AnomalyRecord(BaseModel):
    """Anomali kaydi."""

    anomaly_id: str = ""
    user_id: str = ""
    amount: float = 0.0
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    flags: list[dict] = Field(
        default_factory=list
    )


class ApprovalRequest(BaseModel):
    """Onay istegi."""

    request_id: str = ""
    request_type: str = "payment"
    amount: float = 0.0
    requester_id: str = ""
    status: ApprovalStatus = (
        ApprovalStatus.PENDING
    )
    required_approvals: int = 2


class DisputeRecord(BaseModel):
    """Itiraz kaydi."""

    dispute_id: str = ""
    transaction_id: str = ""
    amount: float = 0.0
    reason: str = "other"
    status: DisputeStatus = (
        DisputeStatus.OPENED
    )
    outcome: str | None = None


class PaymentTransaction(BaseModel):
    """Odeme islemi."""

    transaction_id: str = ""
    amount: float = 0.0
    currency: str = "TRY"
    token_id: str = ""
    merchant_id: str = ""
    status: TransactionStatus = (
        TransactionStatus.PENDING
    )
    gateway_name: str = ""


class PayProtectStatus(BaseModel):
    """PayProtect durumu."""

    active_tokens: int = 0
    pci_violations: int = 0
    limiter_alerts: int = 0
    anomalies: int = 0
    pending_approvals: int = 0
    transactions: int = 0
    open_disputes: int = 0
