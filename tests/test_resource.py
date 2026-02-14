"""Resource Management sistemi testleri."""

import pytest

from app.models.resource import (
    AlertSeverity,
    CostCategory,
    CostRecord,
    OptimizationAction,
    QuotaRecord,
    ResourceAlert,
    ResourceMetric,
    ResourceSnapshot,
    ResourceStatus,
    ResourceType,
    ScaleDirection,
)
from app.core.resource.cpu_manager import CPUManager
from app.core.resource.memory_manager import MemoryManager
from app.core.resource.storage_manager import StorageManager
from app.core.resource.network_manager import NetworkManager
from app.core.resource.api_quota_manager import APIQuotaManager
from app.core.resource.cost_tracker import CostTracker
from app.core.resource.capacity_planner import CapacityPlanner
from app.core.resource.resource_optimizer import ResourceOptimizer
from app.core.resource.resource_orchestrator import ResourceOrchestrator


# ── Model Testleri ──────────────────────────────────────────


class TestModels:
    """Veri modeli testleri."""

    def test_resource_type_values(self):
        assert ResourceType.CPU == "cpu"
        assert ResourceType.MEMORY == "memory"
        assert ResourceType.STORAGE == "storage"
        assert ResourceType.NETWORK == "network"
        assert ResourceType.API == "api"

    def test_resource_status_values(self):
        assert ResourceStatus.NORMAL == "normal"
        assert ResourceStatus.WARNING == "warning"
        assert ResourceStatus.CRITICAL == "critical"

    def test_alert_severity_values(self):
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.CRITICAL == "critical"

    def test_cost_category_values(self):
        assert CostCategory.COMPUTE == "compute"
        assert CostCategory.API_CALL == "api_call"

    def test_scale_direction_values(self):
        assert ScaleDirection.UP == "up"
        assert ScaleDirection.DOWN == "down"
        assert ScaleDirection.NONE == "none"

    def test_optimization_action_values(self):
        assert OptimizationAction.SCALE_UP == "scale_up"
        assert OptimizationAction.CACHE == "cache"
        assert OptimizationAction.EVICT == "evict"

    def test_resource_metric_defaults(self):
        m = ResourceMetric()
        assert len(m.metric_id) == 8
        assert m.value == 0.0

    def test_cost_record_defaults(self):
        r = CostRecord()
        assert r.amount == 0.0
        assert r.currency == "USD"

    def test_quota_record_defaults(self):
        q = QuotaRecord()
        assert q.limit == 0
        assert q.used == 0

    def test_resource_alert_defaults(self):
        a = ResourceAlert()
        assert a.resolved is False

    def test_resource_snapshot_defaults(self):
        s = ResourceSnapshot()
        assert s.cpu_usage == 0.0
        assert s.total_cost == 0.0


# ── CPUManager Testleri ─────────────────────────────────────


class TestCPUManager:
    """CPU yoneticisi testleri."""

    @pytest.fixture()
    def cpu(self):
        return CPUManager(threshold=0.8, total_cores=4)

    def test_init(self, cpu):
        assert cpu.total_cores == 4
        assert cpu.process_count == 0

    def test_record_usage_normal(self, cpu):
        status = cpu.record_usage(0.5)
        assert status == ResourceStatus.NORMAL

    def test_record_usage_warning(self, cpu):
        status = cpu.record_usage(0.85)
        assert status == ResourceStatus.WARNING

    def test_record_usage_critical(self, cpu):
        status = cpu.record_usage(0.96)
        assert status == ResourceStatus.CRITICAL

    def test_register_process(self, cpu):
        proc = cpu.register_process("worker", priority=8)
        assert proc["name"] == "worker"
        assert cpu.process_count == 1

    def test_set_priority(self, cpu):
        cpu.register_process("worker")
        assert cpu.set_priority("worker", 10) is True

    def test_set_priority_nonexistent(self, cpu):
        assert cpu.set_priority("ghost", 5) is False

    def test_allocate_core(self, cpu):
        cpu.register_process("worker")
        assert cpu.allocate_core("worker", 0) is True
        assert cpu.allocated_cores == 1

    def test_allocate_core_invalid(self, cpu):
        cpu.register_process("worker")
        assert cpu.allocate_core("worker", 10) is False

    def test_allocate_core_occupied(self, cpu):
        cpu.register_process("a")
        cpu.register_process("b")
        cpu.allocate_core("a", 0)
        assert cpu.allocate_core("b", 0) is False

    def test_release_core(self, cpu):
        cpu.register_process("worker")
        cpu.allocate_core("worker", 0)
        assert cpu.release_core(0) is True
        assert cpu.allocated_cores == 0

    def test_release_core_nonexistent(self, cpu):
        assert cpu.release_core(99) is False

    def test_throttle(self, cpu):
        cpu.register_process("worker")
        assert cpu.throttle("worker") is True
        assert cpu.throttled_count == 1

    def test_unthrottle(self, cpu):
        cpu.register_process("worker")
        cpu.throttle("worker")
        assert cpu.unthrottle("worker") is True
        assert cpu.throttled_count == 0

    def test_throttle_nonexistent(self, cpu):
        assert cpu.throttle("ghost") is False

    def test_load_balance_suggestion(self, cpu):
        cpu.register_process("a", priority=10)
        cpu.register_process("b", priority=5)
        suggestions = cpu.get_load_balance_suggestion()
        assert len(suggestions) == 2
        assert suggestions[0]["priority"] >= suggestions[1]["priority"]

    def test_avg_usage(self, cpu):
        cpu.record_usage(0.5)
        cpu.record_usage(0.7)
        avg = cpu.get_avg_usage(10)
        assert abs(avg - 0.6) < 0.01

    def test_avg_usage_empty(self, cpu):
        assert cpu.get_avg_usage() == 0.0


