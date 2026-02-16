"""ATLAS Autonomous Purchasing Agent testleri.

PriceComparator, SupplierFinder,
PurchaseDecisionEngine, OrderTracker,
QualityVerifier, PurchaseBudgetChecker,
ReorderPredictor, VendorManager,
PurchasingOrchestrator.
"""

import pytest

from app.core.purchasing.price_comparator import (
    PriceComparator,
)
from app.core.purchasing.supplier_finder import (
    SupplierFinder,
)
from app.core.purchasing.purchase_decision_engine import (
    PurchaseDecisionEngine,
)
from app.core.purchasing.order_tracker import (
    OrderTracker,
)
from app.core.purchasing.quality_verifier import (
    QualityVerifier,
)
from app.core.purchasing.budget_checker import (
    PurchaseBudgetChecker,
)
from app.core.purchasing.reorder_predictor import (
    ReorderPredictor,
)
from app.core.purchasing.vendor_manager import (
    VendorManager,
)
from app.core.purchasing.purchasing_orchestrator import (
    PurchasingOrchestrator,
)


# ── PriceComparator ─────────────────────


class TestPriceComparatorInit:
    def test_init(self):
        p = PriceComparator()
        assert p.comparison_count == 0
        assert p.deal_count == 0


class TestAddPrice:
    def test_basic(self):
        p = PriceComparator()
        r = p.add_price(
            "Widget", "SupA", 10.0,
        )
        assert r["added"] is True
        assert r["price"] == 10.0


class TestComparePrices:
    def test_multiple(self):
        p = PriceComparator()
        p.add_price("W", "A", 10.0)
        p.add_price("W", "B", 8.0)
        p.add_price("W", "C", 12.0)
        r = p.compare_prices("W")
        assert r["compared"] is True
        assert r["cheapest"] == "B"
        assert r["cheapest_price"] == 8.0
        assert r["spread"] == 4.0
        assert p.comparison_count == 1

    def test_no_prices(self):
        p = PriceComparator()
        r = p.compare_prices("none")
        assert r["compared"] is False


class TestGetHistorical:
    def test_with_data(self):
        p = PriceComparator()
        p.add_price("W", "A", 10.0)
        p.add_price("W", "B", 12.0)
        r = p.get_historical("W")
        assert r["count"] == 2
        assert r["avg_price"] == 11.0

    def test_empty(self):
        p = PriceComparator()
        r = p.get_historical("none")
        assert r["count"] == 0


class TestAnalyzeTrend:
    def test_increasing(self):
        p = PriceComparator()
        p.add_price("W", "A", 10.0)
        p.add_price("W", "A", 11.0)
        p.add_price("W", "A", 15.0)
        p.add_price("W", "A", 16.0)
        r = p.analyze_trend("W")
        assert r["trend"] == "increasing"

    def test_insufficient(self):
        p = PriceComparator()
        p.add_price("W", "A", 10.0)
        r = p.analyze_trend("W")
        assert r["trend"] == (
            "insufficient_data"
        )


class TestFindBestDeal:
    def test_found(self):
        p = PriceComparator()
        p.add_price("W", "A", 10.0)
        p.add_price("W", "B", 7.0)
        r = p.find_best_deal("W")
        assert r["found"] is True
        assert r["supplier"] == "B"
        assert r["price"] == 7.0
        assert p.deal_count == 1

    def test_empty(self):
        p = PriceComparator()
        r = p.find_best_deal("none")
        assert r["found"] is False


class TestAlertOnDrop:
    def test_alert(self):
        p = PriceComparator()
        p.add_price("W", "A", 100.0)
        p.add_price("W", "A", 80.0)
        r = p.alert_on_drop("W")
        assert r["alert"] is True
        assert r["drop_pct"] == 20.0

    def test_no_alert(self):
        p = PriceComparator()
        p.add_price("W", "A", 100.0)
        p.add_price("W", "A", 98.0)
        r = p.alert_on_drop("W")
        assert r["alert"] is False


