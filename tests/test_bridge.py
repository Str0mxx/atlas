"""ATLAS Inter-System Bridge testleri."""

import pytest

from app.models.bridge import (
    BridgeEvent,
    BridgeSnapshot,
    BusMessage,
    EventType,
    HealthReport,
    HealthStatus,
    MessagePriority,
    MessageState,
    SystemInfo,
    SystemState,
    WorkflowRecord,
    WorkflowState,
)
from app.core.bridge.system_registry import SystemRegistry
from app.core.bridge.message_bus import MessageBus
from app.core.bridge.event_router import EventRouter
from app.core.bridge.api_gateway import APIGateway
from app.core.bridge.data_transformer import DataTransformer
from app.core.bridge.workflow_connector import WorkflowConnector
from app.core.bridge.health_aggregator import HealthAggregator
from app.core.bridge.config_sync import ConfigSync
from app.core.bridge.bridge_orchestrator import BridgeOrchestrator


# ============================================================
# Model Testleri
# ============================================================

class TestBridgeModels:
    """Model testleri."""

    def test_system_state_enum(self):
        assert SystemState.REGISTERED == "registered"
        assert SystemState.ACTIVE == "active"
        assert SystemState.OFFLINE == "offline"

    def test_message_priority_enum(self):
        assert MessagePriority.LOW == "low"
        assert MessagePriority.CRITICAL == "critical"

    def test_message_state_enum(self):
        assert MessageState.PENDING == "pending"
        assert MessageState.DEAD == "dead"

    def test_event_type_enum(self):
        assert EventType.SYSTEM == "system"
        assert EventType.HEALTH == "health"

    def test_health_status_enum(self):
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.CRITICAL == "critical"

    def test_workflow_state_enum(self):
        assert WorkflowState.PENDING == "pending"
        assert WorkflowState.ROLLED_BACK == "rolled_back"

    def test_system_info_defaults(self):
        s = SystemInfo(system_id="test", name="Test")
        assert s.state == SystemState.REGISTERED
        assert s.version == "1.0.0"

    def test_bus_message_defaults(self):
        m = BusMessage(topic="test")
        assert len(m.message_id) == 8
        assert m.priority == MessagePriority.NORMAL
        assert m.state == MessageState.PENDING

    def test_bridge_event_defaults(self):
        e = BridgeEvent(source="sys1")
        assert e.event_type == EventType.SYSTEM

    def test_workflow_record(self):
        w = WorkflowRecord(name="test", steps=["a", "b"])
        assert w.state == WorkflowState.PENDING
        assert len(w.steps) == 2

    def test_health_report(self):
        h = HealthReport(system_id="s1", status=HealthStatus.HEALTHY)
        assert h.system_id == "s1"

    def test_bridge_snapshot(self):
        s = BridgeSnapshot(total_systems=5, active_systems=3)
        assert s.avg_health == 1.0


# ============================================================
# SystemRegistry Testleri
# ============================================================

