"""Personal Finance Manager testleri."""

import pytest

from app.models.personalfin_models import (
    AccountType,
    SpendingCategory,
    BudgetPeriod,
    GoalType,
    InvestmentType,
    BillFrequency,
    BankAccountRecord,
    TransactionRecord,
    BudgetRecord,
    FinancialGoalRecord,
)
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
from app.core.personalfin.personalfin_orchestrator import (
    PersonalFinOrchestrator,
)


# ============================================================
# Enum testleri
# ============================================================


class TestAccountType:
    def test_values(self):
        assert AccountType.checking == "checking"
        assert AccountType.savings == "savings"
        assert AccountType.credit_card == "credit_card"

    def test_member_count(self):
        assert len(AccountType) == 6


class TestSpendingCategory:
    def test_values(self):
        assert SpendingCategory.food == "food"
        assert SpendingCategory.transport == "transport"
        assert SpendingCategory.entertainment == "entertainment"

    def test_member_count(self):
        assert len(SpendingCategory) == 8


class TestBudgetPeriod:
    def test_values(self):
        assert BudgetPeriod.weekly == "weekly"
        assert BudgetPeriod.monthly == "monthly"
        assert BudgetPeriod.annual == "annual"

    def test_member_count(self):
        assert len(BudgetPeriod) == 5


class TestGoalType:
    def test_values(self):
        assert GoalType.emergency_fund == "emergency_fund"
        assert GoalType.retirement == "retirement"
        assert GoalType.debt_payoff == "debt_payoff"

    def test_member_count(self):
        assert len(GoalType) == 6


class TestInvestmentType:
    def test_values(self):
        assert InvestmentType.stocks == "stocks"
        assert InvestmentType.bonds == "bonds"
        assert InvestmentType.crypto == "crypto"

    def test_member_count(self):
        assert len(InvestmentType) == 6


class TestBillFrequency:
    def test_values(self):
        assert BillFrequency.monthly == "monthly"
        assert BillFrequency.annual == "annual"
        assert BillFrequency.one_time == "one_time"

    def test_member_count(self):
        assert len(BillFrequency) == 6


# ============================================================
# Model testleri
# ============================================================


class TestBankAccountRecord:
    def test_defaults(self):
        r = BankAccountRecord()
        assert r.bank_name == "Default Bank"
        assert r.account_type == "checking"
        assert r.balance == 0.0
        assert r.currency == "TRY"

    def test_custom(self):
        r = BankAccountRecord(
            bank_name="Garanti",
            account_type="savings",
            balance=25000.0,
        )
        assert r.bank_name == "Garanti"
        assert r.balance == 25000.0


class TestTransactionRecord:
    def test_defaults(self):
        r = TransactionRecord()
        assert r.amount == 0.0
        assert r.category == "uncategorized"
        assert isinstance(r.transaction_id, str)

    def test_custom(self):
        r = TransactionRecord(
            amount=150.0,
            category="food",
            merchant="Migros",
        )
        assert r.amount == 150.0
        assert r.merchant == "Migros"


class TestBudgetRecord:
    def test_defaults(self):
        r = BudgetRecord()
        assert r.name == "Monthly Budget"
        assert r.period == "monthly"
        assert r.total_limit == 0.0

    def test_custom(self):
        r = BudgetRecord(
            name="Q1 Budget",
            period="quarterly",
            total_limit=30000.0,
        )
        assert r.name == "Q1 Budget"
        assert r.total_limit == 30000.0


class TestFinancialGoalRecord:
    def test_defaults(self):
        r = FinancialGoalRecord()
        assert r.name == "Savings Goal"
        assert r.goal_type == "emergency_fund"
        assert r.target_amount == 0.0

    def test_custom(self):
        r = FinancialGoalRecord(
            name="Ev Alımı",
            goal_type="home_purchase",
            target_amount=500000.0,
            current_amount=100000.0,
        )
        assert r.target_amount == 500000.0
        assert r.current_amount == 100000.0


# ============================================================
# BankAccountConnector testleri
# ============================================================


