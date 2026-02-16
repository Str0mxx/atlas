"""
Personal Finance Manager modelleri.

Banka hesabı, harcama, bütçe, tasarruf,
fatura, yatırım, hedef, net değer modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AccountType(str, Enum):
    """Hesap türleri."""

    checking = "checking"
    savings = "savings"
    credit_card = "credit_card"
    investment = "investment"
    loan = "loan"
    mortgage = "mortgage"


class SpendingCategory(str, Enum):
    """Harcama kategorileri."""

    food = "food"
    transport = "transport"
    housing = "housing"
    utilities = "utilities"
    entertainment = "entertainment"
    healthcare = "healthcare"
    education = "education"
    shopping = "shopping"


class BudgetPeriod(str, Enum):
    """Bütçe dönemleri."""

    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    quarterly = "quarterly"
    annual = "annual"


class GoalType(str, Enum):
    """Finansal hedef türleri."""

    emergency_fund = "emergency_fund"
    retirement = "retirement"
    vacation = "vacation"
    home_purchase = "home_purchase"
    debt_payoff = "debt_payoff"
    education_fund = "education_fund"


class InvestmentType(str, Enum):
    """Yatırım türleri."""

    stocks = "stocks"
    bonds = "bonds"
    mutual_funds = "mutual_funds"
    etf = "etf"
    crypto = "crypto"
    real_estate = "real_estate"


class BillFrequency(str, Enum):
    """Fatura sıklığı."""

    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    semi_annual = "semi_annual"
    annual = "annual"
    one_time = "one_time"


class BankAccountRecord(BaseModel):
    """Banka hesabı kaydı."""

    account_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    bank_name: str = "Default Bank"
    account_type: str = "checking"
    balance: float = 0.0
    currency: str = "TRY"
    linked_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class TransactionRecord(BaseModel):
    """İşlem kaydı."""

    transaction_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    amount: float = 0.0
    category: str = "uncategorized"
    merchant: str = ""
    description: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class BudgetRecord(BaseModel):
    """Bütçe kaydı."""

    budget_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = "Monthly Budget"
    period: str = "monthly"
    total_limit: float = 0.0
    spent: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class FinancialGoalRecord(BaseModel):
    """Finansal hedef kaydı."""

    goal_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = "Savings Goal"
    goal_type: str = "emergency_fund"
    target_amount: float = 0.0
    current_amount: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