# ── SupplierFinder ──────────────────────


class TestSupplierFinderInit:
    def test_init(self):
        s = SupplierFinder()
        assert s.supplier_count == 0
        assert s.search_count == 0


class TestRegisterSupplier:
    def test_basic(self):
        s = SupplierFinder()
        r = s.register_supplier(
            "Acme", location="Turkey",
            categories=["widgets"],
        )
        assert r["registered"] is True
        assert s.supplier_count == 1


class TestSearchSupplier:
    def test_by_category(self):
        s = SupplierFinder()
        s.register_supplier(
            "A", categories=["widgets"],
        )
        s.register_supplier(
            "B", categories=["bolts"],
        )
        r = s.search(category="widgets")
        assert r["count"] == 1
        assert s.search_count == 1

    def test_by_location(self):
        s = SupplierFinder()
        s.register_supplier(
            "A", location="Turkey",
        )
        r = s.search(location="Turkey")
        assert r["count"] == 1

    def test_empty(self):
        s = SupplierFinder()
        r = s.search(category="none")
        assert r["count"] == 0


class TestQualifySupplier:
    def test_platinum(self):
        s = SupplierFinder()
        r = s.register_supplier("A")
        sid = r["supplier_id"]
        q = s.qualify_supplier(
            sid, quality_score=95,
            delivery_score=92,
            price_score=88,
        )
        assert q["qualified"] is True
        assert q["tier"] == "platinum"

    def test_not_found(self):
        s = SupplierFinder()
        q = s.qualify_supplier("none")
        assert q["qualified"] is False


class TestRateReliability:
    def test_excellent(self):
        s = SupplierFinder()
        r = s.register_supplier("A")
        sid = r["supplier_id"]
        rel = s.rate_reliability(
            sid, on_time_pct=98,
            defect_rate=1, response_time_hrs=2,
        )
        assert rel["level"] == "excellent"


class TestFilterByLocation:
    def test_found(self):
        s = SupplierFinder()
        s.register_supplier(
            "A", location="Istanbul",
        )
        r = s.filter_by_location("Istanbul")
        assert r["count"] == 1


class TestCheckCapacity:
    def test_sufficient(self):
        s = SupplierFinder()
        r = s.register_supplier(
            "A", capacity=1000,
        )
        c = s.check_capacity(
            r["supplier_id"], required=500,
        )
        assert c["sufficient"] is True
        assert c["surplus"] == 500

    def test_insufficient(self):
        s = SupplierFinder()
        r = s.register_supplier(
            "A", capacity=100,
        )
        c = s.check_capacity(
            r["supplier_id"], required=500,
        )
        assert c["sufficient"] is False


# ── PurchaseDecisionEngine ──────────────


class TestDecisionEngineInit:
    def test_init(self):
        d = PurchaseDecisionEngine()
        assert d.decision_count == 0
        assert d.approval_count == 0


class TestSetCriteria:
    def test_basic(self):
        d = PurchaseDecisionEngine()
        r = d.set_criteria(
            "fast",
            weights={"delivery": 0.6,
                      "price": 0.4},
        )
        assert r["set"] is True
        assert r["factor_count"] == 2


class TestScoreOptions:
    def test_basic(self):
        d = PurchaseDecisionEngine()
        r = d.score_options(
            options=[
                {"name": "A", "price": 90,
                 "quality": 80},
                {"name": "B", "price": 70,
                 "quality": 95},
            ],
        )
        assert r["count"] == 2
        assert r["best"] is not None

    def test_empty(self):
        d = PurchaseDecisionEngine()
        r = d.score_options()
        assert r["best"] is None


class TestCheckBudgetDecision:
    def test_within(self):
        d = PurchaseDecisionEngine()
        r = d.check_budget(
            amount=500, budget_limit=1000,
        )
        assert r["within_budget"] is True
        assert r["status"] == "within"

    def test_exceeded(self):
        d = PurchaseDecisionEngine()
        r = d.check_budget(
            amount=500, budget_limit=300,
        )
        assert r["within_budget"] is False
        assert r["status"] == "exceeded"


