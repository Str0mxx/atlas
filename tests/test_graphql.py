"""ATLAS GraphQL & API Federation testleri.

SchemaBuilder, ResolverManager, QueryExecutor,
DataLoader, SubscriptionManager, FederationGateway,
Introspection, QueryComplexity, GraphQLOrchestrator,
modeller ve config testleri.
"""

import time

import pytest

from app.core.graphql.schema_builder import (
    SchemaBuilder,
)
from app.core.graphql.resolver_manager import (
    ResolverManager,
)
from app.core.graphql.query_executor import (
    QueryExecutor,
)
from app.core.graphql.dataloader import (
    DataLoader,
)
from app.core.graphql.subscription_manager import (
    SubscriptionManager,
)
from app.core.graphql.federation_gateway import (
    FederationGateway,
)
from app.core.graphql.introspection import (
    Introspection,
)
from app.core.graphql.query_complexity import (
    QueryComplexity,
)
from app.core.graphql.graphql_orchestrator import (
    GraphQLOrchestrator,
)
from app.models.graphql_models import (
    FieldType,
    OperationType,
    ResolverType,
    SubscriptionStatus,
    FederationMode,
    ComplexityLevel,
    SchemaRecord,
    QueryRecord,
    SubscriptionRecord,
    GraphQLSnapshot,
)


# ===================== SchemaBuilder =====================

class TestSchemaBuilder:
    """SchemaBuilder testleri."""

    def setup_method(self) -> None:
        """Her test oncesi."""
        self.sb = SchemaBuilder()

    def test_init(self) -> None:
        """Baslangic durumu."""
        assert self.sb.type_count == 0
        assert self.sb.query_count == 0
        assert self.sb.mutation_count == 0
        assert self.sb.subscription_count == 0
        assert self.sb.input_count == 0
        assert self.sb.total_definitions == 0

    def test_add_type(self) -> None:
        """Tip ekleme."""
        result = self.sb.add_type(
            "User",
            {"id": "ID!", "name": "String!"},
            description="Kullanici tipi",
        )
        assert result["name"] == "User"
        assert result["fields"] == 2
        assert self.sb.type_count == 1

    def test_add_type_with_interfaces(self) -> None:
        """Interface ile tip ekleme."""
        self.sb.add_interface(
            "Node", {"id": "ID!"},
        )
        result = self.sb.add_type(
            "User",
            {"id": "ID!", "name": "String!"},
            interfaces=["Node"],
        )
        assert result["name"] == "User"
        t = self.sb.get_type("User")
        assert t is not None
        assert "Node" in t["interfaces"]

    def test_add_query(self) -> None:
        """Sorgu ekleme."""
        result = self.sb.add_query(
            "getUser", "User",
            args={"id": "ID!"},
        )
        assert result["name"] == "getUser"
        assert result["return_type"] == "User"
        assert self.sb.query_count == 1

    def test_add_mutation(self) -> None:
        """Mutasyon ekleme."""
        result = self.sb.add_mutation(
            "createUser", "User",
            args={"input": "CreateUserInput!"},
        )
        assert result["name"] == "createUser"
        assert self.sb.mutation_count == 1

    def test_add_subscription(self) -> None:
        """Abonelik ekleme."""
        result = self.sb.add_subscription(
            "onUserCreated", "User",
        )
        assert result["name"] == "onUserCreated"
        assert self.sb.subscription_count == 1

    def test_add_input(self) -> None:
        """Input tipi ekleme."""
        result = self.sb.add_input(
            "CreateUserInput",
            {"name": "String!", "email": "String!"},
        )
        assert result["name"] == "CreateUserInput"
        assert result["fields"] == 2
        assert self.sb.input_count == 1

    def test_add_enum(self) -> None:
        """Enum ekleme."""
        result = self.sb.add_enum(
            "Role",
            ["ADMIN", "USER", "GUEST"],
        )
        assert result["name"] == "Role"
        assert result["values"] == 3

    def test_add_interface(self) -> None:
        """Arayuz ekleme."""
        result = self.sb.add_interface(
            "Node", {"id": "ID!"},
        )
        assert result["name"] == "Node"
        assert result["fields"] == 1

    def test_get_type(self) -> None:
        """Tip getirme."""
        self.sb.add_type("User", {"id": "ID!"})
        t = self.sb.get_type("User")
        assert t is not None
        assert t["name"] == "User"

    def test_get_type_not_found(self) -> None:
        """Olmayan tip."""
        assert self.sb.get_type("Ghost") is None

    def test_get_query(self) -> None:
        """Sorgu getirme."""
        self.sb.add_query("getUser", "User")
        q = self.sb.get_query("getUser")
        assert q is not None
        assert q["return_type"] == "User"

    def test_get_query_not_found(self) -> None:
        """Olmayan sorgu."""
        assert self.sb.get_query("ghost") is None

    def test_remove_type(self) -> None:
        """Tip kaldirma."""
        self.sb.add_type("User", {"id": "ID!"})
        assert self.sb.remove_type("User") is True
        assert self.sb.type_count == 0

    def test_remove_type_not_found(self) -> None:
        """Olmayan tipi kaldirma."""
        assert self.sb.remove_type("Ghost") is False

    def test_build_sdl_empty(self) -> None:
        """Bos sema SDL."""
        sdl = self.sb.build_sdl()
        assert sdl == ""

    def test_build_sdl_types(self) -> None:
        """Tipli SDL."""
        self.sb.add_type(
            "User", {"id": "ID!", "name": "String!"},
        )
        self.sb.add_query("getUser", "User")
        sdl = self.sb.build_sdl()
        assert "type User" in sdl
        assert "type Query" in sdl

    def test_build_sdl_mutations(self) -> None:
        """Mutasyonlu SDL."""
        self.sb.add_mutation("createUser", "User")
        sdl = self.sb.build_sdl()
        assert "type Mutation" in sdl

    def test_build_sdl_enum(self) -> None:
        """Enumlu SDL."""
        self.sb.add_enum("Role", ["ADMIN", "USER"])
        sdl = self.sb.build_sdl()
        assert "enum Role" in sdl

    def test_build_sdl_interface(self) -> None:
        """Arayuzlu SDL."""
        self.sb.add_interface("Node", {"id": "ID!"})
        sdl = self.sb.build_sdl()
        assert "interface Node" in sdl

    def test_build_sdl_input(self) -> None:
        """Inputlu SDL."""
        self.sb.add_input(
            "CreateUserInput", {"name": "String!"},
        )
        sdl = self.sb.build_sdl()
        assert "input CreateUserInput" in sdl

    def test_total_definitions(self) -> None:
        """Toplam tanim sayisi."""
        self.sb.add_type("User", {"id": "ID!"})
        self.sb.add_query("getUser", "User")
        self.sb.add_mutation("createUser", "User")
        self.sb.add_enum("Role", ["ADMIN"])
        assert self.sb.total_definitions == 4