class TestSystemRegistry:
    """Sistem kaydi testleri."""

    def setup_method(self):
        self.reg = SystemRegistry()

    def test_register(self):
        info = self.reg.register("s1", "System1", ["cap1", "cap2"])
        assert info.system_id == "s1"
        assert info.state == SystemState.REGISTERED
        assert self.reg.total_systems == 1

    def test_unregister(self):
        self.reg.register("s1", "System1", ["cap1"])
        assert self.reg.unregister("s1")
        assert self.reg.total_systems == 0

    def test_unregister_nonexistent(self):
        assert not self.reg.unregister("nonexistent")

    def test_activate(self):
        self.reg.register("s1", "System1")
        assert self.reg.activate("s1")
        info = self.reg.get("s1")
        assert info.state == SystemState.ACTIVE

    def test_find_by_capability(self):
        self.reg.register("s1", "S1", ["search", "analyze"])
        self.reg.register("s2", "S2", ["search", "report"])
        systems = self.reg.find_by_capability("search")
        assert len(systems) == 2

    def test_get_dependencies(self):
        self.reg.register("s1", "S1")
        self.reg.register("s2", "S2", dependencies=["s1"])
        deps = self.reg.get_dependencies("s2")
        assert "s1" in deps

    def test_get_dependents(self):
        self.reg.register("s1", "S1")
        self.reg.register("s2", "S2", dependencies=["s1"])
        dependents = self.reg.get_dependents("s1")
        assert "s2" in dependents

    def test_dependency_graph(self):
        self.reg.register("s1", "S1")
        self.reg.register("s2", "S2", dependencies=["s1"])
        graph = self.reg.get_dependency_graph()
        assert "s1" in graph["s2"]

    def test_check_dependencies_met(self):
        self.reg.register("s1", "S1")
        self.reg.register("s2", "S2", dependencies=["s1"])
        assert not self.reg.check_dependencies_met("s2")
        self.reg.activate("s1")
        assert self.reg.check_dependencies_met("s2")

    def test_get_active_systems(self):
        self.reg.register("s1", "S1")
        self.reg.register("s2", "S2")
        self.reg.activate("s1")
        active = self.reg.get_active_systems()
        assert "s1" in active
        assert "s2" not in active

    def test_update_version(self):
        self.reg.register("s1", "S1")
        assert self.reg.update_version("s1", "2.0.0")
        assert self.reg.get("s1").version == "2.0.0"

    def test_set_state(self):
        self.reg.register("s1", "S1")
        self.reg.set_state("s1", SystemState.MAINTENANCE)
        assert self.reg.get("s1").state == SystemState.MAINTENANCE

    def test_properties(self):
        self.reg.register("s1", "S1", ["cap1"])
        self.reg.activate("s1")
        assert self.reg.active_count == 1
        assert self.reg.total_capabilities == 1


# ============================================================
# MessageBus Testleri
# ============================================================

class TestMessageBus:
    """Mesaj yolu testleri."""

    def setup_method(self):
        self.bus = MessageBus()
        self.received = []

    def _handler(self, msg):
        self.received.append(msg)

    def test_publish_no_subscribers(self):
        msg = self.bus.publish("topic1", {"key": "value"})
        assert msg.state == MessageState.DELIVERED

    def test_publish_with_subscriber(self):
        self.bus.subscribe("topic1", self._handler)
        self.bus.publish("topic1", {"key": "value"})
        assert len(self.received) == 1

    def test_unsubscribe(self):
        self.bus.subscribe("topic1", self._handler)
        assert self.bus.unsubscribe("topic1", self._handler)
        self.bus.publish("topic1", {"key": "value"})
        assert len(self.received) == 0

    def test_send_direct(self):
        self.bus.subscribe("direct:sys1", self._handler)
        msg = self.bus.send("sys1", {"data": 1})
        assert msg.state == MessageState.DELIVERED
        assert len(self.received) == 1

    def test_send_no_handler(self):
        msg = self.bus.send("nonexistent", {"data": 1})
        assert msg.state == MessageState.FAILED
        assert self.bus.dead_letter_count == 1

    def test_broadcast(self):
        self.bus.subscribe("t1", self._handler)
        self.bus.subscribe("t2", self._handler)
        messages = self.bus.broadcast({"alert": True})
        assert len(messages) == 2

    def test_request_response(self):
        self.bus.subscribe("direct:sys1", self._handler)
        msg_id = self.bus.request("sys1", {"q": "test"})
        self.bus.respond(msg_id, {"answer": 42})
        assert self.bus.get_response(msg_id) == {"answer": 42}

    def test_dead_letter_retry(self):
        msg = self.bus.send("missing", {"data": 1})
        assert self.bus.dead_letter_count == 1
        # Abone ekle ve yeniden dene
        self.bus.subscribe("direct:missing", self._handler)
        retried = self.bus.retry_dead_letters()
        assert retried == 1

    def test_get_messages(self):
        self.bus.publish("t1", {"a": 1}, "s1")
        self.bus.publish("t2", {"b": 2}, "s2")
        msgs = self.bus.get_messages(source="s1")
        assert len(msgs) == 1

    def test_properties(self):
        self.bus.subscribe("t1", self._handler)
        self.bus.publish("t1", {"a": 1})
        assert self.bus.total_messages == 1
        assert self.bus.subscriber_count == 1


