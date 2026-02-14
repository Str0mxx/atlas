"""External Integration Hub testleri."""

import unittest
from datetime import datetime, timezone, timedelta

from app.models.integration import (
    AuthType,
    CacheEntry,
    ConnectionRecord,
    ErrorCategory,
    IntegrationError,
    IntegrationSnapshot,
    ProtocolType,
    ServiceStatus,
    SyncMode,
    SyncRecord,
    WebhookDirection,
    WebhookRecord,
)

from app.core.integration.api_connector import APIConnector
from app.core.integration.auth_handler import AuthHandler
from app.core.integration.data_sync import DataSync
from app.core.integration.error_handler import IntegrationErrorHandler
from app.core.integration.integration_hub import IntegrationHub
from app.core.integration.rate_limiter import RateLimiter
from app.core.integration.response_cache import ResponseCache
from app.core.integration.service_registry import ExternalServiceRegistry
from app.core.integration.webhook_manager import WebhookManager


# ======================== Model Testleri ========================

class TestIntegrationModels(unittest.TestCase):
    """Model testleri."""

    def test_connection_record_defaults(self):
        r = ConnectionRecord()
        assert len(r.connection_id) == 8
        assert r.protocol == ProtocolType.REST
        assert r.status == ServiceStatus.UNKNOWN

    def test_sync_record_defaults(self):
        r = SyncRecord()
        assert len(r.sync_id) == 8
        assert r.mode == SyncMode.DELTA
        assert r.success is True
        assert r.conflicts == 0

    def test_webhook_record_defaults(self):
        r = WebhookRecord()
        assert len(r.webhook_id) == 8
        assert r.direction == WebhookDirection.INCOMING
        assert r.verified is False

    def test_integration_error_defaults(self):
        e = IntegrationError()
        assert len(e.error_id) == 8
        assert e.category == ErrorCategory.NETWORK
        assert e.retryable is True

    def test_cache_entry_defaults(self):
        e = CacheEntry()
        assert e.ttl_seconds == 300
        assert e.hit_count == 0

    def test_integration_snapshot_defaults(self):
        s = IntegrationSnapshot()
        assert s.total_services == 0
        assert s.cache_hit_rate == 0.0

    def test_enum_values(self):
        assert AuthType.OAUTH2.value == "oauth2"
        assert ProtocolType.GRPC.value == "grpc"
        assert SyncMode.BIDIRECTIONAL.value == "bidirectional"
        assert ServiceStatus.DEGRADED.value == "degraded"
        assert ErrorCategory.RATE_LIMIT.value == "rate_limit"
        assert WebhookDirection.OUTGOING.value == "outgoing"

    def test_unique_ids(self):
        r1 = ConnectionRecord()
        r2 = ConnectionRecord()
        assert r1.connection_id != r2.connection_id

    def test_custom_connection(self):
        r = ConnectionRecord(
            service_name="test",
            protocol=ProtocolType.GRAPHQL,
            base_url="https://api.test.com",
            status=ServiceStatus.ACTIVE,
            latency_ms=42.5,
        )
        assert r.service_name == "test"
        assert r.protocol == ProtocolType.GRAPHQL
        assert r.latency_ms == 42.5

    def test_custom_sync(self):
        r = SyncRecord(
            source="a",
            target="b",
            mode=SyncMode.FULL,
            records_synced=100,
            conflicts=3,
        )
        assert r.source == "a"
        assert r.records_synced == 100
        assert r.conflicts == 3


# ======================== APIConnector Testleri ========================

