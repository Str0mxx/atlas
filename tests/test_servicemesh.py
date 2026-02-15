"""ATLAS Service Mesh & Microservices testleri."""

import pytest

from app.core.servicemesh import (
    MeshCircuitBreaker,
    MeshLoadBalancer,
    MeshOrchestrator,
    MeshServiceRegistry,
    RetryPolicy,
    ServiceMeshConfig,
    SidecarProxy,
    TimeoutManager,
    TrafficManager,
)
from app.models.servicemesh import (
    CircuitRecord,
    CircuitState,
    LoadBalancerAlgorithm,
    MeshServiceRecord,
    MeshSnapshot,
    ProxyMode,
    RetryStrategy,
    ServiceStatus,
    TrafficPolicy,
    TrafficRecord,
)


# ===================== Models =====================


class TestServiceMeshModels:
    """Model testleri."""

    def test_service_status_enum(self):
        assert ServiceStatus.ACTIVE == "active"
        assert ServiceStatus.INACTIVE == "inactive"
        assert ServiceStatus.DRAINING == "draining"
        assert ServiceStatus.STARTING == "starting"
        assert ServiceStatus.STOPPING == "stopping"
        assert ServiceStatus.UNKNOWN == "unknown"

    def test_lb_algorithm_enum(self):
        assert LoadBalancerAlgorithm.ROUND_ROBIN == "round_robin"
        assert LoadBalancerAlgorithm.LEAST_CONNECTIONS == "least_connections"
        assert LoadBalancerAlgorithm.WEIGHTED == "weighted"
        assert LoadBalancerAlgorithm.RANDOM == "random"
        assert LoadBalancerAlgorithm.CONSISTENT_HASH == "consistent_hash"
        assert LoadBalancerAlgorithm.HEALTH_AWARE == "health_aware"

    def test_circuit_state_enum(self):
        assert CircuitState.CLOSED == "closed"
        assert CircuitState.OPEN == "open"
        assert CircuitState.HALF_OPEN == "half_open"
        assert CircuitState.FORCED_OPEN == "forced_open"
        assert CircuitState.FORCED_CLOSED == "forced_closed"
        assert CircuitState.DISABLED == "disabled"

    def test_retry_strategy_enum(self):
        assert RetryStrategy.FIXED == "fixed"
        assert RetryStrategy.EXPONENTIAL == "exponential"
        assert RetryStrategy.LINEAR == "linear"
        assert RetryStrategy.JITTER == "jitter"
        assert RetryStrategy.FIBONACCI == "fibonacci"
        assert RetryStrategy.NONE == "none"

    def test_traffic_policy_enum(self):
        assert TrafficPolicy.NORMAL == "normal"
        assert TrafficPolicy.CANARY == "canary"
        assert TrafficPolicy.BLUE_GREEN == "blue_green"
        assert TrafficPolicy.AB_TEST == "ab_test"
        assert TrafficPolicy.DARK_LAUNCH == "dark_launch"
        assert TrafficPolicy.MIRROR == "mirror"

    def test_proxy_mode_enum(self):
        assert ProxyMode.SIDECAR == "sidecar"
        assert ProxyMode.INGRESS == "ingress"
        assert ProxyMode.EGRESS == "egress"
        assert ProxyMode.PASSTHROUGH == "passthrough"
        assert ProxyMode.INTERCEPT == "intercept"
        assert ProxyMode.TRANSPARENT == "transparent"

    def test_mesh_service_record(self):
        r = MeshServiceRecord(name="api")
        assert r.name == "api"
        assert r.status == ServiceStatus.ACTIVE
        assert r.instances == 0
        assert len(r.service_id) == 8

    def test_mesh_service_record_custom(self):
        r = MeshServiceRecord(
            name="web", instances=3, version="2.0.0",
        )
        assert r.instances == 3
        assert r.version == "2.0.0"

    def test_circuit_record(self):
        r = CircuitRecord(service="api")
        assert r.service == "api"
        assert r.state == CircuitState.CLOSED
        assert r.failure_count == 0

    def test_traffic_record(self):
        r = TrafficRecord(source="web", destination="api")
        assert r.source == "web"
        assert r.policy == TrafficPolicy.NORMAL
        assert r.weight == 100.0

    def test_mesh_snapshot(self):
        s = MeshSnapshot(total_services=5, total_instances=15)
        assert s.total_services == 5
        assert s.total_instances == 15
        assert s.open_circuits == 0