# ============================================================
# EventRouter Testleri
# ============================================================

class TestEventRouter:
    """Olay yonlendirici testleri."""

    def setup_method(self):
        self.router = EventRouter(retention=100)
        self.events_received = []

    def _handler(self, event):
        self.events_received.append(event)

    def test_emit_event(self):
        self.router.register_handler("system", self._handler)
        event = self.router.emit("system", "s1", {"action": "start"})
        assert event.event_type == EventType.SYSTEM
        assert len(self.events_received) == 1

    def test_unregister_handler(self):
        self.router.register_handler("system", self._handler)
        assert self.router.unregister_handler("system", self._handler)
        self.router.emit("system", "s1")
        assert len(self.events_received) == 0

    def test_filter_blocks_event(self):
        self.router.register_handler("system", self._handler)
        self.router.add_filter("block_all", lambda e: False)
        self.router.emit("system", "s1")
        assert len(self.events_received) == 0

    def test_remove_filter(self):
        self.router.add_filter("f1", lambda e: False)
        assert self.router.remove_filter("f1")
        assert not self.router.remove_filter("nonexistent")

    def test_transformer(self):
        def add_flag(event):
            event.data["transformed"] = True
            return event

        self.router.register_handler("data", self._handler)
        self.router.add_transformer("data", add_flag)
        self.router.emit("data", "s1", {"value": 1})
        assert self.events_received[0].data.get("transformed")

    def test_replay(self):
        self.router.register_handler("system", self._handler)
        self.router.emit("system", "s1", {"n": 1})
        self.router.emit("system", "s1", {"n": 2})
        self.events_received.clear()
        replayed = self.router.replay("system")
        assert len(replayed) == 2
        assert len(self.events_received) == 2

    def test_replay_with_limit(self):
        self.router.register_handler("system", self._handler)
        for i in range(5):
            self.router.emit("system", "s1", {"n": i})
        self.events_received.clear()
        replayed = self.router.replay("system", limit=2)
        assert len(replayed) == 2

    def test_get_events(self):
        self.router.emit("system", "s1")
        self.router.emit("error", "s2")
        events = self.router.get_events(event_type="system")
        assert len(events) == 1

    def test_retention_limit(self):
        router = EventRouter(retention=5)
        for i in range(10):
            router.emit("system", "s1", {"n": i})
        assert router.total_events == 5

    def test_properties(self):
        self.router.register_handler("system", self._handler)
        self.router.add_filter("f1", lambda e: True)
        assert self.router.handler_count == 1
        assert self.router.filter_count == 1


# ============================================================
# APIGateway Testleri
# ============================================================

