"""ATLAS Cost-Per-Decision Engine testleri.

CostCalculator, PriceCatalog, BudgetManager,
DecisionCostTracker, AlternativeAnalyzer,
SpendingController, CostOptimizationAdvisor,
BillingReporter, CostEngineOrchestrator testleri.
"""

import unittest

from app.models.costengine_models import (
    BudgetPeriod,
    BudgetRecord,
    CostCategory,
    CostEngineSnapshot,
    CostRecord,
    OptimizationRecord,
    OptimizationType,
    PricingModel,
    ReportFormat,
    SpendingAction,
)


class TestCostEngineModels(unittest.TestCase):
    """Cost engine model testleri."""

    def test_cost_category_values(self):
        self.assertEqual(
            CostCategory.API_CALL, "api_call",
        )
        self.assertEqual(
            CostCategory.COMPUTE, "compute",
        )
        self.assertEqual(
            CostCategory.STORAGE, "storage",
        )
        self.assertEqual(
            CostCategory.TIME, "time",
        )
        self.assertEqual(
            CostCategory.OPPORTUNITY,
            "opportunity",
        )

    def test_budget_period_values(self):
        self.assertEqual(
            BudgetPeriod.HOURLY, "hourly",
        )
        self.assertEqual(
            BudgetPeriod.DAILY, "daily",
        )
        self.assertEqual(
            BudgetPeriod.WEEKLY, "weekly",
        )
        self.assertEqual(
            BudgetPeriod.MONTHLY, "monthly",
        )
        self.assertEqual(
            BudgetPeriod.CUSTOM, "custom",
        )

    def test_spending_action_values(self):
        self.assertEqual(
            SpendingAction.ALLOW, "allow",
        )
        self.assertEqual(
            SpendingAction.WARN, "warn",
        )
        self.assertEqual(
            SpendingAction.PAUSE, "pause",
        )
        self.assertEqual(
            SpendingAction.BLOCK, "block",
        )
        self.assertEqual(
            SpendingAction.APPROVE, "approve",
        )

    def test_optimization_type_values(self):
        self.assertEqual(
            OptimizationType.CACHING, "caching",
        )
        self.assertEqual(
            OptimizationType.BATCHING, "batching",
        )
        self.assertEqual(
            OptimizationType.DOWNGRADE,
            "downgrade",
        )
        self.assertEqual(
            OptimizationType.ELIMINATION,
            "elimination",
        )
        self.assertEqual(
            OptimizationType.SCHEDULING,
            "scheduling",
        )

    def test_report_format_values(self):
        self.assertEqual(
            ReportFormat.SUMMARY, "summary",
        )
        self.assertEqual(
            ReportFormat.DETAILED, "detailed",
        )
        self.assertEqual(
            ReportFormat.BREAKDOWN, "breakdown",
        )
        self.assertEqual(
            ReportFormat.TREND, "trend",
        )
        self.assertEqual(
            ReportFormat.EXPORT, "export",
        )

    def test_pricing_model_values(self):
        self.assertEqual(
            PricingModel.FIXED, "fixed",
        )
        self.assertEqual(
            PricingModel.PER_UNIT, "per_unit",
        )
        self.assertEqual(
            PricingModel.TIERED, "tiered",
        )
        self.assertEqual(
            PricingModel.DYNAMIC, "dynamic",
        )
        self.assertEqual(
            PricingModel.FREE, "free",
        )

    def test_cost_record_defaults(self):
        r = CostRecord()
        self.assertTrue(len(r.cost_id) > 0)
        self.assertEqual(r.decision_id, "")
        self.assertEqual(
            r.category, CostCategory.API_CALL,
        )
        self.assertEqual(r.amount, 0.0)
        self.assertEqual(r.currency, "USD")
        self.assertIsNotNone(r.created_at)

    def test_cost_record_custom(self):
        r = CostRecord(
            cost_id="c1",
            decision_id="d1",
            category=CostCategory.COMPUTE,
            amount=5.50,
            currency="EUR",
        )
        self.assertEqual(r.cost_id, "c1")
        self.assertEqual(r.amount, 5.50)
        self.assertEqual(r.currency, "EUR")

    def test_budget_record_defaults(self):
        r = BudgetRecord()
        self.assertTrue(len(r.budget_id) > 0)
        self.assertEqual(
            r.period, BudgetPeriod.DAILY,
        )
        self.assertEqual(r.limit, 0.0)
        self.assertEqual(r.spent, 0.0)

    def test_optimization_record_defaults(self):
        r = OptimizationRecord()
        self.assertTrue(
            len(r.optimization_id) > 0,
        )
        self.assertEqual(
            r.type, OptimizationType.CACHING,
        )
        self.assertFalse(r.applied)

    def test_cost_engine_snapshot_defaults(self):
        s = CostEngineSnapshot()
        self.assertEqual(s.total_spent, 0.0)
        self.assertEqual(s.active_budgets, 0)
        self.assertEqual(
            s.decisions_tracked, 0,
        )
        self.assertIsNotNone(s.timestamp)

    def test_cost_engine_snapshot_custom(self):
        s = CostEngineSnapshot(
            total_spent=150.0,
            active_budgets=3,
            decisions_tracked=42,
            avg_cost_per_decision=3.57,
        )
        self.assertEqual(s.total_spent, 150.0)
        self.assertEqual(
            s.decisions_tracked, 42,
        )