# ===================== MeshServiceRegistry =====================


class TestMeshServiceRegistry:
    """MeshServiceRegistry testleri."""

    def test_init(self):
        reg = MeshServiceRegistry()
        assert reg.service_count == 0
        assert reg.total_instances == 0

    def test_register(self):
        reg = MeshServiceRegistry()
        r = reg.register("api", "localhost", 8080)
        assert r["status"] == "registered"
        assert reg.service_count == 1
        assert reg.total_instances == 1

    def test_register_multiple_instances(self):
        reg = MeshServiceRegistry()
        reg.register("api", "host1", 8080)
        reg.register("api", "host2", 8080)
        assert reg.service_count == 1
        assert reg.total_instances == 2

    def test_register_update(self):
        reg = MeshServiceRegistry()
        reg.register("api", "localhost", 8080)
        reg.register("api", "localhost", 8080, version="2.0.0")
        assert reg.total_instances == 1

    def test_deregister_instance(self):
        reg = MeshServiceRegistry()
        reg.register("api", "host1", 8080)
        reg.register("api", "host2", 8080)
        assert reg.deregister("api", "host1:8080") is True
        assert reg.total_instances == 1

    def test_deregister_service(self):
        reg = MeshServiceRegistry()
        reg.register("api", "localhost", 8080)
        assert reg.deregister("api") is True
        assert reg.service_count == 0

    def test_deregister_not_found(self):
        reg = MeshServiceRegistry()
        assert reg.deregister("missing") is False

    def test_heartbeat(self):
        reg = MeshServiceRegistry()
        reg.register("api", "localhost", 8080)
        assert reg.heartbeat("api", "localhost:8080") is True
        assert reg.heartbeat("api", "missing") is False

    def test_get_service(self):
        reg = MeshServiceRegistry()
        reg.register("api", "localhost", 8080)
        svc = reg.get_service("api")
        assert svc is not None
        assert svc["name"] == "api"
        assert svc["instance_count"] == 1

    def test_get_service_not_found(self):
        reg = MeshServiceRegistry()
        assert reg.get_service("missing") is None

    def test_get_instances(self):
        reg = MeshServiceRegistry()
        reg.register("api", "h1", 8080)
        reg.register("api", "h2", 8080)
        instances = reg.get_instances("api")
        assert len(instances) == 2

    def test_get_instances_healthy_only(self):
        reg = MeshServiceRegistry()
        reg.register("api", "h1", 8080)
        reg.register("api", "h2", 8080)
        reg.set_instance_status("api", "h2:8080", "inactive")
        healthy = reg.get_instances("api", healthy_only=True)
        assert len(healthy) == 1

    def test_set_instance_status(self):
        reg = MeshServiceRegistry()
        reg.register("api", "localhost", 8080)
        assert reg.set_instance_status("api", "localhost:8080", "draining") is True
        assert reg.set_instance_status("api", "missing", "x") is False

    def test_metadata(self):
        reg = MeshServiceRegistry()
        reg.register("api", "localhost", 8080, metadata={"region": "us"})
        assert reg.set_metadata("api", "localhost:8080", "zone", "a") is True
        assert reg.set_metadata("api", "missing", "k", "v") is False

    def test_cleanup_expired(self):
        reg = MeshServiceRegistry()
        reg.register("api", "h1", 8080, ttl=0)  # sinirsiz
        cleaned = reg.cleanup_expired()
        assert cleaned == 0

    def test_list_services(self):
        reg = MeshServiceRegistry()
        reg.register("api", "h1", 8080)
        reg.register("web", "h2", 3000)
        lst = reg.list_services()
        assert len(lst) == 2


# ===================== MeshLoadBalancer =====================


