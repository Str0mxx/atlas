"""ATLAS Event Sourcing & CQRS testleri."""

import time

from app.models.eventsourcing import (
    EventType,
    CommandStatus,
    SagaState,
    ProjectionStatus,
    ConsistencyLevel,
    AggregateStatus,
    EventRecord,
    CommandRecord,
    SagaRecord,
    ESSnapshot,
)
from app.core.eventsourcing.event_store import (
    EventStore,
)
from app.core.eventsourcing.event_publisher import (
    EventPublisher,
)
from app.core.eventsourcing.event_handler import (
    EventHandler,
)
from app.core.eventsourcing.aggregate_root import (
    AggregateRoot,
)
from app.core.eventsourcing.command_bus import (
    CommandBus,
)
from app.core.eventsourcing.query_handler import (
    QueryHandler,
)
from app.core.eventsourcing.projection_manager import (
    ProjectionManager,
)
from app.core.eventsourcing.saga_coordinator import (
    SagaCoordinator,
)
from app.core.eventsourcing.es_orchestrator import (
    EventSourcingOrchestrator,
)
from app.config import Settings


# ---- Model Testleri ----

class TestESModels:
    def test_event_type_enum(self):
        assert EventType.DOMAIN == "domain"
        assert EventType.INTEGRATION == "integration"
        assert EventType.SYSTEM == "system"
        assert EventType.SNAPSHOT == "snapshot"
        assert EventType.COMPENSATION == "compensation"
        assert EventType.NOTIFICATION == "notification"

    def test_command_status_enum(self):
        assert CommandStatus.PENDING == "pending"
        assert CommandStatus.COMPLETED == "completed"
        assert CommandStatus.FAILED == "failed"
        assert CommandStatus.REJECTED == "rejected"

    def test_saga_state_enum(self):
        assert SagaState.STARTED == "started"
        assert SagaState.RUNNING == "running"
        assert SagaState.COMPENSATING == "compensating"
        assert SagaState.COMPLETED == "completed"
        assert SagaState.TIMED_OUT == "timed_out"

    def test_projection_status_enum(self):
        assert ProjectionStatus.ACTIVE == "active"
        assert ProjectionStatus.REBUILDING == "rebuilding"
        assert ProjectionStatus.PAUSED == "paused"
        assert ProjectionStatus.STALE == "stale"

    def test_consistency_level_enum(self):
        assert ConsistencyLevel.STRONG == "strong"
        assert ConsistencyLevel.EVENTUAL == "eventual"
        assert ConsistencyLevel.CAUSAL == "causal"

    def test_aggregate_status_enum(self):
        assert AggregateStatus.ACTIVE == "active"
        assert AggregateStatus.ARCHIVED == "archived"
        assert AggregateStatus.DELETED == "deleted"

    def test_event_record_defaults(self):
        r = EventRecord()
        assert r.event_id
        assert r.event_type == EventType.DOMAIN
        assert r.version == 1
        assert isinstance(r.data, dict)

    def test_command_record_defaults(self):
        r = CommandRecord()
        assert r.command_id
        assert r.status == CommandStatus.PENDING
        assert isinstance(r.payload, dict)

    def test_saga_record_defaults(self):
        r = SagaRecord()
        assert r.saga_id
        assert r.state == SagaState.STARTED
        assert r.steps_completed == 0

    def test_es_snapshot_defaults(self):
        s = ESSnapshot()
        assert s.total_events == 0
        assert s.total_commands == 0
        assert s.active_sagas == 0


# ---- EventStore Testleri ----