class TestAPIConnector(unittest.TestCase):
    """APIConnector testleri."""

    def setUp(self):
        self.conn = APIConnector(default_timeout=15)

    def test_init(self):
        assert self.conn.service_count == 0
        assert self.conn.request_count == 0

    def test_configure_service(self):
        result = self.conn.configure_service(
            "test", "https://api.test.com",
        )
        assert result["name"] == "test"
        assert result["protocol"] == "rest"
        assert self.conn.service_count == 1

    def test_rest_request(self):
        self.conn.configure_service("svc", "https://api.svc.com")
        result = self.conn.rest_request(
            "svc", "GET", "/users",
        )
        assert result["success"] is True
        assert result["method"] == "GET"
        assert self.conn.request_count == 1

    def test_rest_request_not_found(self):
        result = self.conn.rest_request("missing", "GET", "/")
        assert result["success"] is False

    def test_graphql_query(self):
        self.conn.configure_service(
            "gql", "https://gql.test.com",
            protocol=ProtocolType.GRAPHQL,
        )
        result = self.conn.graphql_query(
            "gql", "{ users { id name } }",
        )
        assert result["success"] is True
        assert "query" in result

    def test_graphql_not_found(self):
        result = self.conn.graphql_query("missing", "{ test }")
        assert result["success"] is False

    def test_soap_call(self):
        self.conn.configure_service(
            "soap", "https://soap.test.com",
            protocol=ProtocolType.SOAP,
        )
        result = self.conn.soap_call("soap", "GetUser")
        assert result["success"] is True
        assert result["action"] == "GetUser"

    def test_soap_not_found(self):
        result = self.conn.soap_call("missing", "Test")
        assert result["success"] is False

    def test_websocket_send(self):
        self.conn.configure_service(
            "ws", "wss://ws.test.com",
            protocol=ProtocolType.WEBSOCKET,
        )
        result = self.conn.websocket_send(
            "ws", {"type": "ping"}, "chat",
        )
        assert result["success"] is True
        assert result["channel"] == "chat"

    def test_websocket_not_found(self):
        result = self.conn.websocket_send("missing", {})
        assert result["success"] is False

    def test_grpc_call(self):
        self.conn.configure_service(
            "grpc", "grpc://grpc.test.com",
            protocol=ProtocolType.GRPC,
        )
        result = self.conn.grpc_call(
            "grpc", "GetUser", {"id": 1},
        )
        assert result["success"] is True
        assert result["method"] == "GetUser"

    def test_grpc_not_found(self):
        result = self.conn.grpc_call("missing", "Test")
        assert result["success"] is False

    def test_get_service_config(self):
        self.conn.configure_service("svc", "https://svc.com")
        config = self.conn.get_service_config("svc")
        assert config is not None
        assert config["name"] == "svc"

    def test_get_service_config_not_found(self):
        assert self.conn.get_service_config("nope") is None

    def test_request_history(self):
        self.conn.configure_service("svc", "https://svc.com")
        self.conn.rest_request("svc", "GET", "/a")
        self.conn.rest_request("svc", "POST", "/b")
        history = self.conn.get_request_history("svc")
        assert len(history) == 2

    def test_request_history_filtered(self):
        self.conn.configure_service("a", "https://a.com")
        self.conn.configure_service("b", "https://b.com")
        self.conn.rest_request("a", "GET", "/")
        self.conn.rest_request("b", "GET", "/")
        assert len(self.conn.get_request_history("a")) == 1

    def test_connection_count(self):
        self.conn.configure_service("svc", "https://svc.com")
        self.conn.rest_request("svc", "GET", "/")
        assert self.conn.connection_count == 1


# ======================== AuthHandler Testleri ========================

class TestAuthHandler(unittest.TestCase):
    """AuthHandler testleri."""

    def setUp(self):
        self.auth = AuthHandler()

    def test_init(self):
        assert self.auth.credential_count == 0
        assert self.auth.active_token_count == 0

    def test_register_api_key(self):
        result = self.auth.register_credentials(
            "svc", AuthType.API_KEY,
            {"api_key": "test-key-123"},
        )
        assert result["auth_type"] == "api_key"
        assert self.auth.credential_count == 1

    def test_api_key_auth(self):
        self.auth.register_credentials(
            "svc", AuthType.API_KEY,
            {"api_key": "key123", "header_name": "X-Key"},
        )
        headers = self.auth.api_key_auth("svc")
        assert headers["X-Key"] == "key123"

    def test_api_key_auth_missing(self):
        headers = self.auth.api_key_auth("missing")
        assert headers == {}

    def test_oauth2_authenticate(self):
        self.auth.register_credentials(
            "svc", AuthType.OAUTH2,
            {"client_id": "cid", "client_secret": "cs"},
        )
        result = self.auth.oauth2_authenticate("svc")
        assert result["success"] is True
        assert "access_token" in result
        assert self.auth.active_token_count == 1

    def test_oauth2_missing(self):
        result = self.auth.oauth2_authenticate("missing")
        assert result["success"] is False

    def test_jwt_authenticate(self):
        self.auth.register_credentials(
            "svc", AuthType.JWT,
            {"secret": "jwt-secret"},
        )
        result = self.auth.jwt_authenticate("svc")
        assert result["success"] is True
        assert result["token_type"] == "JWT"

    def test_jwt_missing(self):
        result = self.auth.jwt_authenticate("missing")
        assert result["success"] is False

    def test_basic_auth(self):
        self.auth.register_credentials(
            "svc", AuthType.BASIC,
            {"username": "user", "password": "pass"},
        )
        headers = self.auth.basic_auth("svc")
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    def test_basic_auth_missing(self):
        headers = self.auth.basic_auth("missing")
        assert headers == {}

    def test_refresh_token(self):
        self.auth.register_credentials(
            "svc", AuthType.OAUTH2,
            {"client_id": "cid", "client_secret": "cs"},
        )
        self.auth.oauth2_authenticate("svc")
        result = self.auth.refresh_token("svc")
        assert result["success"] is True
        assert self.auth.refresh_count == 1

    def test_refresh_token_missing(self):
        result = self.auth.refresh_token("missing")
        assert result["success"] is False

    def test_get_auth_headers_api_key(self):
        self.auth.register_credentials(
            "svc", AuthType.API_KEY,
            {"api_key": "k123"},
        )
        headers = self.auth.get_auth_headers("svc")
        assert "X-API-Key" in headers

    def test_get_auth_headers_bearer(self):
        self.auth.register_credentials(
            "svc", AuthType.OAUTH2,
            {"client_id": "c", "client_secret": "s"},
        )
        self.auth.oauth2_authenticate("svc")
        headers = self.auth.get_auth_headers("svc")
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")

    def test_get_auth_headers_missing(self):
        assert self.auth.get_auth_headers("missing") == {}

    def test_revoke_token(self):
        self.auth.register_credentials(
            "svc", AuthType.OAUTH2,
            {"client_id": "c", "client_secret": "s"},
        )
        self.auth.oauth2_authenticate("svc")
        assert self.auth.revoke_token("svc") is True
        assert self.auth.active_token_count == 0

    def test_revoke_token_missing(self):
        assert self.auth.revoke_token("missing") is False

    def test_has_credentials(self):
        self.auth.register_credentials(
            "svc", AuthType.API_KEY, {"api_key": "k"},
        )
        assert self.auth.has_credentials("svc") is True
        assert self.auth.has_credentials("nope") is False