class TestMeshLoadBalancer:
    """MeshLoadBalancer testleri."""

    def test_init(self):
        lb = MeshLoadBalancer()
        assert lb.algorithm == "round_robin"

    def test_round_robin(self):
        lb = MeshLoadBalancer("round_robin")
        instances = [
            {"instance_id": "a", "status": "active"},
            {"instance_id": "b", "status": "active"},
        ]
        r1 = lb.select("svc", instances)
        r2 = lb.select("svc", instances)
        assert r1["instance_id"] != r2["instance_id"]

    def test_least_connections(self):
        lb = MeshLoadBalancer("least_connections")
        lb.add_connection("a")
        lb.add_connection("a")
        instances = [
            {"instance_id": "a", "status": "active"},
            {"instance_id": "b", "status": "active"},
        ]
        r = lb.select("svc", instances)
        assert r["instance_id"] == "b"

    def test_weighted(self):
        lb = MeshLoadBalancer("weighted")
        lb.set_weight("a", 1.0)
        lb.set_weight("b", 10.0)
        instances = [
            {"instance_id": "a", "status": "active"},
            {"instance_id": "b", "status": "active"},
        ]
        r = lb.select("svc", instances)
        assert r["instance_id"] == "b"

    def test_health_aware(self):
        lb = MeshLoadBalancer("health_aware")
        lb.set_health("a", False)
        lb.set_health("b", True)
        instances = [
            {"instance_id": "a", "status": "active"},
            {"instance_id": "b", "status": "active"},
        ]
        r = lb.select("svc", instances)
        assert r["instance_id"] == "b"

    def test_empty_instances(self):
        lb = MeshLoadBalancer()
        assert lb.select("svc", []) is None

    def test_sticky_session(self):
        lb = MeshLoadBalancer()
        instances = [
            {"instance_id": "a", "status": "active"},
            {"instance_id": "b", "status": "active"},
        ]
        r1 = lb.select("svc", instances, session_id="s1")
        r2 = lb.select("svc", instances, session_id="s1")
        assert r1["instance_id"] == r2["instance_id"]
        assert lb.sticky_count == 1

    def test_clear_sticky(self):
        lb = MeshLoadBalancer()
        instances = [{"instance_id": "a", "status": "active"}]
        lb.select("svc", instances, session_id="s1")
        assert lb.clear_sticky("s1") == 1
        assert lb.clear_sticky("missing") == 0

    def test_clear_sticky_all(self):
        lb = MeshLoadBalancer()
        instances = [{"instance_id": "a", "status": "active"}]
        lb.select("svc", instances, session_id="s1")
        lb.select("svc", instances, session_id="s2")
        assert lb.clear_sticky() == 2

    def test_connections(self):
        lb = MeshLoadBalancer()
        assert lb.add_connection("a") == 1
        assert lb.add_connection("a") == 2
        assert lb.remove_connection("a") == 1
        assert lb.total_connections == 1

    def test_get_stats(self):
        lb = MeshLoadBalancer()
        instances = [{"instance_id": "a", "status": "active"}]
        lb.select("svc", instances)
        stats = lb.get_stats()
        assert stats["a"] == 1


# ===================== MeshCircuitBreaker =====================


class TestMeshCircuitBreaker:
    """MeshCircuitBreaker testleri."""

    def test_init(self):
        cb = MeshCircuitBreaker()
        assert cb.circuit_count == 0

    def test_can_execute_closed(self):
        cb = MeshCircuitBreaker()
        assert cb.can_execute("svc") is True

    def test_record_success(self):
        cb = MeshCircuitBreaker()
        r = cb.record_success("svc")
        assert r["state"] == "closed"

    def test_record_failure_opens(self):
        cb = MeshCircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure("svc")
        assert cb.get_state("svc") == "open"
        assert cb.open_count == 1

    def test_open_rejects(self):
        cb = MeshCircuitBreaker(failure_threshold=1)
        cb.record_failure("svc")
        assert cb.can_execute("svc") is False

    def test_half_open_recovery(self):
        cb = MeshCircuitBreaker(
            failure_threshold=1, recovery_timeout=0.0,
        )
        cb.record_failure("svc")
        assert cb.get_state("svc") == "open"
        # Recovery timeout = 0 -> immediately half-open
        assert cb.can_execute("svc") is True
        assert cb.get_state("svc") == "half_open"

    def test_half_open_success_closes(self):
        cb = MeshCircuitBreaker(
            failure_threshold=1, recovery_timeout=0.0,
        )
        cb.record_failure("svc")
        cb.can_execute("svc")  # -> half_open
        cb.record_success("svc")
        assert cb.get_state("svc") == "closed"

    def test_half_open_failure_reopens(self):
        cb = MeshCircuitBreaker(
            failure_threshold=1, recovery_timeout=0.0,
        )
        cb.record_failure("svc")
        cb.can_execute("svc")  # -> half_open
        cb.record_failure("svc")
        assert cb.get_state("svc") == "open"

    def test_force_open(self):
        cb = MeshCircuitBreaker()
        cb.force_open("svc")
        assert cb.get_state("svc") == "open"

    def test_force_close(self):
        cb = MeshCircuitBreaker(failure_threshold=1)
        cb.record_failure("svc")
        cb.force_close("svc")
        assert cb.get_state("svc") == "closed"

    def test_reset(self):
        cb = MeshCircuitBreaker()
        cb.record_failure("svc")
        assert cb.reset("svc") is True
        assert cb.circuit_count == 0
        assert cb.reset("missing") is False

    def test_fallback(self):
        cb = MeshCircuitBreaker()
        cb.set_fallback("svc", lambda: {"default": True})
        result = cb.get_fallback("svc")
        assert result == {"default": True}
        assert cb.get_fallback("missing") is None

    def test_metrics(self):
        cb = MeshCircuitBreaker()
        cb.record_success("svc")
        cb.record_failure("svc")
        m = cb.get_metrics("svc")
        assert m["total_calls"] == 2
        assert m["total_successes"] == 1
        assert m["total_failures"] == 1