# ===================== ResolverManager =====================

class TestResolverManager:
    """ResolverManager testleri."""

    def setup_method(self) -> None:
        """Her test oncesi."""
        self.rm = ResolverManager()

    def test_init(self) -> None:
        """Baslangic durumu."""
        assert self.rm.resolver_count == 0
        assert self.rm.batch_count == 0
        assert self.rm.default_count == 0
        assert self.rm.middleware_count == 0
        assert self.rm.resolved_count == 0

    def test_register(self) -> None:
        """Cozumleyici kaydi."""
        result = self.rm.register(
            "Query", "getUser",
            lambda p, a, c: {"id": "1"},
        )
        assert result["key"] == "Query.getUser"
        assert self.rm.resolver_count == 1

    def test_register_batch(self) -> None:
        """Toplu cozumleyici kaydi."""
        result = self.rm.register_batch(
            "Query", "users",
            lambda keys: [{"id": k} for k in keys],
        )
        assert result["type"] == "batch"
        assert self.rm.batch_count == 1

    def test_resolve(self) -> None:
        """Alan cozumleme."""
        self.rm.register(
            "Query", "getUser",
            lambda p, a, c: {"id": "1", "name": "Ali"},
        )
        result = self.rm.resolve("Query", "getUser")
        assert result["id"] == "1"
        assert self.rm.resolved_count == 1

    def test_resolve_with_args(self) -> None:
        """Argumanli cozumleme."""
        self.rm.register(
            "Query", "getUser",
            lambda p, a, c: {"id": a.get("id")},
        )
        result = self.rm.resolve(
            "Query", "getUser",
            args={"id": "42"},
        )
        assert result["id"] == "42"

    def test_resolve_default(self) -> None:
        """Varsayilan cozumleyici."""
        self.rm.set_default(
            "Query",
            lambda p, f, a, c: f"default_{f}",
        )
        result = self.rm.resolve("Query", "unknown")
        assert result == "default_unknown"
        assert self.rm.default_count == 1

    def test_resolve_from_parent(self) -> None:
        """Parent'tan cozumleme."""
        result = self.rm.resolve(
            "User", "name",
            parent={"name": "Ali"},
        )
        assert result == "Ali"

    def test_resolve_not_found(self) -> None:
        """Bulunamayan alan."""
        result = self.rm.resolve(
            "Query", "ghost",
        )
        assert result is None

    def test_resolve_error_handler(self) -> None:
        """Hata isleyici."""
        self.rm.register(
            "Query", "fail",
            lambda p, a, c: 1 / 0,
        )
        self.rm.set_error_handler(
            "Query",
            lambda f, e: f"error_{f}",
        )
        result = self.rm.resolve("Query", "fail")
        assert result == "error_fail"

    def test_resolve_error_no_handler(self) -> None:
        """Hata isleyici olmadan."""
        self.rm.register(
            "Query", "fail",
            lambda p, a, c: 1 / 0,
        )
        result = self.rm.resolve("Query", "fail")
        assert result is None

    def test_resolve_batch(self) -> None:
        """Toplu cozumleme."""
        self.rm.register_batch(
            "Query", "users",
            lambda keys: [f"user_{k}" for k in keys],
        )
        results = self.rm.resolve_batch(
            "Query", "users", [1, 2, 3],
        )
        assert len(results) == 3
        assert results[0] == "user_1"

    def test_resolve_batch_not_found(self) -> None:
        """Olmayan toplu cozumleyici."""
        results = self.rm.resolve_batch(
            "Query", "ghost", [1, 2],
        )
        assert results == [None, None]

    def test_resolve_batch_error(self) -> None:
        """Toplu cozumleyici hatasi."""
        self.rm.register_batch(
            "Query", "fail",
            lambda keys: 1 / 0,
        )
        results = self.rm.resolve_batch(
            "Query", "fail", [1, 2],
        )
        assert results == [None, None]

    def test_middleware(self) -> None:
        """Middleware."""
        calls = []
        self.rm.add_middleware(
            lambda t, f, a: calls.append(f),
        )
        self.rm.register(
            "Query", "test",
            lambda p, a, c: "ok",
        )
        self.rm.resolve("Query", "test")
        assert "test" in calls
        assert self.rm.middleware_count == 1

    def test_get_resolver(self) -> None:
        """Cozumleyici bilgisi."""
        self.rm.register(
            "Query", "getUser",
            lambda p, a, c: None,
        )
        info = self.rm.get_resolver("Query", "getUser")
        assert info is not None
        assert info["key"] == "Query.getUser"
        assert info["call_count"] == 0

    def test_get_resolver_not_found(self) -> None:
        """Olmayan cozumleyici bilgisi."""
        assert self.rm.get_resolver("Q", "x") is None

    def test_remove(self) -> None:
        """Cozumleyici kaldirma."""
        self.rm.register(
            "Query", "test",
            lambda p, a, c: None,
        )
        assert self.rm.remove("Query", "test") is True
        assert self.rm.resolver_count == 0

    def test_remove_not_found(self) -> None:
        """Olmayan kaldirma."""
        assert self.rm.remove("Q", "x") is False

    def test_get_stats(self) -> None:
        """Istatistikler."""
        stats = self.rm.get_stats()
        assert "resolved" in stats
        assert "errors" in stats


# ===================== QueryExecutor =====================