class TestCostCalculator(unittest.TestCase):
    """CostCalculator testleri."""

    def setUp(self):
        from app.core.costengine.cost_calculator import (
            CostCalculator,
        )
        self.calc = CostCalculator()

    def test_calculate_api_cost(self):
        r = self.calc.calculate_api_cost(
            "claude", calls=10, rate=0.02,
        )
        self.assertEqual(r["category"], "api_call")
        self.assertAlmostEqual(
            r["cost"], 0.2, places=4,
        )

    def test_calculate_api_cost_default(self):
        r = self.calc.calculate_api_cost("test")
        self.assertEqual(r["cost"], 0.01)

    def test_calculate_api_cost_custom_rate(self):
        self.calc.set_rate("api_claude", 0.05)
        r = self.calc.calculate_api_cost(
            "claude", calls=2,
        )
        self.assertAlmostEqual(
            r["cost"], 0.1, places=4,
        )

    def test_calculate_compute_cost(self):
        r = self.calc.calculate_compute_cost(
            60.0, cpu_units=2.0,
        )
        self.assertEqual(
            r["category"], "compute",
        )
        # 0.001 * 60 * 2 = 0.12
        self.assertAlmostEqual(
            r["cost"], 0.12, places=4,
        )

    def test_calculate_compute_custom_rate(self):
        r = self.calc.calculate_compute_cost(
            10.0, rate=0.01,
        )
        self.assertAlmostEqual(
            r["cost"], 0.1, places=4,
        )

    def test_calculate_storage_cost(self):
        r = self.calc.calculate_storage_cost(
            100.0, duration_hours=24.0,
        )
        self.assertEqual(
            r["category"], "storage",
        )
        # 0.0001 * 100 * 24 = 0.24
        self.assertAlmostEqual(
            r["cost"], 0.24, places=4,
        )

    def test_calculate_time_cost(self):
        r = self.calc.calculate_time_cost(2.0)
        self.assertEqual(r["category"], "time")
        # 10.0 * 2 = 20.0
        self.assertAlmostEqual(
            r["cost"], 20.0, places=4,
        )

    def test_calculate_time_custom_rate(self):
        r = self.calc.calculate_time_cost(
            1.0, rate=25.0,
        )
        self.assertAlmostEqual(
            r["cost"], 25.0, places=4,
        )

    def test_calculate_opportunity_cost(self):
        r = self.calc.calculate_opportunity_cost(
            100.0, alternatives=2,
        )
        self.assertEqual(
            r["category"], "opportunity",
        )
        # 100 * 0.05 * 2 = 10.0
        self.assertAlmostEqual(
            r["cost"], 10.0, places=4,
        )

    def test_calculate_total(self):
        c1 = self.calc.calculate_api_cost(
            "a", rate=1.0,
        )
        c2 = self.calc.calculate_compute_cost(
            10.0, rate=0.1,
        )
        r = self.calc.calculate_total([c1, c2])
        self.assertAlmostEqual(
            r["total_cost"], 2.0, places=4,
        )
        self.assertEqual(r["components"], 2)

    def test_total_cost_property(self):
        self.calc.calculate_api_cost(
            "a", rate=1.0,
        )
        self.assertGreater(
            self.calc.total_cost, 0,
        )

    def test_calculation_count(self):
        self.assertEqual(
            self.calc.calculation_count, 0,
        )
        self.calc.calculate_api_cost("a")
        self.assertEqual(
            self.calc.calculation_count, 1,
        )

    def test_set_rate(self):
        r = self.calc.set_rate(
            "api_gpt", 0.03, unit="per_call",
        )
        self.assertTrue(r["set"])

    def test_get_history(self):
        self.calc.calculate_api_cost("a")
        self.calc.calculate_compute_cost(10.0)
        history = self.calc.get_history()
        self.assertEqual(len(history), 2)

    def test_get_history_filtered(self):
        self.calc.calculate_api_cost("a")
        self.calc.calculate_compute_cost(10.0)
        history = self.calc.get_history(
            category="api_call",
        )
        self.assertEqual(len(history), 1)

    def test_calculate_total_by_category(self):
        c1 = {"cost": 1.0, "category": "api_call"}
        c2 = {"cost": 2.0, "category": "api_call"}
        c3 = {"cost": 3.0, "category": "compute"}
        r = self.calc.calculate_total(
            [c1, c2, c3],
        )
        self.assertEqual(
            r["by_category"]["api_call"], 3.0,
        )
        self.assertEqual(
            r["by_category"]["compute"], 3.0,
        )


class TestPriceCatalog(unittest.TestCase):
    """PriceCatalog testleri."""

    def setUp(self):
        from app.core.costengine.price_catalog import (
            PriceCatalog,
        )
        self.catalog = PriceCatalog()

    def test_set_price(self):
        r = self.catalog.set_price(
            "claude", 0.015, unit="per_1k_tokens",
        )
        self.assertTrue(r["set"])
        self.assertEqual(r["price"], 0.015)

    def test_get_price(self):
        self.catalog.set_price("claude", 0.01)
        r = self.catalog.get_price(
            "claude", quantity=100,
        )
        self.assertAlmostEqual(
            r["total"], 1.0, places=4,
        )

    def test_get_price_not_found(self):
        r = self.catalog.get_price("unknown")
        self.assertIn("error", r)

    def test_price_count(self):
        self.assertEqual(
            self.catalog.price_count, 0,
        )
        self.catalog.set_price("a", 1.0)
        self.assertEqual(
            self.catalog.price_count, 1,
        )

    def test_tiered_pricing(self):
        self.catalog.set_price(
            "api", 0.01, model="tiered",
        )
        self.catalog.set_tiered_pricing("api", [
            {"min": 0, "max": 100, "price": 0.01},
            {"min": 101, "max": 1000, "price": 0.008},
            {"min": 1001, "max": float("inf"), "price": 0.005},
        ])
        # 50 kullanim - tier 1
        r = self.catalog.get_price(
            "api", quantity=50,
        )
        self.assertAlmostEqual(
            r["unit_price"], 0.01, places=4,
        )
        # 500 kullanim - tier 2
        r = self.catalog.get_price(
            "api", quantity=500,
        )
        self.assertAlmostEqual(
            r["unit_price"], 0.008, places=4,
        )

    def test_set_currency_rate(self):
        r = self.catalog.set_currency_rate(
            "EUR", 0.92,
        )
        self.assertTrue(r["set"])

    def test_convert_price(self):
        self.catalog.set_currency_rate(
            "EUR", 0.92,
        )
        r = self.catalog.convert_price(
            100.0, "USD", "EUR",
        )
        self.assertAlmostEqual(
            r["converted"], 92.0, places=2,
        )

    def test_convert_price_reverse(self):
        self.catalog.set_currency_rate(
            "EUR", 0.92,
        )
        r = self.catalog.convert_price(
            92.0, "EUR", "USD",
        )
        self.assertAlmostEqual(
            r["converted"], 100.0, places=2,
        )

    def test_currency_count(self):
        # Default USD
        self.assertEqual(
            self.catalog.currency_count, 1,
        )
        self.catalog.set_currency_rate(
            "EUR", 0.92,
        )
        self.assertEqual(
            self.catalog.currency_count, 2,
        )

    def test_list_prices(self):
        self.catalog.set_price("a", 1.0)
        self.catalog.set_price("b", 2.0)
        prices = self.catalog.list_prices()
        self.assertEqual(len(prices), 2)

    def test_list_prices_filtered(self):
        self.catalog.set_price(
            "a", 1.0, model="fixed",
        )
        self.catalog.set_price(
            "b", 2.0, model="per_unit",
        )
        prices = self.catalog.list_prices(
            model="fixed",
        )
        self.assertEqual(len(prices), 1)

    def test_remove_price(self):
        self.catalog.set_price("a", 1.0)
        r = self.catalog.remove_price("a")
        self.assertTrue(r["removed"])
        self.assertEqual(
            self.catalog.price_count, 0,
        )

    def test_remove_price_not_found(self):
        r = self.catalog.remove_price("no")
        self.assertIn("error", r)

    def test_get_price_with_currency(self):
        self.catalog.set_price(
            "svc", 10.0, currency="USD",
        )
        self.catalog.set_currency_rate(
            "TRY", 32.0,
        )
        r = self.catalog.get_price(
            "svc", quantity=1, currency="TRY",
        )
        self.assertAlmostEqual(
            r["total"], 320.0, places=2,
        )