class TestLinkAccount:
    def test_basic(self):
        bc = BankAccountConnector()
        r = bc.link_account("Garanti", "checking", 10000.0)
        assert r["linked"] is True
        assert r["account_id"].startswith("acc_")
        assert r["balance"] == 10000.0

    def test_count(self):
        bc = BankAccountConnector()
        bc.link_account("A")
        bc.link_account("B")
        assert bc.account_count == 2


class TestGetBalance:
    def test_found(self):
        bc = BankAccountConnector()
        acc = bc.link_account("Test", "checking", 5000.0)
        r = bc.get_balance(acc["account_id"])
        assert r["found"] is True
        assert r["balance"] == 5000.0

    def test_not_found(self):
        bc = BankAccountConnector()
        r = bc.get_balance("xxx")
        assert r["found"] is False


class TestSyncTransactions:
    def test_basic(self):
        bc = BankAccountConnector()
        txns = [{"amount": 100}, {"amount": 200}]
        r = bc.sync_transactions("acc1", txns)
        assert r["synced"] is True
        assert r["synced_count"] == 2
        assert r["total_amount"] == 300.0

    def test_empty(self):
        bc = BankAccountConnector()
        r = bc.sync_transactions("acc1")
        assert r["synced_count"] == 0


class TestListBanks:
    def test_basic(self):
        bc = BankAccountConnector()
        r = bc.list_banks()
        assert r["listed"] is True
        assert r["bank_count"] == 8


class TestValidateSecurity:
    def test_high(self):
        bc = BankAccountConnector()
        r = bc.validate_security("acc1", "a" * 20)
        assert r["security_level"] == "high"
        assert r["token_valid"] is True

    def test_low(self):
        bc = BankAccountConnector()
        r = bc.validate_security("acc1", "short")
        assert r["security_level"] == "low"
        assert r["token_valid"] is False


# ============================================================
# SpendingCategorizer testleri
# ============================================================


class TestAutoCategorize:
    def test_known_merchant(self):
        sc = SpendingCategorizer()
        r = sc.auto_categorize("Migros", 150.0)
        assert r["category"] == "food"
        assert r["confidence"] == 0.95

    def test_unknown(self):
        sc = SpendingCategorizer()
        r = sc.auto_categorize("RandomShop", 50.0)
        assert r["category"] == "uncategorized"
        assert r["confidence"] == 0.0

    def test_count(self):
        sc = SpendingCategorizer()
        sc.auto_categorize("Migros")
        sc.auto_categorize("Shell")
        assert sc.categorized_count == 2


class TestAddCustomCategory:
    def test_basic(self):
        sc = SpendingCategorizer()
        r = sc.add_custom_category("myshop", "shopping")
        assert r["added"] is True
        assert r["total_custom"] == 1

    def test_use_custom(self):
        sc = SpendingCategorizer()
        sc.add_custom_category("myshop", "shopping")
        r = sc.auto_categorize("MyShop", 100.0)
        assert r["category"] == "shopping"


class TestMapMerchant:
    def test_default(self):
        sc = SpendingCategorizer()
        r = sc.map_merchant("Netflix")
        assert r["category"] == "entertainment"
        assert r["source"] == "default"

    def test_unknown(self):
        sc = SpendingCategorizer()
        r = sc.map_merchant("Unknown")
        assert r["mapped"] is False


class TestLearnPattern:
    def test_basic(self):
        sc = SpendingCategorizer()
        txns = [
            {"category": "food"},
            {"category": "food"},
            {"category": "transport"},
        ]
        r = sc.learn_pattern(txns)
        assert r["top_category"] == "food"
        assert r["pattern_count"] == 2

    def test_empty(self):
        sc = SpendingCategorizer()
        r = sc.learn_pattern()
        assert r["top_category"] == "none"


class TestSplitTransaction:
    def test_balanced(self):
        sc = SpendingCategorizer()
        splits = [{"amount": 60}, {"amount": 40}]
        r = sc.split_transaction(100.0, splits)
        assert r["balanced"] is True
        assert r["split_count"] == 2

    def test_unbalanced(self):
        sc = SpendingCategorizer()
        splits = [{"amount": 30}]
        r = sc.split_transaction(100.0, splits)
        assert r["balanced"] is False
        assert r["remainder"] == 70.0