class TestAPIGateway:
    """API gecidi testleri."""

    def setup_method(self):
        self.gw = APIGateway()

    def test_register_and_request(self):
        self.gw.register_route("/health", lambda p: {"status": "ok"})
        result = self.gw.request("/health")
        assert result["success"]
        assert result["data"]["status"] == "ok"

    def test_route_not_found(self):
        result = self.gw.request("/missing")
        assert not result["success"]
        assert result["error"] == "not_found"

    def test_unregister_route(self):
        self.gw.register_route("/test", lambda p: {})
        assert self.gw.unregister_route("/test")
        result = self.gw.request("/test")
        assert not result["success"]

    def test_rate_limiting(self):
        self.gw.register_route("/api", lambda p: {"ok": True})
        self.gw.set_rate_limit("s1", 2)
        self.gw.request("/api", source="s1")
        self.gw.request("/api", source="s1")
        result = self.gw.request("/api", source="s1")
        assert not result["success"]
        assert result["error"] == "rate_limited"

    def test_reset_rate_limits(self):
        self.gw.register_route("/api", lambda p: {"ok": True})
        self.gw.set_rate_limit("s1", 1)
        self.gw.request("/api", source="s1")
        self.gw.reset_rate_limits()
        result = self.gw.request("/api", source="s1")
        assert result["success"]

    def test_circuit_breaker(self):
        self.gw.register_route("/api", lambda p: {"ok": True})
        self.gw.open_circuit("s1")
        result = self.gw.request("/api", source="s1")
        assert not result["success"]
        assert result["error"] == "circuit_open"

    def test_close_circuit(self):
        self.gw.register_route("/api", lambda p: {"ok": True})
        self.gw.open_circuit("s1")
        self.gw.close_circuit("s1")
        result = self.gw.request("/api", source="s1")
        assert result["success"]

    def test_auto_circuit_break(self):
        def fail(p):
            raise ValueError("error")

        self.gw.register_route("/fail", fail)
        self.gw._failure_threshold = 3
        for _ in range(3):
            self.gw.request("/fail", source="s1")
        assert self.gw.is_circuit_open("s1")

    def test_aggregate_requests(self):
        self.gw.register_route("/a", lambda p: {"v": 1})
        self.gw.register_route("/b", lambda p: {"v": 2})
        result = self.gw.aggregate_requests(["/a", "/b"])
        assert result["success"]
        assert result["total"] == 2

    def test_middleware(self):
        def add_auth(ctx):
            ctx["payload"]["auth"] = True
            return ctx

        self.gw.add_middleware(add_auth)
        self.gw.register_route("/test", lambda p: p)
        result = self.gw.request("/test", {"data": 1})
        assert result["data"].get("auth")

    def test_request_log(self):
        self.gw.register_route("/api", lambda p: {})
        self.gw.request("/api")
        logs = self.gw.get_request_log()
        assert len(logs) == 1

    def test_properties(self):
        self.gw.register_route("/a", lambda p: {})
        self.gw.request("/a")
        assert self.gw.total_routes == 1
        assert self.gw.total_requests == 1


# ============================================================
# DataTransformer Testleri
# ============================================================

class TestDataTransformer:
    """Veri donusturucu testleri."""

    def setup_method(self):
        self.tf = DataTransformer()

    def test_register_and_convert(self):
        self.tf.register_converter("upper", lambda d: {
            k: v.upper() if isinstance(v, str) else v
            for k, v in d.items()
        })
        result = self.tf.convert("upper", {"name": "test"})
        assert result["name"] == "TEST"

    def test_convert_unregistered(self):
        result = self.tf.convert("missing", {"a": 1})
        assert result == {"a": 1}

    def test_schema_mapping(self):
        self.tf.register_schema("v1_to_v2", {
            "old_name": "new_name",
            "old_value": "new_value",
        })
        result = self.tf.map_schema("v1_to_v2", {
            "old_name": "Test",
            "old_value": 42,
            "extra": "ignored",
        })
        assert result["new_name"] == "Test"
        assert result["new_value"] == 42
        assert "extra" not in result

    def test_enrich(self):
        self.tf.register_enricher("add_meta", lambda d: {
            **d, "enriched": True,
        })
        result = self.tf.enrich("add_meta", {"a": 1})
        assert result["enriched"]
        assert result["a"] == 1

    def test_validate(self):
        self.tf.register_validator("has_name", lambda d: "name" in d)
        assert self.tf.validate("has_name", {"name": "Test"})
        assert not self.tf.validate("has_name", {"value": 1})

    def test_validate_unregistered(self):
        assert self.tf.validate("missing", {"a": 1})

    def test_normalize(self):
        self.tf.register_normalizer("lower_keys", lambda d: {
            k.lower(): v for k, v in d.items()
        })
        result = self.tf.normalize("lower_keys", {"NAME": "Test"})
        assert "name" in result

    def test_transform_pipeline(self):
        self.tf.register_converter("add_flag", lambda d: {**d, "flag": True})
        self.tf.register_schema("rename", {"flag": "is_flagged"})
        result = self.tf.transform_pipeline({"data": 1}, [
            {"type": "convert", "name": "add_flag"},
            {"type": "schema", "name": "rename"},
        ])
        assert result.get("is_flagged")

    def test_properties(self):
        self.tf.register_converter("c1", lambda d: d)
        self.tf.register_schema("s1", {})
        self.tf.register_validator("v1", lambda d: True)
        assert self.tf.total_converters == 1
        assert self.tf.total_schemas == 1
        assert self.tf.total_validators == 1