class TestRouteApproval:
    def test_auto(self):
        d = PurchaseDecisionEngine()
        r = d.route_approval(50)
        assert r["approval_level"] == "auto"
        assert r["auto_approved"] is True

    def test_executive(self):
        d = PurchaseDecisionEngine()
        r = d.route_approval(50000)
        assert r["approval_level"] == (
            "executive"
        )
        assert r["auto_approved"] is False


class TestDecisionRecommend:
    def test_basic(self):
        d = PurchaseDecisionEngine()
        r = d.recommend(
            "Widget",
            options=[
                {"name": "A", "price": 90},
            ],
        )
        assert r["recommendation"] is not None
        assert d.decision_count == 1


# ── OrderTracker ────────────────────────


class TestOrderTrackerInit:
    def test_init(self):
        o = OrderTracker()
        assert o.order_count == 0
        assert o.delivery_count == 0


class TestCreateOrder:
    def test_basic(self):
        o = OrderTracker()
        r = o.create_order(
            "Widget", "SupA",
            quantity=10, unit_price=5.0,
        )
        assert r["created"] is True
        assert r["total"] == 50.0
        assert o.order_count == 1


class TestUpdateStatus:
    def test_delivered(self):
        o = OrderTracker()
        r = o.create_order("W", "S")
        u = o.update_status(
            r["order_id"], "delivered",
        )
        assert u["updated"] is True
        assert o.delivery_count == 1

    def test_missing(self):
        o = OrderTracker()
        u = o.update_status("none", "x")
        assert u["updated"] is False


class TestTrackShipment:
    def test_basic(self):
        o = OrderTracker()
        r = o.create_order("W", "S")
        s = o.track_shipment(
            r["order_id"],
            carrier="DHL",
            tracking_number="TR123",
            estimated_days=5,
        )
        assert s["tracked"] is True

    def test_missing(self):
        o = OrderTracker()
        s = o.track_shipment("none")
        assert s["tracked"] is False


class TestPredictDelivery:
    def test_with_shipment(self):
        o = OrderTracker()
        r = o.create_order("W", "S")
        o.track_shipment(
            r["order_id"],
            estimated_days=3,
        )
        p = o.predict_delivery(
            r["order_id"],
        )
        assert p["predicted"] is True
        assert p["confidence"] == "high"

    def test_no_shipment(self):
        o = OrderTracker()
        r = o.create_order("W", "S")
        p = o.predict_delivery(
            r["order_id"],
        )
        assert p["predicted"] is False


class TestDetectIssues:
    def test_no_issues(self):
        o = OrderTracker()
        r = o.create_order("W", "S")
        d = o.detect_issues(r["order_id"])
        assert d["checked"] is True

    def test_missing(self):
        o = OrderTracker()
        d = o.detect_issues("none")
        assert d["checked"] is False


class TestGetHistory:
    def test_filter(self):
        o = OrderTracker()
        o.create_order("W", "S1")
        o.create_order("W", "S2")
        h = o.get_history(supplier="S1")
        assert len(h) == 1


# ── QualityVerifier ─────────────────────


class TestQualityVerifierInit:
    def test_init(self):
        q = QualityVerifier()
        assert q.inspection_count == 0
        assert q.return_count == 0


class TestSetQualityCriteria:
    def test_basic(self):
        q = QualityVerifier()
        r = q.set_criteria("electronics")
        assert r["set"] is True
        assert r["criteria_count"] >= 4


class TestInspect:
    def test_passed(self):
        q = QualityVerifier()
        r = q.inspect(
            "ord_1",
            scores={
                "appearance": 85,
                "functionality": 90,
            },
        )
        assert r["passed"] is True
        assert r["grade"] == "good"
        assert q.inspection_count == 1

    def test_rejected(self):
        q = QualityVerifier()
        r = q.inspect(
            "ord_1",
            scores={
                "appearance": 20,
                "functionality": 30,
            },
        )
        assert r["passed"] is False
        assert r["grade"] == "rejected"