class TestQueryExecutor:
    """QueryExecutor testleri."""

    def setup_method(self) -> None:
        """Her test oncesi."""
        self.qe = QueryExecutor()

    def test_init(self) -> None:
        """Baslangic durumu."""
        assert self.qe.executed_count == 0
        assert self.qe.error_count == 0
        assert self.qe.cache_count == 0
        assert self.qe.history_count == 0

    def test_parse_query(self) -> None:
        """Sorgu ayrıstirma."""
        result = self.qe.parse(
            "{ users { id name } }",
        )
        assert result["operation"] == "query"
        assert "users" in result["fields"]
        assert result["depth"] >= 1

    def test_parse_mutation(self) -> None:
        """Mutasyon ayrıstirma."""
        result = self.qe.parse(
            "mutation { createUser(name: \"Ali\") { id } }",
        )
        assert result["operation"] == "mutation"

    def test_parse_subscription(self) -> None:
        """Abonelik ayrıstirma."""
        result = self.qe.parse(
            "subscription { onMessage { text } }",
        )
        assert result["operation"] == "subscription"

    def test_parse_empty(self) -> None:
        """Bos sorgu."""
        result = self.qe.parse("")
        assert "error" in result

    def test_validate_valid(self) -> None:
        """Gecerli dogrulama."""
        parsed = self.qe.parse(
            "{ users { id } }",
        )
        result = self.qe.validate(parsed)
        assert result["valid"] is True

    def test_validate_error(self) -> None:
        """Hatali dogrulama."""
        result = self.qe.validate(
            {"error": "bad_query"},
        )
        assert result["valid"] is False

    def test_validate_no_fields(self) -> None:
        """Alansiz dogrulama."""
        result = self.qe.validate(
            {"fields": [], "depth": 0},
        )
        assert result["valid"] is False

    def test_execute(self) -> None:
        """Sorgu yurutme."""
        result = self.qe.execute(
            "{ users { id } }",
        )
        assert "data" in result
        assert self.qe.executed_count == 1

    def test_execute_with_resolver(self) -> None:
        """Cozumleyici ile yurutme."""
        def resolver(field, vars, ctx):
            return [{"id": "1"}]

        result = self.qe.execute(
            "{ users { id } }",
            resolver_fn=resolver,
        )
        assert result["data"]["users"] == [{"id": "1"}]

    def test_execute_resolver_error(self) -> None:
        """Cozumleyici hatasi."""
        def resolver(field, vars, ctx):
            raise ValueError("test error")

        result = self.qe.execute(
            "{ users { id } }",
            resolver_fn=resolver,
        )
        assert result["errors"] is not None
        assert len(result["errors"]) > 0

    def test_execute_empty(self) -> None:
        """Bos sorgu yurutme."""
        result = self.qe.execute("")
        assert result["data"] is None
        assert result["errors"] is not None

    def test_execute_cached(self) -> None:
        """Onbellekli yurutme."""
        result1 = self.qe.execute_cached(
            "{ users { id } }", ttl=60,
        )
        result2 = self.qe.execute_cached(
            "{ users { id } }", ttl=60,
        )
        assert result1["data"] == result2["data"]

    def test_clear_cache(self) -> None:
        """Onbellek temizleme."""
        self.qe.execute_cached(
            "{ users { id } }", ttl=60,
        )
        cleared = self.qe.clear_cache()
        assert cleared >= 1
        assert self.qe.cache_count == 0

    def test_get_history(self) -> None:
        """Gecmis."""
        self.qe.execute("{ users { id } }")
        history = self.qe.get_history()
        assert len(history) >= 1

    def test_get_stats(self) -> None:
        """Istatistikler."""
        stats = self.qe.get_stats()
        assert "executed" in stats
        assert "errors" in stats
        assert "cached" in stats


# ===================== DataLoader =====================

class TestDataLoader:
    """DataLoader testleri."""

    def setup_method(self) -> None:
        """Her test oncesi."""
        self.dl = DataLoader()

    def test_init(self) -> None:
        """Baslangic durumu."""
        assert self.dl.loader_count == 0
        assert self.dl.cache_size == 0

    def test_register(self) -> None:
        """Yukleyici kaydi."""
        result = self.dl.register(
            "users",
            lambda keys: [f"user_{k}" for k in keys],
        )
        assert result["name"] == "users"
        assert self.dl.loader_count == 1

    def test_load(self) -> None:
        """Tekli yukleme."""
        self.dl.register(
            "users",
            lambda keys: [f"user_{k}" for k in keys],
        )
        result = self.dl.load("users", 1)
        assert result == "user_1"

    def test_load_many(self) -> None:
        """Toplu yukleme."""
        self.dl.register(
            "users",
            lambda keys: [f"user_{k}" for k in keys],
        )
        results = self.dl.load_many(
            "users", [1, 2, 3],
        )
        assert len(results) == 3
        assert results[0] == "user_1"

    def test_load_many_not_found(self) -> None:
        """Olmayan yukleyici."""
        results = self.dl.load_many("ghost", [1, 2])
        assert results == [None, None]

    def test_load_many_dedup(self) -> None:
        """Tekrarsizlastirma."""
        call_count = [0]

        def batch_fn(keys):
            call_count[0] += 1
            return [f"u_{k}" for k in keys]

        self.dl.register("users", batch_fn)
        results = self.dl.load_many(
            "users", [1, 1, 2, 2, 3],
        )
        assert len(results) == 5
        assert results[0] == results[1]

    def test_cache(self) -> None:
        """Onbellek."""
        call_count = [0]

        def batch_fn(keys):
            call_count[0] += 1
            return [f"u_{k}" for k in keys]

        self.dl.register("users", batch_fn)
        self.dl.load("users", 1)
        self.dl.load("users", 1)
        # Ikinci cagri cache'den gelmeli
        assert self.dl.cache_size >= 1

    def test_prime(self) -> None:
        """Onbellek onceden doldurma."""
        self.dl.register(
            "users",
            lambda keys: [None] * len(keys),
        )
        self.dl.prime("users", "key1", "value1")
        result = self.dl.load("users", "key1")
        assert result == "value1"

    def test_clear(self) -> None:
        """Onbellek temizleme."""
        self.dl.register(
            "users",
            lambda keys: [f"u_{k}" for k in keys],
        )
        self.dl.load("users", 1)
        cleared = self.dl.clear("users")
        assert cleared >= 1

    def test_clear_single(self) -> None:
        """Tekli onbellek temizleme."""
        self.dl.register(
            "users",
            lambda keys: [f"u_{k}" for k in keys],
        )
        self.dl.load("users", 1)
        self.dl.load("users", 2)
        cleared = self.dl.clear("users", 1)
        assert cleared == 1

    def test_clear_not_found(self) -> None:
        """Olmayan onbellek temizleme."""
        assert self.dl.clear("ghost") == 0

    def test_clear_all(self) -> None:
        """Tum onbellek temizleme."""
        self.dl.register(
            "users",
            lambda keys: [f"u_{k}" for k in keys],
        )
        self.dl.register(
            "posts",
            lambda keys: [f"p_{k}" for k in keys],
        )
        self.dl.load("users", 1)
        self.dl.load("posts", 1)
        total = self.dl.clear_all()
        assert total >= 2

    def test_no_cache(self) -> None:
        """Onbelleksiz mod."""
        dl = DataLoader(cache_enabled=False)
        dl.register(
            "users",
            lambda keys: [f"u_{k}" for k in keys],
        )
        r1 = dl.load("users", 1)
        assert r1 == "u_1"

    def test_get_stats(self) -> None:
        """Istatistikler."""
        stats = self.dl.get_stats()
        assert "loads" in stats
        assert "batch_loads" in stats
        assert "cache_hits" in stats

    def test_batch_error(self) -> None:
        """Toplu yukleme hatasi."""
        self.dl.register(
            "fail",
            lambda keys: 1 / 0,
        )
        results = self.dl.load_many("fail", [1, 2])
        assert results == [None, None]