# ============================================================
# WorkflowConnector Testleri
# ============================================================

class TestWorkflowConnector:
    """Is akisi baglayici testleri."""

    def setup_method(self):
        self.wf = WorkflowConnector()
        self.wf.register_step("step_a", lambda ctx: {**ctx, "a": True})
        self.wf.register_step("step_b", lambda ctx: {**ctx, "b": True})

    def test_create_workflow(self):
        w = self.wf.create_workflow("test", ["step_a", "step_b"])
        assert w.name == "test"
        assert w.state == WorkflowState.PENDING

    def test_execute_workflow(self):
        w = self.wf.create_workflow("test", ["step_a", "step_b"])
        result = self.wf.execute_workflow(w.workflow_id, {})
        assert result["success"]
        assert result["context"]["a"]
        assert result["context"]["b"]
        assert w.state == WorkflowState.COMPLETED

    def test_execute_missing_step(self):
        w = self.wf.create_workflow("test", ["step_a", "missing"])
        result = self.wf.execute_workflow(w.workflow_id)
        assert not result["success"]
        assert "step_a" in result["completed_steps"]

    def test_execute_step_failure(self):
        def fail(ctx):
            raise ValueError("boom")

        self.wf.register_step("fail_step", fail)
        w = self.wf.create_workflow("test", ["step_a", "fail_step"])
        result = self.wf.execute_workflow(w.workflow_id)
        assert not result["success"]
        assert w.state == WorkflowState.FAILED

    def test_rollback(self):
        compensated = []

        self.wf.register_step(
            "comp_step",
            lambda ctx: {**ctx, "comp": True},
            compensation=lambda ctx: compensated.append("comp"),
        )
        w = self.wf.create_workflow("test", ["comp_step", "missing_step"])
        self.wf.execute_workflow(w.workflow_id)
        result = self.wf.rollback_workflow(w.workflow_id)
        assert result["success"]
        assert "comp_step" in result["rolled_back_steps"]
        assert w.state == WorkflowState.ROLLED_BACK

    def test_rollback_not_failed(self):
        w = self.wf.create_workflow("test", ["step_a"])
        self.wf.execute_workflow(w.workflow_id)
        result = self.wf.rollback_workflow(w.workflow_id)
        assert not result["success"]

    def test_sync_state(self):
        w = self.wf.create_workflow("test", ["step_a"])
        assert self.wf.sync_state(w.workflow_id, "key", "value")
        state = self.wf.get_state(w.workflow_id)
        assert state["key"] == "value"

    def test_get_workflows_by_state(self):
        w1 = self.wf.create_workflow("t1", ["step_a"])
        w2 = self.wf.create_workflow("t2", ["step_a"])
        self.wf.execute_workflow(w1.workflow_id)
        completed = self.wf.get_workflows(WorkflowState.COMPLETED)
        assert len(completed) == 1

    def test_properties(self):
        self.wf.create_workflow("test", ["step_a"])
        assert self.wf.total_workflows == 1
        assert self.wf.registered_steps == 2


# ============================================================
# HealthAggregator Testleri
# ============================================================