class TestEventStore:
    def test_append(self):
        s = EventStore()
        e = s.append("s1", "created", {"k": "v"})
        assert e["stream_id"] == "s1"
        assert e["event_type"] == "created"
        assert e["data"]["k"] == "v"
        assert e["version"] == 1

    def test_append_increments_version(self):
        s = EventStore()
        s.append("s1", "e1")
        e2 = s.append("s1", "e2")
        assert e2["version"] == 2

    def test_append_expected_version(self):
        s = EventStore()
        s.append("s1", "e1")
        e2 = s.append("s1", "e2", expected_version=1)
        assert e2["version"] == 2

    def test_append_version_conflict(self):
        s = EventStore()
        s.append("s1", "e1")
        try:
            s.append("s1", "e2", expected_version=0)
            assert False, "Should raise"
        except ValueError as e:
            assert "Version conflict" in str(e)

    def test_read_stream(self):
        s = EventStore()
        s.append("s1", "e1")
        s.append("s1", "e2")
        events = s.read_stream("s1")
        assert len(events) == 2

    def test_read_stream_from_version(self):
        s = EventStore()
        s.append("s1", "e1")
        s.append("s1", "e2")
        s.append("s1", "e3")
        events = s.read_stream("s1", from_version=2)
        assert len(events) == 2

    def test_read_stream_range(self):
        s = EventStore()
        for i in range(5):
            s.append("s1", f"e{i}")
        events = s.read_stream(
            "s1", from_version=2, to_version=4,
        )
        assert len(events) == 3

    def test_read_stream_empty(self):
        s = EventStore()
        events = s.read_stream("nonexistent")
        assert events == []

    def test_read_all(self):
        s = EventStore()
        s.append("s1", "e1")
        s.append("s2", "e2")
        events = s.read_all()
        assert len(events) == 2

    def test_read_all_limit(self):
        s = EventStore()
        for i in range(10):
            s.append("s1", f"e{i}")
        events = s.read_all(limit=5)
        assert len(events) == 5

    def test_get_stream_version(self):
        s = EventStore()
        assert s.get_stream_version("s1") == 0
        s.append("s1", "e1")
        assert s.get_stream_version("s1") == 1

    def test_save_and_get_snapshot(self):
        s = EventStore()
        s.save_snapshot("s1", {"count": 5}, 5)
        snap = s.get_snapshot("s1")
        assert snap["state"]["count"] == 5
        assert snap["version"] == 5

    def test_get_snapshot_none(self):
        s = EventStore()
        assert s.get_snapshot("none") is None

    def test_delete_stream(self):
        s = EventStore()
        s.append("s1", "e1")
        assert s.delete_stream("s1") is True
        assert s.stream_count == 0

    def test_delete_stream_not_found(self):
        s = EventStore()
        assert s.delete_stream("none") is False

    def test_get_streams(self):
        s = EventStore()
        s.append("s1", "e1")
        s.append("s2", "e2")
        streams = s.get_streams()
        assert "s1" in streams
        assert "s2" in streams

    def test_properties(self):
        s = EventStore()
        s.append("s1", "e1")
        s.append("s1", "e2")
        s.save_snapshot("s1", {}, 2)
        assert s.stream_count == 1
        assert s.event_count == 2
        assert s.snapshot_count == 1
        assert s.global_position == 2


# ---- EventPublisher Testleri ----

