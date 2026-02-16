"""ATLAS Physical Inventory & Asset Tracker testleri."""

import pytest

from app.core.assettrack.asset_registry import (
    AssetRegistry,
)
from app.core.assettrack.barcode_scanner import (
    BarcodeScanner,
)
from app.core.assettrack.stock_level_tracker import (
    StockLevelTracker,
)
from app.core.assettrack.maintenance_scheduler import (
    AssetMaintenanceScheduler,
)
from app.core.assettrack.depreciation_calculator import (
    DepreciationCalculator,
)
from app.core.assettrack.asset_location_mapper import (
    AssetLocationMapper,
)
from app.core.assettrack.reorder_trigger import (
    InventoryReorderTrigger,
)
from app.core.assettrack.inventory_auditor import (
    InventoryAuditor,
)
from app.core.assettrack.assettrack_orchestrator import (
    AssetTrackOrchestrator,
)


# ==================== AssetRegistry ====================


class TestRegisterAsset:
    """register_asset testleri."""

    def test_basic_register(self):
        ar = AssetRegistry()
        r = ar.register_asset(
            name="Laptop",
            category="electronics",
            purchase_cost=5000.0,
        )
        assert r["registered"] is True
        assert r["name"] == "Laptop"
        assert r["category"] == "electronics"

    def test_counter(self):
        ar = AssetRegistry()
        ar.register_asset(name="A1")
        ar.register_asset(name="A2")
        assert ar.asset_count == 2

    def test_with_serial(self):
        ar = AssetRegistry()
        r = ar.register_asset(
            name="Printer",
            serial_number="SN123",
        )
        assert r["registered"] is True


class TestCategorize:
    """categorize testleri."""

    def test_categorize(self):
        ar = AssetRegistry()
        a = ar.register_asset(name="Desk")
        r = ar.categorize(
            a["asset_id"],
            category="furniture",
            subcategory="office",
        )
        assert r["categorized"] is True
        assert r["category"] == "furniture"

    def test_unknown_asset(self):
        ar = AssetRegistry()
        r = ar.categorize("no", "other")
        assert r["found"] is False


class TestManageMetadata:
    """manage_metadata testleri."""

    def test_set_metadata(self):
        ar = AssetRegistry()
        a = ar.register_asset(name="Phone")
        r = ar.manage_metadata(
            a["asset_id"],
            key="color",
            value="black",
        )
        assert r["managed"] is True

    def test_delete_metadata(self):
        ar = AssetRegistry()
        a = ar.register_asset(name="Tab")
        ar.manage_metadata(
            a["asset_id"], "k", "v",
        )
        r = ar.manage_metadata(
            a["asset_id"],
            key="k",
            action="delete",
        )
        assert r["managed"] is True


class TestTrackLifecycle:
    """track_lifecycle testleri."""

    def test_status_change(self):
        ar = AssetRegistry()
        a = ar.register_asset(name="PC")
        r = ar.track_lifecycle(
            a["asset_id"],
            new_status="in_maintenance",
        )
        assert r["updated"] is True
        assert r["old_status"] == "active"
        assert r["new_status"] == "in_maintenance"

    def test_dispose(self):
        ar = AssetRegistry()
        a = ar.register_asset(name="Old")
        ar.track_lifecycle(
            a["asset_id"],
            new_status="disposed",
        )
        assert ar.disposed_count == 1


class TestAssignOwner:
    """assign_owner testleri."""

    def test_assign(self):
        ar = AssetRegistry()
        a = ar.register_asset(name="Chair")
        r = ar.assign_owner(
            a["asset_id"], "user_1",
        )
        assert r["assigned"] is True
        assert r["owner_id"] == "user_1"

    def test_unknown_asset(self):
        ar = AssetRegistry()
        r = ar.assign_owner("no", "u1")
        assert r["found"] is False


# ==================== BarcodeScanner ====================


class TestScanQr:
    """scan_qr testleri."""

    def test_basic_scan(self):
        bs = BarcodeScanner()
        r = bs.scan_qr("asset:A001")
        assert r["scanned"] is True
        assert r["valid"] is True
        assert r["parsed"]["type"] == "asset"

    def test_raw_data(self):
        bs = BarcodeScanner()
        r = bs.scan_qr("simpledata")
        assert r["parsed"]["type"] == "raw"

    def test_empty(self):
        bs = BarcodeScanner()
        r = bs.scan_qr("")
        assert r["valid"] is False