# ===================== RetryPolicy =====================


class TestRetryPolicy:
    """RetryPolicy testleri."""

    def test_init(self):
        rp = RetryPolicy()
        assert rp.policy_count == 0
        assert rp.retry_count == 0

    def test_should_retry(self):
        rp = RetryPolicy(max_attempts=3)
        r = rp.should_retry("svc", 0)
        assert r["retry"] is True
        assert r["attempt"] == 1

    def test_max_attempts(self):
        rp = RetryPolicy(max_attempts=3)
        r = rp.should_retry("svc", 3)
        assert r["retry"] is False
        assert r["reason"] == "max_attempts"

    def test_exponential_delay(self):
        rp = RetryPolicy(strategy="exponential", base_delay=1.0)
        r0 = rp.should_retry("svc", 0)
        r1 = rp.should_retry("svc", 1)
        assert r1["delay"] > r0["delay"]

    def test_fixed_delay(self):
        rp = RetryPolicy(strategy="fixed", base_delay=2.0)
        r = rp.should_retry("svc", 0)
        assert r["delay"] == 2.0

    def test_linear_delay(self):
        rp = RetryPolicy(strategy="linear", base_delay=1.0)
        r0 = rp.should_retry("svc", 0)
        r1 = rp.should_retry("svc", 1)
        assert r1["delay"] > r0["delay"]

    def test_max_delay(self):
        rp = RetryPolicy(
            max_attempts=20,
            strategy="exponential", base_delay=1.0, max_delay=5.0,
        )
        r = rp.should_retry("svc", 10)
        assert r["retry"] is True
        assert r["delay"] <= 5.0

    def test_service_policy(self):
        rp = RetryPolicy(max_attempts=3)
        rp.set_policy("svc", max_attempts=5)
        r = rp.should_retry("svc", 3)
        assert r["retry"] is True

    def test_budget(self):
        rp = RetryPolicy()
        rp.set_budget("svc", max_retries=2)
        rp.should_retry("svc", 0)
        rp.should_retry("svc", 0)
        r = rp.should_retry("svc", 0)
        assert r["retry"] is False
        assert r["reason"] == "budget_exhausted"

    def test_reset_budget(self):
        rp = RetryPolicy()
        rp.set_budget("svc", max_retries=1)
        rp.should_retry("svc", 0)
        assert rp.reset_budget("svc") is True
        r = rp.should_retry("svc", 0)
        assert r["retry"] is True
        assert rp.reset_budget("missing") is False

    def test_idempotency(self):
        rp = RetryPolicy()
        assert rp.mark_idempotent("key1") is True
        assert rp.mark_idempotent("key1") is False
        assert rp.is_idempotent("key1") is True
        assert rp.is_idempotent("missing") is False
        assert rp.idempotent_count == 1

    def test_history(self):
        rp = RetryPolicy()
        rp.should_retry("svc", 0)
        rp.should_retry("svc", 1)
        hist = rp.get_history()
        assert len(hist) == 2

    def test_history_filtered(self):
        rp = RetryPolicy()
        rp.should_retry("a", 0)
        rp.should_retry("b", 0)
        assert len(rp.get_history("a")) == 1

    def test_fibonacci_delay(self):
        rp = RetryPolicy(strategy="fibonacci", base_delay=1.0)
        r = rp.should_retry("svc", 0)
        assert r["retry"] is True
        assert r["delay"] >= 1.0


# ===================== TimeoutManager =====================