class TestReportIssue:
    def test_basic(self):
        q = QualityVerifier()
        r = q.report_issue(
            "ord_1",
            issue_type="defect",
            severity="high",
        )
        assert r["reported"] is True


class TestGiveFeedback:
    def test_positive(self):
        q = QualityVerifier()
        r = q.give_feedback(
            "sup_1", "ord_1", rating=4.5,
        )
        assert r["level"] == "positive"
        assert r["submitted"] is True

    def test_negative(self):
        q = QualityVerifier()
        r = q.give_feedback(
            "sup_1", "ord_1", rating=1.5,
        )
        assert r["level"] == "negative"


class TestHandleReturn:
    def test_basic(self):
        q = QualityVerifier()
        r = q.handle_return(
            "ord_1",
            reason="Defective",
            refund_amount=50.0,
        )
        assert r["processed"] is True
        assert q.return_count == 1


# ── PurchaseBudgetChecker ───────────────


class TestBudgetCheckerInit:
    def test_init(self):
        b = PurchaseBudgetChecker()
        assert b.check_count == 0
        assert b.alert_count == 0


class TestSetBudgetLimit:
    def test_basic(self):
        b = PurchaseBudgetChecker()
        r = b.set_limit(
            "supplies", 5000.0,
        )
        assert r["set"] is True


class TestRecordSpending:
    def test_basic(self):
        b = PurchaseBudgetChecker()
        b.set_limit("supplies", 5000.0)
        r = b.record_spending(
            "supplies", 500.0,
        )
        assert r["recorded"] is True


class TestCheckBudget:
    def test_within(self):
        b = PurchaseBudgetChecker()
        b.set_limit("supplies", 5000.0)
        r = b.check_budget(
            "supplies", 1000.0,
        )
        assert r["status"] == "within"
        assert r["approved"] is True
        assert b.check_count == 1

    def test_exceeded(self):
        b = PurchaseBudgetChecker()
        b.set_limit("supplies", 1000.0)
        b.record_spending("supplies", 900.0)
        r = b.check_budget(
            "supplies", 200.0,
        )
        assert r["status"] == "exceeded"
        assert r["approved"] is False

    def test_no_budget(self):
        b = PurchaseBudgetChecker()
        r = b.check_budget("none")
        assert r["checked"] is False


class TestApprovalThreshold:
    def test_auto(self):
        b = PurchaseBudgetChecker()
        r = b.get_approval_threshold(50)
        assert r["auto_approved"] is True

    def test_executive(self):
        b = PurchaseBudgetChecker()
        r = b.get_approval_threshold(10000)
        assert r["approval_level"] == (
            "executive"
        )


class TestForecastImpact:
    def test_safe(self):
        b = PurchaseBudgetChecker()
        b.set_limit("supplies", 10000.0)
        r = b.forecast_impact(
            "supplies",
            planned_purchases=[
                1000.0, 2000.0,
            ],
        )
        assert r["forecasted"] is True
        assert r["status"] == "safe"

    def test_not_found(self):
        b = PurchaseBudgetChecker()
        r = b.forecast_impact("none")
        assert r["forecasted"] is False


class TestGenerateBudgetAlert:
    def test_alert(self):
        b = PurchaseBudgetChecker()
        b.set_limit("supplies", 1000.0)
        b.record_spending("supplies", 900.0)
        r = b.generate_alert("supplies")
        assert r["alert"] is True
        assert b.alert_count >= 1

    def test_no_alert(self):
        b = PurchaseBudgetChecker()
        b.set_limit("supplies", 10000.0)
        r = b.generate_alert("supplies")
        assert r["alert"] is False


# ── ReorderPredictor ────────────────────


class TestReorderPredictorInit:
    def test_init(self):
        r = ReorderPredictor()
        assert r.prediction_count == 0
        assert r.auto_order_count == 0