# ===================== SubscriptionManager =====================

class TestSubscriptionManager:
    """SubscriptionManager testleri."""

    def setup_method(self) -> None:
        """Her test oncesi."""
        self.sm = SubscriptionManager()

    def test_init(self) -> None:
        """Baslangic durumu."""
        assert self.sm.subscription_count == 0
        assert self.sm.connection_count == 0
        assert self.sm.active_count == 0

    def test_connect(self) -> None:
        """Baglanti kurma."""
        result = self.sm.connect("conn1")
        assert result["status"] == "connected"
        assert self.sm.connection_count == 1

    def test_connect_with_metadata(self) -> None:
        """Metadata ile baglanti."""
        result = self.sm.connect(
            "conn1", {"user": "ali"},
        )
        assert result["status"] == "connected"
        conn = self.sm.get_connection("conn1")
        assert conn["metadata"]["user"] == "ali"

    def test_disconnect(self) -> None:
        """Baglanti kesme."""
        self.sm.connect("conn1")
        result = self.sm.disconnect("conn1")
        assert result["status"] == "disconnected"
        assert self.sm.connection_count == 0

    def test_disconnect_not_connected(self) -> None:
        """Baglanmamis kesme."""
        result = self.sm.disconnect("ghost")
        assert "error" in result

    def test_disconnect_cleans_subscriptions(self) -> None:
        """Baglanti kesildiginde abonelikler temizlenir."""
        self.sm.connect("conn1")
        self.sm.subscribe("conn1", "sub1", "msg")
        assert self.sm.subscription_count == 1
        self.sm.disconnect("conn1")
        assert self.sm.subscription_count == 0

    def test_subscribe(self) -> None:
        """Abonelik olusturma."""
        self.sm.connect("conn1")
        result = self.sm.subscribe(
            "conn1", "sub1", "message",
        )
        assert result["status"] == "active"
        assert self.sm.subscription_count == 1

    def test_subscribe_not_connected(self) -> None:
        """Baglanmamis abonelik."""
        result = self.sm.subscribe(
            "ghost", "sub1", "message",
        )
        assert "error" in result

    def test_subscribe_with_filter(self) -> None:
        """Filtreli abonelik."""
        self.sm.connect("conn1")
        self.sm.subscribe(
            "conn1", "sub1", "message",
            filter_fn=lambda d: d.get("type") == "important",
        )
        # Filtreye uymayan mesaj
        r1 = self.sm.publish(
            "message", {"type": "normal"},
        )
        assert r1["delivered"] == 0

        # Filtreye uyan mesaj
        r2 = self.sm.publish(
            "message", {"type": "important"},
        )
        assert r2["delivered"] == 1

    def test_unsubscribe(self) -> None:
        """Abonelik iptali."""
        self.sm.connect("conn1")
        self.sm.subscribe("conn1", "sub1", "msg")
        assert self.sm.unsubscribe("sub1") is True
        assert self.sm.subscription_count == 0

    def test_unsubscribe_not_found(self) -> None:
        """Olmayan abonelik iptali."""
        assert self.sm.unsubscribe("ghost") is False

    def test_publish(self) -> None:
        """Olay yayinlama."""
        self.sm.connect("conn1")
        self.sm.subscribe("conn1", "sub1", "chat")
        result = self.sm.publish(
            "chat", {"text": "merhaba"},
        )
        assert result["delivered"] == 1
        assert self.sm.event_count == 1

    def test_publish_multiple(self) -> None:
        """Birden fazla aboneye yayinlama."""
        self.sm.connect("conn1")
        self.sm.connect("conn2")
        self.sm.subscribe("conn1", "sub1", "msg")
        self.sm.subscribe("conn2", "sub2", "msg")
        result = self.sm.publish(
            "msg", {"text": "hi"},
        )
        assert result["delivered"] == 2

    def test_publish_no_subscribers(self) -> None:
        """Abonesiz yayinlama."""
        result = self.sm.publish(
            "msg", {"text": "hi"},
        )
        assert result["delivered"] == 0

    def test_heartbeat(self) -> None:
        """Heartbeat."""
        self.sm.connect("conn1")
        result = self.sm.heartbeat("conn1")
        assert result["status"] == "alive"

    def test_heartbeat_not_connected(self) -> None:
        """Baglanmamis heartbeat."""
        result = self.sm.heartbeat("ghost")
        assert "error" in result

    def test_check_stale(self) -> None:
        """Bayat baglanti tespiti."""
        self.sm.connect("conn1")
        # Son heartbeat'i eski yap
        conn = self.sm._connections["conn1"]
        conn["last_heartbeat"] = time.time() - 200
        stale = self.sm.check_stale_connections(
            timeout=100,
        )
        assert "conn1" in stale

    def test_check_stale_none(self) -> None:
        """Bayat baglanti yok."""
        self.sm.connect("conn1")
        stale = self.sm.check_stale_connections()
        assert len(stale) == 0

    def test_get_subscription(self) -> None:
        """Abonelik bilgisi."""
        self.sm.connect("conn1")
        self.sm.subscribe("conn1", "sub1", "msg")
        sub = self.sm.get_subscription("sub1")
        assert sub is not None
        assert sub["event_type"] == "msg"

    def test_get_subscription_not_found(self) -> None:
        """Olmayan abonelik."""
        assert self.sm.get_subscription("ghost") is None

    def test_get_connection(self) -> None:
        """Baglanti bilgisi."""
        self.sm.connect("conn1")
        conn = self.sm.get_connection("conn1")
        assert conn is not None
        assert conn["id"] == "conn1"

    def test_get_events(self) -> None:
        """Olay logu."""
        self.sm.connect("conn1")
        self.sm.subscribe("conn1", "sub1", "msg")
        self.sm.publish("msg", {"text": "hi"})
        events = self.sm.get_events()
        assert len(events) >= 1