class TestBudgetManager(unittest.TestCase):
    """BudgetManager testleri."""

    def setUp(self):
        from app.core.costengine.budget_manager import (
            BudgetManager,
        )
        self.mgr = BudgetManager(
            default_daily_limit=100.0,
        )

    def test_create_budget(self):
        r = self.mgr.create_budget(
            "b1", "Daily", 100.0,
        )
        self.assertTrue(r["created"])
        self.assertEqual(r["limit"], 100.0)

    def test_budget_count(self):
        self.assertEqual(
            self.mgr.budget_count, 0,
        )
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
        )
        self.assertEqual(
            self.mgr.budget_count, 1,
        )

    def test_allocate(self):
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
        )
        r = self.mgr.allocate("b1", 30.0)
        self.assertEqual(r["spent"], 30.0)
        self.assertEqual(r["remaining"], 70.0)
        self.assertFalse(r["exceeded"])

    def test_allocate_exceed(self):
        self.mgr.create_budget(
            "b1", "Daily", 50.0,
        )
        r = self.mgr.allocate("b1", 60.0)
        self.assertTrue(r["exceeded"])

    def test_allocate_not_found(self):
        r = self.mgr.allocate("no", 10.0)
        self.assertIn("error", r)

    def test_allocate_triggers_alert(self):
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
            alert_threshold=0.8,
        )
        r = self.mgr.allocate("b1", 85.0)
        self.assertIsNotNone(r["alert"])
        self.assertEqual(
            r["alert"]["severity"], "warning",
        )

    def test_allocate_critical_alert(self):
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
        )
        r = self.mgr.allocate("b1", 110.0)
        self.assertIsNotNone(r["alert"])
        self.assertEqual(
            r["alert"]["severity"], "critical",
        )

    def test_check_budget(self):
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
        )
        self.mgr.allocate("b1", 40.0)
        r = self.mgr.check_budget("b1", 30.0)
        self.assertTrue(r["can_afford"])
        self.assertEqual(r["remaining"], 60.0)

    def test_check_budget_cant_afford(self):
        self.mgr.create_budget(
            "b1", "Daily", 50.0,
        )
        self.mgr.allocate("b1", 40.0)
        r = self.mgr.check_budget("b1", 20.0)
        self.assertFalse(r["can_afford"])

    def test_check_budget_not_found(self):
        r = self.mgr.check_budget("no")
        self.assertIn("error", r)

    def test_get_budget(self):
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
        )
        b = self.mgr.get_budget("b1")
        self.assertIsNotNone(b)
        self.assertEqual(b["name"], "Daily")

    def test_get_budget_not_found(self):
        r = self.mgr.get_budget("no")
        self.assertIsNone(r)

    def test_reset_budget(self):
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
        )
        self.mgr.allocate("b1", 80.0)
        r = self.mgr.reset_budget("b1")
        self.assertTrue(r["reset"])
        b = self.mgr.get_budget("b1")
        self.assertEqual(b["spent"], 0.0)

    def test_reset_not_found(self):
        r = self.mgr.reset_budget("no")
        self.assertIn("error", r)

    def test_update_limit(self):
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
        )
        r = self.mgr.update_limit("b1", 200.0)
        self.assertTrue(r["updated"])
        self.assertEqual(r["new_limit"], 200.0)

    def test_update_limit_not_found(self):
        r = self.mgr.update_limit("no", 200.0)
        self.assertIn("error", r)

    def test_list_budgets(self):
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
        )
        self.mgr.create_budget(
            "b2", "Weekly", 500.0,
        )
        budgets = self.mgr.list_budgets()
        self.assertEqual(len(budgets), 2)

    def test_list_budgets_filtered(self):
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
        )
        self.mgr.create_budget(
            "b2", "Daily", 50.0,
        )
        self.mgr.allocate("b2", 60.0)
        exceeded = self.mgr.list_budgets(
            status="exceeded",
        )
        self.assertEqual(len(exceeded), 1)

    def test_get_total_spending(self):
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
        )
        self.mgr.create_budget(
            "b2", "Daily", 50.0,
        )
        self.mgr.allocate("b1", 30.0)
        self.mgr.allocate("b2", 20.0)
        r = self.mgr.get_total_spending()
        self.assertEqual(r["total_spent"], 50.0)
        self.assertEqual(r["total_limit"], 150.0)

    def test_alert_count(self):
        self.mgr.create_budget(
            "b1", "Daily", 100.0,
            alert_threshold=0.5,
        )
        self.mgr.allocate("b1", 60.0)
        self.assertGreater(
            self.mgr.alert_count, 0,
        )


