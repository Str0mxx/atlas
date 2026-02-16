"""ATLAS Financial Intelligence & Tracker testleri.

Finansal istihbarat: gelir/gider takibi,
nakit akış, fatura, karlılık testleri.
"""

import time

import pytest

from app.core.financial.cashflow_predictor import (
    CashFlowPredictor,
)
from app.core.financial.expense_analyzer import (
    ExpenseAnalyzer,
)
from app.core.financial.financial_alert_engine import (
    FinancialAlertEngine,
)
from app.core.financial.financial_orchestrator import (
    FinancialOrchestrator,
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
from app.models.financial_models import (
    AlertRecord,
    AlertSeverity,
    ExpenseCategory,
    FinancialSnapshot,
    InvoiceRecord,
    InvoiceStatus,
    ReportPeriod,
    TaxType,
    TransactionRecord,
    TransactionType,
)


# ==================== Models ====================


class TestTransactionType:
    """TransactionType enum testleri."""

    def test_values(self):
        assert TransactionType.INCOME == "income"
        assert TransactionType.EXPENSE == "expense"
        assert TransactionType.TRANSFER == "transfer"
        assert TransactionType.REFUND == "refund"
        assert TransactionType.INVESTMENT == "investment"
        assert TransactionType.TAX == "tax"

    def test_member_count(self):
        assert len(TransactionType) == 6


class TestInvoiceStatus:
    """InvoiceStatus enum testleri."""

    def test_values(self):
        assert InvoiceStatus.DRAFT == "draft"
        assert InvoiceStatus.SENT == "sent"
        assert InvoiceStatus.PAID == "paid"
        assert InvoiceStatus.OVERDUE == "overdue"
        assert InvoiceStatus.CANCELLED == "cancelled"
        assert InvoiceStatus.PARTIAL == "partial"

    def test_member_count(self):
        assert len(InvoiceStatus) == 6


class TestAlertSeverity:
    """AlertSeverity enum testleri."""

    def test_values(self):
        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.HIGH == "high"
        assert AlertSeverity.MEDIUM == "medium"
        assert AlertSeverity.LOW == "low"
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.WARNING == "warning"

    def test_member_count(self):
        assert len(AlertSeverity) == 6


class TestExpenseCategory:
    """ExpenseCategory enum testleri."""

    def test_values(self):
        assert ExpenseCategory.SALARY == "salary"
        assert ExpenseCategory.RENT == "rent"
        assert ExpenseCategory.MARKETING == "marketing"

    def test_member_count(self):
        assert len(ExpenseCategory) == 6


class TestTaxType:
    """TaxType enum testleri."""

    def test_values(self):
        assert TaxType.INCOME == "income"
        assert TaxType.VAT == "vat"
        assert TaxType.CORPORATE == "corporate"

    def test_member_count(self):
        assert len(TaxType) == 6


class TestReportPeriod:
    """ReportPeriod enum testleri."""

    def test_values(self):
        assert ReportPeriod.DAILY == "daily"
        assert ReportPeriod.MONTHLY == "monthly"
        assert ReportPeriod.QUARTERLY == "quarterly"
        assert ReportPeriod.YEARLY == "yearly"

    def test_member_count(self):
        assert len(ReportPeriod) == 6


class TestTransactionRecord:
    """TransactionRecord model testleri."""

    def test_defaults(self):
        r = TransactionRecord()
        assert len(r.transaction_id) == 8
        assert r.transaction_type == TransactionType.INCOME
        assert r.amount == 0.0
        assert r.currency == "TRY"

    def test_custom(self):
        r = TransactionRecord(
            amount=5000.0,
            transaction_type=TransactionType.EXPENSE,
            category="rent",
        )
        assert r.amount == 5000.0
        assert r.category == "rent"

    def test_unique_ids(self):
        r1 = TransactionRecord()
        r2 = TransactionRecord()
        assert r1.transaction_id != r2.transaction_id


class TestInvoiceRecord:
    """InvoiceRecord model testleri."""

    def test_defaults(self):
        r = InvoiceRecord()
        assert len(r.invoice_id) == 8
        assert r.status == InvoiceStatus.DRAFT
        assert r.amount == 0.0

    def test_custom(self):
        r = InvoiceRecord(
            amount=10000.0,
            client="Acme Corp",
            status=InvoiceStatus.SENT,
        )
        assert r.amount == 10000.0
        assert r.client == "Acme Corp"


class TestAlertRecord:
    """AlertRecord model testleri."""

    def test_defaults(self):
        r = AlertRecord()
        assert r.severity == AlertSeverity.MEDIUM
        assert r.acknowledged is False

    def test_custom(self):
        r = AlertRecord(
            severity=AlertSeverity.CRITICAL,
            message="Budget exceeded",
        )
        assert r.severity == AlertSeverity.CRITICAL


class TestFinancialSnapshot:
    """FinancialSnapshot model testleri."""

    def test_defaults(self):
        s = FinancialSnapshot()
        assert s.total_income == 0.0
        assert s.total_expense == 0.0
        assert s.net_profit == 0.0

    def test_custom(self):
        s = FinancialSnapshot(
            total_income=50000.0,
            total_expense=30000.0,
            net_profit=20000.0,
        )
        assert s.net_profit == 20000.0


# =========== IncomeTracker ===========


class TestIncomeTrackerInit:
    """IncomeTracker başlatma testleri."""

    def test_default_init(self):
        it = IncomeTracker()
        assert it.total_income == 0.0
        assert it.income_count == 0
        assert it.source_count == 0

    def test_custom_currency(self):
        it = IncomeTracker(currency="USD")
        assert it._currency == "USD"


class TestIncomeTrackerRecord:
    """Gelir kaydetme testleri."""

    def test_record_income(self):
        it = IncomeTracker()
        r = it.record_income(
            5000.0, "Mapa Health",
        )
        assert r["recorded"] is True
        assert r["amount"] == 5000.0
        assert it.total_income == 5000.0
        assert it.income_count == 1

    def test_record_recurring(self):
        it = IncomeTracker()
        it.record_income(
            3000.0, "subscription",
            recurring=True,
        )
        rec = it.get_recurring()
        assert rec["recurring_incomes"] == 1
        assert rec["monthly_total"] == 3000.0

    def test_multiple_sources(self):
        it = IncomeTracker()
        it.record_income(5000.0, "Mapa")
        it.record_income(3000.0, "FTRK")
        assert it.source_count == 2


class TestIncomeTrackerAnalysis:
    """Gelir analiz testleri."""

    def test_get_by_source(self):
        it = IncomeTracker()
        it.record_income(5000.0, "Mapa")
        it.record_income(3000.0, "Mapa")
        r = it.get_by_source("Mapa")
        assert r["total"] == 8000.0
        assert r["count"] == 2

    def test_get_by_category(self):
        it = IncomeTracker()
        it.record_income(
            5000.0, "A", category="service",
        )
        it.record_income(
            2000.0, "B", category="product",
        )
        r = it.get_by_category("service")
        assert r["total"] == 5000.0

    def test_analyze_growth_insufficient(self):
        it = IncomeTracker()
        it.record_income(1000.0, "A")
        r = it.analyze_growth()
        assert r["trend"] == "insufficient_data"

    def test_analyze_growth_growing(self):
        it = IncomeTracker()
        it.record_income(1000.0, "A")
        it.record_income(1000.0, "A")
        it.record_income(5000.0, "A")
        it.record_income(5000.0, "A")
        r = it.analyze_growth()
        assert r["trend"] == "growing"

    def test_source_breakdown(self):
        it = IncomeTracker()
        it.record_income(7000.0, "Mapa")
        it.record_income(3000.0, "FTRK")
        r = it.get_source_breakdown()
        assert r["source_count"] == 2
        assert r["total_income"] == 10000.0
        assert (
            r["breakdown"]["Mapa"]["percentage"]
            == 70.0
        )


# =========== ExpenseAnalyzer ===========


class TestExpenseAnalyzerInit:
    """ExpenseAnalyzer başlatma testleri."""

    def test_default_init(self):
        ea = ExpenseAnalyzer()
        assert ea.total_expense == 0.0
        assert ea.expense_count == 0
        assert ea.category_count == 0


class TestExpenseAnalyzerRecord:
    """Gider kaydetme testleri."""

    def test_record_expense(self):
        ea = ExpenseAnalyzer()
        r = ea.record_expense(
            2000.0, "rent",
        )
        assert r["recorded"] is True
        assert ea.total_expense == 2000.0

    def test_multiple_categories(self):
        ea = ExpenseAnalyzer()
        ea.record_expense(2000.0, "rent")
        ea.record_expense(500.0, "utilities")
        assert ea.category_count == 2


class TestExpenseAnalyzerAnalysis:
    """Gider analiz testleri."""

    def test_analyze_trends_insufficient(self):
        ea = ExpenseAnalyzer()
        ea.record_expense(100.0, "rent")
        r = ea.analyze_trends()
        assert r["trend"] == "insufficient_data"

    def test_analyze_trends(self):
        ea = ExpenseAnalyzer()
        for i in range(4):
            ea.record_expense(
                1000.0 + i * 100, "rent",
            )
        r = ea.analyze_trends()
        assert r["trend"] == "analyzed"
        assert "rent" in r["categories"]

    def test_detect_anomalies(self):
        ea = ExpenseAnalyzer()
        for _ in range(5):
            ea.record_expense(100.0, "office")
        ea.record_expense(500.0, "office")
        r = ea.detect_anomalies()
        assert r["count"] >= 1

    def test_no_anomalies(self):
        ea = ExpenseAnalyzer()
        for _ in range(5):
            ea.record_expense(100.0, "office")
        r = ea.detect_anomalies()
        assert r["count"] == 0

    def test_budget_comparison(self):
        ea = ExpenseAnalyzer()
        ea.set_budget("rent", 3000.0)
        ea.record_expense(3500.0, "rent")
        r = ea.compare_budget()
        assert "rent" in r["over_budget"]

    def test_budget_within(self):
        ea = ExpenseAnalyzer()
        ea.set_budget("rent", 3000.0)
        ea.record_expense(2000.0, "rent")
        r = ea.compare_budget()
        assert len(r["over_budget"]) == 0

    def test_suggest_optimizations(self):
        ea = ExpenseAnalyzer()
        ea.set_budget("rent", 3000.0)
        ea.record_expense(3500.0, "rent")
        r = ea.suggest_optimizations()
        assert r["count"] >= 1

    def test_category_breakdown(self):
        ea = ExpenseAnalyzer()
        ea.record_expense(3000.0, "rent")
        ea.record_expense(1000.0, "utils")
        r = ea.get_category_breakdown()
        assert r["total_expense"] == 4000.0


# =========== CashFlowPredictor ===========


class TestCashFlowPredictorInit:
    """CashFlowPredictor başlatma."""

    def test_default_init(self):
        cf = CashFlowPredictor()
        assert cf.current_balance == 0.0
        assert cf.flow_count == 0
        assert cf.scenario_count == 0


class TestCashFlowPredictorRecord:
    """Nakit akış kaydetme testleri."""

    def test_record_inflow(self):
        cf = CashFlowPredictor()
        r = cf.record_flow(
            5000.0, "inflow",
        )
        assert r["recorded"] is True
        assert cf.current_balance == 5000.0

    def test_record_outflow(self):
        cf = CashFlowPredictor()
        cf.record_flow(10000.0, "inflow")
        cf.record_flow(3000.0, "outflow")
        assert cf.current_balance == 7000.0


class TestCashFlowPredictorForecast:
    """Nakit akış tahmin testleri."""

    def test_forecast_empty(self):
        cf = CashFlowPredictor()
        r = cf.forecast()
        assert r["confidence"] == 0.0

    def test_forecast_with_data(self):
        cf = CashFlowPredictor()
        for _ in range(5):
            cf.record_flow(10000.0, "inflow")
            cf.record_flow(6000.0, "outflow")
        r = cf.forecast(periods=3)
        assert len(r["forecasts"]) == 3
        assert r["confidence"] > 0

    def test_calculate_runway(self):
        cf = CashFlowPredictor()
        cf.record_flow(30000.0, "inflow")
        cf.record_flow(5000.0, "outflow")
        cf.record_flow(5000.0, "outflow")
        r = cf.calculate_runway()
        assert r["runway_months"] > 0

    def test_runway_no_burn(self):
        cf = CashFlowPredictor()
        cf.record_flow(10000.0, "inflow")
        r = cf.calculate_runway(
            monthly_burn=0,
        )
        assert r["status"] == "sustainable"


class TestCashFlowPredictorScenario:
    """Senaryo testleri."""

    def test_create_scenario(self):
        cf = CashFlowPredictor()
        cf.record_flow(10000.0, "inflow")
        cf.record_flow(6000.0, "outflow")
        r = cf.create_scenario(
            "optimistic",
            inflow_change=20,
            outflow_change=-10,
        )
        assert r["created"] is True
        assert cf.scenario_count == 1

    def test_assess_risk_low(self):
        cf = CashFlowPredictor()
        cf.record_flow(100000.0, "inflow")
        r = cf.assess_risk()
        assert r["risk_level"] == "low"

    def test_assess_risk_negative(self):
        cf = CashFlowPredictor()
        cf.record_flow(1000.0, "inflow")
        cf.record_flow(5000.0, "outflow")
        r = cf.assess_risk()
        assert r["risk_level"] in (
            "critical", "high",
        )

    def test_generate_alerts(self):
        cf = CashFlowPredictor()
        cf.record_flow(500.0, "inflow")
        r = cf.generate_alerts(
            low_balance=1000.0,
        )
        assert r["count"] >= 1


# =========== InvoiceManager ===========


class TestInvoiceManagerInit:
    """InvoiceManager başlatma testleri."""

    def test_default_init(self):
        im = InvoiceManager()
        assert im.invoice_count == 0
        assert im.paid_count == 0


class TestInvoiceManagerCreate:
    """Fatura oluşturma testleri."""

    def test_create_invoice(self):
        im = InvoiceManager()
        r = im.create_invoice(
            "Acme Corp", 10000.0,
        )
        assert r["created"] is True
        assert r["client"] == "Acme Corp"
        assert im.invoice_count == 1
        assert im.total_invoiced == 10000.0

    def test_record_payment(self):
        im = InvoiceManager()
        inv = im.create_invoice(
            "Client A", 5000.0,
        )
        iid = inv["invoice_id"]
        r = im.record_payment(iid, 5000.0)
        assert r["recorded"] is True
        assert r["status"] == "paid"
        assert im.paid_count == 1

    def test_partial_payment(self):
        im = InvoiceManager()
        inv = im.create_invoice(
            "Client B", 10000.0,
        )
        iid = inv["invoice_id"]
        r = im.record_payment(iid, 3000.0)
        assert r["status"] == "partial"

    def test_payment_not_found(self):
        im = InvoiceManager()
        r = im.record_payment("invalid", 100)
        assert "error" in r


class TestInvoiceManagerOverdue:
    """Gecikmiş fatura testleri."""

    def test_get_overdue(self):
        im = InvoiceManager()
        inv = im.create_invoice(
            "Client C", 5000.0,
            due_days=-1,
        )
        r = im.get_overdue()
        assert r["count"] >= 1

    def test_create_reminder(self):
        im = InvoiceManager()
        inv = im.create_invoice(
            "Client D", 3000.0,
        )
        iid = inv["invoice_id"]
        r = im.create_reminder(iid)
        assert r["sent"] is True

    def test_reminder_not_found(self):
        im = InvoiceManager()
        r = im.create_reminder("invalid")
        assert "error" in r


class TestInvoiceManagerReconcile:
    """Mutabakat testleri."""

    def test_reconcile(self):
        im = InvoiceManager()
        inv = im.create_invoice(
            "X", 10000.0,
        )
        im.record_payment(
            inv["invoice_id"], 7000.0,
        )
        r = im.reconcile()
        assert r["total_invoiced"] == 10000.0
        assert r["total_collected"] == 7000.0
        assert r["outstanding"] == 3000.0
        assert r["collection_rate"] == 70.0

    def test_cancel_invoice(self):
        im = InvoiceManager()
        inv = im.create_invoice("Y", 5000.0)
        r = im.cancel_invoice(
            inv["invoice_id"],
        )
        assert r["cancelled"] is True

    def test_cancel_not_found(self):
        im = InvoiceManager()
        r = im.cancel_invoice("invalid")
        assert "error" in r

    def test_get_invoice(self):
        im = InvoiceManager()
        inv = im.create_invoice("Z", 8000.0)
        r = im.get_invoice(
            inv["invoice_id"],
        )
        assert r["client"] == "Z"

    def test_get_invoice_not_found(self):
        im = InvoiceManager()
        r = im.get_invoice("invalid")
        assert "error" in r


# ======== ProfitabilityCalculator ========


class TestProfitabilityInit:
    """ProfitabilityCalculator başlatma."""

    def test_default_init(self):
        pc = ProfitabilityCalculator()
        assert pc.product_count == 0
        assert pc.customer_count == 0
        assert pc.project_count == 0


class TestProfitabilityMargin:
    """Marj hesaplama testleri."""

    def test_calculate_margin(self):
        pc = ProfitabilityCalculator()
        r = pc.calculate_margin(
            revenue=10000.0, cost=6000.0,
        )
        assert r["profit"] == 4000.0
        assert r["margin_percent"] == 40.0
        assert r["profitable"] is True

    def test_negative_margin(self):
        pc = ProfitabilityCalculator()
        r = pc.calculate_margin(
            revenue=5000.0, cost=7000.0,
        )
        assert r["profitable"] is False

    def test_zero_revenue(self):
        pc = ProfitabilityCalculator()
        r = pc.calculate_margin(
            revenue=0.0, cost=1000.0,
        )
        assert r["margin_percent"] == 0.0


class TestProfitabilityTracking:
    """Karlılık takip testleri."""

    def test_track_product(self):
        pc = ProfitabilityCalculator()
        r = pc.track_product(
            "prod_1",
            revenue=5000.0,
            cost=3000.0,
            units=10,
        )
        assert r["tracked"] is True
        assert r["total_profit"] == 2000.0
        assert pc.product_count == 1

    def test_track_customer(self):
        pc = ProfitabilityCalculator()
        r = pc.track_customer(
            "cust_1",
            revenue=8000.0,
            cost=5000.0,
        )
        assert r["tracked"] is True
        assert r["total_profit"] == 3000.0
        assert pc.customer_count == 1

    def test_track_project(self):
        pc = ProfitabilityCalculator()
        r = pc.track_project(
            "proj_1",
            revenue=20000.0,
            cost=15000.0,
        )
        assert r["tracked"] is True
        assert r["total_profit"] == 5000.0
        assert pc.project_count == 1

    def test_product_ranking(self):
        pc = ProfitabilityCalculator()
        pc.track_product(
            "A", revenue=10000, cost=8000,
        )
        pc.track_product(
            "B", revenue=5000, cost=2000,
        )
        r = pc.get_product_ranking()
        assert r["count"] == 2
        # B daha karlı (3000 vs 2000)
        assert (
            r["rankings"][0]["product_id"]
            == "B"
        )

    def test_customer_ranking(self):
        pc = ProfitabilityCalculator()
        pc.track_customer(
            "C1", revenue=10000, cost=8000,
        )
        pc.track_customer(
            "C2", revenue=5000, cost=1000,
        )
        r = pc.get_customer_ranking()
        assert r["count"] == 2
        assert (
            r["rankings"][0]["customer_id"]
            == "C2"
        )

    def test_trend_insufficient(self):
        pc = ProfitabilityCalculator()
        r = pc.get_trend()
        assert r["trend"] == "insufficient_data"

    def test_trend_with_data(self):
        pc = ProfitabilityCalculator()
        for i in range(6):
            pc.calculate_margin(
                revenue=10000,
                cost=5000 + i * 100,
            )
        r = pc.get_trend()
        assert r["trend"] in (
            "improving", "declining", "stable",
        )


# ======== FinancialAlertEngine ========


class TestAlertEngineInit:
    """FinancialAlertEngine başlatma."""

    def test_default_init(self):
        ae = FinancialAlertEngine()
        assert ae.alert_count == 0
        assert ae.active_count == 0
        assert ae.rule_count == 0


class TestAlertEngineRules:
    """Uyarı kuralı testleri."""

    def test_add_rule(self):
        ae = FinancialAlertEngine()
        r = ae.add_rule(
            "high_expense",
            "threshold",
            "expense > limit",
            threshold=5000.0,
        )
        assert r["created"] is True
        assert ae.rule_count == 1


class TestAlertEngineThreshold:
    """Eşik uyarı testleri."""

    def test_threshold_triggered(self):
        ae = FinancialAlertEngine()
        r = ae.check_threshold(
            "expense", 6000.0, 5000.0,
        )
        assert r["triggered"] is True
        assert ae.alert_count == 1

    def test_threshold_not_triggered(self):
        ae = FinancialAlertEngine()
        r = ae.check_threshold(
            "expense", 3000.0, 5000.0,
        )
        assert r["triggered"] is False

    def test_threshold_below(self):
        ae = FinancialAlertEngine()
        r = ae.check_threshold(
            "balance", 500.0, 1000.0,
            direction="below",
        )
        assert r["triggered"] is True


class TestAlertEngineAnomaly:
    """Anomali uyarı testleri."""

    def test_anomaly_detected(self):
        ae = FinancialAlertEngine()
        r = ae.check_anomaly(
            "expense",
            value=10000.0,
            historical=[
                1000, 1200, 900, 1100,
            ],
        )
        assert r["anomaly"] is True

    def test_no_anomaly(self):
        ae = FinancialAlertEngine()
        r = ae.check_anomaly(
            "expense",
            value=1100.0,
            historical=[
                1000, 1200, 900, 1100,
            ],
        )
        assert r["anomaly"] is False

    def test_anomaly_no_history(self):
        ae = FinancialAlertEngine()
        r = ae.check_anomaly(
            "expense", 1000.0, [],
        )
        assert r["anomaly"] is False


class TestAlertEngineDeadline:
    """Son tarih uyarı testleri."""

    def test_deadline_overdue(self):
        ae = FinancialAlertEngine()
        r = ae.check_deadline(
            "inv_1", "invoice",
            due_timestamp=time.time() - 86400,
        )
        assert r["alert_needed"] is True
        assert r["status"] == "overdue"

    def test_deadline_approaching(self):
        ae = FinancialAlertEngine()
        r = ae.check_deadline(
            "inv_2", "invoice",
            due_timestamp=time.time() + 86400 * 3,
            warning_days=7,
        )
        assert r["alert_needed"] is True
        assert r["status"] == "approaching"

    def test_deadline_ok(self):
        ae = FinancialAlertEngine()
        r = ae.check_deadline(
            "inv_3", "invoice",
            due_timestamp=time.time() + 86400 * 30,
        )
        assert r["alert_needed"] is False


class TestAlertEngineOpportunityRisk:
    """Fırsat ve risk uyarı testleri."""

    def test_alert_opportunity(self):
        ae = FinancialAlertEngine()
        r = ae.alert_opportunity(
            "New contract",
            potential_value=50000.0,
        )
        assert r["created"] is True

    def test_alert_risk(self):
        ae = FinancialAlertEngine()
        r = ae.alert_risk(
            "Client default",
            impact=0.9,
            probability=0.8,
        )
        assert r["created"] is True
        assert r["severity"] == "critical"

    def test_alert_risk_low(self):
        ae = FinancialAlertEngine()
        r = ae.alert_risk(
            "Minor delay",
            impact=0.3,
            probability=0.2,
        )
        assert r["severity"] == "medium"


class TestAlertEngineManage:
    """Uyarı yönetimi testleri."""

    def test_acknowledge(self):
        ae = FinancialAlertEngine()
        ae.check_threshold(
            "x", 6000, 5000,
        )
        alerts = ae.get_active_alerts()
        assert len(alerts) == 1
        ae.acknowledge(
            alerts[0]["alert_id"],
        )
        assert ae.active_count == 0

    def test_filter_by_type(self):
        ae = FinancialAlertEngine()
        ae.check_threshold("x", 6000, 5000)
        ae.alert_risk("r", 0.9, 0.9)
        alerts = ae.get_active_alerts(
            alert_type="risk",
        )
        assert len(alerts) == 1

    def test_filter_by_severity(self):
        ae = FinancialAlertEngine()
        ae.alert_risk("hi", 0.9, 0.9)
        ae.alert_opportunity("lo", 100)
        alerts = ae.get_active_alerts(
            severity="info",
        )
        assert len(alerts) == 1


# =========== TaxEstimator ===========


class TestTaxEstimatorInit:
    """TaxEstimator başlatma testleri."""

    def test_default_init(self):
        te = TaxEstimator()
        assert te.estimate_count == 0
        assert te.deduction_count == 0
        assert te.total_income == 0.0


class TestTaxEstimatorRecord:
    """Vergi kayıt testleri."""

    def test_record_income(self):
        te = TaxEstimator()
        r = te.record_taxable_income(
            50000.0, quarter=1,
        )
        assert r["recorded"] is True
        assert te.total_income == 50000.0

    def test_add_deduction(self):
        te = TaxEstimator()
        r = te.add_deduction(
            5000.0, "insurance",
        )
        assert r["recorded"] is True
        assert te.deduction_count == 1


class TestTaxEstimatorEstimate:
    """Vergi tahmin testleri."""

    def test_estimate_flat(self):
        te = TaxEstimator(tax_rate=0.20)
        te.record_taxable_income(100000.0)
        r = te.estimate_tax()
        assert r["taxable_income"] == 100000.0
        assert r["estimated_tax"] == 20000.0

    def test_estimate_with_deductions(self):
        te = TaxEstimator(tax_rate=0.20)
        te.record_taxable_income(100000.0)
        te.add_deduction(20000.0, "insurance")
        r = te.estimate_tax()
        assert r["taxable_income"] == 80000.0
        assert r["estimated_tax"] == 16000.0

    def test_estimate_bracketed(self):
        te = TaxEstimator()
        r = te.estimate_tax(
            income=200000.0,
            use_brackets=True,
        )
        assert r["estimated_tax"] > 0
        assert r["effective_rate"] > 0

    def test_estimate_quarterly(self):
        te = TaxEstimator(tax_rate=0.20)
        te.record_taxable_income(
            30000.0, quarter=1,
        )
        te.add_deduction(
            5000.0, "expense", quarter=1,
        )
        r = te.estimate_quarterly(1)
        assert r["taxable"] == 25000.0
        assert r["estimated_tax"] == 5000.0


class TestTaxEstimatorCompliance:
    """Uyumluluk testleri."""

    def test_compliance_ok(self):
        te = TaxEstimator()
        te.record_taxable_income(
            50000.0, quarter=1,
        )
        r = te.check_compliance()
        assert r["compliant"] is True

    def test_compliance_issue(self):
        te = TaxEstimator()
        te.record_taxable_income(
            10000.0, quarter=1,
        )
        te.add_deduction(
            20000.0, "expense", quarter=1,
        )
        r = te.check_compliance()
        assert r["compliant"] is False

    def test_create_reminder(self):
        te = TaxEstimator()
        r = te.create_reminder(
            "KDV", "2026-03-20",
        )
        assert r["created"] is True

    def test_deduction_summary(self):
        te = TaxEstimator()
        te.add_deduction(
            5000.0, "insurance",
        )
        te.add_deduction(
            3000.0, "insurance",
        )
        te.add_deduction(
            2000.0, "travel",
        )
        r = te.get_deduction_summary()
        assert r["total"] == 10000.0
        assert (
            r["by_category"]["insurance"]
            == 8000.0
        )


# ======== FinancialReporter ========


class TestFinancialReporterInit:
    """FinancialReporter başlatma."""

    def test_default_init(self):
        fr = FinancialReporter()
        assert fr.report_count == 0
        assert fr.pnl_count == 0


class TestFinancialReporterPNL:
    """P&L raporu testleri."""

    def test_generate_pnl(self):
        fr = FinancialReporter()
        fr.add_revenue(10000.0, "sales")
        fr.add_expense(6000.0, "operations")
        r = fr.generate_pnl()
        assert r["type"] == "pnl"
        assert r["net_income"] == 4000.0
        assert r["margin_percent"] == 40.0
        assert fr.report_count == 1

    def test_pnl_by_period(self):
        fr = FinancialReporter()
        fr.add_revenue(
            5000.0, "sales", period="Q1",
        )
        fr.add_revenue(
            8000.0, "sales", period="Q2",
        )
        fr.add_expense(
            3000.0, "ops", period="Q1",
        )
        r = fr.generate_pnl(period="Q1")
        assert r["revenue"]["total"] == 5000.0


class TestFinancialReporterBalance:
    """Bilanço testleri."""

    def test_balance_sheet(self):
        fr = FinancialReporter()
        fr.set_asset("cash", 50000.0)
        fr.set_asset("equipment", 30000.0)
        fr.set_liability("loan", 20000.0)
        r = fr.generate_balance_sheet()
        assert r["total_assets"] == 80000.0
        assert r["total_liabilities"] == 20000.0
        assert r["equity"] == 60000.0

    def test_cashflow_statement(self):
        fr = FinancialReporter()
        fr.add_revenue(10000.0)
        fr.add_expense(4000.0)
        r = fr.generate_cashflow_statement()
        assert r["net_change"] == 6000.0


class TestFinancialReporterCustom:
    """Özel rapor testleri."""

    def test_generate_custom(self):
        fr = FinancialReporter()
        r = fr.generate_custom(
            "Monthly KPI",
            {"growth": 15.0, "churn": 2.0},
        )
        assert r["type"] == "custom"
        assert r["title"] == "Monthly KPI"

    def test_visualization_data(self):
        fr = FinancialReporter()
        fr.add_revenue(5000.0, "sales")
        fr.add_expense(3000.0, "ops")
        r = fr.get_visualization_data()
        assert "revenue_data" in r
        assert "expense_data" in r


# ======== FinancialOrchestrator ========


class TestOrchestratorInit:
    """FinancialOrchestrator başlatma."""

    def test_default_init(self):
        fo = FinancialOrchestrator()
        assert fo.transaction_count == 0

    def test_custom_init(self):
        fo = FinancialOrchestrator(
            currency="USD",
            tax_rate=0.25,
        )
        assert fo._currency == "USD"


class TestOrchestratorTransactions:
    """İşlem testleri."""

    def test_record_income(self):
        fo = FinancialOrchestrator()
        r = fo.record_transaction(
            5000.0,
            transaction_type="income",
            source="Mapa",
            category="service",
        )
        assert r["processed"] is True
        assert fo.transaction_count == 1

    def test_record_expense(self):
        fo = FinancialOrchestrator()
        r = fo.record_transaction(
            2000.0,
            transaction_type="expense",
            category="rent",
        )
        assert r["processed"] is True

    def test_create_invoice(self):
        fo = FinancialOrchestrator()
        r = fo.create_invoice(
            "Client X", 10000.0,
        )
        assert r["created"] is True


class TestOrchestratorHealth:
    """Finansal sağlık testleri."""

    def test_health_excellent(self):
        fo = FinancialOrchestrator()
        fo.record_transaction(
            50000.0, "income",
        )
        fo.record_transaction(
            20000.0, "expense",
        )
        h = fo.get_financial_health()
        assert h["health"] in (
            "excellent", "good",
        )
        assert h["net_profit"] == 30000.0

    def test_health_critical(self):
        fo = FinancialOrchestrator()
        fo.record_transaction(
            5000.0, "income",
        )
        fo.record_transaction(
            10000.0, "expense",
        )
        h = fo.get_financial_health()
        assert h["health"] == "critical"


class TestOrchestratorReports:
    """Rapor testleri."""

    def test_generate_pnl(self):
        fo = FinancialOrchestrator()
        fo.record_transaction(
            10000.0, "income",
        )
        fo.record_transaction(
            4000.0, "expense",
        )
        r = fo.generate_report("pnl")
        assert r["type"] == "pnl"
        assert r["net_income"] == 6000.0

    def test_generate_balance(self):
        fo = FinancialOrchestrator()
        r = fo.generate_report(
            "balance_sheet",
        )
        assert r["type"] == "balance_sheet"

    def test_generate_cashflow(self):
        fo = FinancialOrchestrator()
        r = fo.generate_report("cashflow")
        assert r["type"] == "cashflow_statement"

    def test_generate_custom(self):
        fo = FinancialOrchestrator()
        r = fo.generate_report("summary")
        assert r["type"] == "custom"


class TestOrchestratorAnalytics:
    """Analitik testleri."""

    def test_get_analytics(self):
        fo = FinancialOrchestrator()
        fo.record_transaction(
            5000.0, "income", source="A",
        )
        a = fo.get_analytics()
        assert a["transactions_processed"] == 1
        assert a["total_income"] == 5000.0
        assert "income_sources" in a
        assert "expense_categories" in a
        assert "invoices_created" in a
        assert "cash_balance" in a

    def test_get_status(self):
        fo = FinancialOrchestrator()
        fo.record_transaction(
            10000.0, "income",
        )
        s = fo.get_status()
        assert "health" in s
        assert "net_profit" in s
        assert "cash_balance" in s


class TestOrchestratorIntegration:
    """Entegrasyon testleri."""

    def test_full_pipeline(self):
        fo = FinancialOrchestrator()

        # 1. Gelir kaydet
        fo.record_transaction(
            50000.0, "income",
            source="Mapa Health",
            category="service",
        )
        fo.record_transaction(
            30000.0, "income",
            source="FTRK Store",
            category="product",
        )

        # 2. Gider kaydet
        fo.record_transaction(
            10000.0, "expense",
            category="rent",
        )
        fo.record_transaction(
            5000.0, "expense",
            category="salary",
        )

        # 3. Fatura oluştur
        fo.create_invoice(
            "Client A", 15000.0,
        )

        # 4. Rapor üret
        report = fo.generate_report("pnl")
        assert report["net_income"] == 65000.0

        # 5. Analitik kontrol
        a = fo.get_analytics()
        assert a["transactions_processed"] == 4
        assert a["total_income"] == 80000.0
        assert a["total_expense"] == 15000.0
        assert a["invoices_created"] == 1

        # 6. Sağlık kontrolü
        h = fo.get_financial_health()
        assert h["net_profit"] == 65000.0


# =========== Config ===========


class TestFinancialConfig:
    """Financial config testleri."""

    def test_config_defaults(self):
        from app.config import Settings

        s = Settings()
        assert s.financial_enabled is True
        assert s.currency == "TRY"
        assert s.tax_rate == 0.20
        assert s.alert_threshold == 1000.0
        assert s.auto_categorize is True


# =========== Imports ===========


class TestFinancialImports:
    """Import testleri."""

    def test_import_all(self):
        from app.core.financial import (
            CashFlowPredictor,
            ExpenseAnalyzer,
            FinancialAlertEngine,
            FinancialOrchestrator,
            FinancialReporter,
            IncomeTracker,
            InvoiceManager,
            ProfitabilityCalculator,
            TaxEstimator,
        )

        assert CashFlowPredictor is not None
        assert ExpenseAnalyzer is not None
        assert FinancialAlertEngine is not None
        assert FinancialOrchestrator is not None
        assert FinancialReporter is not None
        assert IncomeTracker is not None
        assert InvoiceManager is not None
        assert ProfitabilityCalculator is not None
        assert TaxEstimator is not None

    def test_import_models(self):
        from app.models.financial_models import (
            AlertRecord,
            AlertSeverity,
            ExpenseCategory,
            FinancialSnapshot,
            InvoiceRecord,
            InvoiceStatus,
            ReportPeriod,
            TaxType,
            TransactionRecord,
            TransactionType,
        )

        assert TransactionType is not None
        assert InvoiceStatus is not None
        assert AlertSeverity is not None
        assert ExpenseCategory is not None
        assert TaxType is not None
        assert ReportPeriod is not None
        assert TransactionRecord is not None
        assert InvoiceRecord is not None
        assert AlertRecord is not None
        assert FinancialSnapshot is not None