class TestEventPublisher:
    def test_subscribe(self):
        p = EventPublisher()
        r = p.subscribe("created", lambda t, d: None, "s1")
        assert r["subscriber_id"] == "s1"
        assert p.subscriber_count == 1

    def test_unsubscribe(self):
        p = EventPublisher()
        p.subscribe("created", lambda t, d: None, "s1")
        assert p.unsubscribe("created", "s1") is True
        assert p.subscriber_count == 0

    def test_unsubscribe_not_found(self):
        p = EventPublisher()
        assert p.unsubscribe("x", "y") is False

    def test_publish(self):
        received = []
        p = EventPublisher()
        p.subscribe(
            "created",
            lambda t, d: received.append(d),
        )
        r = p.publish("created", {"k": "v"})
        assert r["delivered"] == 1
        assert r["failed"] == 0
        assert received[0]["k"] == "v"

    def test_publish_no_subscribers(self):
        p = EventPublisher()
        r = p.publish("created")
        assert r["subscribers"] == 0
        assert r["delivered"] == 0

    def test_publish_handler_error(self):
        def bad_handler(t, d):
            raise ValueError("boom")

        p = EventPublisher(max_retries=1)
        p.subscribe("err", bad_handler, "s1")
        r = p.publish("err")
        assert r["failed"] == 1
        assert p.dead_letter_count == 1

    def test_broadcast(self):
        received = []
        p = EventPublisher()
        p.subscribe(
            "a", lambda t, d: received.append("a"),
        )
        p.subscribe(
            "b", lambda t, d: received.append("b"),
        )
        r = p.broadcast({"x": 1})
        assert r["types_published"] == 2
        assert r["total_delivered"] == 2

    def test_retry_dead_letters(self):
        call_count = [0]

        def flaky(t, d):
            call_count[0] += 1
            if call_count[0] <= 1:
                raise ValueError("fail")

        p = EventPublisher(max_retries=1)
        p.subscribe("x", flaky, "s1")
        p.publish("x")
        assert p.dead_letter_count == 1

        r = p.retry_dead_letters()
        assert r["recovered"] == 1
        assert r["remaining"] == 0

    def test_get_subscribers(self):
        p = EventPublisher()
        p.subscribe("a", lambda t, d: None, "s1")
        p.subscribe("b", lambda t, d: None, "s2")
        subs = p.get_subscribers()
        assert len(subs) == 2

    def test_get_subscribers_by_type(self):
        p = EventPublisher()
        p.subscribe("a", lambda t, d: None, "s1")
        p.subscribe("b", lambda t, d: None, "s2")
        subs = p.get_subscribers("a")
        assert len(subs) == 1

    def test_published_count(self):
        p = EventPublisher()
        p.publish("x")
        p.publish("y")
        assert p.published_count == 2


# ---- EventHandler Testleri ----

class TestEventHandler:
    def test_register(self):
        h = EventHandler()
        r = h.register("created", lambda d: d, "h1")
        assert r["handler_id"] == "h1"
        assert h.handler_count == 1

    def test_unregister(self):
        h = EventHandler()
        h.register("created", lambda d: d, "h1")
        assert h.unregister("created", "h1") is True
        assert h.handler_count == 0

    def test_unregister_not_found(self):
        h = EventHandler()
        assert h.unregister("x", "y") is False

    def test_handle(self):
        results = []
        h = EventHandler()
        h.register(
            "created",
            lambda d: results.append(d),
            "h1",
        )
        r = h.handle("created", "e1", {"k": "v"})
        assert r["status"] == "success"
        assert r["handlers_called"] == 1
        assert results[0]["k"] == "v"

    def test_handle_idempotent(self):
        count = [0]
        h = EventHandler()
        h.register(
            "created",
            lambda d: count.__setitem__(0, count[0] + 1),
            "h1",
            idempotent=True,
        )
        h.handle("created", "e1")
        r2 = h.handle("created", "e1")
        assert r2["status"] == "duplicate"
        assert count[0] == 1

    def test_handle_error(self):
        def bad(d):
            raise ValueError("boom")

        h = EventHandler()
        h.register("err", bad, "h1")
        r = h.handle("err", "e1")
        assert r["status"] == "partial"
        assert r["errors"] == 1
        assert h.error_count == 1

    def test_handle_batch(self):
        count = [0]
        h = EventHandler()
        h.register(
            "a",
            lambda d: count.__setitem__(0, count[0] + 1),
            idempotent=False,
        )
        events = [
            {"event_type": "a", "event_id": "1"},
            {"event_type": "a", "event_id": "2"},
        ]
        r = h.handle_batch(events)
        assert r["processed"] == 2

    def test_handle_batch_duplicates(self):
        h = EventHandler()
        h.register("a", lambda d: None, idempotent=True)
        events = [
            {"event_type": "a", "event_id": "1"},
            {"event_type": "a", "event_id": "1"},
        ]
        r = h.handle_batch(events)
        assert r["duplicates"] == 1

    def test_get_handlers(self):
        h = EventHandler()
        h.register("a", lambda d: d, "h1")
        h.register("b", lambda d: d, "h2")
        handlers = h.get_handlers()
        assert len(handlers) == 2

    def test_get_handlers_by_type(self):
        h = EventHandler()
        h.register("a", lambda d: d, "h1")
        h.register("b", lambda d: d, "h2")
        handlers = h.get_handlers("a")
        assert len(handlers) == 1

    def test_clear_processed(self):
        h = EventHandler()
        h.register("a", lambda d: None, idempotent=True)
        h.handle("a", "e1")
        count = h.clear_processed()
        assert count >= 1

    def test_processed_count(self):
        h = EventHandler()
        h.register("a", lambda d: None)
        h.handle("a", "e1")
        assert h.processed_count == 1