class TestDecisionCostTracker(unittest.TestCase):
    """DecisionCostTracker testleri."""

    def setUp(self):
        from app.core.costengine.cost_tracker import (
            DecisionCostTracker,
        )
        self.tracker = DecisionCostTracker()

    def test_start_tracking(self):
        r = self.tracker.start_tracking(
            "d1", system="master_agent",
        )
        self.assertTrue(r["tracking"])

    def test_add_cost(self):
        self.tracker.start_tracking("d1")
        r = self.tracker.add_cost(
            "d1", "api_call", 0.05,
        )
        self.assertTrue(r["added"])
        self.assertEqual(r["cumulative"], 0.05)

    def test_add_cost_not_found(self):
        r = self.tracker.add_cost(
            "no", "api_call", 0.05,
        )
        self.assertIn("error", r)

    def test_add_multiple_costs(self):
        self.tracker.start_tracking("d1")
        self.tracker.add_cost(
            "d1", "api_call", 0.05,
        )
        r = self.tracker.add_cost(
            "d1", "compute", 0.10,
        )
        self.assertAlmostEqual(
            r["cumulative"], 0.15, places=4,
        )

    def test_complete_tracking(self):
        self.tracker.start_tracking("d1")
        self.tracker.add_cost(
            "d1", "api_call", 0.05,
        )
        r = self.tracker.complete_tracking("d1")
        self.assertTrue(r["completed"])
        self.assertEqual(r["total_cost"], 0.05)

    def test_complete_not_found(self):
        r = self.tracker.complete_tracking("no")
        self.assertIn("error", r)

    def test_get_decision_cost(self):
        self.tracker.start_tracking(
            "d1", system="agent",
        )
        self.tracker.add_cost(
            "d1", "api_call", 0.05,
        )
        self.tracker.add_cost(
            "d1", "compute", 0.10,
        )
        r = self.tracker.get_decision_cost("d1")
        self.assertAlmostEqual(
            r["total_cost"], 0.15, places=4,
        )
        self.assertEqual(r["cost_items"], 2)
        self.assertEqual(r["system"], "agent")

    def test_get_decision_cost_not_found(self):
        r = self.tracker.get_decision_cost("no")
        self.assertIn("error", r)

    def test_get_cost_by_system(self):
        self.tracker.start_tracking(
            "d1", system="agent",
        )
        self.tracker.add_cost(
            "d1", "api_call", 1.0,
        )
        self.tracker.start_tracking(
            "d2", system="monitor",
        )
        self.tracker.add_cost(
            "d2", "api_call", 2.0,
        )
        by_sys = self.tracker.get_cost_by_system()
        self.assertEqual(by_sys["agent"], 1.0)
        self.assertEqual(by_sys["monitor"], 2.0)

    def test_get_cost_by_category(self):
        self.tracker.start_tracking("d1")
        self.tracker.add_cost(
            "d1", "api_call", 1.0,
        )
        self.tracker.add_cost(
            "d1", "compute", 2.0,
        )
        by_cat = (
            self.tracker.get_cost_by_category()
        )
        self.assertEqual(
            by_cat["api_call"], 1.0,
        )
        self.assertEqual(
            by_cat["compute"], 2.0,
        )

    def test_get_avg_cost(self):
        for i in range(4):
            did = f"d{i}"
            self.tracker.start_tracking(did)
            self.tracker.add_cost(
                did, "api", float(i + 1),
            )
            self.tracker.complete_tracking(did)
        # (1+2+3+4) / 4 = 2.5
        self.assertAlmostEqual(
            self.tracker.get_avg_cost(),
            2.5, places=4,
        )

    def test_get_avg_cost_empty(self):
        self.assertEqual(
            self.tracker.get_avg_cost(), 0.0,
        )

    def test_get_trend(self):
        for i in range(8):
            did = f"d{i}"
            self.tracker.start_tracking(did)
            # Artan maliyet
            self.tracker.add_cost(
                did, "api", float((i + 1) * 10),
            )
            self.tracker.complete_tracking(did)
        r = self.tracker.get_trend()
        self.assertEqual(
            r["direction"], "increasing",
        )

    def test_get_trend_insufficient(self):
        self.tracker.start_tracking("d1")
        self.tracker.complete_tracking("d1")
        r = self.tracker.get_trend()
        self.assertEqual(
            r["direction"], "insufficient",
        )

    def test_decision_count(self):
        self.tracker.start_tracking("d1")
        self.tracker.start_tracking("d2")
        self.assertEqual(
            self.tracker.decision_count, 2,
        )

    def test_total_cost(self):
        self.tracker.start_tracking("d1")
        self.tracker.add_cost(
            "d1", "api", 1.5,
        )
        self.assertEqual(
            self.tracker.total_cost, 1.5,
        )

    def test_get_history(self):
        self.tracker.start_tracking("d1")
        self.tracker.add_cost(
            "d1", "api", 1.0,
        )
        self.tracker.add_cost(
            "d1", "compute", 2.0,
        )
        history = self.tracker.get_history()
        self.assertEqual(len(history), 2)