class TestParseBarcode:
    """parse_barcode testleri."""

    def test_code128(self):
        bs = BarcodeScanner()
        r = bs.parse_barcode(
            "ABC123", "code128",
        )
        assert r["parsed"] is True
        assert r["valid"] is True

    def test_ean13_valid(self):
        bs = BarcodeScanner()
        r = bs.parse_barcode(
            "1234567890123", "ean13",
        )
        assert r["valid"] is True

    def test_ean13_invalid(self):
        bs = BarcodeScanner()
        r = bs.parse_barcode(
            "short", "ean13",
        )
        assert r["valid"] is False


class TestBatchScan:
    """batch_scan testleri."""

    def test_batch(self):
        bs = BarcodeScanner()
        r = bs.batch_scan(
            ["A1", "A2", "A3"],
        )
        assert r["scanned"] is True
        assert r["total"] == 3
        assert r["valid"] == 3

    def test_mixed_validity(self):
        bs = BarcodeScanner()
        r = bs.batch_scan(
            ["valid", ""],
            barcode_format="code128",
        )
        assert r["valid"] == 1
        assert r["invalid"] == 1


class TestGenerateLabel:
    """generate_label testleri."""

    def test_generate(self):
        bs = BarcodeScanner()
        r = bs.generate_label(
            "asset_1", label_format="qr",
        )
        assert r["generated"] is True
        assert r["label_hash"]
        assert bs.label_count == 1


class TestValidateCode:
    """validate_code testleri."""

    def test_valid(self):
        bs = BarcodeScanner()
        r = bs.validate_code(
            "123456789012", "upc",
        )
        assert r["valid"] is True

    def test_invalid_upc(self):
        bs = BarcodeScanner()
        r = bs.validate_code(
            "short", "upc",
        )
        assert r["valid"] is False


# ==================== StockLevelTracker ====================


class TestTrackQuantity:
    """track_quantity testleri."""

    def test_basic_track(self):
        st = StockLevelTracker()
        r = st.track_quantity(
            "item1", 100, "main",
        )
        assert r["tracked"] is True
        assert r["quantity"] == 100

    def test_multi_location(self):
        st = StockLevelTracker()
        st.track_quantity("i1", 50, "wh1")
        st.track_quantity("i1", 30, "wh2")
        assert st.item_count == 2


class TestSetLevels:
    """set_levels testleri."""

    def test_normal(self):
        st = StockLevelTracker()
        st.track_quantity("i1", 50)
        r = st.set_levels(
            "i1", min_level=10,
            max_level=100,
        )
        assert r["set"] is True
        assert r["alert"] == "normal"

    def test_below_min(self):
        st = StockLevelTracker()
        st.track_quantity("i1", 5)
        r = st.set_levels(
            "i1", min_level=10,
        )
        assert r["alert"] == "below_minimum"

    def test_above_max(self):
        st = StockLevelTracker()
        st.track_quantity("i1", 200)
        r = st.set_levels(
            "i1", max_level=100,
        )
        assert r["alert"] == "above_maximum"


class TestLogMovement:
    """log_movement testleri."""

    def test_inbound(self):
        st = StockLevelTracker()
        st.track_quantity("i1", 50)
        r = st.log_movement(
            "i1", "inbound", 20,
        )
        assert r["logged"] is True
        assert r["new_quantity"] == 70

    def test_outbound(self):
        st = StockLevelTracker()
        st.track_quantity("i1", 50)
        r = st.log_movement(
            "i1", "outbound", 30,
        )
        assert r["new_quantity"] == 20

    def test_outbound_floor(self):
        st = StockLevelTracker()
        st.track_quantity("i1", 10)
        r = st.log_movement(
            "i1", "outbound", 50,
        )
        assert r["new_quantity"] == 0


class TestReserveStock:
    """reserve_stock testleri."""

    def test_reserve_ok(self):
        st = StockLevelTracker()
        st.track_quantity("i1", 100)
        r = st.reserve_stock(
            "i1", 50, "dept_a",
        )
        assert r["reserved"] is True

    def test_reserve_fail(self):
        st = StockLevelTracker()
        st.track_quantity("i1", 10)
        r = st.reserve_stock("i1", 50)
        assert r["reserved"] is False


class TestGetMultiLocation:
    """get_multi_location testleri."""

    def test_multi(self):
        st = StockLevelTracker()
        st.track_quantity("i1", 30, "wh1")
        st.track_quantity("i1", 20, "wh2")
        r = st.get_multi_location("i1")
        assert r["retrieved"] is True
        assert r["locations"] == 2
        assert r["total_quantity"] == 50