# ---- AggregateRoot Testleri ----

class TestAggregateRoot:
    def test_init(self):
        a = AggregateRoot("a1", "order")
        assert a.aggregate_id == "a1"
        assert a.aggregate_type == "order"
        assert a.version == 0

    def test_apply_event(self):
        a = AggregateRoot("a1")
        e = a.apply_event("created", {"name": "x"})
        assert e["event_type"] == "created"
        assert e["version"] == 1
        assert a.state["name"] == "x"
        assert a.version == 1

    def test_apply_event_custom_applier(self):
        a = AggregateRoot("a1")

        def apply_add(state, data):
            state["items"] = state.get("items", [])
            state["items"].append(data["item"])

        a.register_event_applier("add_item", apply_add)
        a.apply_event("add_item", {"item": "x"})
        a.apply_event("add_item", {"item": "y"})
        assert a.state["items"] == ["x", "y"]

    def test_handle_command(self):
        a = AggregateRoot("a1")

        def create_handler(payload):
            a.apply_event("created", payload)
            return {"ok": True}

        a.register_command_handler(
            "create", create_handler,
        )
        r = a.handle_command("create", {"name": "test"})
        assert r["result"]["ok"] is True
        assert a.state["name"] == "test"

    def test_handle_command_unknown(self):
        a = AggregateRoot("a1")
        try:
            a.handle_command("unknown")
            assert False, "Should raise"
        except ValueError as e:
            assert "Unknown command" in str(e)

    def test_invariant_violation(self):
        a = AggregateRoot("a1")
        a.add_invariant(
            lambda state: state.get("count", 0) >= 0,
        )

        def dec_handler(payload):
            a.apply_event("dec", {"count": -1})
            return {}

        a.register_command_handler("dec", dec_handler)
        try:
            a.handle_command("dec")
            assert False, "Should raise"
        except ValueError as e:
            assert "Invariant violation" in str(e)

    def test_uncommitted_events(self):
        a = AggregateRoot("a1")
        a.apply_event("e1")
        a.apply_event("e2")
        events = a.get_uncommitted_events()
        assert len(events) == 2
        assert a.uncommitted_count == 2

    def test_clear_uncommitted(self):
        a = AggregateRoot("a1")
        a.apply_event("e1")
        count = a.clear_uncommitted()
        assert count == 1
        assert a.uncommitted_count == 0

    def test_load_from_history(self):
        a = AggregateRoot("a1")
        history = [
            {"event_type": "created", "data": {"name": "x"}, "version": 1},
            {"event_type": "updated", "data": {"name": "y"}, "version": 2},
        ]
        a.load_from_history(history)
        assert a.state["name"] == "y"
        assert a.version == 2

    def test_snapshot(self):
        a = AggregateRoot("a1", "order")
        a.apply_event("created", {"name": "x"})
        snap = a.get_snapshot()
        assert snap["aggregate_id"] == "a1"
        assert snap["state"]["name"] == "x"
        assert snap["version"] == 1

    def test_load_from_snapshot(self):
        a = AggregateRoot("a1")
        a.load_from_snapshot({
            "state": {"name": "x"},
            "version": 5,
        })
        assert a.state["name"] == "x"
        assert a.version == 5


# ---- CommandBus Testleri ----