class TestTimeoutManager:
    """TimeoutManager testleri."""

    def test_init(self):
        tm = TimeoutManager()
        assert tm.default_timeout == 30.0
        assert tm.active_count == 0

    def test_set_timeout(self):
        tm = TimeoutManager()
        r = tm.set_timeout("svc", request_timeout=10.0)
        assert r["request"] == 10.0

    def test_get_timeout(self):
        tm = TimeoutManager(default_timeout=5.0)
        assert tm.get_timeout("svc")["request"] == 5.0
        tm.set_timeout("svc", request_timeout=10.0)
        assert tm.get_timeout("svc")["request"] == 10.0

    def test_start_request(self):
        tm = TimeoutManager()
        r = tm.start_request("r1", "svc")
        assert r["request_id"] == "r1"
        assert r["remaining"] > 0
        assert tm.active_count == 1

    def test_check_timeout_ok(self):
        tm = TimeoutManager(default_timeout=60.0)
        tm.start_request("r1", "svc")
        r = tm.check_timeout("r1")
        assert r["timed_out"] is False
        assert r["remaining"] > 0

    def test_check_timeout_expired(self):
        tm = TimeoutManager()
        import time
        tm.start_request("r1", "svc", deadline=time.time() - 1)
        r = tm.check_timeout("r1")
        assert r["timed_out"] is True
        assert tm.timeout_count == 1

    def test_check_timeout_not_found(self):
        tm = TimeoutManager()
        r = tm.check_timeout("missing")
        assert r["status"] == "not_found"

    def test_end_request(self):
        tm = TimeoutManager()
        tm.start_request("r1", "svc")
        r = tm.end_request("r1")
        assert r is not None
        assert r["elapsed"] >= 0
        assert tm.active_count == 0

    def test_end_request_not_found(self):
        tm = TimeoutManager()
        assert tm.end_request("missing") is None

    def test_propagate_deadline(self):
        tm = TimeoutManager()
        tm.start_request("parent", "svc")
        r = tm.propagate_deadline("parent", "child", "svc2")
        assert r["request_id"] == "child"
        assert tm.active_count == 2

    def test_propagate_no_parent(self):
        tm = TimeoutManager()
        r = tm.propagate_deadline("missing", "child", "svc")
        assert r["request_id"] == "child"

    def test_budget(self):
        tm = TimeoutManager()
        tm.set_budget("svc", 10.0)
        r = tm.consume_budget("svc", 3.0)
        assert r["remaining"] == 7.0
        assert r["exhausted"] is False

    def test_budget_exhausted(self):
        tm = TimeoutManager()
        tm.set_budget("svc", 5.0)
        r = tm.consume_budget("svc", 6.0)
        assert r["remaining"] == 0
        assert r["exhausted"] is True

    def test_budget_no_service(self):
        tm = TimeoutManager()
        r = tm.consume_budget("missing", 1.0)
        assert r["status"] == "no_budget"

    def test_timeout_history(self):
        tm = TimeoutManager()
        import time
        tm.start_request("r1", "svc", deadline=time.time() - 1)
        tm.check_timeout("r1")
        hist = tm.get_timeout_history()
        assert len(hist) == 1


# ===================== TrafficManager =====================