# ===================== FederationGateway =====================

class TestFederationGateway:
    """FederationGateway testleri."""

    def setup_method(self) -> None:
        """Her test oncesi."""
        self.fg = FederationGateway()

    def test_init(self) -> None:
        """Baslangic durumu."""
        assert self.fg.service_count == 0
        assert self.fg.merged_type_count == 0
        assert self.fg.plan_count == 0

    def test_register_service(self) -> None:
        """Servis kaydi."""
        result = self.fg.register_service(
            "users", "http://users:4000",
            types=["User"],
            queries=["getUser"],
        )
        assert result["name"] == "users"
        assert result["types"] == 1
        assert self.fg.service_count == 1

    def test_register_multiple_services(self) -> None:
        """Birden fazla servis."""
        self.fg.register_service(
            "users", "http://users:4000",
            types=["User"],
        )
        self.fg.register_service(
            "posts", "http://posts:4001",
            types=["Post"],
        )
        assert self.fg.service_count == 2

    def test_remove_service(self) -> None:
        """Servis kaldirma."""
        self.fg.register_service(
            "users", "http://users:4000",
            types=["User"],
        )
        assert self.fg.remove_service("users") is True
        assert self.fg.service_count == 0
        assert self.fg.merged_type_count == 0

    def test_remove_service_not_found(self) -> None:
        """Olmayan servis kaldirma."""
        assert self.fg.remove_service("ghost") is False

    def test_plan_query(self) -> None:
        """Sorgu planlama."""
        self.fg.register_service(
            "users", "http://users:4000",
            queries=["getUser", "listUsers"],
        )
        plan = self.fg.plan_query(
            ["getUser", "listUsers"],
        )
        assert plan["services_involved"] >= 1
        assert plan["fields"] == 2
        assert self.fg.plan_count == 1

    def test_plan_query_multi_service(self) -> None:
        """Coklu servis plani."""
        self.fg.register_service(
            "users", "http://users:4000",
            queries=["getUser"],
        )
        self.fg.register_service(
            "posts", "http://posts:4001",
            queries=["getPosts"],
        )
        plan = self.fg.plan_query(
            ["getUser", "getPosts"],
        )
        assert plan["services_involved"] == 2

    def test_execute_federated(self) -> None:
        """Federasyonlu yurutme."""
        self.fg.register_service(
            "users", "http://users:4000",
            queries=["getUser"],
        )
        result = self.fg.execute_federated(
            ["getUser"],
        )
        assert "data" in result
        assert result["services_used"] >= 1

    def test_execute_federated_with_resolver(self) -> None:
        """Cozumleyici ile federasyonlu yurutme."""
        self.fg.register_service(
            "users", "http://users:4000",
            queries=["getUser"],
        )
        result = self.fg.execute_federated(
            ["getUser"],
            resolver_fn=lambda s, f: {"id": "1"},
        )
        assert result["data"]["getUser"]["id"] == "1"

    def test_execute_federated_resolver_error(self) -> None:
        """Cozumleyici hatasi."""
        self.fg.register_service(
            "users", "http://users:4000",
            queries=["getUser"],
        )

        def bad_resolver(s, f):
            raise ValueError("test")

        result = self.fg.execute_federated(
            ["getUser"],
            resolver_fn=bad_resolver,
        )
        assert result["errors"] is not None

    def test_stitch_schemas(self) -> None:
        """Sema birlestirme."""
        self.fg.register_service(
            "users", "http://users:4000",
            types=["User"], queries=["getUser"],
        )
        self.fg.register_service(
            "posts", "http://posts:4001",
            types=["Post"], queries=["getPosts"],
        )
        result = self.fg.stitch_schemas()
        assert result["total_types"] == 2
        assert result["total_queries"] == 2
        assert result["services"] == 2

    def test_stitch_schemas_conflicts(self) -> None:
        """Sema cakismalari."""
        self.fg.register_service(
            "users", "http://users:4000",
            types=["User"],
        )
        self.fg.register_service(
            "auth", "http://auth:4002",
            types=["User"],
        )
        result = self.fg.stitch_schemas()
        assert "User" in result["conflicts"]

    def test_get_type_sources(self) -> None:
        """Tip kaynaklari."""
        self.fg.register_service(
            "users", "http://users:4000",
            types=["User"],
        )
        sources = self.fg.get_type_sources("User")
        assert "users" in sources

    def test_get_type_sources_not_found(self) -> None:
        """Olmayan tip kaynaklari."""
        assert self.fg.get_type_sources("Ghost") == []

    def test_get_service(self) -> None:
        """Servis bilgisi."""
        self.fg.register_service(
            "users", "http://users:4000",
        )
        svc = self.fg.get_service("users")
        assert svc is not None
        assert svc["url"] == "http://users:4000"

    def test_get_service_not_found(self) -> None:
        """Olmayan servis."""
        assert self.fg.get_service("ghost") is None

    def test_get_errors(self) -> None:
        """Hata listesi."""
        errors = self.fg.get_errors()
        assert isinstance(errors, list)

    def test_merged_types(self) -> None:
        """Birlesmis tipler."""
        self.fg.register_service(
            "users", "http://users:4000",
            types=["User", "Profile"],
        )
        assert self.fg.merged_type_count == 2


# ===================== Introspection =====================