class TestCommandBus:
    def test_register_handler(self):
        b = CommandBus()
        r = b.register_handler(
            "create", lambda p: {"ok": True},
        )
        assert r["command_type"] == "create"
        assert b.handler_count == 1

    def test_dispatch(self):
        b = CommandBus()
        b.register_handler(
            "create", lambda p: {"id": 1},
        )
        r = b.dispatch("create", {"name": "x"})
        assert r["status"] == "completed"
        assert r["result"]["id"] == 1

    def test_dispatch_no_handler(self):
        b = CommandBus()
        r = b.dispatch("unknown")
        assert r["status"] == "rejected"
        assert r["reason"] == "no_handler"

    def test_dispatch_validation_failed(self):
        b = CommandBus()
        b.register_handler("create", lambda p: {})
        b.register_validator(
            "create",
            lambda p: "name" in p,
        )
        r = b.dispatch("create", {})
        assert r["status"] == "rejected"
        assert r["reason"] == "validation_failed"

    def test_dispatch_unauthorized(self):
        b = CommandBus()
        b.register_handler("create", lambda p: {})
        b.register_authorizer(
            "create",
            lambda actor, p: actor == "admin",
        )
        r = b.dispatch(
            "create", {}, actor="guest",
        )
        assert r["status"] == "rejected"
        assert r["reason"] == "unauthorized"

    def test_dispatch_authorized(self):
        b = CommandBus()
        b.register_handler("create", lambda p: {})
        b.register_authorizer(
            "create",
            lambda actor, p: actor == "admin",
        )
        r = b.dispatch(
            "create", {}, actor="admin",
        )
        assert r["status"] == "completed"

    def test_dispatch_handler_error(self):
        def bad(p):
            raise ValueError("boom")

        b = CommandBus()
        b.register_handler("fail", bad)
        r = b.dispatch("fail")
        assert r["status"] == "failed"
        assert "boom" in r["error"]

    def test_middleware(self):
        log = []
        b = CommandBus()
        b.register_handler("create", lambda p: {})
        b.add_middleware(
            lambda cmd, p: log.append(cmd),
        )
        b.dispatch("create")
        assert "create" in log

    def test_dispatch_batch(self):
        b = CommandBus()
        b.register_handler("a", lambda p: {})
        r = b.dispatch_batch([
            {"command_type": "a"},
            {"command_type": "a"},
            {"command_type": "b"},
        ])
        assert r["completed"] == 2
        assert r["rejected"] == 1

    def test_get_history(self):
        b = CommandBus()
        b.register_handler("a", lambda p: {})
        b.dispatch("a")
        b.dispatch("b")
        assert len(b.get_history()) == 2
        assert len(b.get_history(status="completed")) == 1

    def test_success_rate(self):
        b = CommandBus()
        b.register_handler("a", lambda p: {})
        b.dispatch("a")
        b.dispatch("b")
        assert b.success_rate == 0.5

    def test_success_rate_empty(self):
        b = CommandBus()
        assert b.success_rate == 0.0


# ---- QueryHandler Testleri ----