# ── MemoryManager Testleri ──────────────────────────────────


class TestMemoryManager:
    """Bellek yoneticisi testleri."""

    @pytest.fixture()
    def mm(self):
        return MemoryManager(threshold=0.8, total_mb=1024)

    def test_init(self, mm):
        assert mm.available_mb == 1024.0
        assert mm.allocation_count == 0

    def test_record_usage_normal(self, mm):
        status = mm.record_usage(500.0)
        assert status == ResourceStatus.NORMAL

    def test_record_usage_warning(self, mm):
        status = mm.record_usage(850.0)
        assert status == ResourceStatus.WARNING

    def test_record_usage_critical(self, mm):
        status = mm.record_usage(980.0)
        assert status == ResourceStatus.CRITICAL

    def test_allocate(self, mm):
        assert mm.allocate("buffer", 100.0) is True
        assert mm.allocation_count == 1
        assert mm.used_mb == 100.0

    def test_allocate_exceed(self, mm):
        assert mm.allocate("huge", 2000.0) is False

    def test_release(self, mm):
        mm.allocate("buffer", 100.0)
        assert mm.release("buffer") is True
        assert mm.allocation_count == 0

    def test_release_nonexistent(self, mm):
        assert mm.release("ghost") is False

    def test_trigger_gc(self, mm):
        mm.allocate("small", 0.5)
        mm.allocate("big", 100.0)
        result = mm.trigger_gc()
        assert result["removed_count"] == 1
        assert mm.gc_count == 1

    def test_set_limit(self, mm):
        mm.allocate("buffer", 50.0)
        assert mm.set_limit("buffer", 100.0) is True

    def test_set_limit_nonexistent(self, mm):
        assert mm.set_limit("ghost", 100.0) is False

    def test_detect_leaks(self, mm):
        mm.allocate("leaky", 200.0)
        mm.set_limit("leaky", 100.0)
        leaks = mm.detect_leaks()
        assert len(leaks) == 1
        assert mm.leak_count == 1

    def test_no_leaks(self, mm):
        mm.allocate("ok", 50.0)
        mm.set_limit("ok", 100.0)
        assert mm.detect_leaks() == []

    def test_cache_put(self, mm):
        assert mm.cache_put("key1", 10.0) is True
        assert mm.cache_count == 1

    def test_cache_evict(self, mm):
        mm.cache_put("low", 10.0, priority=1)
        mm.cache_put("high", 10.0, priority=10)
        evicted = mm.cache_evict()
        assert evicted == 1
        assert mm.cache_count == 1

    def test_cache_evict_target(self, mm):
        mm.cache_put("a", 5.0, priority=1)
        mm.cache_put("b", 5.0, priority=2)
        mm.cache_put("c", 5.0, priority=10)
        evicted = mm.cache_evict(target_mb=8.0)
        assert evicted == 2

    def test_usage_ratio(self, mm):
        mm.record_usage(512.0)
        assert abs(mm.get_usage_ratio() - 0.5) < 0.01


