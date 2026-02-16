"""
ATLAS Kişisel Finans Orkestratörü.

Tam kişisel finans yönetimi pipeline,
Track → Budget → Save → Invest → Grow,
finansal sağlık ve analitik.
"""

import logging
from typing import Any

from app.core.personalfin.bank_account_connector import (
    BankAccountConnector,
)
from app.core.personalfin.spending_categorizer import (
    SpendingCategorizer,
)
from app.core.personalfin.budget_planner import (
    PersonalBudgetPlanner,
)
from app.core.personalfin.savings_advisor import (
    SavingsAdvisor,
)
from app.core.personalfin.bill_reminder import (
    BillReminder,
)
from app.core.personalfin.personal_investment_tracker import (
    PersonalInvestmentTracker,
)
from app.core.personalfin.financial_goal_tracker import (
    PersonalFinancialGoalTracker,
)
from app.core.personalfin.net_worth_calculator import (
    NetWorthCalculator,
)

logger = logging.getLogger(__name__)


class PersonalFinOrchestrator:
    """Kişisel finans orkestratörü.

    Tüm kişisel finans bileşenlerini
    koordine eder.

    Attributes:
        bank: Banka bağlayıcı.
        categorizer: Harcama kategorize.
        budget: Bütçe planlayıcı.
        savings: Tasarruf danışmanı.
        bills: Fatura hatırlatıcı.
        investments: Yatırım takipçisi.
        goals: Hedef takipçisi.
        net_worth: Net değer hesaplayıcı.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.bank = BankAccountConnector()
        self.categorizer = (
            SpendingCategorizer()
        )
        self.budget = (
            PersonalBudgetPlanner()
        )
        self.savings = SavingsAdvisor()
        self.bills = BillReminder()
        self.investments = (
            PersonalInvestmentTracker()
        )
        self.goals = (
            PersonalFinancialGoalTracker()
        )
        self.net_worth = (
            NetWorthCalculator()
        )
        self._stats: dict[str, int] = {
            "cycles_run": 0,
        }

        logger.info(
            "PersonalFinOrchestrator "
            "baslatildi"
        )

    @property
    def cycle_count(self) -> int:
        """Döngü sayısı."""
        return self._stats["cycles_run"]

    def financial_health_check(
        self,
        income: float = 0.0,
        expenses: float = 0.0,
        assets: float = 0.0,
        liabilities: float = 0.0,
    ) -> dict[str, Any]:
        """Finansal sağlık kontrolü yapar.

        Args:
            income: Aylık gelir.
            expenses: Aylık gider.
            assets: Toplam varlıklar.
            liabilities: Toplam borçlar.

        Returns:
            Finansal sağlık raporu.
        """
        try:
            # Tasarruf önerisi
            save_rec = (
                self.savings
                .recommend_savings(
                    income, expenses
                )
            )

            # Net değer hesapla
            if assets > 0:
                self.net_worth.add_asset(
                    "Total Assets", assets
                )
            if liabilities > 0:
                self.net_worth.add_liability(
                    "Total Liabilities",
                    liabilities,
                )
            nw = (
                self.net_worth
                .calculate_net_worth()
            )

            # Sağlık skoru
            savings_rate = save_rec[
                "savings_rate"
            ]
            debt_ratio = round(
                (
                    liabilities
                    / max(assets, 1)
                )
                * 100,
                1,
            )

            if (
                savings_rate >= 20
                and debt_ratio < 30
            ):
                health = "excellent"
            elif (
                savings_rate >= 10
                and debt_ratio < 50
            ):
                health = "good"
            elif savings_rate >= 0:
                health = "fair"
            else:
                health = "poor"

            self._stats["cycles_run"] += 1

            return {
                "savings_rate": savings_rate,
                "debt_ratio": debt_ratio,
                "net_worth": nw["net_worth"],
                "health_score": health,
                "tips": save_rec["tips"],
                "health_checked": True,
            }

        except Exception as e:
            logger.error(
                f"Saglik kontrol "
                f"hatasi: {e}"
            )
            return {
                "savings_rate": 0.0,
                "debt_ratio": 0.0,
                "net_worth": 0.0,
                "health_score": "unknown",
                "tips": [],
                "health_checked": False,
                "error": str(e),
            }

    def monthly_summary(
        self,
        income: float = 0.0,
        transactions: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Aylık özet oluşturur.

        Args:
            income: Aylık gelir.
            transactions: İşlem listesi.

        Returns:
            Aylık özet.
        """
        try:
            if transactions is None:
                transactions = []

            total_spent = sum(
                t.get("amount", 0)
                for t in transactions
            )

            # Kategorize et
            categories: dict[
                str, float
            ] = {}
            for t in transactions:
                cat = self.categorizer \
                    .auto_categorize(
                        t.get("merchant", ""),
                        t.get("amount", 0),
                    )
                c = cat["category"]
                categories[c] = (
                    categories.get(c, 0)
                    + t.get("amount", 0)
                )

            remaining = round(
                income - total_spent, 2
            )
            spend_pct = round(
                (
                    total_spent
                    / max(income, 1)
                )
                * 100,
                1,
            )

            self._stats["cycles_run"] += 1

            return {
                "income": income,
                "total_spent": round(
                    total_spent, 2
                ),
                "remaining": remaining,
                "spend_pct": spend_pct,
                "categories": categories,
                "transaction_count": len(
                    transactions
                ),
                "summarized": True,
            }

        except Exception as e:
            logger.error(
                f"Aylik ozet hatasi: {e}"
            )
            return {
                "income": income,
                "total_spent": 0.0,
                "remaining": income,
                "spend_pct": 0.0,
                "categories": {},
                "summarized": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "cycles_run": self._stats[
                "cycles_run"
            ],
            "accounts_linked": (
                self.bank.account_count
            ),
            "transactions_categorized": (
                self.categorizer
                .categorized_count
            ),
            "budgets_created": (
                self.budget.budget_count
            ),
            "savings_goals": (
                self.savings.goal_count
            ),
            "bills_tracked": (
                self.bills.bill_count
            ),
            "investments_held": (
                self.investments
                .holding_count
            ),
            "financial_goals": (
                self.goals.goal_count
            ),
            "net_worth_calcs": (
                self.net_worth
                .calculation_count
            ),
        }