class TestTrafficManager:
    """TrafficManager testleri."""

    def test_init(self):
        tm = TrafficManager()
        assert tm.rule_count == 0

    def test_traffic_split(self):
        tm = TrafficManager()
        r = tm.set_traffic_split("svc", [
            {"version": "v1", "weight": 80},
            {"version": "v2", "weight": 20},
        ])
        assert r["splits"] == 2
        assert tm.rule_count == 1

    def test_route_default(self):
        tm = TrafficManager()
        r = tm.route_request("svc", "req1")
        assert r["version"] == "default"
        assert r["routing"] == "default"

    def test_route_with_split(self):
        tm = TrafficManager()
        tm.set_traffic_split("svc", [
            {"version": "v1", "weight": 100},
        ])
        r = tm.route_request("svc", "req1")
        assert r["version"] == "v1"
        assert r["routing"] == "split"

    def test_canary(self):
        tm = TrafficManager()
        r = tm.setup_canary("svc", "v2", percentage=100.0)
        assert r["percentage"] == 100.0
        assert tm.canary_count == 1
        route = tm.route_request("svc", "req1")
        assert route["version"] == "v2"
        assert route["routing"] == "canary"

    def test_promote_canary(self):
        tm = TrafficManager()
        tm.setup_canary("svc", "v2", percentage=10.0)
        r = tm.promote_canary("svc")
        assert r["status"] == "promoted"

    def test_promote_canary_not_found(self):
        tm = TrafficManager()
        r = tm.promote_canary("missing")
        assert r["status"] == "error"

    def test_rollback_canary(self):
        tm = TrafficManager()
        tm.setup_canary("svc", "v2")
        assert tm.rollback_canary("svc") is True
        assert tm.rollback_canary("missing") is False

    def test_ab_test(self):
        tm = TrafficManager()
        r = tm.setup_ab_test("svc", "v1", "v2", split_pct=50.0)
        assert r["variant_a"] == "v1"
        assert tm.ab_test_count == 1
        # Deterministik: route bircok istek
        versions = set()
        for i in range(50):
            route = tm.route_request("svc", f"req_{i}")
            versions.add(route["version"])
        assert "v1" in versions or "v2" in versions

    def test_end_ab_test(self):
        tm = TrafficManager()
        tm.setup_ab_test("svc", "v1", "v2")
        r = tm.end_ab_test("svc", winner="v2")
        assert r["winner"] == "v2"

    def test_end_ab_test_not_found(self):
        tm = TrafficManager()
        r = tm.end_ab_test("missing")
        assert r["status"] == "error"

    def test_dark_launch(self):
        tm = TrafficManager()
        r = tm.setup_dark_launch("svc", "v2", mirror_pct=100.0)
        assert r["mirror_pct"] == 100.0
        assert tm.dark_launch_count == 1

    def test_should_mirror(self):
        tm = TrafficManager()
        tm.setup_dark_launch("svc", "v2", mirror_pct=100.0)
        assert tm.should_mirror("svc", "req1") is True

    def test_should_not_mirror(self):
        tm = TrafficManager()
        assert tm.should_mirror("svc", "req1") is False

    def test_routing_count(self):
        tm = TrafficManager()
        tm.route_request("svc", "r1")
        tm.route_request("svc", "r2")
        assert tm.routing_count == 2


# ===================== SidecarProxy =====================


class TestSidecarProxy:
    """SidecarProxy testleri."""

    def test_init(self):
        sp = SidecarProxy("proxy1")
        assert sp.proxy_id == "proxy1"
        assert sp.log_count == 0

    def test_intercept_request(self):
        sp = SidecarProxy()
        r = sp.intercept_request({"path": "/api", "method": "GET"})
        assert "headers" in r
        assert r["headers"]["x-proxy-id"] == "default"

    def test_intercept_response(self):
        sp = SidecarProxy()
        r = sp.intercept_response({"status_code": 200, "body": "ok"})
        assert r["headers"]["x-proxy-id"] == "default"

    def test_error_tracking(self):
        sp = SidecarProxy()
        sp.intercept_response({"status_code": 500})
        stats = sp.get_stats()
        assert stats["total_errors"] == 1

    def test_header_injection(self):
        sp = SidecarProxy()
        sp.inject_header("x-trace-id", "abc123")
        r = sp.intercept_request({"path": "/"})
        assert r["headers"]["x-trace-id"] == "abc123"

    def test_remove_header(self):
        sp = SidecarProxy()
        sp.inject_header("x-test", "val")
        assert sp.remove_header("x-test") is True
        assert sp.remove_header("missing") is False

    def test_mtls(self):
        sp = SidecarProxy()
        assert sp.mtls_enabled is False
        sp.enable_mtls(cert="cert.pem", key="key.pem")
        assert sp.mtls_enabled is True
        r = sp.intercept_request({"path": "/"})
        assert r["mtls"] is True
        sp.disable_mtls()
        assert sp.mtls_enabled is False

    def test_request_interceptor(self):
        sp = SidecarProxy()
        sp.add_request_interceptor(
            "add_auth", lambda r: {**r, "auth": True},
        )
        r = sp.intercept_request({"path": "/"})
        assert r.get("auth") is True
        assert sp.interceptor_count == 1

    def test_response_interceptor(self):
        sp = SidecarProxy()
        sp.add_response_interceptor(
            "add_cors", lambda r: {**r, "cors": True},
        )
        r = sp.intercept_response({"status_code": 200})
        assert r.get("cors") is True

    def test_access_log(self):
        sp = SidecarProxy()
        sp.intercept_request({"path": "/api"})
        sp.intercept_response({"status_code": 200})
        log = sp.get_access_log()
        assert len(log) == 2

    def test_stats(self):
        sp = SidecarProxy()
        sp.intercept_request({"path": "/"})
        sp.intercept_response({"status_code": 200})
        stats = sp.get_stats()
        assert stats["total_requests"] == 1
        assert stats["total_responses"] == 1