class TestQueryHandler:
    def test_register_handler(self):
        q = QueryHandler()
        r = q.register_handler(
            "get_all", lambda p: [],
        )
        assert r["query_type"] == "get_all"
        assert q.handler_count == 1

    def test_query(self):
        q = QueryHandler()
        q.register_handler(
            "get_items",
            lambda p: [{"id": 1}, {"id": 2}],
        )
        r = q.query("get_items")
        assert r["status"] == "success"
        assert len(r["data"]) == 2

    def test_query_not_found(self):
        q = QueryHandler()
        r = q.query("unknown")
        assert r["status"] == "not_found"

    def test_query_cache(self):
        call_count = [0]

        def handler(p):
            call_count[0] += 1
            return [1, 2, 3]

        q = QueryHandler(cache_ttl=60)
        q.register_handler("items", handler)
        q.query("items")
        q.query("items")
        assert call_count[0] == 1

    def test_query_no_cache(self):
        call_count = [0]

        def handler(p):
            call_count[0] += 1
            return []

        q = QueryHandler()
        q.register_handler("items", handler)
        q.query("items", use_cache=False)
        q.query("items", use_cache=False)
        assert call_count[0] == 2

    def test_query_error(self):
        q = QueryHandler()
        q.register_handler(
            "bad",
            lambda p: (_ for _ in ()).throw(
                ValueError("boom"),
            ),
        )
        r = q.query("bad", use_cache=False)
        assert r["status"] == "error"

    def test_query_paginated(self):
        q = QueryHandler()
        q.register_handler(
            "items",
            lambda p: list(range(25)),
        )
        r = q.query_paginated(
            "items", page=2, page_size=10,
        )
        assert r["status"] == "success"
        assert len(r["data"]) == 10
        assert r["pagination"]["page"] == 2
        assert r["pagination"]["total"] == 25
        assert r["pagination"]["total_pages"] == 3

    def test_query_paginated_last_page(self):
        q = QueryHandler()
        q.register_handler(
            "items",
            lambda p: list(range(25)),
        )
        r = q.query_paginated(
            "items", page=3, page_size=10,
        )
        assert len(r["data"]) == 5

    def test_query_filtered(self):
        q = QueryHandler()
        q.register_handler(
            "items",
            lambda p: [
                {"name": "a", "type": "x"},
                {"name": "b", "type": "y"},
                {"name": "c", "type": "x"},
            ],
        )
        r = q.query_filtered(
            "items", filters={"type": "x"},
        )
        assert r["filtered_count"] == 2
        assert r["original_count"] == 3

    def test_invalidate_cache(self):
        q = QueryHandler()
        q.register_handler("a", lambda p: [])
        q.query("a")
        assert q.cache_size == 1
        count = q.invalidate_cache()
        assert count == 1
        assert q.cache_size == 0

    def test_invalidate_cache_by_type(self):
        q = QueryHandler()
        q.register_handler("a", lambda p: [])
        q.register_handler("b", lambda p: [])
        q.query("a")
        q.query("b")
        count = q.invalidate_cache("a")
        assert count == 1
        assert q.cache_size == 1

    def test_query_count(self):
        q = QueryHandler()
        q.register_handler("a", lambda p: [])
        q.query("a")
        q.query("a")
        assert q.query_count == 2


# ---- ProjectionManager Testleri ----

class TestProjectionMgr:
    def test_register_projection(self):
        p = ProjectionManager()
        r = p.register_projection(
            "orders", lambda t, d: d,
        )
        assert r["name"] == "orders"
        assert r["status"] == "active"
        assert p.projection_count == 1

    def test_project_event(self):
        p = ProjectionManager()
        p.register_projection(
            "log",
            lambda t, d: {"type": t, **d},
        )
        r = p.project_event("created", {"id": 1})
        assert r["applied"] == 1

    def test_project_event_filter(self):
        p = ProjectionManager()
        p.register_projection(
            "orders",
            lambda t, d: d,
            event_types=["order_created"],
        )
        r = p.project_event("user_created", {})
        assert r["applied"] == 0
        assert r["skipped"] == 1

    def test_project_event_error(self):
        def bad(t, d):
            raise ValueError("boom")

        p = ProjectionManager()
        p.register_projection("bad", bad)
        p.project_event("x", {})
        status = p.get_projection_status("bad")
        assert status["status"] == "error"

    def test_rebuild(self):
        items = []
        p = ProjectionManager()
        p.register_projection(
            "log",
            lambda t, d: items.append(d) or d,
        )
        events = [
            {"event_type": "a", "data": {"x": 1}},
            {"event_type": "b", "data": {"x": 2}},
        ]
        r = p.rebuild("log", events)
        assert r["status"] == "completed"
        assert r["processed"] == 2

    def test_rebuild_not_found(self):
        p = ProjectionManager()
        r = p.rebuild("none", [])
        assert r["status"] == "not_found"

    def test_check_consistency(self):
        p = ProjectionManager()
        p.register_projection("log", lambda t, d: d)
        p.project_event("a", {})
        p.project_event("b", {})
        r = p.check_consistency("log", 2)
        assert r["consistent"] is True
        assert r["drift"] == 0

    def test_check_consistency_drift(self):
        p = ProjectionManager()
        p.register_projection("log", lambda t, d: d)
        p.project_event("a", {})
        r = p.check_consistency("log", 5)
        assert r["consistent"] is False
        assert r["drift"] == 4

    def test_get_read_model(self):
        p = ProjectionManager()
        p.register_projection(
            "log", lambda t, d: d,
        )
        p.project_event("a", {"x": 1})
        model = p.get_read_model("log")
        assert len(model) == 1

    def test_pause_resume(self):
        p = ProjectionManager()
        p.register_projection("log", lambda t, d: d)
        assert p.pause_projection("log") is True
        status = p.get_projection_status("log")
        assert status["status"] == "paused"
        assert p.resume_projection("log") is True
        status = p.get_projection_status("log")
        assert status["status"] == "active"

    def test_pause_not_found(self):
        p = ProjectionManager()
        assert p.pause_projection("none") is False

    def test_resume_not_paused(self):
        p = ProjectionManager()
        p.register_projection("log", lambda t, d: d)
        assert p.resume_projection("log") is False

    def test_active_count(self):
        p = ProjectionManager()
        p.register_projection("a", lambda t, d: d)
        p.register_projection("b", lambda t, d: d)
        p.pause_projection("b")
        assert p.active_count == 1