# ── StorageManager Testleri ─────────────────────────────────


class TestStorageManager:
    """Depolama yoneticisi testleri."""

    @pytest.fixture()
    def sm(self):
        return StorageManager(threshold=0.8)

    def test_init(self, sm):
        assert sm.volume_count == 0

    def test_add_volume(self, sm):
        vol = sm.add_volume("sda1", 500.0, 200.0)
        assert vol["name"] == "sda1"
        assert sm.volume_count == 1

    def test_check_volume_normal(self, sm):
        sm.add_volume("sda1", 500.0, 200.0)
        assert sm.check_volume("sda1") == ResourceStatus.NORMAL

    def test_check_volume_warning(self, sm):
        sm.add_volume("sda1", 100.0, 85.0)
        assert sm.check_volume("sda1") == ResourceStatus.WARNING

    def test_check_volume_critical(self, sm):
        sm.add_volume("sda1", 100.0, 96.0)
        assert sm.check_volume("sda1") == ResourceStatus.CRITICAL

    def test_check_nonexistent_volume(self, sm):
        assert sm.check_volume("ghost") == ResourceStatus.NORMAL

    def test_register_file(self, sm):
        f = sm.register_file("/data/log.txt", 50.0, age_days=10)
        assert f["path"] == "/data/log.txt"
        assert sm.file_count == 1

    def test_cleanup_old_files(self, sm):
        sm.register_file("/old.log", 100.0, age_days=60)
        sm.register_file("/new.log", 50.0, age_days=5)
        result = sm.cleanup_old_files(max_age_days=30)
        assert result["removed_count"] == 1
        assert result["freed_mb"] == 100.0

    def test_archive_files(self, sm):
        sm.register_file("/data/a.csv", 100.0, category="data")
        sm.register_file("/data/b.csv", 100.0, category="data")
        sm.register_file("/log/x.log", 50.0, category="log")
        archive = sm.archive_files("data")
        assert archive["file_count"] == 2
        assert archive["savings_mb"] > 0
        assert sm.archive_count == 1

    def test_set_quota(self, sm):
        sm.set_quota("user1", 10.0)
        result = sm.check_quota("user1", 5.0)
        assert result["within_quota"] is True

    def test_check_quota_exceeded(self, sm):
        sm.set_quota("user1", 10.0)
        result = sm.check_quota("user1", 15.0)
        assert result["within_quota"] is False

    def test_check_quota_no_quota(self, sm):
        result = sm.check_quota("user1", 5.0)
        assert result["no_quota"] is True

    def test_compress_estimate(self, sm):
        sm.register_file("/big.dat", 200.0)
        est = sm.compress_estimate("/big.dat", 0.5)
        assert est is not None
        assert est["estimated_mb"] == 100.0

    def test_compress_nonexistent(self, sm):
        assert sm.compress_estimate("/ghost") is None

    def test_cleaned_mb(self, sm):
        sm.register_file("/old.log", 100.0, age_days=60)
        sm.cleanup_old_files(30)
        assert sm.cleaned_mb == 100.0


# ── NetworkManager Testleri ─────────────────────────────────


class TestNetworkManager:
    """Ag yoneticisi testleri."""

    @pytest.fixture()
    def nm(self):
        return NetworkManager(max_connections=5, bandwidth_limit_mbps=100.0)

    def test_init(self, nm):
        assert nm.connection_count == 0
        assert nm.rule_count == 0

    def test_record_bandwidth_normal(self, nm):
        status = nm.record_bandwidth(50.0)
        assert status == ResourceStatus.NORMAL

    def test_record_bandwidth_warning(self, nm):
        status = nm.record_bandwidth(85.0)
        assert status == ResourceStatus.WARNING

    def test_record_bandwidth_critical(self, nm):
        status = nm.record_bandwidth(96.0)
        assert status == ResourceStatus.CRITICAL

    def test_create_connection(self, nm):
        conn = nm.create_connection("db", "localhost:5432")
        assert conn is not None
        assert nm.connection_count == 1

    def test_create_connection_limit(self, nm):
        for i in range(5):
            nm.create_connection(f"c{i}", f"host{i}")
        assert nm.create_connection("c5", "host5") is None

    def test_close_connection(self, nm):
        nm.create_connection("db", "localhost")
        assert nm.close_connection("db") is True
        assert nm.connection_count == 0

    def test_close_nonexistent(self, nm):
        assert nm.close_connection("ghost") is False

    def test_add_traffic_rule(self, nm):
        rule = nm.add_traffic_rule("limit_api", "/api", 50.0)
        assert rule["name"] == "limit_api"
        assert nm.rule_count == 1

    def test_set_timeout(self, nm):
        nm.set_timeout("api", 60.0)
        assert nm.get_timeout("api") == 60.0

    def test_get_default_timeout(self, nm):
        assert nm.get_timeout("unknown") == 30.0

    def test_priority_queue(self, nm):
        nm.enqueue_priority("req1", 5)
        nm.enqueue_priority("req2", 10)
        item = nm.dequeue_priority()
        assert item["request_id"] == "req2"

    def test_dequeue_empty(self, nm):
        assert nm.dequeue_priority() is None

    def test_avg_bandwidth(self, nm):
        nm.record_bandwidth(50.0)
        nm.record_bandwidth(70.0)
        assert abs(nm.get_avg_bandwidth() - 60.0) < 0.01

    def test_avg_bandwidth_empty(self, nm):
        assert nm.get_avg_bandwidth() == 0.0

    def test_queue_size(self, nm):
        nm.enqueue_priority("a", 1)
        nm.enqueue_priority("b", 2)
        assert nm.queue_size == 2