# ======================== WebhookManager Testleri ========================

class TestWebhookManager(unittest.TestCase):
    """WebhookManager testleri."""

    def setUp(self):
        self.wm = WebhookManager(max_retries=3)

    def test_init(self):
        assert self.wm.webhook_count == 0
        assert self.wm.event_count == 0

    def test_register_incoming(self):
        wh = self.wm.register_webhook(
            "https://hook.test/in", "order.created",
        )
        assert wh.direction == WebhookDirection.INCOMING
        assert self.wm.webhook_count == 1

    def test_register_outgoing(self):
        wh = self.wm.register_webhook(
            "https://hook.test/out", "user.updated",
            direction=WebhookDirection.OUTGOING,
        )
        assert wh.direction == WebhookDirection.OUTGOING

    def test_register_with_secret(self):
        wh = self.wm.register_webhook(
            "https://hook.test", "event",
            secret="my-secret",
        )
        assert wh.verified is True

    def test_process_incoming(self):
        self.wm.register_webhook(
            "https://hook.test", "order.created",
        )
        result = self.wm.process_incoming(
            "order.created", {"id": 1},
        )
        assert result["success"] is True
        assert self.wm.event_count == 1

    def test_send_outgoing(self):
        self.wm.register_webhook(
            "https://hook.test/out", "notify",
            direction=WebhookDirection.OUTGOING,
        )
        result = self.wm.send_outgoing(
            "notify", {"msg": "hello"},
        )
        assert result["success"] is True
        assert result["targets_count"] == 1

    def test_send_outgoing_no_target(self):
        result = self.wm.send_outgoing(
            "unknown", {"msg": "test"},
        )
        assert result["success"] is False

    def test_send_outgoing_with_url(self):
        result = self.wm.send_outgoing(
            "event", {"data": 1},
            target_url="https://custom.url",
        )
        assert result["success"] is True

    def test_signature_verification(self):
        payload = {"key": "value"}
        secret = "test-secret"
        sig = self.wm.generate_signature(payload, secret)
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA256 hex

    def test_add_route(self):
        self.wm.add_route("event.a", "wh1")
        self.wm.add_route("event.a", "wh2")
        routes = self.wm.get_routes("event.a")
        assert len(routes["event.a"]) == 2

    def test_get_routes_all(self):
        self.wm.add_route("a", "1")
        self.wm.add_route("b", "2")
        routes = self.wm.get_routes()
        assert "a" in routes
        assert "b" in routes

    def test_get_events(self):
        self.wm.register_webhook("https://h.t", "ev")
        self.wm.process_incoming("ev", {"a": 1})
        self.wm.process_incoming("ev", {"b": 2})
        events = self.wm.get_events("ev")
        assert len(events) == 2

    def test_get_events_limited(self):
        self.wm.register_webhook("https://h.t", "ev")
        for i in range(5):
            self.wm.process_incoming("ev", {"i": i})
        events = self.wm.get_events("ev", limit=3)
        assert len(events) == 3

    def test_route_count(self):
        self.wm.add_route("a", "1")
        self.wm.add_route("a", "2")
        self.wm.add_route("b", "3")
        assert self.wm.route_count == 3