class TestHealthAggregator:
    """Saglik birlestiricisi testleri."""

    def setup_method(self):
        self.health = HealthAggregator()

    def test_report_health(self):
        r = self.health.report_health("s1", HealthStatus.HEALTHY)
        assert r.status == HealthStatus.HEALTHY
        assert self.health.total_reports == 1

    def test_critical_generates_alert(self):
        self.health.report_health("s1", HealthStatus.CRITICAL)
        assert self.health.alert_count == 1

    def test_check_all(self):
        self.health.register_checker("s1", lambda: HealthStatus.HEALTHY)
        self.health.register_checker("s2", lambda: HealthStatus.WARNING)
        results = self.health.check_all()
        assert results["s1"] == HealthStatus.HEALTHY
        assert results["s2"] == HealthStatus.WARNING

    def test_check_system(self):
        self.health.register_checker("s1", lambda: HealthStatus.HEALTHY)
        status = self.health.check_system("s1")
        assert status == HealthStatus.HEALTHY

    def test_check_unknown_system(self):
        status = self.health.check_system("missing")
        assert status == HealthStatus.UNKNOWN

    def test_aggregate_status(self):
        self.health.report_health("s1", HealthStatus.HEALTHY)
        self.health.report_health("s2", HealthStatus.HEALTHY)
        agg = self.health.get_aggregate_status()
        assert agg["overall"] == "healthy"
        assert agg["health_ratio"] == 1.0

    def test_aggregate_with_critical(self):
        self.health.report_health("s1", HealthStatus.HEALTHY)
        self.health.report_health("s2", HealthStatus.CRITICAL)
        agg = self.health.get_aggregate_status()
        assert agg["overall"] == "critical"

    def test_unhealthy_systems(self):
        self.health.report_health("s1", HealthStatus.HEALTHY)
        self.health.report_health("s2", HealthStatus.WARNING)
        unhealthy = self.health.get_unhealthy_systems()
        assert "s2" in unhealthy
        assert "s1" not in unhealthy

    def test_trigger_healing(self):
        healed = []
        self.health.register_healer("s1", lambda: healed.append("s1"))
        assert self.health.trigger_healing("s1")
        assert "s1" in healed

    def test_auto_heal(self):
        healed = []
        self.health.register_healer("s1", lambda: healed.append("s1"))
        self.health.report_health("s1", HealthStatus.CRITICAL)
        result = self.health.auto_heal()
        assert "s1" in result

    def test_get_alerts(self):
        self.health.report_health("s1", HealthStatus.WARNING)
        self.health.report_health("s2", HealthStatus.CRITICAL)
        alerts = self.health.get_alerts("s1")
        assert len(alerts) == 1

    def test_properties(self):
        self.health.report_health("s1", HealthStatus.HEALTHY)
        assert self.health.healthy_count == 1


# ============================================================
# ConfigSync Testleri
# ============================================================

class TestConfigSync:
    """Konfigurasyon senkronizasyonu testleri."""

    def setup_method(self):
        self.sync = ConfigSync()

    def test_set_and_get_shared(self):
        self.sync.set_shared("key", "value")
        assert self.sync.get_shared("key") == "value"

    def test_get_default(self):
        assert self.sync.get_shared("missing", "default") == "default"

    def test_get_all_shared(self):
        self.sync.set_shared("a", 1)
        self.sync.set_shared("b", 2)
        all_config = self.sync.get_all_shared()
        assert len(all_config) == 2

    def test_system_config(self):
        self.sync.set_system_config("s1", {"timeout": 30})
        config = self.sync.get_system_config("s1")
        assert config["timeout"] == 30

    def test_propagate(self):
        self.sync.set_shared("timeout", 30)
        self.sync.set_system_config("s1", {})
        self.sync.set_system_config("s2", {})
        updated = self.sync.propagate("timeout")
        assert updated == 2
        assert self.sync.get_system_config("s1")["timeout"] == 30

    def test_propagate_selective(self):
        self.sync.set_shared("key", "val")
        self.sync.set_system_config("s1", {})
        self.sync.set_system_config("s2", {})
        updated = self.sync.propagate("key", ["s1"])
        assert updated == 1

    def test_listener(self):
        changes = []
        self.sync.add_listener("key", lambda k, n, o: changes.append((k, n, o)))
        self.sync.set_shared("key", "value")
        assert len(changes) == 1
        assert changes[0] == ("key", "value", None)

    def test_remove_listener(self):
        handler = lambda k, n, o: None
        self.sync.add_listener("key", handler)
        assert self.sync.remove_listener("key", handler)

    def test_check_consistency(self):
        self.sync.set_shared("timeout", 30)
        self.sync.set_system_config("s1", {"timeout": 60})
        issues = self.sync.check_consistency()
        assert len(issues) == 1
        assert issues[0]["system_value"] == 60

    def test_snapshot_and_rollback(self):
        self.sync.set_shared("key", "v1")
        snap_id = self.sync.create_snapshot()
        self.sync.set_shared("key", "v2")
        assert self.sync.get_shared("key") == "v2"
        assert self.sync.rollback(snap_id)
        assert self.sync.get_shared("key") == "v1"

    def test_rollback_nonexistent(self):
        assert not self.sync.rollback("nonexistent")

    def test_history(self):
        self.sync.set_shared("a", 1)
        self.sync.set_shared("b", 2)
        self.sync.set_shared("a", 3)
        history = self.sync.get_history("a")
        assert len(history) == 2

    def test_properties(self):
        self.sync.set_shared("k", "v")
        self.sync.set_system_config("s1", {})
        self.sync.create_snapshot()
        assert self.sync.shared_count == 1
        assert self.sync.system_count == 1
        assert self.sync.snapshot_count == 1