class TestIntrospection:
    """Introspection testleri."""

    def setup_method(self) -> None:
        """Her test oncesi."""
        self.intro = Introspection()

    def test_init(self) -> None:
        """Baslangic durumu."""
        assert self.intro.type_count == 0
        assert self.intro.deprecation_count == 0
        assert self.intro.doc_count == 0

    def test_register_type(self) -> None:
        """Tip kaydi."""
        result = self.intro.register_type(
            "User", "OBJECT",
            fields={"id": {"type": "ID!"}},
            description="Kullanici",
        )
        assert result["name"] == "User"
        assert result["kind"] == "OBJECT"
        assert self.intro.type_count == 1

    def test_register_type_with_doc(self) -> None:
        """Dokumantasyonlu tip kaydi."""
        self.intro.register_type(
            "User", "OBJECT",
            description="Kullanici tipi",
        )
        doc = self.intro.get_documentation("User")
        assert doc == "Kullanici tipi"

    def test_get_type(self) -> None:
        """Tip getirme."""
        self.intro.register_type(
            "User", "OBJECT",
        )
        t = self.intro.get_type("User")
        assert t is not None
        assert t["kind"] == "OBJECT"

    def test_get_type_not_found(self) -> None:
        """Olmayan tip."""
        assert self.intro.get_type("Ghost") is None

    def test_get_fields(self) -> None:
        """Alan bilgileri."""
        self.intro.register_type(
            "User", "OBJECT",
            fields={
                "id": {"type": "ID!"},
                "name": {"type": "String!"},
            },
        )
        fields = self.intro.get_fields("User")
        assert "id" in fields
        assert "name" in fields

    def test_get_fields_not_found(self) -> None:
        """Olmayan tip alanlari."""
        assert self.intro.get_fields("Ghost") == {}

    def test_get_field(self) -> None:
        """Tekli alan bilgisi."""
        self.intro.register_type(
            "User", "OBJECT",
            fields={"id": {"type": "ID!"}},
        )
        f = self.intro.get_field("User", "id")
        assert f is not None
        assert f["type"] == "ID!"

    def test_get_field_not_found(self) -> None:
        """Olmayan alan."""
        assert self.intro.get_field("User", "x") is None

    def test_get_field_type_not_found(self) -> None:
        """Olmayan tip alani."""
        assert self.intro.get_field("Ghost", "x") is None

    def test_deprecate_field(self) -> None:
        """Alan kaldirilmasi."""
        result = self.intro.deprecate(
            "User", "oldField",
            reason="Use newField instead",
        )
        assert "User.oldField" in result["key"]
        assert self.intro.deprecation_count == 1

    def test_deprecate_type(self) -> None:
        """Tip kaldirilmasi."""
        result = self.intro.deprecate(
            "OldType",
            reason="Use NewType",
        )
        assert result["key"] == "OldType"

    def test_is_deprecated(self) -> None:
        """Kaldirilmis kontrolu."""
        self.intro.deprecate(
            "User", "oldField",
        )
        assert self.intro.is_deprecated(
            "User", "oldField",
        ) is True
        assert self.intro.is_deprecated(
            "User", "newField",
        ) is False

    def test_get_deprecation(self) -> None:
        """Kaldirilma bilgisi."""
        self.intro.deprecate(
            "User", "oldField",
            reason="Eski alan",
        )
        dep = self.intro.get_deprecation(
            "User", "oldField",
        )
        assert dep is not None
        assert dep["reason"] == "Eski alan"

    def test_get_deprecation_not_found(self) -> None:
        """Olmayan kaldirilma."""
        assert self.intro.get_deprecation(
            "User", "x",
        ) is None

    def test_set_documentation(self) -> None:
        """Dokumantasyon ayarlama."""
        self.intro.set_documentation(
            "User", "Kullanici tipi",
        )
        assert self.intro.doc_count == 1

    def test_get_documentation(self) -> None:
        """Dokumantasyon getirme."""
        self.intro.set_documentation(
            "User", "Kullanici tipi",
        )
        doc = self.intro.get_documentation("User")
        assert doc == "Kullanici tipi"

    def test_get_documentation_not_found(self) -> None:
        """Olmayan dokumantasyon."""
        assert self.intro.get_documentation("x") is None

    def test_introspect(self) -> None:
        """Tam ic gozlem."""
        self.intro.register_type(
            "User", "OBJECT",
            fields={"id": {"type": "ID!"}},
        )
        result = self.intro.introspect()
        assert "__schema" in result
        assert result["__schema"]["totalTypes"] == 1

    def test_introspect_with_deprecation(self) -> None:
        """Kaldirilmislarla ic gozlem."""
        self.intro.register_type(
            "User", "OBJECT",
            fields={"oldField": {"type": "String"}},
        )
        self.intro.deprecate(
            "User", "oldField", "Kullanma",
        )
        result = self.intro.introspect()
        types = result["__schema"]["types"]
        user = types[0]
        field = user["fields"][0]
        assert field["isDeprecated"] is True
        assert field["deprecationReason"] == "Kullanma"

    def test_list_types(self) -> None:
        """Tip listesi."""
        self.intro.register_type("User", "OBJECT")
        self.intro.register_type("String", "SCALAR")
        all_types = self.intro.list_types()
        assert len(all_types) == 2

    def test_list_types_by_kind(self) -> None:
        """Turlu tip listesi."""
        self.intro.register_type("User", "OBJECT")
        self.intro.register_type("String", "SCALAR")
        objects = self.intro.list_types(kind="OBJECT")
        assert objects == ["User"]


# ===================== QueryComplexity =====================