# ======================== DataSync Testleri ========================

class TestDataSync(unittest.TestCase):
    """DataSync testleri."""

    def setUp(self):
        self.sync = DataSync()

    def test_init(self):
        assert self.sync.sync_count == 0
        assert self.sync.schedule_count == 0

    def test_full_sync(self):
        data = [{"id": 1}, {"id": 2}]
        record = self.sync.full_sync("src", "dst", data)
        assert record.mode == SyncMode.FULL
        assert record.records_synced == 2
        assert self.sync.sync_count == 1

    def test_delta_sync(self):
        changes = [{"id": 1, "op": "update"}]
        record = self.sync.delta_sync("src", "dst", changes)
        assert record.mode == SyncMode.DELTA
        assert record.records_synced == 1

    def test_bidirectional_sync(self):
        data_a = [{"id": 1, "name": "a"}]
        data_b = [{"id": 2, "name": "b"}]
        record = self.sync.bidirectional_sync(
            "svc_a", "svc_b", data_a, data_b,
        )
        assert record.mode == SyncMode.BIDIRECTIONAL
        assert record.records_synced == 2
        assert record.conflicts == 0

    def test_bidirectional_with_conflicts(self):
        data_a = [{"id": 1, "name": "from_a"}]
        data_b = [{"id": 1, "name": "from_b"}]
        record = self.sync.bidirectional_sync(
            "a", "b", data_a, data_b,
        )
        assert record.conflicts == 1

    def test_conflict_rule(self):
        self.sync.set_conflict_rule("field1", "target_wins")
        assert self.sync.conflict_rule_count == 1

    def test_schedule_sync(self):
        schedule = self.sync.schedule_sync(
            "src", "dst", SyncMode.DELTA, 30,
        )
        assert schedule["interval_minutes"] == 30
        assert self.sync.schedule_count == 1

    def test_get_due_syncs(self):
        self.sync.schedule_sync("a", "b", SyncMode.DELTA)
        due = self.sync.get_due_syncs()
        assert len(due) == 1  # last_run is None

    def test_sync_history(self):
        self.sync.full_sync("a", "b", [{"id": 1}])
        self.sync.delta_sync("a", "b", [{"id": 2}])
        history = self.sync.get_sync_history("a")
        assert len(history) == 2

    def test_sync_history_filtered(self):
        self.sync.full_sync("a", "b", [])
        self.sync.full_sync("c", "d", [])
        assert len(self.sync.get_sync_history("a")) == 1

    def test_last_sync_time(self):
        self.sync.full_sync("src", "dst", [])
        last = self.sync.get_last_sync_time("src", "dst")
        assert last is not None

    def test_last_sync_time_missing(self):
        assert self.sync.get_last_sync_time("x", "y") is None


# ======================== ExternalServiceRegistry Testleri ========================