# ===================== ServiceMeshConfig =====================


class TestServiceMeshConfig:
    """ServiceMeshConfig testleri."""

    def test_init(self):
        mc = ServiceMeshConfig()
        assert mc.policy_count == 0

    def test_set_policy(self):
        mc = ServiceMeshConfig()
        r = mc.set_policy("retry", "retry", {"max": 3})
        assert r["name"] == "retry"
        assert mc.policy_count == 1

    def test_get_policy(self):
        mc = ServiceMeshConfig()
        mc.set_policy("p1", "type", {"k": "v"})
        p = mc.get_policy("p1")
        assert p is not None
        assert mc.get_policy("missing") is None

    def test_remove_policy(self):
        mc = ServiceMeshConfig()
        mc.set_policy("p1", "type", {})
        assert mc.remove_policy("p1") is True
        assert mc.remove_policy("missing") is False

    def test_add_route(self):
        mc = ServiceMeshConfig()
        r = mc.add_route("svc", "/api", "api-v1")
        assert r["destination"] == "api-v1"
        assert mc.route_count == 1

    def test_get_routes(self):
        mc = ServiceMeshConfig()
        mc.add_route("svc", "/api", "v1")
        mc.add_route("svc", "/web", "v2")
        routes = mc.get_routes("svc")
        assert len(routes) == 2

    def test_match_route(self):
        mc = ServiceMeshConfig()
        mc.add_route("svc", "/api", "backend")
        r = mc.match_route("svc", "/api/users")
        assert r is not None
        assert r["destination"] == "backend"

    def test_match_route_method(self):
        mc = ServiceMeshConfig()
        mc.add_route("svc", "/api", "v1", method="GET")
        assert mc.match_route("svc", "/api", "GET") is not None
        assert mc.match_route("svc", "/api", "POST") is None

    def test_match_route_wildcard(self):
        mc = ServiceMeshConfig()
        mc.add_route("svc", "*", "catch_all")
        assert mc.match_route("svc", "/anything") is not None

    def test_match_route_not_found(self):
        mc = ServiceMeshConfig()
        assert mc.match_route("svc", "/api") is None

    def test_rate_limit(self):
        mc = ServiceMeshConfig()
        r = mc.set_rate_limit("svc", 100)
        assert r["rps"] == 100
        assert mc.rate_limit_count == 1

    def test_check_rate_limit(self):
        mc = ServiceMeshConfig()
        mc.set_rate_limit("svc", 1, burst=2)
        r1 = mc.check_rate_limit("svc")
        assert r1["allowed"] is True
        r2 = mc.check_rate_limit("svc")
        assert r2["allowed"] is True
        r3 = mc.check_rate_limit("svc")
        assert r3["limited"] is True

    def test_check_rate_limit_no_limit(self):
        mc = ServiceMeshConfig()
        r = mc.check_rate_limit("svc")
        assert r["allowed"] is True

    def test_access_policy(self):
        mc = ServiceMeshConfig()
        mc.set_access_policy("svc", ["web", "mobile"])
        assert mc.check_access("svc", "web") is True
        assert mc.check_access("svc", "hacker") is False

    def test_access_policy_denied(self):
        mc = ServiceMeshConfig()
        mc.set_access_policy("svc", [], denied_sources=["bad"])
        assert mc.check_access("svc", "bad") is False

    def test_access_no_policy(self):
        mc = ServiceMeshConfig()
        assert mc.check_access("svc", "anyone") is True

    def test_fault_injection(self):
        mc = ServiceMeshConfig()
        r = mc.inject_fault("svc", "delay", probability=0.5, delay_ms=100)
        assert r["fault_type"] == "delay"
        assert mc.fault_count == 1

    def test_get_fault_injection(self):
        mc = ServiceMeshConfig()
        mc.inject_fault("svc", "abort", status_code=503)
        f = mc.get_fault_injection("svc")
        assert f is not None
        assert f["status_code"] == 503
        assert mc.get_fault_injection("missing") is None

    def test_remove_fault_injection(self):
        mc = ServiceMeshConfig()
        mc.inject_fault("svc", "delay")
        assert mc.remove_fault_injection("svc") is True
        assert mc.remove_fault_injection("missing") is False


