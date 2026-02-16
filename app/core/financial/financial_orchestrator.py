"""ATLAS Finansal Orkestratör modülü.

Tam finansal yönetim pipeline'ı,
Track → Analyze → Predict → Alert → Report,
karar entegrasyonu, analitik.
"""

import logging
from typing import Any

from app.core.financial.cashflow_predictor import (
    CashFlowPredictor,
)
from app.core.financial.expense_analyzer import (
    ExpenseAnalyzer,
)
from app.core.financial.financial_alert_engine import (
    FinancialAlertEngine,
)
from app.core.financial.financial_reporter import (
    FinancialReporter,
)
from app.core.financial.income_tracker import (
    IncomeTracker,
)
from app.core.financial.invoice_manager import (
    InvoiceManager,
)
from app.core.financial.profitability_calculator import (
    ProfitabilityCalculator,
)
from app.core.financial.tax_estimator import (
    TaxEstimator,
)

logger = logging.getLogger(__name__)


class FinancialOrchestrator:
    """Finansal orkestratör.

    Tüm finansal bileşenleri koordine eder.

    Attributes:
        income: Gelir takipçisi.
        expenses: Gider analizcisi.
        cashflow: Nakit akış tahmincisi.
        invoices: Fatura yöneticisi.
        profitability: Karlılık hesaplayıcı.
        alerts: Uyarı motoru.
        tax: Vergi tahmincisi.
        reporter: Raporlayıcı.
    """

    def __init__(
        self,
        currency: str = "TRY",
        tax_rate: float = 0.20,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            currency: Para birimi.
            tax_rate: Vergi oranı.
        """
        self.income = IncomeTracker(
            currency=currency,
        )
        self.expenses = ExpenseAnalyzer(
            currency=currency,
        )
        self.cashflow = CashFlowPredictor(
            currency=currency,
        )
        self.invoices = InvoiceManager(
            currency=currency,
        )
        self.profitability = (
            ProfitabilityCalculator()
        )
        self.alerts = FinancialAlertEngine()
        self.tax = TaxEstimator(
            tax_rate=tax_rate,
        )
        self.reporter = FinancialReporter()

        self._currency = currency
        self._stats = {
            "transactions_processed": 0,
            "reports_generated": 0,
            "alerts_triggered": 0,
        }

        logger.info(
            "FinancialOrchestrator "
            "baslatildi",
        )

    def record_transaction(
        self,
        amount: float,
        transaction_type: str = "income",
        source: str = "",
        category: str = "general",
        description: str = "",
    ) -> dict[str, Any]:
        """İşlem kaydeder - tam pipeline.

        Args:
            amount: Tutar.
            transaction_type: İşlem tipi.
            source: Kaynak.
            category: Kategori.
            description: Açıklama.

        Returns:
            İşlem bilgisi.
        """
        result: dict[str, Any] = {
            "amount": amount,
            "type": transaction_type,
        }

        if transaction_type == "income":
            # Gelir kaydet
            inc = self.income.record_income(
                amount=amount,
                source=source or "general",
                category=category,
                description=description,
            )
            result["income"] = inc

            # Nakit akış
            self.cashflow.record_flow(
                amount=amount,
                flow_type="inflow",
                category=category,
            )

            # Rapor verisi
            self.reporter.add_revenue(
                amount=amount,
                category=category,
            )

            # Vergi
            self.tax.record_taxable_income(
                amount=amount,
                category=category,
            )

        elif transaction_type == "expense":
            # Gider kaydet
            exp = self.expenses.record_expense(
                amount=amount,
                category=category,
                description=description,
            )
            result["expense"] = exp

            # Nakit akış
            self.cashflow.record_flow(
                amount=amount,
                flow_type="outflow",
                category=category,
            )

            # Rapor verisi
            self.reporter.add_expense(
                amount=amount,
                category=category,
            )

        self._stats[
            "transactions_processed"
        ] += 1
        result["processed"] = True

        return result

    def create_invoice(
        self,
        client: str,
        amount: float,
        due_days: int = 30,
    ) -> dict[str, Any]:
        """Fatura oluşturur.

        Args:
            client: Müşteri.
            amount: Tutar.
            due_days: Vade günü.

        Returns:
            Fatura bilgisi.
        """
        return self.invoices.create_invoice(
            client=client,
            amount=amount,
            due_days=due_days,
        )

    def get_financial_health(
        self,
    ) -> dict[str, Any]:
        """Finansal sağlık raporu.

        Returns:
            Sağlık bilgisi.
        """
        total_income = self.income.total_income
        total_expense = (
            self.expenses.total_expense
        )
        net = total_income - total_expense

        # Risk değerlendirme
        risk = self.cashflow.assess_risk()

        # Uyarılar
        active_alerts = len(
            self.alerts.get_active_alerts(),
        )

        health = (
            "excellent" if net > 0
            and risk["risk_level"] == "low"
            else "good" if net > 0
            else "warning" if net == 0
            else "critical"
        )

        return {
            "health": health,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_profit": round(net, 2),
            "margin": round(
                net / max(total_income, 0.01)
                * 100, 1,
            ),
            "risk_level": risk["risk_level"],
            "active_alerts": active_alerts,
            "cash_balance": (
                self.cashflow.current_balance
            ),
        }

    def generate_report(
        self,
        report_type: str = "pnl",
        period: str = "",
    ) -> dict[str, Any]:
        """Rapor üretir.

        Args:
            report_type: Rapor tipi.
            period: Dönem.

        Returns:
            Rapor bilgisi.
        """
        if report_type == "pnl":
            report = (
                self.reporter.generate_pnl(
                    period=period,
                )
            )
        elif report_type == "balance_sheet":
            report = (
                self.reporter
                .generate_balance_sheet()
            )
        elif report_type == "cashflow":
            report = (
                self.reporter
                .generate_cashflow_statement()
            )
        else:
            report = (
                self.reporter.generate_custom(
                    title=report_type,
                    metrics={},
                    period=period,
                )
            )

        self._stats[
            "reports_generated"
        ] += 1
        return report

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Analitik bilgisi.
        """
        return {
            "transactions_processed": (
                self._stats[
                    "transactions_processed"
                ]
            ),
            "total_income": (
                self.income.total_income
            ),
            "total_expense": (
                self.expenses.total_expense
            ),
            "income_sources": (
                self.income.source_count
            ),
            "expense_categories": (
                self.expenses.category_count
            ),
            "invoices_created": (
                self.invoices.invoice_count
            ),
            "invoices_paid": (
                self.invoices.paid_count
            ),
            "cash_balance": (
                self.cashflow.current_balance
            ),
            "products_tracked": (
                self.profitability
                .product_count
            ),
            "customers_tracked": (
                self.profitability
                .customer_count
            ),
            "alerts_active": (
                self.alerts.active_count
            ),
            "reports_generated": (
                self._stats[
                    "reports_generated"
                ]
            ),
            "tax_estimates": (
                self.tax.estimate_count
            ),
        }

    def get_status(
        self,
    ) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        health = self.get_financial_health()
        return {
            "health": health["health"],
            "net_profit": health["net_profit"],
            "cash_balance": (
                health["cash_balance"]
            ),
            "active_alerts": (
                health["active_alerts"]
            ),
            "transactions": self._stats[
                "transactions_processed"
            ],
        }

    @property
    def transaction_count(self) -> int:
        """İşlem sayısı."""
        return self._stats[
            "transactions_processed"
        ]