# ============================================================
# BridgeOrchestrator Testleri
# ============================================================

class TestBridgeOrchestrator:
    """Kopru orkestratoru testleri."""

    def setup_method(self):
        self.bridge = BridgeOrchestrator()

    def test_register_system(self):
        result = self.bridge.register_system(
            "s1", "System1", ["cap1"],
        )
        assert result["success"]
        assert result["system_id"] == "s1"

    def test_activate_system(self):
        self.bridge.register_system("s1", "S1")
        result = self.bridge.activate_system("s1")
        assert result["success"]

    def test_activate_with_unmet_deps(self):
        self.bridge.register_system("s1", "S1")
        self.bridge.register_system(
            "s2", "S2", dependencies=["s1"],
        )
        result = self.bridge.activate_system("s2")
        assert not result["success"]
        assert "s1" in result["unmet"]

    def test_send_message(self):
        result = self.bridge.send_message(
            "events", {"type": "test"}, "s1",
        )
        assert result["success"]

    def test_api_request(self):
        self.bridge.gateway.register_route(
            "/test", lambda p: {"result": True},
        )
        result = self.bridge.api_request("/test")
        assert result["success"]

    def test_execute_workflow(self):
        self.bridge.workflows.register_step(
            "init", lambda ctx: {**ctx, "init": True},
        )
        self.bridge.workflows.register_step(
            "process", lambda ctx: {**ctx, "done": True},
        )
        result = self.bridge.execute_workflow(
            "test_flow", ["init", "process"],
            systems=["s1", "s2"],
        )
        assert result["success"]

    def test_check_health(self):
        self.bridge.health.register_checker(
            "s1", lambda: HealthStatus.HEALTHY,
        )
        result = self.bridge.check_health()
        assert result["overall"] == "healthy"

    def test_auto_heal(self):
        healed = []
        self.bridge.health.register_healer(
            "s1", lambda: healed.append("s1"),
        )
        self.bridge.health.report_health("s1", HealthStatus.CRITICAL)
        result = self.bridge.auto_heal()
        assert result["count"] == 1

    def test_troubleshoot_healthy(self):
        self.bridge.register_system("s1", "S1")
        self.bridge.activate_system("s1")
        result = self.bridge.troubleshoot("s1")
        assert "Sorun tespit edilmedi" in result["issues"]

    def test_troubleshoot_offline(self):
        self.bridge.register_system("s1", "S1")
        self.bridge.registry.set_state("s1", SystemState.OFFLINE)
        result = self.bridge.troubleshoot("s1")
        assert any("cevrimdisi" in i for i in result["issues"])

    def test_troubleshoot_unregistered(self):
        result = self.bridge.troubleshoot("missing")
        assert "Sistem kayitli degil" in result["issues"]

    def test_get_snapshot(self):
        self.bridge.register_system("s1", "S1")
        self.bridge.activate_system("s1")
        snap = self.bridge.get_snapshot()
        assert snap.total_systems == 1
        assert snap.active_systems == 1

    def test_subsystem_properties(self):
        assert self.bridge.registry is not None
        assert self.bridge.bus is not None
        assert self.bridge.events is not None
        assert self.bridge.gateway is not None
        assert self.bridge.transformer is not None
        assert self.bridge.workflows is not None
        assert self.bridge.health is not None
        assert self.bridge.config is not None