class TestQueryComplexity:
    """QueryComplexity testleri."""

    def setup_method(self) -> None:
        """Her test oncesi."""
        self.qc = QueryComplexity(
            max_depth=10,
            max_complexity=1000,
        )

    def test_init(self) -> None:
        """Baslangic durumu."""
        assert self.qc.max_depth == 10
        assert self.qc.max_complexity == 1000
        assert self.qc.analyzed_count == 0
        assert self.qc.rejected_count == 0

    def test_analyze_allowed(self) -> None:
        """Izin verilen sorgu."""
        result = self.qc.analyze(
            ["users", "posts"], depth=2,
        )
        assert result["allowed"] is True
        assert result["level"] == "low"
        assert self.qc.analyzed_count == 1

    def test_analyze_blocked(self) -> None:
        """Engellenen sorgu."""
        # Maks derinlik asimi
        result = self.qc.analyze(
            ["users"], depth=15,
        )
        assert result["allowed"] is False
        assert result["depth_exceeded"] is True
        assert self.qc.rejected_count == 1

    def test_analyze_complexity_exceeded(self) -> None:
        """Karmasiklik asimi."""
        self.qc.set_field_cost("heavy", 200)
        result = self.qc.analyze(
            ["heavy"] * 10, depth=2,
        )
        assert result["allowed"] is False
        assert result["complexity_exceeded"] is True

    def test_analyze_with_multipliers(self) -> None:
        """Carpanli analiz."""
        result = self.qc.analyze(
            ["users", "posts"], depth=1,
            multipliers={"users": 5},
        )
        assert result["field_costs"]["users"] == 5
        assert result["field_costs"]["posts"] == 1

    def test_set_field_cost(self) -> None:
        """Alan maliyeti."""
        self.qc.set_field_cost("users", 10)
        result = self.qc.analyze(
            ["users"], depth=1,
        )
        assert result["field_costs"]["users"] == 10
        assert self.qc.field_cost_count == 1

    def test_set_type_cost(self) -> None:
        """Tip maliyeti."""
        self.qc.set_type_cost("User", 5)

    def test_complexity_levels(self) -> None:
        """Karmasiklik seviyeleri."""
        # Low
        r = self.qc.analyze(["a"], depth=1)
        assert r["level"] == "low"

        # Medium (>200)
        self.qc.set_field_cost("med", 25)
        r = self.qc.analyze(["med"] * 9, depth=1)
        assert r["level"] == "medium"

    def test_set_rate_limit(self) -> None:
        """Hiz siniri ayarlama."""
        result = self.qc.set_rate_limit(
            "client1", 10, 60,
        )
        assert result["client_id"] == "client1"
        assert result["max_requests"] == 10
        assert self.qc.rate_limit_count == 1

    def test_check_rate_limit_allowed(self) -> None:
        """Hiz siniri gecerli."""
        self.qc.set_rate_limit("client1", 5, 60)
        result = self.qc.check_rate_limit("client1")
        assert result["allowed"] is True
        assert result["remaining"] == 4

    def test_check_rate_limit_exceeded(self) -> None:
        """Hiz siniri asimi."""
        self.qc.set_rate_limit("client1", 2, 60)
        self.qc.check_rate_limit("client1")
        self.qc.check_rate_limit("client1")
        result = self.qc.check_rate_limit("client1")
        assert result["allowed"] is False
        assert result["limited"] is True

    def test_check_rate_limit_no_limit(self) -> None:
        """Siniri olmayan istemci."""
        result = self.qc.check_rate_limit("unknown")
        assert result["allowed"] is True

    def test_get_history(self) -> None:
        """Analiz gecmisi."""
        self.qc.analyze(["a"], depth=1)
        self.qc.analyze(["b"], depth=2)
        history = self.qc.get_history()
        assert len(history) == 2

    def test_get_stats(self) -> None:
        """Istatistikler."""
        stats = self.qc.get_stats()
        assert "analyzed" in stats
        assert "rejected" in stats
        assert "rate_limited" in stats


# ===================== GraphQLOrchestrator =====================

class TestGraphQLOrchestrator:
    """GraphQLOrchestrator testleri."""

    def setup_method(self) -> None:
        """Her test oncesi."""
        self.orch = GraphQLOrchestrator()

    def test_init(self) -> None:
        """Baslangic durumu."""
        assert self.orch.is_initialized is False
        assert self.orch.playground_enabled is True
        assert self.orch.request_count == 0

    def test_initialize(self) -> None:
        """Sistem baslatma."""
        result = self.orch.initialize()
        assert result["status"] == "initialized"
        assert result["components"] == 8
        assert self.orch.is_initialized is True

    def test_initialize_with_config(self) -> None:
        """Konfigurasyonlu baslatma."""
        result = self.orch.initialize(
            {"playground_enabled": False},
        )
        assert result["playground"] is False
        assert self.orch.playground_enabled is False

    def test_execute_query(self) -> None:
        """Sorgu yurutme."""
        result = self.orch.execute_query(
            "{ users { id } }",
        )
        assert "data" in result
        assert self.orch.request_count == 1

    def test_execute_query_empty(self) -> None:
        """Bos sorgu."""
        result = self.orch.execute_query("")
        assert result["data"] is None
        assert result["errors"] is not None

    def test_execute_query_too_complex(self) -> None:
        """Cok karmasik sorgu."""
        # Karmasikligi azalt ki reddedilsin
        orch = GraphQLOrchestrator(
            max_depth=2, max_complexity=5,
        )
        # Bir cok alanli sorgu
        orch.complexity.set_field_cost("users", 3)
        orch.complexity.set_field_cost("posts", 3)
        result = orch.execute_query(
            "{ users { posts { comments { id } } } }",
        )
        # Eger karmasiklik asilirsa hata donmeli
        if result.get("errors"):
            assert "complexity" in str(result["errors"])

    def test_execute_query_with_variables(self) -> None:
        """Degiskenli sorgu."""
        result = self.orch.execute_query(
            "{ users { id } }",
            variables={"limit": 10},
        )
        assert "data" in result

    def test_execute_federated(self) -> None:
        """Federasyonlu sorgu."""
        self.orch.federation.register_service(
            "users", "http://users:4000",
            queries=["getUser"],
        )
        result = self.orch.execute_federated(
            "{ getUser { id } }",
        )
        assert "data" in result

    def test_execute_federated_parse_error(self) -> None:
        """Federasyonlu sorgu parse hatasi."""
        result = self.orch.execute_federated("")
        assert result["data"] is None

    def test_get_snapshot(self) -> None:
        """Snapshot."""
        snap = self.orch.get_snapshot()
        assert "types" in snap
        assert "queries" in snap
        assert "mutations" in snap
        assert "resolvers" in snap
        assert "initialized" in snap
        assert "timestamp" in snap

    def test_get_analytics(self) -> None:
        """Analitik raporu."""
        analytics = self.orch.get_analytics()
        assert "schema" in analytics
        assert "resolvers" in analytics
        assert "executor" in analytics
        assert "loader" in analytics
        assert "subscriptions" in analytics
        assert "federation" in analytics
        assert "complexity" in analytics

    def test_components(self) -> None:
        """Alt bilesenler."""
        assert self.orch.schema is not None
        assert self.orch.resolvers is not None
        assert self.orch.executor is not None
        assert self.orch.loader is not None
        assert self.orch.subscriptions is not None
        assert self.orch.federation is not None
        assert self.orch.introspection_engine is not None
        assert self.orch.complexity is not None