# ---- SagaCoordinator Testleri ----

class TestSagaCoord:
    def test_define_saga(self):
        s = SagaCoordinator()
        r = s.define_saga("order", [
            {"name": "validate"},
            {"name": "pay"},
            {"name": "ship"},
        ])
        assert r["saga_type"] == "order"
        assert r["step_count"] == 3
        assert s.definition_count == 1

    def test_start_saga(self):
        s = SagaCoordinator()
        s.define_saga("order", [{"name": "s1"}])
        r = s.start_saga("order", {"id": 1})
        assert r["state"] == "running"
        assert s.active_count == 1

    def test_start_saga_undefined(self):
        s = SagaCoordinator()
        r = s.start_saga("unknown")
        assert r["status"] == "error"

    def test_advance_step(self):
        s = SagaCoordinator()
        s.define_saga("order", [
            {"name": "s1"},
            {"name": "s2"},
        ])
        r = s.start_saga("order")
        saga_id = r["saga_id"]
        r = s.advance_step(saga_id, {"ok": True})
        assert r["steps_completed"] == 1
        assert r["state"] == "running"

    def test_advance_completes(self):
        s = SagaCoordinator()
        s.define_saga("order", [{"name": "s1"}])
        r = s.start_saga("order")
        saga_id = r["saga_id"]
        r = s.advance_step(saga_id)
        assert r["state"] == "completed"
        assert s.completed_count == 1

    def test_advance_not_found(self):
        s = SagaCoordinator()
        r = s.advance_step("none")
        assert r["status"] == "error"

    def test_compensate(self):
        compensated = []
        s = SagaCoordinator()
        s.define_saga("order", [
            {"name": "s1"},
            {"name": "s2"},
        ])
        r = s.start_saga("order")
        saga_id = r["saga_id"]
        s.advance_step(
            saga_id,
            compensation=lambda ctx: compensated.append("c1"),
        )
        r = s.compensate(saga_id, "test_reason")
        assert r["compensated"] == 1
        assert len(compensated) == 1

    def test_compensate_not_found(self):
        s = SagaCoordinator()
        r = s.compensate("none")
        assert r["status"] == "error"

    def test_get_saga(self):
        s = SagaCoordinator()
        s.define_saga("order", [{"name": "s1"}])
        r = s.start_saga("order")
        saga_id = r["saga_id"]
        saga = s.get_saga(saga_id)
        assert saga["saga_type"] == "order"
        assert saga["state"] == "running"

    def test_get_saga_none(self):
        s = SagaCoordinator()
        assert s.get_saga("none") is None

    def test_check_timeouts(self):
        s = SagaCoordinator(default_timeout=0)
        s.define_saga("order", [{"name": "s1"}])
        s.start_saga("order")
        time.sleep(0.01)
        r = s.check_timeouts()
        assert r["timed_out"] == 1

    def test_recover_saga(self):
        s = SagaCoordinator(default_timeout=0)
        s.define_saga("order", [
            {"name": "s1"},
            {"name": "s2"},
        ])
        r = s.start_saga("order")
        saga_id = r["saga_id"]
        time.sleep(0.01)
        s.check_timeouts()
        r = s.recover_saga(saga_id)
        assert r["status"] == "recovered"

    def test_recover_not_needed(self):
        s = SagaCoordinator()
        s.define_saga("order", [{"name": "s1"}])
        r = s.start_saga("order")
        saga_id = r["saga_id"]
        r = s.recover_saga(saga_id)
        assert r["status"] == "no_recovery_needed"

    def test_recover_not_found(self):
        s = SagaCoordinator()
        r = s.recover_saga("none")
        assert r["status"] == "error"

    def test_total_count(self):
        s = SagaCoordinator()
        s.define_saga("a", [{"name": "s"}])
        s.start_saga("a")
        s.start_saga("a")
        assert s.total_count == 2