# ── APIQuotaManager Testleri ────────────────────────────────


class TestAPIQuotaManager:
    """API kota yoneticisi testleri."""

    @pytest.fixture()
    def qm(self):
        return APIQuotaManager()

    def test_init(self, qm):
        assert qm.quota_count == 0

    def test_set_quota(self, qm):
        q = qm.set_quota("openai", 1000, "daily", 0.01)
        assert q["limit"] == 1000
        assert qm.quota_count == 1

    def test_record_call_within(self, qm):
        qm.set_quota("openai", 100)
        result = qm.record_call("openai")
        assert result["allowed"] is True
        assert result["remaining"] == 99

    def test_record_call_exhausted(self, qm):
        qm.set_quota("openai", 2)
        qm.record_call("openai")
        qm.record_call("openai")
        result = qm.record_call("openai")
        assert result["allowed"] is False

    def test_record_call_no_quota(self, qm):
        result = qm.record_call("unknown")
        assert result["allowed"] is True
        assert result.get("no_quota") is True

    def test_check_quota(self, qm):
        qm.set_quota("openai", 100)
        qm.record_call("openai")
        status = qm.check_quota("openai")
        assert status["used"] == 1
        assert status["exhausted"] is False

    def test_check_quota_nonexistent(self, qm):
        assert qm.check_quota("ghost")["exists"] is False

    def test_forecast_usage(self, qm):
        qm.set_quota("openai", 100)
        for _ in range(10):
            qm.record_call("openai")
        forecast = qm.forecast_usage("openai", 2)
        assert forecast["forecast"] > 10

    def test_forecast_empty(self, qm):
        result = qm.forecast_usage("ghost")
        assert result["forecast"] == 0

    def test_optimize_cost_underused(self, qm):
        qm.set_quota("svc", 1000, cost_per_call=0.01)
        for _ in range(100):
            qm.record_call("svc")
        suggestions = qm.optimize_cost()
        assert len(suggestions) >= 1
        assert suggestions[0]["suggestion"] == "downgrade_plan"

    def test_optimize_cost_overused(self, qm):
        qm.set_quota("svc", 10, cost_per_call=0.01)
        for _ in range(9):
            qm.record_call("svc")
        suggestions = qm.optimize_cost()
        assert any(s["suggestion"] == "upgrade_plan" for s in suggestions)

    def test_reset_quota(self, qm):
        qm.set_quota("openai", 100)
        qm.record_call("openai")
        assert qm.reset_quota("openai") is True
        status = qm.check_quota("openai")
        assert status["used"] == 0

    def test_reset_nonexistent(self, qm):
        assert qm.reset_quota("ghost") is False

    def test_total_cost(self, qm):
        qm.set_quota("svc", 100, cost_per_call=0.1)
        qm.record_call("svc")
        qm.record_call("svc")
        assert abs(qm.get_total_cost() - 0.2) < 0.01


# ── CostTracker Testleri ────────────────────────────────────