class TestAlternativeAnalyzer(unittest.TestCase):
    """AlternativeAnalyzer testleri."""

    def setUp(self):
        from app.core.costengine.alternative_analyzer import (
            AlternativeAnalyzer,
        )
        self.analyzer = AlternativeAnalyzer()

    def test_compare_alternatives(self):
        alts = [
            {"name": "A", "cost": 10, "benefit": 50},
            {"name": "B", "cost": 20, "benefit": 80},
            {"name": "C", "cost": 5, "benefit": 30},
        ]
        r = self.analyzer.compare_alternatives(
            "d1", alts,
        )
        self.assertEqual(r["best"], "B")
        self.assertEqual(r["count"], 3)

    def test_compare_alternatives_empty(self):
        r = self.analyzer.compare_alternatives(
            "d1", [],
        )
        self.assertIn("error", r)

    def test_cost_benefit_analysis(self):
        r = self.analyzer.cost_benefit_analysis(
            "project",
            costs=[100, 50, 25],
            benefits=[80, 120, 150],
        )
        self.assertTrue(r["viable"])
        self.assertGreater(r["bcr"], 1.0)

    def test_cost_benefit_not_viable(self):
        r = self.analyzer.cost_benefit_analysis(
            "project",
            costs=[100, 100],
            benefits=[30, 20],
        )
        self.assertFalse(r["viable"])
        self.assertLess(r["bcr"], 1.0)

    def test_cost_benefit_with_discount(self):
        r = self.analyzer.cost_benefit_analysis(
            "project",
            costs=[100, 100],
            benefits=[150, 150],
            discount_rate=0.1,
        )
        self.assertTrue(r["viable"])

    def test_calculate_roi(self):
        r = self.analyzer.calculate_roi(
            "invest", 1000, 1500,
        )
        self.assertTrue(r["profitable"])
        self.assertEqual(r["roi_pct"], 50.0)
        self.assertEqual(r["profit"], 500.0)

    def test_calculate_roi_loss(self):
        r = self.analyzer.calculate_roi(
            "invest", 1000, 800,
        )
        self.assertFalse(r["profitable"])
        self.assertEqual(r["roi_pct"], -20.0)

    def test_calculate_roi_zero_investment(self):
        r = self.analyzer.calculate_roi(
            "free", 0, 100,
        )
        self.assertEqual(
            r["roi_pct"], float("inf"),
        )

    def test_trade_off_analysis(self):
        a = {"cost": 3, "speed": 8, "quality": 9}
        b = {"cost": 7, "speed": 9, "quality": 5}
        r = self.analyzer.trade_off_analysis(
            "d1", a, b,
        )
        self.assertIn(
            r["winner"], ("a", "b", "tie"),
        )
        self.assertIn("criteria", r)

    def test_trade_off_with_weights(self):
        a = {"cost": 3, "quality": 9}
        b = {"cost": 7, "quality": 5}
        r = self.analyzer.trade_off_analysis(
            "d1", a, b,
            weights={"cost": 0.3, "quality": 0.7},
        )
        # a: 3*0.3 + 9*0.7 = 7.2
        # b: 7*0.3 + 5*0.7 = 5.6
        self.assertEqual(r["winner"], "a")

    def test_recommend(self):
        alts = [
            {"name": "A", "cost": 10, "benefit": 50},
            {"name": "B", "cost": 100, "benefit": 200},
            {"name": "C", "cost": 5, "benefit": 30},
        ]
        r = self.analyzer.recommend(
            "d1", alts, max_cost=50,
        )
        self.assertIsNotNone(
            r["recommendation"],
        )
        # B filtered out (cost 100 > max 50)
        self.assertNotEqual(
            r["recommendation"], "B",
        )

    def test_recommend_with_min_benefit(self):
        alts = [
            {"name": "A", "cost": 10, "benefit": 50},
            {"name": "B", "cost": 5, "benefit": 10},
        ]
        r = self.analyzer.recommend(
            "d1", alts, min_benefit=20,
        )
        self.assertEqual(
            r["recommendation"], "A",
        )

    def test_recommend_no_viable(self):
        alts = [
            {"name": "A", "cost": 100, "benefit": 50},
        ]
        r = self.analyzer.recommend(
            "d1", alts, max_cost=10,
        )
        self.assertIsNone(r["recommendation"])

    def test_analysis_count(self):
        self.assertEqual(
            self.analyzer.analysis_count, 0,
        )
        self.analyzer.calculate_roi(
            "x", 100, 200,
        )
        self.assertEqual(
            self.analyzer.analysis_count, 1,
        )

    def test_get_analyses(self):
        self.analyzer.calculate_roi(
            "a", 100, 200,
        )
        self.analyzer.calculate_roi(
            "b", 50, 80,
        )
        analyses = self.analyzer.get_analyses()
        self.assertEqual(len(analyses), 2)


class TestSpendingController(unittest.TestCase):
    """SpendingController testleri."""

    def setUp(self):
        from app.core.costengine.spending_controller import (
            SpendingController,
        )
        self.ctrl = SpendingController(
            pause_on_exceed=True,
            require_approval_above=50.0,
        )

    def test_check_spending_allow(self):
        r = self.ctrl.check_spending(10.0)
        self.assertEqual(r["action"], "allow")

    def test_check_spending_approve(self):
        r = self.ctrl.check_spending(60.0)
        self.assertEqual(r["action"], "approve")
        self.assertIn("request_id", r)

    def test_check_spending_emergency(self):
        self.ctrl.emergency_stop()
        r = self.ctrl.check_spending(1.0)
        self.assertEqual(r["action"], "block")
        self.assertEqual(
            r["reason"], "emergency_stop",
        )

    def test_check_spending_paused(self):
        self.ctrl.pause()
        r = self.ctrl.check_spending(1.0)
        self.assertEqual(r["action"], "pause")

    def test_check_spending_limit(self):
        self.ctrl.set_limit("l1", 100.0)
        self.ctrl.record_spending(
            90.0, limit_id="l1",
        )
        r = self.ctrl.check_spending(
            20.0, limit_id="l1",
        )
        self.assertEqual(r["action"], "block")

    def test_set_limit(self):
        r = self.ctrl.set_limit("l1", 200.0)
        self.assertTrue(r["set"])

    def test_record_spending(self):
        self.ctrl.set_limit("l1", 100.0)
        r = self.ctrl.record_spending(
            30.0, limit_id="l1",
        )
        self.assertTrue(r["recorded"])

    def test_approve_request(self):
        r = self.ctrl.check_spending(60.0)
        req_id = r["request_id"]
        r2 = self.ctrl.approve_request(req_id)
        self.assertTrue(r2["approved"])

    def test_approve_not_found(self):
        r = self.ctrl.approve_request("no")
        self.assertIn("error", r)

    def test_deny_request(self):
        r = self.ctrl.check_spending(60.0)
        req_id = r["request_id"]
        r2 = self.ctrl.deny_request(
            req_id, reason="too_expensive",
        )
        self.assertTrue(r2["denied"])

    def test_deny_not_found(self):
        r = self.ctrl.deny_request("no")
        self.assertIn("error", r)

    def test_emergency_stop(self):
        r = self.ctrl.emergency_stop()
        self.assertTrue(r["emergency_stop"])
        self.assertTrue(self.ctrl.is_emergency)

    def test_pause(self):
        r = self.ctrl.pause()
        self.assertTrue(r["paused"])
        self.assertTrue(self.ctrl.is_paused)

    def test_resume(self):
        self.ctrl.pause()
        self.ctrl.emergency_stop()
        r = self.ctrl.resume()
        self.assertTrue(r["resumed"])
        self.assertFalse(self.ctrl.is_paused)
        self.assertFalse(self.ctrl.is_emergency)

    def test_add_override(self):
        r = self.ctrl.add_override(
            "o1", "emergency", 1000.0,
        )
        self.assertTrue(r["set"])

    def test_get_pending(self):
        self.ctrl.check_spending(60.0)
        self.ctrl.check_spending(70.0)
        pending = self.ctrl.get_pending()
        self.assertEqual(len(pending), 2)

    def test_pending_count(self):
        self.ctrl.check_spending(60.0)
        self.assertEqual(
            self.ctrl.pending_count, 1,
        )

    def test_check_count(self):
        self.ctrl.check_spending(10.0)
        self.ctrl.check_spending(20.0)
        self.assertEqual(
            self.ctrl.check_count, 2,
        )

    def test_warn_on_exceed_no_pause(self):
        from app.core.costengine.spending_controller import (
            SpendingController,
        )
        ctrl = SpendingController(
            pause_on_exceed=False,
            require_approval_above=1000.0,
        )
        ctrl.set_limit("l1", 50.0)
        ctrl.record_spending(
            45.0, limit_id="l1",
        )
        r = ctrl.check_spending(
            10.0, limit_id="l1",
        )
        self.assertEqual(r["action"], "warn")