# ---- EventSourcingOrchestrator Testleri ----

class TestESOrch:
    def test_init(self):
        o = EventSourcingOrchestrator()
        assert o.store is not None
        assert o.publisher is not None
        assert o.handler is not None
        assert o.command_bus is not None

    def test_emit_event(self):
        o = EventSourcingOrchestrator()
        e = o.emit_event("s1", "created", {"k": "v"})
        assert e["event_type"] == "created"
        assert o.store.event_count == 1

    def test_emit_event_auto_snapshot(self):
        o = EventSourcingOrchestrator(
            snapshot_frequency=2,
        )
        o.emit_event("s1", "e1")
        assert o.store.get_snapshot("s1") is None
        o.emit_event("s1", "e2")
        snap = o.store.get_snapshot("s1")
        assert snap is not None

    def test_execute_command(self):
        o = EventSourcingOrchestrator()
        o.command_bus.register_handler(
            "create", lambda p: {"id": 1},
        )
        r = o.execute_command("create", {"name": "x"})
        assert r["status"] == "completed"

    def test_run_query(self):
        o = EventSourcingOrchestrator()
        o.query_handler.register_handler(
            "items", lambda p: [1, 2, 3],
        )
        r = o.run_query("items")
        assert r["status"] == "success"
        assert len(r["data"]) == 3

    def test_create_aggregate(self):
        o = EventSourcingOrchestrator()
        agg = o.create_aggregate("a1", "order")
        assert agg.aggregate_id == "a1"
        assert o.get_aggregate("a1") is agg

    def test_get_aggregate_none(self):
        o = EventSourcingOrchestrator()
        assert o.get_aggregate("none") is None

    def test_replay_events(self):
        o = EventSourcingOrchestrator()
        o.store.append("s1", "e1", {"x": 1})
        o.store.append("s1", "e2", {"x": 2})
        r = o.replay_events("s1")
        assert r["replayed"] == 2

    def test_get_analytics(self):
        o = EventSourcingOrchestrator()
        o.emit_event("s1", "e1")
        a = o.get_analytics()
        assert a["total_events"] == 1
        assert a["total_streams"] == 1

    def test_snapshot(self):
        o = EventSourcingOrchestrator()
        o.emit_event("s1", "e1")
        snap = o.snapshot()
        assert snap["events"] == 1
        assert snap["streams"] == 1
        assert "uptime" in snap


# ---- Config Testleri ----

class TestESConfig:
    def test_config_defaults(self):
        s = Settings()
        assert s.eventsourcing_enabled is True
        assert s.snapshot_frequency == 100
        assert s.event_retention_days == 90
        assert s.projection_rebuild_batch == 100
        assert s.saga_timeout_minutes == 60