class TestCostTracker:
    """Maliyet takipcisi testleri."""

    @pytest.fixture()
    def ct(self):
        return CostTracker(monthly_budget=100.0)

    def test_init(self, ct):
        assert ct.record_count == 0

    def test_record_cost(self, ct):
        record = ct.record_cost(CostCategory.COMPUTE, 10.0, "server")
        assert record.amount == 10.0
        assert ct.record_count == 1

    def test_get_total_cost(self, ct):
        ct.record_cost(CostCategory.COMPUTE, 10.0)
        ct.record_cost(CostCategory.STORAGE, 5.0)
        assert ct.get_total_cost() == 15.0

    def test_get_total_by_category(self, ct):
        ct.record_cost(CostCategory.COMPUTE, 10.0)
        ct.record_cost(CostCategory.STORAGE, 5.0)
        assert ct.get_total_cost(CostCategory.COMPUTE) == 10.0

    def test_get_cost_breakdown(self, ct):
        ct.record_cost(CostCategory.COMPUTE, 10.0)
        ct.record_cost(CostCategory.COMPUTE, 5.0)
        ct.record_cost(CostCategory.STORAGE, 3.0)
        breakdown = ct.get_cost_breakdown()
        assert breakdown["compute"] == 15.0
        assert breakdown["storage"] == 3.0

    def test_get_cost_by_resource(self, ct):
        ct.record_cost(CostCategory.COMPUTE, 10.0, "server-a")
        ct.record_cost(CostCategory.COMPUTE, 5.0, "server-b")
        by_res = ct.get_cost_by_resource()
        assert by_res["server-a"] == 10.0

    def test_set_budget(self, ct):
        ct.set_budget("compute", 50.0)
        result = ct.check_budget("compute")
        assert result["has_budget"] is True

    def test_check_budget_within(self, ct):
        result = ct.check_budget("total")
        assert result["over_budget"] is False

    def test_check_budget_exceeded(self, ct):
        for _ in range(11):
            ct.record_cost(CostCategory.COMPUTE, 10.0)
        result = ct.check_budget("total")
        assert result["over_budget"] is True

    def test_check_budget_no_budget(self, ct):
        result = ct.check_budget("nonexistent")
        assert result["has_budget"] is False

    def test_optimization_suggestions(self, ct):
        ct.record_cost(CostCategory.COMPUTE, 80.0)
        ct.record_cost(CostCategory.STORAGE, 10.0)
        suggestions = ct.get_optimization_suggestions()
        assert len(suggestions) >= 1

    def test_budget_alert_on_exceed(self, ct):
        for _ in range(11):
            ct.record_cost(CostCategory.COMPUTE, 10.0)
        assert ct.alert_count > 0


# ── CapacityPlanner Testleri ────────────────────────────────


class TestCapacityPlanner:
    """Kapasite planlayici testleri."""

    @pytest.fixture()
    def cp(self):
        return CapacityPlanner()

    def test_init(self, cp):
        assert cp.capacity_count == 0

    def test_register_capacity(self, cp):
        cap = cp.register_capacity("cpu", ResourceType.CPU, 50.0, 100.0)
        assert cap["ratio"] == 0.5
        assert cp.capacity_count == 1

    def test_record_usage(self, cp):
        cp.register_capacity("cpu", ResourceType.CPU, 0.0, 100.0)
        cp.record_usage("cpu", 60.0)
        assert cp._capacities["cpu"]["current"] == 60.0

    def test_forecast_demand(self, cp):
        cp.register_capacity("cpu", ResourceType.CPU, 0.0, 100.0)
        for i in range(10):
            cp.record_usage("cpu", 40.0 + i * 2)
        forecast = cp.forecast_demand("cpu", 3)
        assert len(forecast["forecast"]) == 3

    def test_forecast_insufficient_data(self, cp):
        cp.record_usage("cpu", 50.0)
        forecast = cp.forecast_demand("cpu")
        assert forecast["confidence"] == 0.0

    def test_recommend_scaling_up(self, cp):
        cp.register_capacity("cpu", ResourceType.CPU, 90.0, 100.0)
        rec = cp.recommend_scaling("cpu")
        assert rec["direction"] == ScaleDirection.UP.value

    def test_recommend_scaling_down(self, cp):
        cp.register_capacity("cpu", ResourceType.CPU, 10.0, 100.0)
        rec = cp.recommend_scaling("cpu")
        assert rec["direction"] == ScaleDirection.DOWN.value

    def test_recommend_scaling_none(self, cp):
        cp.register_capacity("cpu", ResourceType.CPU, 50.0, 100.0)
        rec = cp.recommend_scaling("cpu")
        assert rec["direction"] == ScaleDirection.NONE.value

    def test_recommend_nonexistent(self, cp):
        rec = cp.recommend_scaling("ghost")
        assert rec["direction"] == ScaleDirection.NONE.value

    def test_reserve_capacity(self, cp):
        cp.register_capacity("mem", ResourceType.MEMORY, 50.0, 100.0)
        assert cp.reserve_capacity("mem", 30.0, "agent1") is True
        assert cp.reservation_count == 1

    def test_reserve_exceed(self, cp):
        cp.register_capacity("mem", ResourceType.MEMORY, 90.0, 100.0)
        assert cp.reserve_capacity("mem", 20.0) is False

    def test_release_reservation(self, cp):
        cp.register_capacity("mem", ResourceType.MEMORY, 50.0, 100.0)
        cp.reserve_capacity("mem", 20.0, "agent1")
        assert cp.release_reservation("mem", "agent1") is True
        assert cp.reservation_count == 0

    def test_release_nonexistent(self, cp):
        assert cp.release_reservation("ghost") is False

    def test_predict_bottleneck(self, cp):
        cp.register_capacity("cpu", ResourceType.CPU, 0.0, 100.0)
        for i in range(10):
            cp.record_usage("cpu", 80.0 + i * 3)
        bns = cp.predict_bottleneck()
        assert len(bns) >= 1