class TestCostOptimizationAdvisor(
    unittest.TestCase,
):
    """CostOptimizationAdvisor testleri."""

    def setUp(self):
        from app.core.costengine.optimization_advisor import (
            CostOptimizationAdvisor,
        )
        self.advisor = CostOptimizationAdvisor()

    def test_analyze_spending(self):
        costs = [
            {"amount": 50, "category": "api_call",
             "service": "claude"},
            {"amount": 30, "category": "api_call",
             "service": "claude"},
            {"amount": 10, "category": "compute"},
        ]
        r = self.advisor.analyze_spending(costs)
        self.assertEqual(r["total_spent"], 90)
        self.assertGreater(
            len(r["suggestions"]), 0,
        )

    def test_analyze_spending_empty(self):
        r = self.advisor.analyze_spending([])
        self.assertEqual(
            len(r["suggestions"]), 0,
        )

    def test_analyze_spending_caching_suggestion(self):
        costs = []
        for _ in range(10):
            costs.append({
                "amount": 1.0,
                "category": "api_call",
                "service": "gpt",
            })
        r = self.advisor.analyze_spending(costs)
        caching = [
            s for s in r["suggestions"]
            if s["type"] == "caching"
        ]
        self.assertGreater(len(caching), 0)

    def test_suggest_caching(self):
        r = self.advisor.suggest_caching(
            "claude", 100, 0.01,
            cache_hit_rate=0.7,
        )
        self.assertEqual(r["type"], "caching")
        self.assertGreater(r["savings"], 0)
        # 100 * 0.01 = 1.0 -> savings 0.7
        self.assertAlmostEqual(
            r["savings"], 0.7, places=2,
        )

    def test_suggest_batching(self):
        r = self.advisor.suggest_batching(
            100, 0.01, batch_size=10,
            batch_discount=0.3,
        )
        self.assertEqual(r["type"], "batching")
        self.assertGreater(r["savings"], 0)

    def test_detect_waste(self):
        costs = [
            {"amount": 5.0, "category": "api",
             "benefit": 0, "description": "unused"},
            {"amount": 3.0, "category": "api",
             "benefit": 10, "description": "useful"},
        ]
        r = self.advisor.detect_waste(costs)
        self.assertGreater(
            r["waste_items"], 0,
        )
        self.assertGreater(
            r["total_waste"], 0,
        )

    def test_detect_waste_duplicates(self):
        costs = []
        for _ in range(5):
            costs.append({
                "amount": 1.0,
                "category": "api",
                "description": "same_call",
                "benefit": 1,
            })
        r = self.advisor.detect_waste(costs)
        dup = [
            w for w in r["details"]
            if w.get("reason") == "duplicate"
        ]
        self.assertGreater(len(dup), 0)

    def test_apply_suggestion(self):
        self.advisor.suggest_caching(
            "svc", 100, 0.01,
        )
        r = self.advisor.apply_suggestion(0)
        self.assertTrue(r["applied"])
        self.assertGreater(r["savings"], 0)

    def test_apply_suggestion_invalid(self):
        r = self.advisor.apply_suggestion(999)
        self.assertIn("error", r)

    def test_suggestion_count(self):
        self.advisor.suggest_caching(
            "a", 100, 0.01,
        )
        self.advisor.suggest_batching(
            50, 0.02,
        )
        self.assertEqual(
            self.advisor.suggestion_count, 2,
        )

    def test_total_savings(self):
        self.advisor.suggest_caching(
            "svc", 100, 0.01,
        )
        self.advisor.apply_suggestion(0)
        self.assertGreater(
            self.advisor.total_savings, 0,
        )

    def test_get_suggestions(self):
        self.advisor.suggest_caching(
            "a", 100, 0.01,
        )
        self.advisor.suggest_batching(
            50, 0.02,
        )
        all_s = self.advisor.get_suggestions()
        self.assertEqual(len(all_s), 2)

    def test_get_suggestions_filtered(self):
        self.advisor.suggest_caching(
            "a", 100, 0.01,
        )
        self.advisor.suggest_batching(
            50, 0.02,
        )
        cached = self.advisor.get_suggestions(
            suggestion_type="caching",
        )
        self.assertEqual(len(cached), 1)