# ============================================================
# PersonalBudgetPlanner testleri
# ============================================================


class TestCreateBudget:
    def test_basic(self):
        bp = PersonalBudgetPlanner()
        r = bp.create_budget("Aylik", "monthly", 15000.0)
        assert r["created"] is True
        assert r["budget_id"].startswith("bud_")
        assert r["total_limit"] == 15000.0

    def test_count(self):
        bp = PersonalBudgetPlanner()
        bp.create_budget("A")
        bp.create_budget("B")
        assert bp.budget_count == 2


class TestSetCategoryBudget:
    def test_basic(self):
        bp = PersonalBudgetPlanner()
        b = bp.create_budget("Test")
        r = bp.set_category_budget(
            b["budget_id"], "food", 3000.0
        )
        assert r["set"] is True

    def test_not_found(self):
        bp = PersonalBudgetPlanner()
        r = bp.set_category_budget("xxx", "food")
        assert r["set"] is False


class TestTrackSpending:
    def test_basic(self):
        bp = PersonalBudgetPlanner()
        b = bp.create_budget("Test", "monthly", 10000.0)
        r = bp.track_spending(b["budget_id"], "food", 2000.0)
        assert r["tracked"] is True
        assert r["total_spent"] == 2000.0
        assert r["used_pct"] == 20.0

    def test_not_found(self):
        bp = PersonalBudgetPlanner()
        r = bp.track_spending("xxx", "food", 100.0)
        assert r["tracked"] is False


class TestCheckAlerts:
    def test_on_track(self):
        bp = PersonalBudgetPlanner()
        b = bp.create_budget("Test", "monthly", 10000.0)
        bp.track_spending(b["budget_id"], "food", 1000.0)
        r = bp.check_alerts(b["budget_id"])
        assert r["status"] == "on_track"

    def test_over_budget(self):
        bp = PersonalBudgetPlanner()
        b = bp.create_budget("Test", "monthly", 1000.0)
        bp.track_spending(b["budget_id"], "food", 1500.0)
        r = bp.check_alerts(b["budget_id"])
        assert r["status"] == "over_budget"


class TestAdjustBudget:
    def test_basic(self):
        bp = PersonalBudgetPlanner()
        b = bp.create_budget("Test", "monthly", 10000.0)
        r = bp.adjust_budget(b["budget_id"], 15000.0)
        assert r["adjusted"] is True
        assert r["change"] == 5000.0

    def test_not_found(self):
        bp = PersonalBudgetPlanner()
        r = bp.adjust_budget("xxx", 5000.0)
        assert r["adjusted"] is False


# ============================================================
# SavingsAdvisor testleri
# ============================================================


class TestCreateSavingsGoal:
    def test_basic(self):
        sa = SavingsAdvisor()
        r = sa.create_goal("Acil Fon", 60000.0, 5000.0)
        assert r["created"] is True
        assert r["months_to_goal"] == 12.0

    def test_count(self):
        sa = SavingsAdvisor()
        sa.create_goal("A")
        sa.create_goal("B")
        assert sa.goal_count == 2


class TestRecommendSavings:
    def test_low_rate(self):
        sa = SavingsAdvisor()
        r = sa.recommend_savings(10000.0, 9500.0)
        assert "reduce_discretionary" in r["tips"]
        assert r["savings_rate"] == 5.0

    def test_good_rate(self):
        sa = SavingsAdvisor()
        r = sa.recommend_savings(10000.0, 6500.0)
        assert "consider_investing" in r["tips"]


class TestAddAutoRule:
    def test_basic(self):
        sa = SavingsAdvisor()
        r = sa.add_auto_rule("percentage", 10.0, "income")
        assert r["added"] is True
        assert r["total_rules"] == 1


class TestTrackSavingsProgress:
    def test_basic(self):
        sa = SavingsAdvisor()
        g = sa.create_goal("Test", 10000.0)
        r = sa.track_progress(g["goal_id"], 5000.0)
        assert r["tracked"] is True
        assert r["progress_pct"] == 50.0

    def test_not_found(self):
        sa = SavingsAdvisor()
        r = sa.track_progress("xxx", 100.0)
        assert r["tracked"] is False