# ── ResourceOptimizer Testleri ──────────────────────────────


class TestResourceOptimizer:
    """Kaynak optimizasyonu testleri."""

    @pytest.fixture()
    def ro(self):
        return ResourceOptimizer(
            scale_up_threshold=0.85, scale_down_threshold=0.2,
        )

    def test_init(self, ro):
        assert ro.action_count == 0

    def test_check_scale_up(self, ro):
        result = ro.check_auto_scale("cpu", ResourceType.CPU, 0.9)
        assert result["action"] == OptimizationAction.SCALE_UP.value
        assert result["triggered"] is True

    def test_check_scale_down(self, ro):
        result = ro.check_auto_scale("cpu", ResourceType.CPU, 0.1)
        assert result["action"] == OptimizationAction.SCALE_DOWN.value

    def test_check_no_scale(self, ro):
        result = ro.check_auto_scale("cpu", ResourceType.CPU, 0.5)
        assert result["triggered"] is False

    def test_rebalance(self, ro):
        resources = {"a": 80.0, "b": 20.0}
        balanced = ro.rebalance(resources)
        assert balanced["a"] == balanced["b"]
        assert ro.action_count == 1

    def test_rebalance_empty(self, ro):
        assert ro.rebalance({}) == {}

    def test_detect_waste(self, ro):
        allocs = {
            "server-a": {"allocated": 100.0, "used": 10.0},
            "server-b": {"allocated": 100.0, "used": 80.0},
        }
        wastes = ro.detect_waste(allocs)
        assert len(wastes) == 1
        assert wastes[0]["resource"] == "server-a"

    def test_no_waste(self, ro):
        allocs = {"server": {"allocated": 100.0, "used": 90.0}}
        assert ro.detect_waste(allocs) == []

    def test_suggest_efficiency_high_usage(self, ro):
        result = ro.suggest_efficiency(
            "api", ResourceType.API,
            {"usage": 0.9, "latency": 0.5, "error_rate": 0.01},
        )
        actions = [i["action"] for i in result["improvements"]]
        assert OptimizationAction.CACHE.value in actions

    def test_suggest_efficiency_high_latency(self, ro):
        result = ro.suggest_efficiency(
            "api", ResourceType.API,
            {"usage": 0.3, "latency": 2.0, "error_rate": 0.01},
        )
        actions = [i["action"] for i in result["improvements"]]
        assert OptimizationAction.SCALE_UP.value in actions

    def test_suggest_efficiency_high_errors(self, ro):
        result = ro.suggest_efficiency(
            "api", ResourceType.API,
            {"usage": 0.3, "latency": 0.5, "error_rate": 0.1},
        )
        actions = [i["action"] for i in result["improvements"]]
        assert OptimizationAction.REBALANCE.value in actions

    def test_tune_performance(self, ro):
        result = ro.tune_performance("cpu", "freq", 2.4, 3.0)
        assert result["old_value"] == 2.4
        assert ro.tuning_count == 1


# ── ResourceOrchestrator Testleri ───────────────────────────