# ===================== MeshOrchestrator =====================


class TestMeshOrchestrator:
    """MeshOrchestrator testleri."""

    def test_init(self):
        mo = MeshOrchestrator()
        assert mo.is_initialized is False

    def test_init_custom(self):
        mo = MeshOrchestrator(
            lb_algorithm="weighted",
            default_timeout=10.0,
        )
        assert mo.lb.algorithm == "weighted"

    def test_initialize(self):
        mo = MeshOrchestrator()
        r = mo.initialize(services=[
            {"name": "api", "host": "h1", "port": 8080},
            {"name": "web", "host": "h2", "port": 3000},
        ])
        assert r["status"] == "initialized"
        assert r["services_registered"] == 2
        assert mo.is_initialized is True

    def test_initialize_empty(self):
        mo = MeshOrchestrator()
        r = mo.initialize()
        assert r["services_registered"] == 0

    def test_route_request(self):
        mo = MeshOrchestrator()
        mo.registry.register("api", "h1", 8080)
        r = mo.route_request("api", {"request_id": "r1"})
        assert r["status"] == "routed"
        assert r["instance"] == "h1:8080"

    def test_route_request_circuit_open(self):
        mo = MeshOrchestrator(failure_threshold=1)
        mo.cb.record_failure("api")
        r = mo.route_request("api", {"request_id": "r1"})
        assert r["status"] == "circuit_open"

    def test_route_request_rate_limited(self):
        mo = MeshOrchestrator()
        mo.registry.register("api", "h1", 8080)
        mo.config.set_rate_limit("api", 1, burst=1)
        mo.route_request("api", {"request_id": "r1"})
        r = mo.route_request("api", {"request_id": "r2"})
        assert r["status"] == "rate_limited"

    def test_route_request_no_instances(self):
        mo = MeshOrchestrator()
        mo.registry.register("api", "h1", 8080)
        mo.registry.set_instance_status("api", "h1:8080", "inactive")
        r = mo.route_request("api", {"request_id": "r1"})
        assert r["status"] == "no_instances"

    def test_record_result_success(self):
        mo = MeshOrchestrator()
        r = mo.record_result("api", "r1", success=True)
        assert r["success"] is True
        assert r["circuit_state"] == "closed"

    def test_record_result_failure(self):
        mo = MeshOrchestrator()
        r = mo.record_result("api", "r1", success=False)
        assert r["success"] is False

    def test_get_service_health(self):
        mo = MeshOrchestrator()
        mo.registry.register("api", "h1", 8080)
        h = mo.get_service_health("api")
        assert h["service"] == "api"
        assert h["instances"] == 1
        assert h["healthy"] == 1

    def test_get_service_health_not_found(self):
        mo = MeshOrchestrator()
        r = mo.get_service_health("missing")
        assert r["status"] == "not_found"

    def test_get_snapshot(self):
        mo = MeshOrchestrator()
        mo.initialize(services=[
            {"name": "api", "host": "h1", "port": 8080},
        ])
        snap = mo.get_snapshot()
        assert snap["total_services"] == 1
        assert snap["initialized"] is True

    def test_get_analytics(self):
        mo = MeshOrchestrator()
        mo.initialize()
        analytics = mo.get_analytics()
        assert "registry" in analytics
        assert "load_balancer" in analytics
        assert "circuit_breaker" in analytics
        assert "retry" in analytics
        assert "traffic" in analytics

    def test_request_count(self):
        mo = MeshOrchestrator()
        mo.registry.register("api", "h1", 8080)
        mo.route_request("api", {"request_id": "r1"})
        assert mo.request_count == 1


# ===================== Config Settings =====================


class TestConfigSettings:
    """Config ayarlari testleri."""

    def test_servicemesh_settings(self):
        from app.config import settings
        assert hasattr(settings, "servicemesh_enabled")
        assert hasattr(settings, "default_timeout_ms")
        assert hasattr(settings, "circuit_failure_threshold")
        assert hasattr(settings, "retry_max_attempts")
        assert hasattr(settings, "load_balancer_algorithm")

    def test_servicemesh_defaults(self):
        from app.config import settings
        assert settings.servicemesh_enabled is True
        assert settings.default_timeout_ms == 30000
        assert settings.circuit_failure_threshold == 5
        assert settings.retry_max_attempts == 3
        assert settings.load_balancer_algorithm == "round_robin"