class TestTrackItem:
    def test_basic(self):
        r = ReorderPredictor()
        res = r.track_item(
            "Widget", current_stock=100,
            lead_time_days=7,
        )
        assert res["tracked"] is True


class TestRecordConsumption:
    def test_basic(self):
        r = ReorderPredictor()
        res = r.record_consumption(
            "Widget", daily_usage=10.0,
        )
        assert res["recorded"] is True
        assert res["data_points"] == 1


class TestAnalyzeConsumption:
    def test_with_data(self):
        r = ReorderPredictor()
        r.record_consumption("W", 10.0)
        r.record_consumption("W", 12.0)
        r.record_consumption("W", 8.0)
        res = r.analyze_consumption("W")
        assert res["analyzed"] is True
        assert res["avg_daily"] == 10.0

    def test_empty(self):
        r = ReorderPredictor()
        res = r.analyze_consumption("none")
        assert res["analyzed"] is False


class TestCalculateLeadTime:
    def test_with_buffer(self):
        r = ReorderPredictor()
        r.track_item("W", lead_time_days=5)
        res = r.calculate_lead_time(
            "W", buffer_days=3,
        )
        assert res["total_lead_days"] == 8


class TestCalculateReorderPoint:
    def test_calculated(self):
        r = ReorderPredictor()
        r.track_item("W", lead_time_days=7)
        r.record_consumption("W", 10.0)
        r.record_consumption("W", 12.0)
        res = r.calculate_reorder_point("W")
        assert res["calculated"] is True
        assert res["reorder_point"] > 0
        assert r.prediction_count == 1

    def test_no_data(self):
        r = ReorderPredictor()
        res = r.calculate_reorder_point("x")
        assert res["calculated"] is False


class TestCalculateSafetyStock:
    def test_basic(self):
        r = ReorderPredictor()
        r.track_item("W", lead_time_days=7)
        r.record_consumption("W", 10.0)
        r.record_consumption("W", 15.0)
        res = r.calculate_safety_stock("W")
        assert res["calculated"] is True
        assert res["safety_stock"] >= 0

    def test_empty(self):
        r = ReorderPredictor()
        res = r.calculate_safety_stock("x")
        assert res["calculated"] is False


class TestAutoReorder:
    def test_needs_reorder(self):
        r = ReorderPredictor()
        r.track_item(
            "W", current_stock=5,
            lead_time_days=7,
            min_order_qty=50,
        )
        r.record_consumption("W", 10.0)
        r.record_consumption("W", 12.0)
        res = r.auto_reorder("W")
        assert res["ordered"] is True
        assert r.auto_order_count == 1

    def test_stock_sufficient(self):
        r = ReorderPredictor()
        r.track_item(
            "W", current_stock=10000,
            lead_time_days=7,
        )
        r.record_consumption("W", 10.0)
        r.record_consumption("W", 12.0)
        res = r.auto_reorder("W")
        assert res["ordered"] is False

    def test_not_tracked(self):
        r = ReorderPredictor()
        res = r.auto_reorder("x")
        assert res["ordered"] is False


# ── VendorManager ───────────────────────


class TestVendorManagerInit:
    def test_init(self):
        v = VendorManager()
        assert v.vendor_count == 0
        assert v.contract_count == 0


class TestCreateProfile:
    def test_basic(self):
        v = VendorManager()
        r = v.create_profile(
            "Acme Corp",
            location="Istanbul",
            categories=["widgets"],
        )
        assert r["created"] is True
        assert v.vendor_count == 1


class TestTrackVendorPerformance:
    def test_excellent(self):
        v = VendorManager()
        r = v.create_profile("Acme")
        vid = r["vendor_id"]
        p = v.track_performance(
            vid, quality=90, delivery=95,
            price=85, communication=90,
        )
        assert p["tracked"] is True
        assert p["level"] == "excellent"

    def test_missing(self):
        v = VendorManager()
        p = v.track_performance("none")
        assert p["tracked"] is False