class TestResourceOrchestrator:
    """Kaynak orkestratoru testleri."""

    @pytest.fixture()
    def orch(self):
        return ResourceOrchestrator(
            cpu_threshold=0.8,
            memory_threshold=0.8,
            cost_budget=100.0,
        )

    def test_init(self, orch):
        assert orch.alert_count == 0
        assert orch.policy_count == 0

    def test_record_metrics_normal(self, orch):
        statuses = orch.record_metrics(
            cpu_usage=0.5, memory_mb=500.0, bandwidth_mbps=50.0,
        )
        assert statuses["cpu"] == "normal"

    def test_record_metrics_critical(self, orch):
        statuses = orch.record_metrics(cpu_usage=0.96)
        assert statuses["cpu"] == "critical"
        assert orch.alert_count >= 1

    def test_track_api_cost(self, orch):
        orch.api_quota.set_quota("openai", 100, cost_per_call=0.01)
        result = orch.track_api_cost("openai", tokens=100, cost=0.01)
        assert result["allowed"] is True

    def test_add_policy(self, orch):
        policy = orch.add_policy(
            "cpu_limit", ResourceType.CPU,
            {"max_usage": 0.9},
        )
        assert policy["name"] == "cpu_limit"
        assert orch.policy_count == 1

    def test_health_report(self, orch):
        orch.record_metrics(cpu_usage=0.5, memory_mb=100.0)
        report = orch.get_health_report()
        assert "cpu" in report
        assert "memory" in report
        assert "network" in report

    def test_snapshot(self, orch):
        orch.record_metrics(cpu_usage=0.6)
        snapshot = orch.get_snapshot()
        assert isinstance(snapshot, ResourceSnapshot)
        assert snapshot.cpu_usage == 0.6

    def test_resolve_alert(self, orch):
        orch.record_metrics(cpu_usage=0.96)
        assert orch.alert_count >= 1
        alert_id = orch._alerts[0].alert_id
        assert orch.resolve_alert(alert_id) is True

    def test_resolve_nonexistent_alert(self, orch):
        assert orch.resolve_alert("fake") is False

    def test_all_components(self, orch):
        assert orch.cpu is not None
        assert orch.memory is not None
        assert orch.storage is not None
        assert orch.network is not None
        assert orch.api_quota is not None
        assert orch.costs is not None
        assert orch.capacity is not None
        assert orch.optimizer is not None


# ── Entegrasyon Testleri ────────────────────────────────────


class TestResourceIntegration:
    """Entegrasyon testleri."""

    def test_full_monitoring_cycle(self):
        orch = ResourceOrchestrator(cost_budget=50.0)
        # Metrik kaydi
        orch.record_metrics(
            cpu_usage=0.7, memory_mb=4000.0, bandwidth_mbps=500.0,
        )
        # API kullanim
        orch.api_quota.set_quota("claude", 1000, cost_per_call=0.005)
        orch.track_api_cost("claude", cost=0.005)
        # Rapor
        report = orch.get_health_report()
        assert report["cpu"]["usage"] == 0.7

    def test_cost_budget_alert(self):
        ct = CostTracker(monthly_budget=10.0)
        for _ in range(12):
            ct.record_cost(CostCategory.COMPUTE, 1.0)
        assert ct.alert_count > 0
        assert ct.check_budget("total")["over_budget"] is True

    def test_capacity_planning_flow(self):
        cp = CapacityPlanner()
        cp.register_capacity("cpu", ResourceType.CPU, 0.0, 100.0)
        for i in range(15):
            cp.record_usage("cpu", 50.0 + i * 3)
        rec = cp.recommend_scaling("cpu")
        assert rec["direction"] == ScaleDirection.UP.value

    def test_memory_lifecycle(self):
        mm = MemoryManager(total_mb=512)
        mm.allocate("app", 200.0)
        mm.allocate("cache", 100.0)
        mm.allocate("temp", 0.5)
        # GC
        result = mm.trigger_gc()
        assert result["removed_count"] == 1
        assert mm.allocation_count == 2

    def test_snapshot_reflects_state(self):
        orch = ResourceOrchestrator()
        orch.record_metrics(cpu_usage=0.75, memory_mb=6000.0)
        orch.costs.record_cost(CostCategory.COMPUTE, 25.0)
        snapshot = orch.get_snapshot()
        assert snapshot.cpu_usage == 0.75
        assert snapshot.total_cost == 25.0