class TestExternalServiceRegistry(unittest.TestCase):
    """ExternalServiceRegistry testleri."""

    def setUp(self):
        self.reg = ExternalServiceRegistry()

    def test_init(self):
        assert self.reg.service_count == 0

    def test_register_service(self):
        svc = self.reg.register_service(
            "payment", "https://pay.api.com",
            tags=["billing"],
        )
        assert svc["name"] == "payment"
        assert self.reg.service_count == 1

    def test_check_health_ok(self):
        self.reg.register_service("svc", "https://svc.com")
        result = self.reg.check_health("svc", True, 50.0)
        assert result["healthy"] is True
        assert result["status"] == ServiceStatus.ACTIVE.value

    def test_check_health_fail(self):
        self.reg.register_service("svc", "https://svc.com")
        result = self.reg.check_health("svc", False)
        assert result["healthy"] is False
        assert result["status"] == ServiceStatus.DEGRADED.value

    def test_check_health_missing(self):
        result = self.reg.check_health("missing")
        assert "error" in result

    def test_circuit_breaker_opens(self):
        self.reg.register_service("svc", "https://svc.com")
        self.reg.set_circuit_breaker_threshold("svc", 3)
        for _ in range(3):
            self.reg.check_health("svc", False)
        state = self.reg.get_circuit_breaker_state("svc")
        assert state == "open"

    def test_circuit_breaker_recovery(self):
        self.reg.register_service("svc", "https://svc.com")
        self.reg.set_circuit_breaker_threshold("svc", 2)
        self.reg.check_health("svc", False)
        self.reg.check_health("svc", False)
        assert self.reg.get_circuit_breaker_state("svc") == "open"
        # Basarili kontrol half_open yapar
        self.reg.check_health("svc", True)
        assert self.reg.get_circuit_breaker_state("svc") == "half_open"
        # Bir daha basarili: closed
        self.reg.check_health("svc", True)
        assert self.reg.get_circuit_breaker_state("svc") == "closed"

    def test_discover_services(self):
        self.reg.register_service(
            "a", "https://a.com", tags=["api"],
        )
        self.reg.register_service(
            "b", "https://b.com", tags=["db"],
        )
        all_svcs = self.reg.discover_services()
        assert len(all_svcs) == 2
        api_svcs = self.reg.discover_services(tag="api")
        assert len(api_svcs) == 1

    def test_failover(self):
        self.reg.register_service("primary", "https://p.com")
        self.reg.register_service("backup", "https://b.com")
        assert self.reg.set_failover("primary", "backup") is True

    def test_failover_missing(self):
        assert self.reg.set_failover("x", "y") is False

    def test_get_active_service_failover(self):
        self.reg.register_service("primary", "https://p.com")
        self.reg.register_service("backup", "https://b.com")
        self.reg.set_failover("primary", "backup")
        # Backup'i aktif yap
        self.reg.check_health("backup", True)
        # Primary'yi down yap
        self.reg.set_circuit_breaker_threshold("primary", 1)
        self.reg.check_health("primary", False)
        active = self.reg.get_active_service("primary")
        assert active == "backup"

    def test_unregister(self):
        self.reg.register_service("svc", "https://svc.com")
        assert self.reg.unregister_service("svc") is True
        assert self.reg.service_count == 0

    def test_unregister_missing(self):
        assert self.reg.unregister_service("nope") is False

    def test_get_service(self):
        self.reg.register_service("svc", "https://svc.com")
        svc = self.reg.get_service("svc")
        assert svc is not None
        assert svc["url"] == "https://svc.com"

    def test_active_count(self):
        self.reg.register_service("a", "https://a.com")
        self.reg.register_service("b", "https://b.com")
        self.reg.check_health("a", True)
        assert self.reg.active_count == 1


# ======================== RateLimiter Testleri ========================

class TestRateLimiter(unittest.TestCase):
    """RateLimiter testleri."""

    def setUp(self):
        self.rl = RateLimiter(default_limit=10)

    def test_init(self):
        assert self.rl.service_count == 0
        assert self.rl.queue_size == 0

    def test_set_limit(self):
        limit = self.rl.set_limit("svc", 50)
        assert limit["requests_per_minute"] == 50
        assert self.rl.service_count == 1

    def test_check_limit_allowed(self):
        self.rl.set_limit("svc", 10)
        result = self.rl.check_limit("svc")
        assert result["allowed"] is True
        assert result["remaining"] == 10

    def test_check_limit_blocked(self):
        self.rl.set_limit("svc", 2)
        self.rl.record_request("svc")
        self.rl.record_request("svc")
        result = self.rl.check_limit("svc")
        assert result["allowed"] is False
        assert self.rl.blocked_count == 1

    def test_priority_bypass(self):
        self.rl.set_limit("svc", 1, priority_bypass=True)
        self.rl.record_request("svc")
        result = self.rl.check_limit("svc", priority=1)
        assert result["allowed"] is True
        assert result["reason"] == "priority_bypass"

    def test_enqueue(self):
        result = self.rl.enqueue(
            "svc", {"method": "GET", "url": "/test"},
        )
        assert result["total_queued"] == 1
        assert self.rl.queue_size == 1

    def test_dequeue(self):
        self.rl.enqueue("svc", {"a": 1})
        item = self.rl.dequeue()
        assert item is not None
        assert item["data"]["a"] == 1
        assert self.rl.queue_size == 0

    def test_dequeue_by_service(self):
        self.rl.enqueue("a", {"x": 1})
        self.rl.enqueue("b", {"y": 2})
        item = self.rl.dequeue("b")
        assert item["service"] == "b"

    def test_dequeue_empty(self):
        assert self.rl.dequeue() is None
        assert self.rl.dequeue("svc") is None

    def test_get_quota(self):
        self.rl.set_limit("svc", 100)
        self.rl.record_request("svc")
        quota = self.rl.get_quota("svc")
        assert quota["limit"] == 100
        assert quota["used"] == 1
        assert quota["remaining"] == 99

    def test_backoff_exponential(self):
        result = self.rl.apply_backoff("svc", 3, "exponential")
        assert result["wait_seconds"] == 8  # 2^3

    def test_backoff_linear(self):
        result = self.rl.apply_backoff("svc", 4, "linear")
        assert result["wait_seconds"] == 20  # 4*5

    def test_backoff_fixed(self):
        result = self.rl.apply_backoff("svc", 10, "fixed")
        assert result["wait_seconds"] == 10

    def test_reset_counter(self):
        self.rl.set_limit("svc", 5)
        self.rl.record_request("svc")
        self.rl.record_request("svc")
        self.rl.reset_counter("svc")
        quota = self.rl.get_quota("svc")
        assert quota["used"] == 0

    def test_priority_ordering(self):
        self.rl.enqueue("svc", {"a": 1}, priority=1)
        self.rl.enqueue("svc", {"b": 2}, priority=5)
        self.rl.enqueue("svc", {"c": 3}, priority=3)
        first = self.rl.dequeue()
        assert first["priority"] == 5  # Yuksek oncelik once