class TestManageContract:
    def test_basic(self):
        v = VendorManager()
        r = v.create_profile("Acme")
        c = v.manage_contract(
            r["vendor_id"],
            value=50000.0,
        )
        assert c["created"] is True
        assert v.contract_count == 1


class TestScoreRelationship:
    def test_with_data(self):
        v = VendorManager()
        r = v.create_profile("Acme")
        vid = r["vendor_id"]
        v.track_performance(
            vid, quality=85, delivery=80,
            price=75, communication=80,
        )
        v.manage_contract(vid, value=10000)
        s = v.score_relationship(vid)
        assert s["scored"] is True
        assert s["level"] in (
            "strategic", "preferred",
            "approved", "probation",
        )

    def test_missing(self):
        v = VendorManager()
        s = v.score_relationship("none")
        assert s["scored"] is False


class TestLogNegotiation:
    def test_basic(self):
        v = VendorManager()
        r = v.log_negotiation(
            "vnd_1",
            topic="Price reduction",
            outcome="5% discount",
            savings=500.0,
        )
        assert r["logged"] is True


# ── PurchasingOrchestrator ──────────────


class TestPurchOrchInit:
    def test_init(self):
        o = PurchasingOrchestrator()
        assert o.purchase_count == 0
        assert o.pipeline_count == 0


class TestRunPurchasePipeline:
    def test_basic(self):
        o = PurchasingOrchestrator()
        o.prices.add_price(
            "Widget", "SupA", 5.0,
        )
        r = o.run_purchase_pipeline(
            "Widget", quantity=10,
        )
        assert r["pipeline_complete"] is True
        assert r["total_cost"] == 50.0
        assert o.pipeline_count == 1

    def test_no_prices(self):
        o = PurchasingOrchestrator()
        r = o.run_purchase_pipeline(
            "Unknown", max_price=10.0,
        )
        assert r["pipeline_complete"] is True


class TestAutonomousPurchase:
    def test_auto_approved(self):
        o = PurchasingOrchestrator()
        o.prices.add_price(
            "Pen", "SupA", 2.0,
        )
        r = o.autonomous_purchase(
            "Pen", quantity=5,
            auto_limit=100.0,
        )
        assert r["purchased"] is True
        assert r["auto_approved"] is True

    def test_exceeds_limit(self):
        o = PurchasingOrchestrator()
        o.prices.add_price(
            "Server", "SupA", 5000.0,
        )
        r = o.autonomous_purchase(
            "Server", auto_limit=100.0,
        )
        assert r["purchased"] is False
        assert r["auto_approved"] is False


class TestPurchOrchAnalytics:
    def test_basic(self):
        o = PurchasingOrchestrator()
        o.prices.add_price("W", "A", 5.0)
        o.run_purchase_pipeline("W")
        a = o.get_analytics()
        assert a["pipelines_run"] == 1
        assert a["orders"] >= 1

    def test_empty(self):
        o = PurchasingOrchestrator()
        a = o.get_analytics()
        assert a["purchases_made"] == 0


# ── Config ──────────────────────────────


class TestPurchasingConfig:
    def test_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.purchasing_enabled is True
        assert s.auto_purchase_limit == 100.0
        assert s.reorder_auto is True
        assert s.quality_check is True
        assert s.multi_supplier is True


# ── __init__ imports ────────────────────


class TestPurchasingImports:
    def test_all_imports(self):
        from app.core.purchasing import (
            OrderTracker,
            PriceComparator,
            PurchaseBudgetChecker,
            PurchaseDecisionEngine,
            PurchasingOrchestrator,
            QualityVerifier,
            ReorderPredictor,
            SupplierFinder,
            VendorManager,
        )
        assert OrderTracker is not None
        assert PriceComparator is not None
        assert PurchaseBudgetChecker is not None
        assert PurchaseDecisionEngine is not None
        assert PurchasingOrchestrator is not None
        assert QualityVerifier is not None
        assert ReorderPredictor is not None
        assert SupplierFinder is not None
        assert VendorManager is not None