class TestBillingReporter(unittest.TestCase):
    """BillingReporter testleri."""

    def setUp(self):
        from app.core.costengine.billing_reporter import (
            BillingReporter,
        )
        self.reporter = BillingReporter()

    def test_generate_cost_report(self):
        costs = [
            {"amount": 10.0, "category": "api"},
            {"amount": 20.0, "category": "compute"},
        ]
        r = self.reporter.generate_cost_report(
            costs,
        )
        self.assertEqual(r["type"], "cost")
        self.assertEqual(r["total_cost"], 30.0)
        self.assertEqual(r["item_count"], 2)

    def test_cost_report_by_category(self):
        costs = [
            {"amount": 10.0, "category": "api"},
            {"amount": 5.0, "category": "api"},
            {"amount": 20.0, "category": "compute"},
        ]
        r = self.reporter.generate_cost_report(
            costs,
        )
        self.assertEqual(
            r["by_category"]["api"], 15.0,
        )

    def test_generate_usage_report(self):
        usage = {"claude": 100, "gpt": 50}
        costs = {"claude": 10.0, "gpt": 5.0}
        r = self.reporter.generate_usage_report(
            usage, costs,
        )
        self.assertEqual(r["type"], "usage")
        self.assertEqual(r["total_usage"], 150)
        self.assertEqual(r["total_cost"], 15.0)

    def test_usage_report_no_costs(self):
        usage = {"svc": 100}
        r = self.reporter.generate_usage_report(
            usage,
        )
        self.assertEqual(r["total_cost"], 0.0)

    def test_generate_system_breakdown(self):
        system_costs = {
            "agent": 50.0,
            "monitor": 30.0,
            "api": 20.0,
        }
        r = (
            self.reporter
            .generate_system_breakdown(
                system_costs,
            )
        )
        self.assertEqual(
            r["type"], "system_breakdown",
        )
        self.assertEqual(r["total_cost"], 100.0)
        self.assertEqual(r["systems"], 3)
        # Sorted by cost desc
        self.assertEqual(
            r["breakdown"][0]["system"], "agent",
        )

    def test_generate_task_breakdown(self):
        task_costs = {
            "task1": 15.0,
            "task2": 25.0,
            "task3": 10.0,
        }
        r = (
            self.reporter
            .generate_task_breakdown(task_costs)
        )
        self.assertEqual(
            r["type"], "task_breakdown",
        )
        self.assertEqual(r["task_count"], 3)
        self.assertEqual(
            r["most_expensive"], "task2",
        )

    def test_generate_summary(self):
        r = self.reporter.generate_summary(
            total_cost=75.0,
            budget_limit=100.0,
            decisions=50,
        )
        self.assertEqual(r["type"], "summary")
        self.assertEqual(r["usage_pct"], 75.0)
        self.assertEqual(r["status"], "warning")

    def test_summary_good(self):
        r = self.reporter.generate_summary(
            total_cost=50.0,
            budget_limit=100.0,
            decisions=10,
        )
        self.assertEqual(r["status"], "good")

    def test_summary_critical(self):
        r = self.reporter.generate_summary(
            total_cost=95.0,
            budget_limit=100.0,
            decisions=10,
        )
        self.assertEqual(r["status"], "critical")

    def test_export_json(self):
        report = {"type": "test", "cost": 10.0}
        r = self.reporter.export_report(
            report, format="json",
        )
        self.assertTrue(r["exported"])
        self.assertEqual(r["format"], "json")

    def test_export_csv(self):
        report = {"type": "test", "cost": 10.0}
        r = self.reporter.export_report(
            report, format="csv",
        )
        self.assertTrue(r["exported"])
        self.assertIn("cost,10.0", r["content"])

    def test_export_text(self):
        report = {"type": "test", "cost": 10.0}
        r = self.reporter.export_report(
            report, format="text",
        )
        self.assertTrue(r["exported"])
        self.assertIn("cost: 10.0", r["content"])

    def test_report_count(self):
        self.assertEqual(
            self.reporter.report_count, 0,
        )
        self.reporter.generate_cost_report([])
        self.assertEqual(
            self.reporter.report_count, 1,
        )

    def test_get_reports(self):
        self.reporter.generate_cost_report([])
        self.reporter.generate_summary(
            10.0, 100.0, 5,
        )
        reports = self.reporter.get_reports()
        self.assertEqual(len(reports), 2)

    def test_get_reports_filtered(self):
        self.reporter.generate_cost_report([])
        self.reporter.generate_summary(
            10.0, 100.0, 5,
        )
        reports = self.reporter.get_reports(
            report_type="cost",
        )
        self.assertEqual(len(reports), 1)

    def test_cost_report_with_period(self):
        r = self.reporter.generate_cost_report(
            [], period="2026-Q1",
        )
        self.assertEqual(r["period"], "2026-Q1")