# ======================== ResponseCache Testleri ========================

class TestResponseCache(unittest.TestCase):
    """ResponseCache testleri."""

    def setUp(self):
        self.cache = ResponseCache(default_ttl=60)

    def test_init(self):
        assert self.cache.entry_count == 0
        assert self.cache.hit_rate == 0.0

    def test_set_and_get(self):
        self.cache.set("key1", {"data": "test"}, "svc")
        result = self.cache.get("key1", "svc")
        assert result == {"data": "test"}
        assert self.cache.entry_count == 1

    def test_get_miss(self):
        result = self.cache.get("missing")
        assert result is None

    def test_hit_rate(self):
        self.cache.set("k", {"v": 1})
        self.cache.get("k")  # hit
        self.cache.get("missing")  # miss
        stats = self.cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_invalidate(self):
        self.cache.set("k", {"v": 1}, "svc")
        assert self.cache.invalidate("k", "svc") is True
        assert self.cache.entry_count == 0

    def test_invalidate_missing(self):
        assert self.cache.invalidate("nope") is False

    def test_invalidate_service(self):
        self.cache.set("a", {"v": 1}, "svc")
        self.cache.set("b", {"v": 2}, "svc")
        self.cache.set("c", {"v": 3}, "other")
        removed = self.cache.invalidate_service("svc")
        assert removed == 2
        assert self.cache.entry_count == 1

    def test_add_invalidation_rule(self):
        rule = self.cache.add_invalidation_rule(
            "user:*", "user.updated",
        )
        assert rule["pattern"] == "user:*"
        assert self.cache.rule_count == 1

    def test_warm_cache(self):
        entries = [
            {"key": "a", "data": {"v": 1}, "service": "s"},
            {"key": "b", "data": {"v": 2}},
            {"key": "", "data": {}},  # Atlanir
        ]
        added = self.cache.warm_cache(entries)
        assert added == 2

    def test_cleanup_expired(self):
        # Manuel olarak suresi dolmus girdi ekle
        entry = self.cache.set("old", {"v": 1})
        # Expires_at'i gecmise cek
        key = list(self.cache._cache.keys())[0]
        self.cache._cache[key].expires_at = (
            datetime.now(timezone.utc) - timedelta(seconds=10)
        )
        removed = self.cache.cleanup_expired()
        assert removed == 1

    def test_custom_ttl(self):
        self.cache.set("k", {"v": 1}, ttl=3600)
        entry = list(self.cache._cache.values())[0]
        assert entry.ttl_seconds == 3600

    def test_stats(self):
        self.cache.set("k", {"v": 1})
        self.cache.get("k")
        stats = self.cache.get_stats()
        assert stats["total_entries"] == 1
        assert stats["hits"] == 1


# ======================== IntegrationErrorHandler Testleri ========================