# ==================== AssetMaintenanceScheduler ====================


class TestScheduleMaintenance:
    """schedule_maintenance testleri."""

    def test_schedule(self):
        ms = AssetMaintenanceScheduler()
        r = ms.schedule_maintenance(
            "a1",
            maintenance_type="preventive",
            interval_days=90,
        )
        assert r["scheduled"] is True
        assert r["interval_days"] == 90
        assert ms.schedule_count == 1


class TestRunPreventive:
    """run_preventive testleri."""

    def test_run(self):
        ms = AssetMaintenanceScheduler()
        r = ms.run_preventive(
            "a1",
            tasks=["inspect", "clean"],
        )
        assert r["completed"] is True
        assert r["tasks_completed"] == 2
        assert ms.maintenance_count == 1


class TestGetServiceHistory:
    """get_service_history testleri."""

    def test_history(self):
        ms = AssetMaintenanceScheduler()
        ms.run_preventive("a1")
        ms.run_preventive("a1")
        r = ms.get_service_history("a1")
        assert r["retrieved"] is True
        assert r["entries"] == 2


class TestGenerateReminder:
    """generate_reminder testleri."""

    def test_reminder(self):
        ms = AssetMaintenanceScheduler()
        ms.schedule_maintenance(
            "a1", interval_days=0,
        )
        r = ms.generate_reminder(
            days_ahead=30,
        )
        assert r["generated"] is True
        assert r["reminders"] >= 1


class TestCoordinateVendor:
    """coordinate_vendor testleri."""

    def test_coordinate(self):
        ms = AssetMaintenanceScheduler()
        r = ms.coordinate_vendor(
            "v1", "a1", "repair",
        )
        assert r["coordinated"] is True


# ==================== DepreciationCalculator ====================


class TestCalculateDepreciation:
    """calculate_depreciation testleri."""

    def test_straight_line(self):
        dc = DepreciationCalculator()
        r = dc.calculate_depreciation(
            "a1",
            cost=10000.0,
            salvage_value=1000.0,
            useful_life_years=5,
            method="straight_line",
            year=1,
        )
        assert r["calculated"] is True
        assert r["annual_depreciation"] == 1800.0
        assert r["book_value"] == 8200.0

    def test_declining_balance(self):
        dc = DepreciationCalculator()
        r = dc.calculate_depreciation(
            "a1",
            cost=10000.0,
            salvage_value=0.0,
            useful_life_years=5,
            method="declining_balance",
            year=1,
        )
        assert r["calculated"] is True
        assert r["annual_depreciation"] == 4000.0

    def test_year3(self):
        dc = DepreciationCalculator()
        r = dc.calculate_depreciation(
            "a1",
            cost=10000.0,
            salvage_value=0.0,
            useful_life_years=5,
            method="straight_line",
            year=3,
        )
        assert r["accumulated"] == 6000.0
        assert r["book_value"] == 4000.0


class TestGetBookValue:
    """get_book_value testleri."""

    def test_found(self):
        dc = DepreciationCalculator()
        dc.calculate_depreciation(
            "a1", cost=5000.0,
        )
        r = dc.get_book_value("a1")
        assert r["found"] is True

    def test_not_found(self):
        dc = DepreciationCalculator()
        r = dc.get_book_value("none")
        assert r["found"] is False


class TestCalculateTax:
    """calculate_tax testleri."""

    def test_tax(self):
        dc = DepreciationCalculator()
        dc.calculate_depreciation(
            "a1",
            cost=10000.0,
            salvage_value=0.0,
            useful_life_years=5,
        )
        r = dc.calculate_tax(
            "a1", tax_rate=0.2,
        )
        assert r["calculated"] is True
        assert r["tax_benefit"] == 400.0


class TestHandleDisposal:
    """handle_disposal testleri."""

    def test_gain(self):
        dc = DepreciationCalculator()
        dc.calculate_depreciation(
            "a1",
            cost=10000.0,
            useful_life_years=5,
            year=5,
        )
        r = dc.handle_disposal(
            "a1", sale_price=2000.0,
        )
        assert r["disposed"] is True
        assert r["gain_loss"] == 2000.0

    def test_loss(self):
        dc = DepreciationCalculator()
        dc.calculate_depreciation(
            "a1",
            cost=10000.0,
            useful_life_years=5,
            year=1,
        )
        r = dc.handle_disposal(
            "a1", sale_price=5000.0,
        )
        assert r["disposed"] is True
        assert r["gain_loss"] == -3000.0