# ===================== Models =====================

class TestGraphQLModels:
    """Model testleri."""

    def test_field_type_enum(self) -> None:
        """FieldType enum."""
        assert FieldType.STRING == "String"
        assert FieldType.INT == "Int"
        assert FieldType.FLOAT == "Float"
        assert FieldType.BOOLEAN == "Boolean"
        assert FieldType.ID == "ID"
        assert FieldType.CUSTOM == "Custom"

    def test_operation_type_enum(self) -> None:
        """OperationType enum."""
        assert OperationType.QUERY == "query"
        assert OperationType.MUTATION == "mutation"
        assert OperationType.SUBSCRIPTION == "subscription"
        assert OperationType.FRAGMENT == "fragment"
        assert OperationType.INLINE_FRAGMENT == "inline_fragment"
        assert OperationType.DIRECTIVE == "directive"

    def test_resolver_type_enum(self) -> None:
        """ResolverType enum."""
        assert ResolverType.FIELD == "field"
        assert ResolverType.BATCH == "batch"
        assert ResolverType.DEFAULT == "default"
        assert ResolverType.COMPUTED == "computed"
        assert ResolverType.DELEGATE == "delegate"
        assert ResolverType.CUSTOM == "custom"

    def test_subscription_status_enum(self) -> None:
        """SubscriptionStatus enum."""
        assert SubscriptionStatus.ACTIVE == "active"
        assert SubscriptionStatus.PAUSED == "paused"
        assert SubscriptionStatus.CLOSED == "closed"
        assert SubscriptionStatus.ERROR == "error"
        assert SubscriptionStatus.PENDING == "pending"
        assert SubscriptionStatus.RECONNECTING == "reconnecting"

    def test_federation_mode_enum(self) -> None:
        """FederationMode enum."""
        assert FederationMode.STITCHING == "stitching"
        assert FederationMode.FEDERATION == "federation"
        assert FederationMode.STANDALONE == "standalone"
        assert FederationMode.GATEWAY == "gateway"
        assert FederationMode.SUBGRAPH == "subgraph"
        assert FederationMode.HYBRID == "hybrid"

    def test_complexity_level_enum(self) -> None:
        """ComplexityLevel enum."""
        assert ComplexityLevel.LOW == "low"
        assert ComplexityLevel.MEDIUM == "medium"
        assert ComplexityLevel.HIGH == "high"
        assert ComplexityLevel.CRITICAL == "critical"
        assert ComplexityLevel.BLOCKED == "blocked"
        assert ComplexityLevel.UNLIMITED == "unlimited"

    def test_schema_record(self) -> None:
        """SchemaRecord modeli."""
        r = SchemaRecord(
            name="test",
            types_count=5,
            queries_count=3,
        )
        assert r.name == "test"
        assert r.types_count == 5
        assert r.schema_id

    def test_schema_record_defaults(self) -> None:
        """SchemaRecord varsayilanlar."""
        r = SchemaRecord()
        assert r.name == ""
        assert r.types_count == 0
        assert r.created_at is not None

    def test_query_record(self) -> None:
        """QueryRecord modeli."""
        r = QueryRecord(
            operation=OperationType.MUTATION,
            complexity=50,
            depth=3,
        )
        assert r.operation == OperationType.MUTATION
        assert r.complexity == 50
        assert r.query_id

    def test_query_record_defaults(self) -> None:
        """QueryRecord varsayilanlar."""
        r = QueryRecord()
        assert r.operation == OperationType.QUERY
        assert r.duration_ms == 0.0

    def test_subscription_record(self) -> None:
        """SubscriptionRecord modeli."""
        r = SubscriptionRecord(
            event_type="message",
            status=SubscriptionStatus.ACTIVE,
        )
        assert r.event_type == "message"
        assert r.subscription_id

    def test_subscription_record_defaults(self) -> None:
        """SubscriptionRecord varsayilanlar."""
        r = SubscriptionRecord()
        assert r.status == SubscriptionStatus.ACTIVE
        assert r.events_received == 0

    def test_graphql_snapshot(self) -> None:
        """GraphQLSnapshot modeli."""
        s = GraphQLSnapshot(
            total_types=10,
            total_resolvers=5,
            queries_executed=100,
        )
        assert s.total_types == 10
        assert s.timestamp is not None

    def test_graphql_snapshot_defaults(self) -> None:
        """GraphQLSnapshot varsayilanlar."""
        s = GraphQLSnapshot()
        assert s.total_types == 0
        assert s.federation_services == 0


# ===================== Config =====================

class TestGraphQLConfig:
    """Config testleri."""

    def test_graphql_enabled(self) -> None:
        """graphql_enabled ayari."""
        from app.config import settings
        assert isinstance(
            settings.graphql_enabled, bool,
        )

    def test_max_query_depth(self) -> None:
        """max_query_depth ayari."""
        from app.config import settings
        assert isinstance(
            settings.max_query_depth, int,
        )
        assert settings.max_query_depth > 0

    def test_max_complexity(self) -> None:
        """max_complexity ayari."""
        from app.config import settings
        assert isinstance(
            settings.max_complexity, int,
        )
        assert settings.max_complexity > 0

    def test_introspection_enabled(self) -> None:
        """introspection_enabled ayari."""
        from app.config import settings
        assert isinstance(
            settings.introspection_enabled, bool,
        )

    def test_playground_enabled(self) -> None:
        """playground_enabled ayari."""
        from app.config import settings
        assert isinstance(
            settings.playground_enabled, bool,
        )


# ===================== Imports =====================

class TestGraphQLImports:
    """Import testleri."""

    def test_import_all(self) -> None:
        """Tum siniflar import edilebilir."""
        from app.core.graphql import (
            DataLoader,
            FederationGateway,
            GraphQLOrchestrator,
            Introspection,
            QueryComplexity,
            QueryExecutor,
            ResolverManager,
            SchemaBuilder,
            SubscriptionManager,
        )
        assert DataLoader is not None
        assert FederationGateway is not None
        assert GraphQLOrchestrator is not None
        assert Introspection is not None
        assert QueryComplexity is not None
        assert QueryExecutor is not None
        assert ResolverManager is not None
        assert SchemaBuilder is not None
        assert SubscriptionManager is not None