class TestOptimizeSavings:
    def test_basic(self):
        sa = SavingsAdvisor()
        goals = [
            {"name": "Emergency", "target": 5000, "saved": 2000, "priority": 1},
            {"name": "Vacation", "target": 3000, "saved": 500, "priority": 2},
        ]
        r = sa.optimize_savings(goals, 4000.0)
        assert r["optimized"] is True
        assert r["allocated_count"] == 2

    def test_empty(self):
        sa = SavingsAdvisor()
        r = sa.optimize_savings()
        assert r["unallocated"] == 10000.0


# ============================================================
# BillReminder testleri
# ============================================================


class TestAddBill:
    def test_basic(self):
        br = BillReminder()
        r = br.add_bill("Elektrik", 500.0, 15, "monthly")
        assert r["added"] is True
        assert r["bill_id"].startswith("bill_")

    def test_count(self):
        br = BillReminder()
        br.add_bill("A")
        br.add_bill("B")
        assert br.bill_count == 2


class TestCheckDue:
    def test_due_soon(self):
        br = BillReminder()
        br.add_bill("Elektrik", 500.0, 15)
        r = br.check_due(13)
        assert r["due_soon_count"] == 1
        assert r["checked"] is True

    def test_overdue(self):
        br = BillReminder()
        br.add_bill("Elektrik", 500.0, 10)
        r = br.check_due(15)
        assert r["overdue_count"] == 1


class TestSetupAutoPay:
    def test_basic(self):
        br = BillReminder()
        b = br.add_bill("Test", 100.0)
        r = br.setup_auto_pay(b["bill_id"])
        assert r["setup"] is True
        assert r["auto_pay"] is True

    def test_not_found(self):
        br = BillReminder()
        r = br.setup_auto_pay("xxx")
        assert r["setup"] is False


class TestRecordPayment:
    def test_basic(self):
        br = BillReminder()
        b = br.add_bill("Test", 500.0)
        r = br.record_payment(b["bill_id"], 500.0)
        assert r["recorded"] is True
        assert r["difference"] == 0.0

    def test_not_found(self):
        br = BillReminder()
        r = br.record_payment("xxx", 100.0)
        assert r["recorded"] is False


class TestEstimateLateFees:
    def test_basic(self):
        br = BillReminder()
        r = br.estimate_late_fees(1000.0, 10, 2.0)
        assert r["late_fee"] == 20.0
        assert r["total_due"] == 1020.0
        assert r["risk_level"] == "medium"

    def test_no_late(self):
        br = BillReminder()
        r = br.estimate_late_fees(1000.0, 0)
        assert r["late_fee"] == 0.0
        assert r["risk_level"] == "none"


# ============================================================
# PersonalInvestmentTracker testleri
# ============================================================


class TestAddHolding:
    def test_basic(self):
        it = PersonalInvestmentTracker()
        r = it.add_holding("THYAO", "stocks", 15000.0, 10000.0)
        assert r["added"] is True
        assert r["gain"] == 5000.0
        assert r["gain_pct"] == 50.0

    def test_count(self):
        it = PersonalInvestmentTracker()
        it.add_holding("A")
        it.add_holding("B")
        assert it.holding_count == 2


class TestAnalyzePerformance:
    def test_basic(self):
        it = PersonalInvestmentTracker()
        it.add_holding("A", "stocks", 15000.0, 10000.0)
        it.add_holding("B", "bonds", 8000.0, 7000.0)
        r = it.analyze_performance()
        assert r["total_value"] == 23000.0
        assert r["total_gain"] == 6000.0
        assert r["analyzed"] is True

    def test_empty(self):
        it = PersonalInvestmentTracker()
        r = it.analyze_performance()
        assert r["total_value"] == 0.0


class TestViewAllocation:
    def test_diversified(self):
        it = PersonalInvestmentTracker()
        it.add_holding("A", "stocks", 5000.0)
        it.add_holding("B", "bonds", 3000.0)
        it.add_holding("C", "etf", 2000.0)
        r = it.view_allocation()
        assert r["diversified"] is True
        assert r["type_count"] == 3

    def test_not_diversified(self):
        it = PersonalInvestmentTracker()
        it.add_holding("A", "stocks", 5000.0)
        r = it.view_allocation()
        assert r["diversified"] is False