class TestIntegrationErrorHandler(unittest.TestCase):
    """IntegrationErrorHandler testleri."""

    def setUp(self):
        self.handler = IntegrationErrorHandler(max_retries=3)

    def test_init(self):
        assert self.handler.error_count == 0
        assert self.handler.recovery_count == 0

    def test_handle_error(self):
        result = self.handler.handle_error(
            "svc", "Connection refused", 0,
        )
        assert "error_id" in result
        assert result["category"] == "network"
        assert result["retryable"] is True
        assert self.handler.error_count == 1

    def test_handle_timeout(self):
        result = self.handler.handle_error(
            "svc", "Request timeout", 0,
        )
        assert result["category"] == "timeout"

    def test_handle_rate_limit(self):
        result = self.handler.handle_error(
            "svc", "Too many requests", 429,
        )
        assert result["category"] == "rate_limit"

    def test_handle_auth_error(self):
        result = self.handler.handle_error(
            "svc", "Unauthorized", 401,
        )
        assert result["category"] == "auth"
        assert result["retryable"] is False

    def test_handle_server_error(self):
        result = self.handler.handle_error(
            "svc", "Internal error", 500,
        )
        assert result["category"] == "server"
        assert result["retryable"] is True

    def test_handle_client_error(self):
        result = self.handler.handle_error(
            "svc", "Bad request", 400,
        )
        assert result["category"] == "client"
        assert result["retryable"] is False

    def test_handle_with_fallback(self):
        self.handler.set_fallback(
            "svc", {"default": True},
        )
        result = self.handler.handle_error(
            "svc", "Error", 500,
        )
        assert result.get("used_fallback") is True
        assert result["fallback"] == {"default": True}

    def test_set_retry_policy(self):
        policy = self.handler.set_retry_policy(
            "svc", max_retries=5, backoff="linear",
        )
        assert policy["max_retries"] == 5
        assert policy["backoff"] == "linear"

    def test_should_retry_yes(self):
        self.handler.set_retry_policy("svc", max_retries=3)
        result = self.handler.should_retry(
            "svc", 1, ErrorCategory.NETWORK,
        )
        assert result["retry"] is True
        assert result["attempt"] == 2

    def test_should_retry_max_reached(self):
        self.handler.set_retry_policy("svc", max_retries=2)
        result = self.handler.should_retry(
            "svc", 2, ErrorCategory.NETWORK,
        )
        assert result["retry"] is False

    def test_should_retry_not_retryable(self):
        result = self.handler.should_retry(
            "svc", 0, ErrorCategory.CLIENT,
        )
        assert result["retry"] is False

    def test_set_fallback(self):
        fb = self.handler.set_fallback(
            "svc", {"data": []}, "Empty response",
        )
        assert fb["service"] == "svc"
        assert self.handler.fallback_count == 1

    def test_get_error_report(self):
        self.handler.handle_error("svc", "err1", 500)
        self.handler.handle_error("svc", "err2", 503)
        report = self.handler.get_error_report("svc")
        assert report["total_errors"] == 2
        assert "category_distribution" in report

    def test_get_errors_by_service(self):
        self.handler.handle_error("a", "err", 500)
        self.handler.handle_error("b", "err", 500)
        errors = self.handler.get_errors_by_service("a")
        assert len(errors) == 1

    def test_clear_errors(self):
        self.handler.handle_error("svc", "err", 500)
        cleared = self.handler.clear_errors("svc")
        assert cleared == 1
        assert self.handler.error_count == 0

    def test_clear_all_errors(self):
        self.handler.handle_error("a", "e1", 500)
        self.handler.handle_error("b", "e2", 500)
        cleared = self.handler.clear_errors()
        assert cleared == 2

    def test_recovery_action(self):
        self.handler.handle_error("svc", "timeout", 0)
        assert self.handler.recovery_count == 1


# ======================== IntegrationHub Testleri ========================