class TestCostEngineOrchestrator(
    unittest.TestCase,
):
    """CostEngineOrchestrator testleri."""

    def setUp(self):
        from app.core.costengine.costengine_orchestrator import (
            CostEngineOrchestrator,
        )
        self.orch = CostEngineOrchestrator(
            default_budget=100.0,
            pause_on_exceed=True,
            require_approval_above=50.0,
        )

    def test_init(self):
        self.assertIsNotNone(self.orch.calculator)
        self.assertIsNotNone(self.orch.catalog)
        self.assertIsNotNone(self.orch.budget)
        self.assertIsNotNone(self.orch.tracker)
        self.assertIsNotNone(
            self.orch.alternatives,
        )
        self.assertIsNotNone(self.orch.spending)
        self.assertIsNotNone(self.orch.optimizer)
        self.assertIsNotNone(self.orch.reporter)

    def test_pre_decision_cost(self):
        components = [
            {"type": "api_call", "service": "claude",
             "calls": 5, "rate": 0.01},
            {"type": "compute", "duration": 10.0},
        ]
        r = self.orch.pre_decision_cost(
            "d1", components,
        )
        self.assertGreater(
            r["estimated_cost"], 0,
        )
        self.assertTrue(r["proceed"])
        self.assertEqual(r["components"], 2)

    def test_pre_decision_cost_budget_check(self):
        self.orch.budget.create_budget(
            "b1", "Daily", 100.0,
        )
        self.orch.budget.allocate("b1", 95.0)
        components = [
            {"type": "time", "hours": 1.0},
        ]
        r = self.orch.pre_decision_cost(
            "d1", components, budget_id="b1",
        )
        self.assertFalse(r["budget_ok"])
        self.assertFalse(r["proceed"])

    def test_pre_decision_cost_approval(self):
        components = [
            {"type": "time", "hours": 10.0},
        ]
        r = self.orch.pre_decision_cost(
            "d1", components,
        )
        # 10 * 10 = 100 > 50 threshold
        self.assertEqual(
            r["spending_action"], "approve",
        )

    def test_track_decision(self):
        costs = [
            {"category": "api_call", "amount": 0.5},
            {"category": "compute", "amount": 0.3},
        ]
        r = self.orch.track_decision(
            "d1", system="agent", costs=costs,
        )
        self.assertTrue(r["completed"])
        self.assertAlmostEqual(
            r["total_cost"], 0.8, places=4,
        )

    def test_track_decision_with_budget(self):
        self.orch.budget.create_budget(
            "b1", "Daily", 100.0,
        )
        costs = [
            {"category": "api", "amount": 10.0},
        ]
        self.orch.track_decision(
            "d1", costs=costs, budget_id="b1",
        )
        b = self.orch.budget.get_budget("b1")
        self.assertEqual(b["spent"], 10.0)

    def test_get_status(self):
        s = self.orch.get_status()
        self.assertEqual(s["total_spent"], 0.0)
        self.assertEqual(
            s["decisions_tracked"], 0,
        )
        self.assertFalse(s["is_paused"])

    def test_get_status_after_work(self):
        self.orch.track_decision(
            "d1",
            costs=[
                {"category": "api", "amount": 5.0},
            ],
        )
        s = self.orch.get_status()
        self.assertGreater(s["total_spent"], 0)
        self.assertGreater(
            s["decisions_tracked"], 0,
        )

    def test_get_analytics(self):
        self.orch.track_decision(
            "d1", system="agent",
            costs=[
                {"category": "api", "amount": 5.0},
            ],
        )
        r = self.orch.get_analytics()
        self.assertIn("by_system", r)
        self.assertIn("by_category", r)
        self.assertIn("trend", r)

    def test_generate_report(self):
        self.orch.track_decision(
            "d1",
            costs=[
                {"category": "api", "amount": 5.0},
            ],
        )
        r = self.orch.generate_report(
            period="daily",
        )
        self.assertEqual(r["type"], "cost")

    def test_decisions_costed(self):
        self.assertEqual(
            self.orch.decisions_costed, 0,
        )
        self.orch.track_decision("d1")
        self.assertEqual(
            self.orch.decisions_costed, 1,
        )

    def test_full_pipeline(self):
        # Butce olustur
        self.orch.budget.create_budget(
            "daily", "Daily Budget", 100.0,
        )
        # On-maliyet
        pre = self.orch.pre_decision_cost(
            "d1",
            [{"type": "api_call", "service": "claude",
              "calls": 5, "rate": 0.01}],
            budget_id="daily",
        )
        self.assertTrue(pre["proceed"])
        # Takip et
        self.orch.track_decision(
            "d1", system="agent",
            costs=[
                {"category": "api_call",
                 "amount": 0.05},
            ],
            budget_id="daily",
        )
        # Durum
        s = self.orch.get_status()
        self.assertGreater(s["total_spent"], 0)
        # Rapor
        r = self.orch.generate_report()
        self.assertIsNotNone(r)

    def test_multiple_decisions(self):
        for i in range(5):
            self.orch.track_decision(
                f"d{i}",
                costs=[
                    {"category": "api",
                     "amount": float(i + 1)},
                ],
            )
        s = self.orch.get_status()
        self.assertEqual(
            s["decisions_tracked"], 5,
        )
        # 1+2+3+4+5 = 15
        self.assertAlmostEqual(
            s["total_spent"], 15.0, places=4,
        )


class TestCostEngineInit(unittest.TestCase):
    """CostEngine __init__ testleri."""

    def test_imports(self):
        from app.core.costengine import (
            AlternativeAnalyzer,
            BillingReporter,
            BudgetManager,
            CostCalculator,
            CostEngineOrchestrator,
            CostOptimizationAdvisor,
            DecisionCostTracker,
            PriceCatalog,
            SpendingController,
        )
        self.assertIsNotNone(AlternativeAnalyzer)
        self.assertIsNotNone(BillingReporter)
        self.assertIsNotNone(BudgetManager)
        self.assertIsNotNone(CostCalculator)
        self.assertIsNotNone(
            CostEngineOrchestrator,
        )
        self.assertIsNotNone(
            CostOptimizationAdvisor,
        )
        self.assertIsNotNone(DecisionCostTracker)
        self.assertIsNotNone(PriceCatalog)
        self.assertIsNotNone(SpendingController)

    def test_instantiate_all(self):
        from app.core.costengine import (
            AlternativeAnalyzer,
            BillingReporter,
            BudgetManager,
            CostCalculator,
            CostEngineOrchestrator,
            CostOptimizationAdvisor,
            DecisionCostTracker,
            PriceCatalog,
            SpendingController,
        )
        self.assertIsNotNone(CostCalculator())
        self.assertIsNotNone(PriceCatalog())
        self.assertIsNotNone(BudgetManager())
        self.assertIsNotNone(
            DecisionCostTracker(),
        )
        self.assertIsNotNone(
            AlternativeAnalyzer(),
        )
        self.assertIsNotNone(
            SpendingController(),
        )
        self.assertIsNotNone(
            CostOptimizationAdvisor(),
        )
        self.assertIsNotNone(BillingReporter())
        self.assertIsNotNone(
            CostEngineOrchestrator(),
        )


class TestCostEngineConfig(unittest.TestCase):
    """CostEngine config testleri."""

    def test_config_defaults(self):
        from app.config import settings
        self.assertTrue(
            settings.costengine_enabled,
        )
        self.assertEqual(
            settings.default_budget_daily, 100.0,
        )
        self.assertTrue(
            settings.pause_on_budget_exceed,
        )
        self.assertEqual(
            settings.cost_alert_threshold, 0.8,
        )
        self.assertEqual(
            settings.require_approval_above, 50.0,
        )


if __name__ == "__main__":
    unittest.main()