# ============================================================
# Entegrasyon Testleri
# ============================================================

class TestBridgeIntegration:
    """Entegrasyon testleri."""

    def test_full_system_lifecycle(self):
        """Tam sistem yasam dongusu."""
        bridge = BridgeOrchestrator()

        # Kayit
        bridge.register_system("core", "Core", ["compute"])
        bridge.register_system(
            "analytics", "Analytics",
            ["analyze"], dependencies=["core"],
        )

        # Aktivasyon (bagimlilik sirasi)
        bridge.activate_system("core")
        result = bridge.activate_system("analytics")
        assert result["success"]

        # Saglik kontrolu
        bridge.health.register_checker(
            "core", lambda: HealthStatus.HEALTHY,
        )
        health = bridge.check_health()
        assert health["overall"] == "healthy"

        snap = bridge.get_snapshot()
        assert snap.total_systems == 2
        assert snap.active_systems == 2

    def test_cross_system_workflow(self):
        """Sistemler arasi is akisi."""
        bridge = BridgeOrchestrator()

        bridge.register_system("ingestion", "Ingestion")
        bridge.register_system("processing", "Processing")
        bridge.register_system("storage", "Storage")

        bridge.workflows.register_step(
            "ingest", lambda ctx: {**ctx, "data": [1, 2, 3]},
        )
        bridge.workflows.register_step(
            "process", lambda ctx: {
                **ctx, "processed": [x * 2 for x in ctx["data"]],
            },
        )
        bridge.workflows.register_step(
            "store", lambda ctx: {**ctx, "stored": True},
        )

        result = bridge.execute_workflow(
            "ETL Pipeline",
            ["ingest", "process", "store"],
            systems=["ingestion", "processing", "storage"],
        )
        assert result["success"]
        assert result["context"]["processed"] == [2, 4, 6]
        assert result["context"]["stored"]

    def test_config_propagation(self):
        """Konfigurasyon yayilimi."""
        bridge = BridgeOrchestrator()

        bridge.register_system("s1", "S1")
        bridge.register_system("s2", "S2")

        bridge.config.set_system_config("s1", {})
        bridge.config.set_system_config("s2", {})
        bridge.config.set_shared("log_level", "DEBUG")
        bridge.config.propagate("log_level")

        assert bridge.config.get_system_config("s1")["log_level"] == "DEBUG"
        assert bridge.config.get_system_config("s2")["log_level"] == "DEBUG"

    def test_event_driven_messaging(self):
        """Olay tabanli mesajlasma."""
        bridge = BridgeOrchestrator()
        received = []

        bridge.bus.subscribe("alerts", lambda m: received.append(m))
        bridge.events.register_handler(
            "error",
            lambda e: bridge.bus.publish(
                "alerts", {"error": e.data}, e.source,
            ),
        )

        bridge.events.emit("error", "s1", {"msg": "disk full"})
        assert len(received) == 1

    def test_data_transformation_flow(self):
        """Veri donusturme akisi."""
        bridge = BridgeOrchestrator()

        bridge.transformer.register_schema("api_to_internal", {
            "userName": "user_name",
            "emailAddress": "email",
        })
        bridge.transformer.register_validator(
            "has_email", lambda d: "email" in d,
        )

        mapped = bridge.transformer.map_schema("api_to_internal", {
            "userName": "fatih",
            "emailAddress": "f@test.com",
        })
        assert mapped["user_name"] == "fatih"
        assert bridge.transformer.validate("has_email", mapped)

    def test_health_monitoring_and_healing(self):
        """Saglik izleme ve iyilestirme."""
        bridge = BridgeOrchestrator()

        bridge.register_system("db", "Database")
        healed = []

        bridge.health.register_checker(
            "db", lambda: HealthStatus.CRITICAL,
        )
        bridge.health.register_healer(
            "db", lambda: healed.append("db"),
        )

        health = bridge.check_health()
        assert health["overall"] == "critical"

        result = bridge.auto_heal()
        assert "db" in result["healed"]