class TestGenerateReport:
    """generate_report testleri."""

    def test_report(self):
        dc = DepreciationCalculator()
        dc.calculate_depreciation(
            "a1", cost=10000.0,
        )
        dc.calculate_depreciation(
            "a2", cost=5000.0,
        )
        r = dc.generate_report()
        assert r["reported"] is True
        assert r["assets_calculated"] == 2
        assert r["total_cost"] == 15000.0


# ==================== AssetLocationMapper ====================


class TestTrackAssetLocation:
    """track_location testleri."""

    def test_track(self):
        lm = AssetLocationMapper()
        r = lm.track_location(
            "a1", "Warehouse A",
            building="B1",
            floor="1",
        )
        assert r["tracked"] is True
        assert lm.location_count == 1

    def test_update(self):
        lm = AssetLocationMapper()
        lm.track_location("a1", "WH-A")
        lm.track_location("a1", "WH-B")
        assert lm.location_count == 1


class TestLogTransfer:
    """log_transfer testleri."""

    def test_transfer(self):
        lm = AssetLocationMapper()
        lm.track_location("a1", "WH-A")
        r = lm.log_transfer(
            "a1", "WH-A", "WH-B",
            reason="reorg",
        )
        assert r["transferred"] is True
        assert lm.transfer_count == 1


class TestMapZone:
    """map_zone testleri."""

    def test_map(self):
        lm = AssetLocationMapper()
        r = lm.map_zone(
            "Loading Dock",
            capacity=50,
        )
        assert r["mapped"] is True
        assert r["capacity"] == 50


class TestSearchByLocation:
    """search_by_location testleri."""

    def test_search(self):
        lm = AssetLocationMapper()
        lm.track_location("a1", "WH-A")
        lm.track_location("a2", "WH-A")
        lm.track_location("a3", "WH-B")
        r = lm.search_by_location("WH-A")
        assert r["searched"] is True
        assert r["assets_found"] == 2


class TestGetVisualization:
    """get_visualization testleri."""

    def test_visualization(self):
        lm = AssetLocationMapper()
        lm.track_location("a1", "WH-A")
        lm.track_location("a2", "WH-B")
        r = lm.get_visualization()
        assert r["generated"] is True
        assert r["total_assets"] == 2
        assert r["locations"] == 2


# ==================== InventoryReorderTrigger ====================


class TestCalculateReorderPoint:
    """calculate_reorder_point testleri."""

    def test_calculate(self):
        rt = InventoryReorderTrigger()
        r = rt.calculate_reorder_point(
            "i1",
            daily_usage=5.0,
            lead_time_days=7,
            safety_stock=10,
        )
        assert r["calculated"] is True
        assert r["reorder_point"] == 45
        assert rt.point_count == 1


class TestCheckAndOrder:
    """check_and_order testleri."""

    def test_needs_order(self):
        rt = InventoryReorderTrigger()
        rt.calculate_reorder_point(
            "i1",
            daily_usage=5.0,
            lead_time_days=7,
            safety_stock=10,
        )
        r = rt.check_and_order("i1", 30)
        assert r["needs_order"] is True
        assert r["order_quantity"] == 70
        assert rt.order_count == 1

    def test_no_order_needed(self):
        rt = InventoryReorderTrigger()
        rt.calculate_reorder_point(
            "i1",
            daily_usage=5.0,
            lead_time_days=7,
            safety_stock=10,
        )
        r = rt.check_and_order("i1", 100)
        assert r["needs_order"] is False

    def test_unknown_item(self):
        rt = InventoryReorderTrigger()
        r = rt.check_and_order("no", 10)
        assert r["found"] is False


class TestSelectSupplier:
    """select_supplier testleri."""

    def test_select(self):
        rt = InventoryReorderTrigger()
        suppliers = [
            {"supplier_id": "s1", "price": 100},
            {"supplier_id": "s2", "price": 80},
        ]
        r = rt.select_supplier(
            "i1", suppliers,
        )
        assert r["selected"] is True
        assert r["supplier_id"] == "s2"

    def test_no_suppliers(self):
        rt = InventoryReorderTrigger()
        r = rt.select_supplier("i1")
        assert r["selected"] is False


class TestSetLeadTime:
    """set_lead_time testleri."""

    def test_update(self):
        rt = InventoryReorderTrigger()
        rt.calculate_reorder_point(
            "i1",
            daily_usage=5.0,
            lead_time_days=7,
            safety_stock=10,
        )
        r = rt.set_lead_time("i1", 14)
        assert r["updated"] is True
        assert r["new_reorder_point"] == 80