class TestTrackDividends:
    def test_basic(self):
        it = PersonalInvestmentTracker()
        h = it.add_holding("THYAO", "stocks", 10000.0)
        r = it.track_dividends(h["holding_id"], 500.0)
        assert r["tracked"] is True
        assert r["total_dividends"] == 500.0

    def test_not_found(self):
        it = PersonalInvestmentTracker()
        r = it.track_dividends("xxx", 100.0)
        assert r["tracked"] is False


class TestCalculateTax:
    def test_long_term(self):
        it = PersonalInvestmentTracker()
        r = it.calculate_tax(10000.0, 15.0, 18)
        assert r["term"] == "long_term"
        assert r["tax_rate"] == 7.5
        assert r["tax_amount"] == 750.0

    def test_short_term(self):
        it = PersonalInvestmentTracker()
        r = it.calculate_tax(10000.0, 15.0, 6)
        assert r["term"] == "short_term"
        assert r["tax_amount"] == 1500.0


# ============================================================
# PersonalFinancialGoalTracker testleri
# ============================================================


class TestSetGoal:
    def test_basic(self):
        gt = PersonalFinancialGoalTracker()
        r = gt.set_goal("Ev Alımı", "home_purchase", 500000.0, 60)
        assert r["set"] is True
        assert r["goal_id"].startswith("fg_")
        assert r["monthly_required"] > 0

    def test_count(self):
        gt = PersonalFinancialGoalTracker()
        gt.set_goal("A")
        gt.set_goal("B")
        assert gt.goal_count == 2


class TestUpdateGoalProgress:
    def test_basic(self):
        gt = PersonalFinancialGoalTracker()
        g = gt.set_goal("Test", "emergency_fund", 10000.0)
        r = gt.update_progress(g["goal_id"], 7500.0)
        assert r["updated"] is True
        assert r["status"] == "almost_there"
        assert r["progress_pct"] == 75.0

    def test_completed(self):
        gt = PersonalFinancialGoalTracker()
        g = gt.set_goal("Test", "emergency_fund", 1000.0)
        r = gt.update_progress(g["goal_id"], 1000.0)
        assert r["status"] == "completed"

    def test_not_found(self):
        gt = PersonalFinancialGoalTracker()
        r = gt.update_progress("xxx", 100.0)
        assert r["updated"] is False


class TestCheckMilestones:
    def test_basic(self):
        gt = PersonalFinancialGoalTracker()
        g = gt.set_goal("Test", "emergency_fund", 10000.0)
        gt.update_progress(g["goal_id"], 6000.0)
        r = gt.check_milestones(g["goal_id"])
        assert r["checked"] is True
        assert 50 in r["reached"]
        assert r["next_milestone"] == 75

    def test_not_found(self):
        gt = PersonalFinancialGoalTracker()
        r = gt.check_milestones("xxx")
        assert r["checked"] is False


class TestProjectCompletion:
    def test_on_track(self):
        gt = PersonalFinancialGoalTracker()
        g = gt.set_goal("Test", "emergency_fund", 12000.0, 12)
        gt.update_progress(g["goal_id"], 6000.0)
        r = gt.project_completion(g["goal_id"], 1000.0)
        assert r["projected"] is True
        assert r["on_track"] is True

    def test_not_found(self):
        gt = PersonalFinancialGoalTracker()
        r = gt.project_completion("xxx", 1000.0)
        assert r["projected"] is False


class TestAdjustStrategy:
    def test_basic(self):
        gt = PersonalFinancialGoalTracker()
        g = gt.set_goal("Test", "emergency_fund", 12000.0, 12)
        r = gt.adjust_strategy(g["goal_id"], 2000.0)
        assert r["adjusted"] is True
        assert r["new_monthly"] == 2000.0

    def test_not_found(self):
        gt = PersonalFinancialGoalTracker()
        r = gt.adjust_strategy("xxx", 1000.0)
        assert r["adjusted"] is False


# ============================================================
# NetWorthCalculator testleri
# ============================================================