class TestIntegrationHub(unittest.TestCase):
    """IntegrationHub testleri."""

    def setUp(self):
        self.hub = IntegrationHub(
            default_timeout=10,
            max_retries=3,
            cache_enabled=True,
            rate_limit_default=100,
        )

    def test_init(self):
        assert self.hub.total_requests == 0

    def test_register_service(self):
        result = self.hub.register_service(
            "payment", "https://pay.api.com",
            auth_type=AuthType.API_KEY,
            credentials={"api_key": "key123"},
            rate_limit=50,
        )
        assert result["registered"] is True
        assert result["service"] == "payment"

    def test_request_success(self):
        self.hub.register_service(
            "svc", "https://api.test.com",
        )
        result = self.hub.request("svc", "GET", "/users")
        assert result["success"] is True
        assert result["cached"] is False
        assert self.hub.total_requests == 1

    def test_request_cached(self):
        self.hub.register_service("svc", "https://api.test.com")
        self.hub.request("svc", "GET", "/data")
        # Ikinci istek cache'ten gelmeli
        result = self.hub.request("svc", "GET", "/data")
        assert result["success"] is True
        assert result["cached"] is True

    def test_request_no_cache(self):
        self.hub.register_service("svc", "https://api.test.com")
        self.hub.request("svc", "GET", "/data", use_cache=False)
        result = self.hub.request(
            "svc", "GET", "/data", use_cache=False,
        )
        assert result["cached"] is False

    def test_request_rate_limited(self):
        self.hub.register_service(
            "svc", "https://api.test.com",
            rate_limit=2,
        )
        self.hub.request("svc", "POST", "/a")
        self.hub.request("svc", "POST", "/b")
        result = self.hub.request("svc", "POST", "/c")
        assert result["success"] is False
        assert "Rate limit" in result["error"]

    def test_sync_data(self):
        result = self.hub.sync_data(
            "src", "dst",
            [{"id": 1}],
            SyncMode.FULL,
        )
        assert result["success"] is True
        assert result["records_synced"] == 1

    def test_process_webhook(self):
        self.hub.webhooks.register_webhook(
            "https://hook.test", "order.created",
        )
        result = self.hub.process_webhook(
            "order.created", {"id": 1},
        )
        assert result["success"] is True

    def test_get_service_health(self):
        self.hub.register_service("svc", "https://api.test.com")
        health = self.hub.get_service_health("svc")
        assert "status" in health

    def test_get_service_health_all(self):
        self.hub.register_service("a", "https://a.com")
        self.hub.register_service("b", "https://b.com")
        health = self.hub.get_service_health()
        assert health["total"] == 2

    def test_get_service_health_missing(self):
        result = self.hub.get_service_health("nope")
        assert "error" in result

    def test_get_snapshot(self):
        self.hub.register_service("svc", "https://svc.com")
        self.hub.request("svc", "GET", "/")
        snap = self.hub.get_snapshot()
        assert snap.total_services == 1
        assert snap.total_requests == 1
        assert snap.uptime_seconds >= 0

    def test_subsystem_access(self):
        assert self.hub.connector is not None
        assert self.hub.auth is not None
        assert self.hub.webhooks is not None
        assert self.hub.sync is not None
        assert self.hub.registry is not None
        assert self.hub.limiter is not None
        assert self.hub.cache is not None
        assert self.hub.errors is not None


# ======================== Integration Testleri ========================

class TestIntegrationIntegration(unittest.TestCase):
    """Entegrasyon testleri."""

    def test_full_service_lifecycle(self):
        hub = IntegrationHub()

        # Servis kaydet
        hub.register_service(
            "api", "https://api.test.com",
            auth_type=AuthType.API_KEY,
            credentials={"api_key": "key"},
        )

        # Istek yap
        result = hub.request("api", "GET", "/users")
        assert result["success"] is True

        # Saglik kontrol
        health = hub.get_service_health("api")
        assert health["status"] == ServiceStatus.ACTIVE.value

        # Snapshot
        snap = hub.get_snapshot()
        assert snap.total_services == 1
        assert snap.total_requests == 1

    def test_error_handling_pipeline(self):
        handler = IntegrationErrorHandler(max_retries=3)
        handler.set_fallback("api", {"data": []})
        handler.set_retry_policy("api", backoff="exponential")

        result = handler.handle_error("api", "timeout", 0)
        assert result["retryable"] is True

        retry = handler.should_retry(
            "api", 0, ErrorCategory.TIMEOUT,
        )
        assert retry["retry"] is True

    def test_sync_and_webhook_flow(self):
        hub = IntegrationHub()

        # Webhook kaydet
        hub.webhooks.register_webhook(
            "https://hook.test", "sync.complete",
        )

        # Sync yap
        result = hub.sync_data(
            "crm", "erp",
            [{"id": 1}, {"id": 2}],
            SyncMode.FULL,
        )
        assert result["success"] is True

        # Webhook tetikle
        wh_result = hub.process_webhook(
            "sync.complete",
            {"records": result["records_synced"]},
        )
        assert wh_result["success"] is True

    def test_rate_limit_and_cache(self):
        hub = IntegrationHub(rate_limit_default=5)
        hub.register_service("api", "https://api.test.com")

        # GET istekleri cache'lenir
        hub.request("api", "GET", "/items")
        result = hub.request("api", "GET", "/items")
        assert result["cached"] is True

    def test_failover_scenario(self):
        reg = ExternalServiceRegistry()
        reg.register_service("primary", "https://p.com")
        reg.register_service("backup", "https://b.com")
        reg.set_failover("primary", "backup")

        # Backup'i aktif yap
        reg.check_health("backup", True)

        # Primary'yi down yap
        reg.set_circuit_breaker_threshold("primary", 1)
        reg.check_health("primary", False)

        active = reg.get_active_service("primary")
        assert active == "backup"


if __name__ == "__main__":
    unittest.main()