class TestGetOrderStatus:
    """get_order_status testleri."""

    def test_status(self):
        rt = InventoryReorderTrigger()
        rt.calculate_reorder_point(
            "i1", daily_usage=5.0,
            lead_time_days=7,
        )
        rt.check_and_order("i1", 5)
        r = rt.get_order_status("i1")
        assert r["retrieved"] is True
        assert r["total_orders"] == 1


# ==================== InventoryAuditor ====================


class TestScheduleAudit:
    """schedule_audit testleri."""

    def test_schedule(self):
        ia = InventoryAuditor()
        r = ia.schedule_audit(
            audit_type="full",
            location="WH-A",
            frequency="monthly",
        )
        assert r["scheduled"] is True
        assert r["frequency"] == "monthly"


class TestDetectDiscrepancy:
    """detect_discrepancy testleri."""

    def test_shortage(self):
        ia = InventoryAuditor()
        r = ia.detect_discrepancy(
            "i1", expected=100, actual=90,
        )
        assert r["detected"] is True
        assert r["type"] == "shortage"
        assert r["difference"] == -10
        assert ia.discrepancy_count == 1

    def test_surplus(self):
        ia = InventoryAuditor()
        r = ia.detect_discrepancy(
            "i1", expected=100, actual=110,
        )
        assert r["type"] == "surplus"

    def test_match(self):
        ia = InventoryAuditor()
        r = ia.detect_discrepancy(
            "i1", expected=100, actual=100,
        )
        assert r["type"] == "match"
        assert r["has_discrepancy"] is False


class TestReconcile:
    """reconcile testleri."""

    def test_reconcile(self):
        ia = InventoryAuditor()
        a = ia.schedule_audit()
        r = ia.reconcile(
            a["audit_id"],
            adjustments=[
                {"item": "i1", "adj": 5},
            ],
        )
        assert r["reconciled"] is True
        assert r["adjustments_made"] == 1
        assert ia.audit_count == 1

    def test_unknown_audit(self):
        ia = InventoryAuditor()
        r = ia.reconcile("no_audit")
        assert r["found"] is False


class TestGenerateAuditReport:
    """generate_audit_report testleri."""

    def test_report(self):
        ia = InventoryAuditor()
        a = ia.schedule_audit()
        r = ia.generate_audit_report(
            a["audit_id"],
        )
        assert r["generated"] is True


class TestCheckCompliance:
    """check_compliance testleri."""

    def test_compliant(self):
        ia = InventoryAuditor()
        a = ia.schedule_audit()
        ia.reconcile(a["audit_id"])
        r = ia.check_compliance(
            a["audit_id"],
            requirements=["accuracy"],
        )
        assert r["checked"] is True
        assert r["compliant"] is True

    def test_not_compliant(self):
        ia = InventoryAuditor()
        a = ia.schedule_audit()
        r = ia.check_compliance(
            a["audit_id"],
            requirements=["accuracy"],
        )
        assert r["compliant"] is False


# ==================== AssetTrackOrchestrator ====================


class TestRegisterAndTrack:
    """register_and_track testleri."""

    def test_pipeline(self):
        ato = AssetTrackOrchestrator()
        r = ato.register_and_track(
            name="Laptop",
            category="electronics",
            purchase_cost=5000.0,
            location="Office",
        )
        assert r["pipeline_complete"] is True
        assert r["registered"] is True
        assert r["tracked"] is True
        assert r["labeled"] is True
        assert ato.pipeline_count == 1

    def test_no_cost(self):
        ato = AssetTrackOrchestrator()
        r = ato.register_and_track(
            name="Pen", purchase_cost=0.0,
        )
        assert r["pipeline_complete"] is True


class TestFullAudit:
    """full_audit testleri."""

    def test_audit(self):
        ato = AssetTrackOrchestrator()
        r = ato.full_audit(
            location="WH-A",
        )
        assert r["completed"] is True
        assert r["audit_id"]


class TestAssetTrackAnalytics:
    """get_analytics testleri."""

    def test_analytics(self):
        ato = AssetTrackOrchestrator()
        ato.register_and_track(
            name="Server",
            purchase_cost=10000.0,
        )
        a = ato.get_analytics()
        assert a["pipelines_run"] == 1
        assert a["assets_registered"] >= 1
        assert a["locations_tracked"] >= 1
        assert a["calculations_done"] >= 1
        assert "scans_done" in a
        assert "audits_completed" in a