class TestAddAsset:
    def test_basic(self):
        nw = NetWorthCalculator()
        r = nw.add_asset("Ev", 500000.0, "real_estate")
        assert r["added"] is True
        assert r["total_assets"] == 500000.0

    def test_multiple(self):
        nw = NetWorthCalculator()
        nw.add_asset("Ev", 500000.0)
        r = nw.add_asset("Araba", 100000.0)
        assert r["total_assets"] == 600000.0


class TestAddLiability:
    def test_basic(self):
        nw = NetWorthCalculator()
        r = nw.add_liability("Mortgage", 300000.0)
        assert r["added"] is True
        assert r["total_liabilities"] == 300000.0


class TestCalculateNetWorth:
    def test_positive(self):
        nw = NetWorthCalculator()
        nw.add_asset("Ev", 500000.0)
        nw.add_liability("Mortgage", 200000.0)
        r = nw.calculate_net_worth()
        assert r["net_worth"] == 300000.0
        assert r["status"] == "positive"
        assert r["calculated"] is True

    def test_negative(self):
        nw = NetWorthCalculator()
        nw.add_asset("Cash", 10000.0)
        nw.add_liability("Loan", 50000.0)
        r = nw.calculate_net_worth()
        assert r["status"] == "negative"

    def test_count(self):
        nw = NetWorthCalculator()
        nw.calculate_net_worth()
        assert nw.calculation_count == 1


class TestGetNetWorthTrend:
    def test_improving(self):
        nw = NetWorthCalculator()
        nw.add_asset("A", 100000.0)
        nw.calculate_net_worth()
        nw.add_asset("B", 50000.0)
        nw.calculate_net_worth()
        r = nw.get_trend()
        assert r["trend"] == "improving"

    def test_insufficient(self):
        nw = NetWorthCalculator()
        r = nw.get_trend()
        assert r["trend"] == "insufficient_data"


class TestProjectNetWorth:
    def test_basic(self):
        nw = NetWorthCalculator()
        nw.add_asset("Cash", 100000.0)
        nw.calculate_net_worth()
        r = nw.project_net_worth(5000.0, 12, 5.0)
        assert r["projected_ok"] is True
        assert r["projected"] > r["current"]
        assert r["gain"] > 0


# ============================================================
# PersonalFinOrchestrator testleri
# ============================================================


class TestFinancialHealthCheck:
    def test_excellent(self):
        orch = PersonalFinOrchestrator()
        r = orch.financial_health_check(
            20000.0, 10000.0, 500000.0, 100000.0
        )
        assert r["health_checked"] is True
        assert r["health_score"] == "excellent"
        assert r["savings_rate"] == 50.0

    def test_poor(self):
        orch = PersonalFinOrchestrator()
        r = orch.financial_health_check(
            10000.0, 11000.0, 50000.0, 200000.0
        )
        assert r["health_score"] == "poor"


class TestMonthlySummary:
    def test_basic(self):
        orch = PersonalFinOrchestrator()
        txns = [
            {"merchant": "Migros", "amount": 500},
            {"merchant": "Shell", "amount": 300},
            {"merchant": "Netflix", "amount": 100},
        ]
        r = orch.monthly_summary(15000.0, txns)
        assert r["summarized"] is True
        assert r["total_spent"] == 900.0
        assert r["transaction_count"] == 3

    def test_empty(self):
        orch = PersonalFinOrchestrator()
        r = orch.monthly_summary(10000.0)
        assert r["total_spent"] == 0.0
        assert r["remaining"] == 10000.0


class TestPersonalFinGetAnalytics:
    def test_initial(self):
        orch = PersonalFinOrchestrator()
        a = orch.get_analytics()
        assert a["cycles_run"] == 0
        assert a["accounts_linked"] == 0
        assert a["budgets_created"] == 0

    def test_after_operations(self):
        orch = PersonalFinOrchestrator()
        orch.financial_health_check(
            20000.0, 10000.0, 100000.0, 50000.0
        )
        orch.monthly_summary(15000.0, [
            {"merchant": "Migros", "amount": 200}
        ])
        a = orch.get_analytics()
        assert a["cycles_run"] == 2
        assert a["net_worth_calcs"] >= 1
        assert a["transactions_categorized"] >= 1
