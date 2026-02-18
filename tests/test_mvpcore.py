"""
Working MVP Core testleri.

CoreEngine, CoreEventLoop, CoreSessionManager,
CoreWebSocketServer, CoreTaskExecutor,
CoreConfigLoader, HealthEndpoint,
GracefulShutdown, MVPCoreOrchestrator
testleri.
"""

import time

import pytest

from app.core.mvpcore.config_loader import (
    CoreConfigLoader,
)
from app.core.mvpcore.core_engine import (
    CoreEngine,
)
from app.core.mvpcore.event_loop import (
    CoreEventLoop,
)
from app.core.mvpcore.graceful_shutdown import (
    GracefulShutdown,
)
from app.core.mvpcore.health_endpoint import (
    HealthEndpoint,
)
from app.core.mvpcore.mvpcore_orchestrator import (
    MVPCoreOrchestrator,
)
from app.core.mvpcore.session_manager import (
    CoreSessionManager,
)
from app.core.mvpcore.task_executor import (
    CoreTaskExecutor,
)
from app.core.mvpcore.websocket_server import (
    CoreWebSocketServer,
)


# ==========================================
# CoreEngine Testleri
# ==========================================


class TestCoreEngine:
    """CoreEngine testleri."""

    def setup_method(self):
        self.engine = CoreEngine(
            app_name="test"
        )

    def test_init(self):
        assert self.engine.state == "created"
        assert self.engine.component_count == 0

    def test_register_component(self):
        r = self.engine.register_component(
            name="comp1",
            component=object(),
        )
        assert r["registered"] is True
        assert self.engine.component_count == 1

    def test_get_component(self):
        obj = object()
        self.engine.register_component(
            name="mycomp", component=obj
        )
        assert self.engine.get_component("mycomp") is obj
        assert self.engine.get_component("none") is None

    def test_resolve_dependencies(self):
        self.engine.register_component("a", object())
        self.engine.register_component(
            "b", object(), depends_on=["a"]
        )
        r = self.engine.resolve_dependencies()
        assert r["resolved"] is True
        assert r["order"] == ["a", "b"]

    def test_circular_dependency(self):
        self.engine.register_component(
            "x", object(), depends_on=["y"]
        )
        self.engine.register_component(
            "y", object(), depends_on=["x"]
        )
        r = self.engine.resolve_dependencies()
        assert r["resolved"] is False

    def test_initialize(self):
        self.engine.register_component("c", object())
        r = self.engine.initialize()
        assert r["started"] is True
        assert self.engine.state == "running"

    def test_shutdown(self):
        self.engine.register_component("c", object())
        self.engine.initialize()
        r = self.engine.shutdown()
        assert r["shutdown"] is True
        assert self.engine.state == "stopped"

    def test_lifecycle_hooks(self):
        called = []
        self.engine.add_hook(
            "pre_init", lambda: called.append("pre")
        )
        self.engine.add_hook(
            "post_init", lambda: called.append("post")
        )
        self.engine.initialize()
        assert "pre" in called
        assert "post" in called

    def test_add_hook_invalid(self):
        r = self.engine.add_hook("invalid_event")
        assert r["added"] is False

    def test_register_signal(self):
        r = self.engine.register_signal("SIGTERM")
        assert r["registered"] is True

    def test_emit_signal(self):
        results = []
        self.engine.register_signal(
            "test_sig",
            handler=lambda d: results.append(d),
        )
        r = self.engine.emit_signal("test_sig", "data")
        assert r["emitted"] is True
        assert "data" in results

    def test_get_summary(self):
        r = self.engine.get_summary()
        assert r["retrieved"] is True
        assert r["app_name"] == "test"

    def test_states_list(self):
        assert "running" in CoreEngine.STATES
        assert "error" in CoreEngine.STATES

    def test_component_with_metadata(self):
        r = self.engine.register_component(
            name="meta",
            component=object(),
            metadata={"version": "1.0"},
        )
        assert r["registered"] is True


# ==========================================
# CoreEventLoop Testleri
# ==========================================


class TestCoreEventLoop:
    """CoreEventLoop testleri."""

    def setup_method(self):
        self.loop = CoreEventLoop()

    def test_init(self):
        assert self.loop.queue_size == 0
        assert self.loop.is_running is False

    def test_start_stop(self):
        r = self.loop.start()
        assert r["running"] is True
        assert self.loop.is_running is True
        r = self.loop.stop()
        assert r["stopped"] is True

    def test_dispatch(self):
        r = self.loop.dispatch("test_event", {"key": "val"})
        assert r["dispatched"] is True
        assert self.loop.queue_size == 1

    def test_dispatch_priority(self):
        self.loop.dispatch("low", priority="low")
        self.loop.dispatch("critical", priority="critical")
        # Critical should be first
        r = self.loop.process_next()
        assert r["event_type"] == "critical"

    def test_on_off_handler(self):
        handler = lambda d: d
        r = self.loop.on("evt", handler)
        assert r["registered"] is True
        r = self.loop.off("evt", handler)
        assert r["removed"] is True

    def test_off_nonexistent(self):
        r = self.loop.off("evt", lambda: None)
        assert r["removed"] is False

    def test_process_next(self):
        results = []
        self.loop.on("test", lambda d: results.append(d))
        self.loop.dispatch("test", "hello")
        r = self.loop.process_next()
        assert r["processed"] is True
        assert "hello" in results

    def test_process_next_empty(self):
        r = self.loop.process_next()
        assert r["processed"] is False

    def test_process_all(self):
        self.loop.dispatch("a")
        self.loop.dispatch("b")
        r = self.loop.process_all()
        assert r["processed"] is True
        assert r["processed_count"] == 2

    def test_drain(self):
        self.loop.dispatch("a")
        self.loop.dispatch("b")
        r = self.loop.drain()
        assert r["drained"] == 2
        assert self.loop.queue_size == 0

    def test_backpressure(self):
        loop = CoreEventLoop(max_queue_size=10, backpressure_threshold=0.5)
        for i in range(6):
            loop.dispatch(f"evt_{i}")
        r = loop.dispatch("over_threshold")
        assert r["backpressure"] is True

    def test_queue_full(self):
        loop = CoreEventLoop(max_queue_size=2)
        loop.dispatch("a")
        loop.dispatch("b")
        r = loop.dispatch("c")
        assert r["dispatched"] is False
        assert r["backpressure"] is True

    def test_handler_error_recovery(self):
        def bad_handler(d):
            raise ValueError("boom")

        self.loop.on("err", bad_handler)
        self.loop.dispatch("err", "data")
        r = self.loop.process_next()
        assert r["processed"] is True
        assert r["error_count"] == 1

    def test_get_summary(self):
        r = self.loop.get_summary()
        assert r["retrieved"] is True


# ==========================================
# CoreSessionManager Testleri
# ==========================================


class TestCoreSessionManager:
    """CoreSessionManager testleri."""

    def setup_method(self):
        self.mgr = CoreSessionManager()

    def test_init(self):
        assert self.mgr.active_count == 0

    def test_create_session(self):
        r = self.mgr.create_session(user_id="user1")
        assert r["created"] is True
        assert r["user_id"] == "user1"
        assert self.mgr.active_count == 1

    def test_get_session(self):
        r = self.mgr.create_session(user_id="u1")
        sid = r["session_id"]
        s = self.mgr.get_session(sid)
        assert s["found"] is True
        assert s["user_id"] == "u1"

    def test_get_session_not_found(self):
        r = self.mgr.get_session("nonexistent")
        assert r["found"] is False

    def test_set_get_data(self):
        r = self.mgr.create_session()
        sid = r["session_id"]
        self.mgr.set_data(sid, "key1", "val1")
        d = self.mgr.get_data(sid, "key1")
        assert d["found"] is True
        assert d["value"] == "val1"

    def test_touch(self):
        r = self.mgr.create_session()
        sid = r["session_id"]
        t = self.mgr.touch(sid)
        assert t["touched"] is True

    def test_close_session(self):
        r = self.mgr.create_session()
        sid = r["session_id"]
        c = self.mgr.close_session(sid)
        assert c["closed"] is True
        assert self.mgr.active_count == 0

    def test_close_nonexistent(self):
        r = self.mgr.close_session("x")
        assert r["closed"] is False

    def test_cleanup(self):
        mgr = CoreSessionManager(default_timeout=0)
        mgr.create_session()
        time.sleep(0.01)
        r = mgr.cleanup()
        assert r["cleaned"] is True
        assert r["expired_count"] == 1

    def test_persist_restore(self):
        r = self.mgr.create_session(user_id="u1")
        sid = r["session_id"]
        p = self.mgr.persist_session(sid)
        assert p["persisted"] is True
        self.mgr.close_session(sid)
        res = self.mgr.restore_session(sid)
        assert res["restored"] is True
        assert self.mgr.active_count == 1

    def test_restore_nonexistent(self):
        r = self.mgr.restore_session("x")
        assert r["restored"] is False

    def test_max_sessions(self):
        mgr = CoreSessionManager(max_sessions=2)
        mgr.create_session()
        mgr.create_session()
        r = mgr.create_session()
        assert r["created"] is False

    def test_session_timeout_on_get(self):
        mgr = CoreSessionManager(default_timeout=0)
        r = mgr.create_session()
        time.sleep(0.01)
        s = mgr.get_session(r["session_id"])
        assert s["found"] is False

    def test_get_summary(self):
        r = self.mgr.get_summary()
        assert r["retrieved"] is True


# ==========================================
# CoreWebSocketServer Testleri
# ==========================================


class TestCoreWebSocketServer:
    """CoreWebSocketServer testleri."""

    def setup_method(self):
        self.ws = CoreWebSocketServer()

    def test_init(self):
        assert self.ws.connection_count == 0
        assert self.ws.is_running is False

    def test_start_stop(self):
        r = self.ws.start()
        assert r["started"] is True
        assert self.ws.is_running is True
        r = self.ws.stop()
        assert r["stopped"] is True

    def test_connect(self):
        r = self.ws.connect(client_id="c1")
        assert r["connected"] is True
        assert self.ws.connection_count == 1

    def test_disconnect(self):
        self.ws.connect(client_id="c1")
        r = self.ws.disconnect("c1")
        assert r["disconnected"] is True
        assert self.ws.connection_count == 0

    def test_disconnect_nonexistent(self):
        r = self.ws.disconnect("x")
        assert r["disconnected"] is False

    def test_send(self):
        self.ws.connect(client_id="c1")
        r = self.ws.send("c1", "chat", {"msg": "hi"})
        assert r["sent"] is True

    def test_send_nonexistent(self):
        r = self.ws.send("x", "chat", {})
        assert r["sent"] is False

    def test_receive(self):
        self.ws.connect(client_id="c1")
        r = self.ws.receive("c1", "chat", {"msg": "hi"})
        assert r["received"] is True

    def test_on_message(self):
        r = self.ws.on_message("chat", lambda c, d: None)
        assert r["registered"] is True

    def test_broadcast(self):
        self.ws.connect(client_id="c1")
        self.ws.connect(client_id="c2")
        r = self.ws.broadcast("update", {"v": 1})
        assert r["broadcast"] is True
        assert r["sent_to"] == 2

    def test_broadcast_exclude(self):
        self.ws.connect(client_id="c1")
        self.ws.connect(client_id="c2")
        r = self.ws.broadcast("update", {}, exclude=["c1"])
        assert r["sent_to"] == 1

    def test_join_room(self):
        self.ws.connect(client_id="c1")
        r = self.ws.join_room("c1", "room1")
        assert r["joined"] is True
        assert r["members"] == 1

    def test_leave_room(self):
        self.ws.connect(client_id="c1")
        self.ws.join_room("c1", "room1")
        r = self.ws.leave_room("c1", "room1")
        assert r["left"] is True

    def test_room_broadcast(self):
        self.ws.connect(client_id="c1")
        self.ws.connect(client_id="c2")
        self.ws.join_room("c1", "r1")
        self.ws.join_room("c2", "r1")
        r = self.ws.room_broadcast("r1", "msg", {})
        assert r["broadcast"] is True
        assert r["sent_to"] == 2

    def test_heartbeat(self):
        self.ws.connect(client_id="c1")
        r = self.ws.heartbeat("c1")
        assert r["alive"] is True

    def test_heartbeat_nonexistent(self):
        r = self.ws.heartbeat("x")
        assert r["alive"] is False

    def test_check_stale(self):
        ws = CoreWebSocketServer(heartbeat_interval=0)
        ws.connect(client_id="c1")
        # Force old heartbeat
        ws._connections["c1"]["last_heartbeat"] = 0
        r = ws.check_stale()
        assert r["stale_count"] == 1

    def test_max_connections(self):
        ws = CoreWebSocketServer(max_connections=1)
        ws.connect(client_id="c1")
        r = ws.connect(client_id="c2")
        assert r["connected"] is False

    def test_reconnect(self):
        self.ws.connect(client_id="c1")
        r = self.ws.connect(client_id="c1")
        assert r["reconnected"] is True

    def test_disconnect_removes_from_room(self):
        self.ws.connect(client_id="c1")
        self.ws.join_room("c1", "r1")
        self.ws.disconnect("c1")
        assert "c1" not in self.ws._rooms.get("r1", set())

    def test_get_summary(self):
        r = self.ws.get_summary()
        assert r["retrieved"] is True


# ==========================================
# CoreTaskExecutor Testleri
# ==========================================


class TestCoreTaskExecutor:
    """CoreTaskExecutor testleri."""

    def setup_method(self):
        self.executor = CoreTaskExecutor()

    def test_init(self):
        assert self.executor.queue_size == 0
        assert self.executor.running_count == 0

    def test_submit(self):
        r = self.executor.submit(func=lambda: 42)
        assert r["submitted"] is True
        assert self.executor.queue_size == 1

    def test_execute_next(self):
        self.executor.submit(func=lambda: 42)
        r = self.executor.execute_next()
        assert r["executed"] is True
        assert r["result"] == 42

    def test_execute_next_empty(self):
        r = self.executor.execute_next()
        assert r["executed"] is False

    def test_execute_all(self):
        self.executor.submit(func=lambda: 1)
        self.executor.submit(func=lambda: 2)
        r = self.executor.execute_all()
        assert r["executed"] is True
        assert r["completed"] == 2

    def test_priority_ordering(self):
        self.executor.submit(func=lambda: "low", priority="low")
        self.executor.submit(func=lambda: "high", priority="high")
        r = self.executor.execute_next()
        assert r["result"] == "high"

    def test_cancel(self):
        r = self.executor.submit(func=lambda: 1)
        tid = r["task_id"]
        c = self.executor.cancel(tid)
        assert c["cancelled"] is True
        assert self.executor.queue_size == 0

    def test_cancel_nonexistent(self):
        r = self.executor.cancel("x")
        assert r["cancelled"] is False

    def test_cancel_completed(self):
        r = self.executor.submit(func=lambda: 1)
        tid = r["task_id"]
        self.executor.execute_next()
        c = self.executor.cancel(tid)
        assert c["cancelled"] is False

    def test_get_result(self):
        r = self.executor.submit(func=lambda: 99)
        tid = r["task_id"]
        self.executor.execute_next()
        res = self.executor.get_result(tid)
        assert res["found"] is True
        assert res["result"] == 99

    def test_get_result_not_found(self):
        r = self.executor.get_result("x")
        assert r["found"] is False

    def test_get_task_status(self):
        r = self.executor.submit(func=lambda: 1)
        tid = r["task_id"]
        s = self.executor.get_task_status(tid)
        assert s["found"] is True
        assert s["state"] == "queued"

    def test_failed_task(self):
        def fail():
            raise ValueError("boom")

        r = self.executor.submit(func=fail)
        tid = r["task_id"]
        res = self.executor.execute_next()
        assert res["executed"] is False
        result = self.executor.get_result(tid)
        assert result["state"] == "failed"

    def test_retry(self):
        counter = {"val": 0}

        def inc():
            counter["val"] += 1
            if counter["val"] < 2:
                raise ValueError("not yet")
            return counter["val"]

        r = self.executor.submit(func=inc)
        tid = r["task_id"]
        self.executor.execute_next()  # fails
        ret = self.executor.retry(tid)
        assert ret["retried"] is True
        res = self.executor.execute_next()  # succeeds
        assert res["executed"] is True

    def test_retry_non_failed(self):
        r = self.executor.submit(func=lambda: 1)
        tid = r["task_id"]
        ret = self.executor.retry(tid)
        assert ret["retried"] is False

    def test_queue_full(self):
        ex = CoreTaskExecutor(max_queue_size=1)
        ex.submit(func=lambda: 1)
        r = ex.submit(func=lambda: 2)
        assert r["submitted"] is False

    def test_max_concurrent(self):
        ex = CoreTaskExecutor(max_concurrent=0)
        ex.submit(func=lambda: 1)
        r = ex.execute_next()
        assert r["executed"] is False

    def test_get_summary(self):
        r = self.executor.get_summary()
        assert r["retrieved"] is True


# ==========================================
# CoreConfigLoader Testleri
# ==========================================


class TestCoreConfigLoader:
    """CoreConfigLoader testleri."""

    def setup_method(self):
        self.loader = CoreConfigLoader(
            auto_load_env=False
        )

    def test_init(self):
        assert self.loader.config_count == 0

    def test_set_get(self):
        self.loader.set("key1", "val1")
        assert self.loader.get("key1") == "val1"

    def test_get_default(self):
        assert self.loader.get("missing", "def") == "def"

    def test_set_default(self):
        self.loader.set_default("dk", "dv")
        assert self.loader.get("dk") == "dv"

    def test_set_defaults(self):
        r = self.loader.set_defaults({"a": 1, "b": 2})
        assert r["set"] is True
        assert self.loader.get("a") == 1

    def test_load_dict_override(self):
        self.loader.set("x", 1)
        r = self.loader.load_dict({"x": 2})
        assert r["success"] is True
        assert self.loader.get("x") == 2

    def test_load_dict_keep_existing(self):
        self.loader.set("x", 1)
        self.loader.load_dict(
            {"x": 2, "y": 3},
            strategy="keep_existing",
        )
        assert self.loader.get("x") == 1
        assert self.loader.get("y") == 3

    def test_load_dict_merge_deep(self):
        self.loader.set("nested", {"a": 1, "b": 2})
        self.loader.load_dict(
            {"nested": {"b": 3, "c": 4}},
            strategy="merge_deep",
        )
        nested = self.loader.get("nested")
        assert nested["a"] == 1
        assert nested["b"] == 3
        assert nested["c"] == 4

    def test_load_dict_merge_shallow(self):
        self.loader.set("nested", {"a": 1})
        self.loader.load_dict(
            {"nested": {"b": 2}},
            strategy="merge_shallow",
        )
        nested = self.loader.get("nested")
        assert nested["a"] == 1
        assert nested["b"] == 2

    def test_validator(self):
        self.loader.add_validator(
            "port", lambda v: isinstance(v, int) and v > 0
        )
        r = self.loader.set("port", 8080)
        assert r["set"] is True
        r = self.loader.set("port", -1)
        assert r["set"] is False

    def test_validate_all(self):
        self.loader.add_validator(
            "x", lambda v: v > 0
        )
        self.loader.set("x", 5)
        r = self.loader.validate_all()
        assert r["valid"] is True

    def test_export_config(self):
        self.loader.set("k", "v")
        r = self.loader.export_config()
        assert r["exported"] is True
        assert "k" in r["config"]

    def test_reset(self):
        self.loader.set_default("k", "def")
        self.loader.set("k", "override")
        r = self.loader.reset()
        assert r["reset"] is True
        assert self.loader.get("k") == "def"

    def test_convert_env_bool(self):
        assert self.loader._convert_env("true") is True
        assert self.loader._convert_env("false") is False

    def test_convert_env_int(self):
        assert self.loader._convert_env("42") == 42

    def test_convert_env_float(self):
        assert self.loader._convert_env("3.14") == 3.14

    def test_convert_env_string(self):
        assert self.loader._convert_env("hello") == "hello"

    def test_get_summary(self):
        r = self.loader.get_summary()
        assert r["retrieved"] is True


# ==========================================
# HealthEndpoint Testleri
# ==========================================


class TestHealthEndpoint:
    """HealthEndpoint testleri."""

    def setup_method(self):
        self.health = HealthEndpoint()

    def test_init(self):
        assert self.health.status == "unknown"
        assert self.health.check_count == 0

    def test_register_check(self):
        r = self.health.register_check(
            name="db", check_func=lambda: True
        )
        assert r["registered"] is True
        assert self.health.check_count == 1

    def test_run_check_pass(self):
        self.health.register_check(
            "ok", check_func=lambda: True
        )
        r = self.health.run_check("ok")
        assert r["passed"] is True

    def test_run_check_fail(self):
        self.health.register_check(
            "bad", check_func=lambda: False
        )
        r = self.health.run_check("bad")
        assert r["passed"] is False

    def test_run_check_exception(self):
        def boom():
            raise RuntimeError("fail")

        self.health.register_check("err", check_func=boom)
        r = self.health.run_check("err")
        assert r["passed"] is False

    def test_run_check_not_found(self):
        r = self.health.run_check("x")
        assert r["passed"] is False

    def test_run_all(self):
        self.health.register_check("a", lambda: True)
        self.health.register_check("b", lambda: True)
        r = self.health.run_all()
        assert r["checked"] is True
        assert r["status"] == "healthy"
        assert r["passed"] == 2

    def test_run_all_degraded(self):
        self.health.register_check("a", lambda: True)
        self.health.register_check("b", lambda: False)
        r = self.health.run_all()
        assert r["status"] == "degraded"

    def test_run_all_unhealthy(self):
        self.health.register_check(
            "a", lambda: False, critical=True
        )
        r = self.health.run_all()
        assert r["status"] == "unhealthy"

    def test_liveness(self):
        self.health.register_check(
            "live", lambda: True, check_type="liveness"
        )
        r = self.health.liveness()
        assert r["alive"] is True

    def test_liveness_no_checks(self):
        r = self.health.liveness()
        assert r["alive"] is True

    def test_readiness(self):
        self.health.register_check(
            "ready", lambda: True, check_type="readiness"
        )
        r = self.health.readiness()
        assert r["ready"] is True

    def test_readiness_not_ready(self):
        self.health.register_check(
            "ready", lambda: False, check_type="readiness"
        )
        r = self.health.readiness()
        assert r["ready"] is False

    def test_check_dependencies(self):
        self.health.register_check(
            "dep1", lambda: True, check_type="dependency"
        )
        r = self.health.check_dependencies()
        assert r["checked"] is True
        assert r["all_healthy"] is True

    def test_get_report(self):
        self.health.register_check("a", lambda: True)
        self.health.run_all()
        r = self.health.get_report()
        assert r["retrieved"] is True
        assert "a" in r["checks"]

    def test_consecutive_failures(self):
        self.health.register_check("f", lambda: False)
        self.health.run_check("f")
        self.health.run_check("f")
        assert self.health._checks["f"]["consecutive_failures"] == 2

    def test_get_summary(self):
        r = self.health.get_summary()
        assert r["retrieved"] is True


# ==========================================
# GracefulShutdown Testleri
# ==========================================


class TestGracefulShutdown:
    """GracefulShutdown testleri."""

    def setup_method(self):
        self.gs = GracefulShutdown()

    def test_init(self):
        assert self.gs.phase == "running"
        assert self.gs.is_shutting_down is False

    def test_register_handler(self):
        r = self.gs.register_handler(
            name="h1", handler=lambda: None
        )
        assert r["registered"] is True

    def test_register_resource(self):
        r = self.gs.register_resource(
            name="db", cleanup_func=lambda: None
        )
        assert r["registered"] is True

    def test_add_pending_task(self):
        r = self.gs.add_pending_task("t1", "desc")
        assert r["added"] is True

    def test_complete_task(self):
        self.gs.add_pending_task("t1", "desc")
        r = self.gs.complete_task("t1")
        assert r["completed"] is True

    def test_complete_task_not_found(self):
        r = self.gs.complete_task("x")
        assert r["completed"] is False

    def test_persist_state(self):
        r = self.gs.persist_state("key1", "val1")
        assert r["persisted"] is True

    def test_get_persisted_state(self):
        self.gs.persist_state("k", "v")
        state = self.gs.get_persisted_state()
        assert state["k"] == "v"

    def test_initiate_shutdown(self):
        called = []
        self.gs.register_handler(
            "h1", lambda: called.append("h1"), priority=1
        )
        self.gs.register_resource(
            "r1", lambda: called.append("r1")
        )
        r = self.gs.initiate_shutdown()
        assert r["shutdown"] is True
        assert self.gs.phase == "stopped"
        assert "h1" in called
        assert "r1" in called

    def test_handler_priority_order(self):
        order = []
        self.gs.register_handler(
            "second", lambda: order.append("B"), priority=20
        )
        self.gs.register_handler(
            "first", lambda: order.append("A"), priority=10
        )
        self.gs.initiate_shutdown()
        assert order == ["A", "B"]

    def test_handler_error_tolerance(self):
        def bad():
            raise RuntimeError("fail")

        self.gs.register_handler("bad", bad)
        r = self.gs.initiate_shutdown()
        assert r["shutdown"] is True

    def test_shutdown_log(self):
        self.gs.initiate_shutdown()
        log = self.gs.get_shutdown_log()
        phases = [e["phase"] for e in log]
        assert "draining" in phases
        assert "stopped" in phases

    def test_is_shutting_down(self):
        assert self.gs.is_shutting_down is False
        self.gs.initiate_shutdown()
        assert self.gs.is_shutting_down is True

    def test_get_summary(self):
        r = self.gs.get_summary()
        assert r["retrieved"] is True


# ==========================================
# MVPCoreOrchestrator Testleri
# ==========================================


class TestMVPCoreOrchestrator:
    """MVPCoreOrchestrator testleri."""

    def setup_method(self):
        self.orch = MVPCoreOrchestrator()

    def test_init(self):
        assert self.orch.is_running is False

    def test_startup(self):
        r = self.orch.startup()
        assert r["startup"] is True
        assert r["all_success"] is True
        assert self.orch.is_running is True

    def test_shutdown(self):
        self.orch.startup()
        r = self.orch.shutdown()
        assert r["shutdown"] is True
        assert self.orch.is_running is False

    def test_dispatch_event(self):
        self.orch.startup()
        r = self.orch.dispatch_event("test", {"k": "v"})
        assert r["dispatched"] is True

    def test_submit_task(self):
        self.orch.startup()
        r = self.orch.submit_task(func=lambda: 42)
        assert r["submitted"] is True

    def test_create_session(self):
        self.orch.startup()
        r = self.orch.create_session(user_id="u1")
        assert r["created"] is True

    def test_health_check(self):
        self.orch.startup()
        r = self.orch.health_check()
        assert r["checked"] is True

    def test_get_config(self):
        self.orch.startup()
        v = self.orch.get_config("app_name")
        assert v == "atlas"

    def test_get_config_default(self):
        v = self.orch.get_config("missing", "fallback")
        assert v == "fallback"

    def test_get_analytics(self):
        self.orch.startup()
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert "engine" in r
        assert "event_loop" in r

    def test_get_summary(self):
        r = self.orch.get_summary()
        assert r["retrieved"] is True

    def test_full_lifecycle(self):
        # Startup
        self.orch.startup()
        assert self.orch.is_running is True

        # Create session
        s = self.orch.create_session("u1")
        assert s["created"] is True

        # Dispatch event
        e = self.orch.dispatch_event("user_login", {"uid": "u1"})
        assert e["dispatched"] is True

        # Submit task
        t = self.orch.submit_task(func=lambda: "done")
        assert t["submitted"] is True

        # Health check
        h = self.orch.health_check()
        assert h["checked"] is True

        # Summary
        sm = self.orch.get_summary()
        assert sm["active_sessions"] >= 1

        # Shutdown
        self.orch.shutdown()
        assert self.orch.is_running is False

    def test_custom_params(self):
        orch = MVPCoreOrchestrator(
            app_name="custom",
            ws_port=9999,
            max_concurrent_tasks=5,
            health_check_interval=60,
            shutdown_timeout=10,
        )
        r = orch.startup()
        assert r["startup"] is True
        orch.shutdown()


# ==========================================
# Model Testleri
# ==========================================


class TestMVPCoreModels:
    """Pydantic model testleri."""

    def test_engine_state_enum(self):
        from app.models.mvpcore_models import EngineState
        assert EngineState.RUNNING == "running"
        assert len(EngineState) == 6

    def test_event_priority_enum(self):
        from app.models.mvpcore_models import EventPriority
        assert EventPriority.CRITICAL == "critical"
        assert len(EventPriority) == 5

    def test_session_state_enum(self):
        from app.models.mvpcore_models import SessionState
        assert SessionState.ACTIVE == "active"
        assert len(SessionState) == 5

    def test_connection_state_enum(self):
        from app.models.mvpcore_models import ConnectionState
        assert ConnectionState.CONNECTED == "connected"
        assert len(ConnectionState) == 5

    def test_task_state_enum(self):
        from app.models.mvpcore_models import TaskState
        assert TaskState.COMPLETED == "completed"
        assert len(TaskState) == 7

    def test_health_state_enum(self):
        from app.models.mvpcore_models import HealthState
        assert HealthState.HEALTHY == "healthy"
        assert len(HealthState) == 4

    def test_check_type_enum(self):
        from app.models.mvpcore_models import CheckType
        assert CheckType.LIVENESS == "liveness"
        assert len(CheckType) == 4

    def test_shutdown_phase_enum(self):
        from app.models.mvpcore_models import ShutdownPhase
        assert ShutdownPhase.STOPPED == "stopped"
        assert len(ShutdownPhase) == 6

    def test_merge_strategy_enum(self):
        from app.models.mvpcore_models import MergeStrategy
        assert MergeStrategy.OVERRIDE == "override"
        assert len(MergeStrategy) == 4

    def test_task_priority_enum(self):
        from app.models.mvpcore_models import TaskPriority
        assert TaskPriority.NORMAL == "normal"
        assert len(TaskPriority) == 4

    def test_engine_info_model(self):
        from app.models.mvpcore_models import EngineInfo
        m = EngineInfo(app_name="test")
        assert m.app_name == "test"

    def test_event_info_model(self):
        from app.models.mvpcore_models import EventInfo
        m = EventInfo(event_id="e1", event_type="click")
        assert m.event_type == "click"

    def test_session_info_model(self):
        from app.models.mvpcore_models import SessionInfo
        m = SessionInfo(session_id="s1", user_id="u1")
        assert m.user_id == "u1"

    def test_websocket_info_model(self):
        from app.models.mvpcore_models import WebSocketInfo
        m = WebSocketInfo(port=9090)
        assert m.port == 9090

    def test_task_info_model(self):
        from app.models.mvpcore_models import TaskInfo
        m = TaskInfo(task_id="t1")
        assert m.task_id == "t1"

    def test_health_check_result_model(self):
        from app.models.mvpcore_models import HealthCheckResult
        m = HealthCheckResult(name="db", passed=True)
        assert m.passed is True

    def test_shutdown_info_model(self):
        from app.models.mvpcore_models import ShutdownInfo
        m = ShutdownInfo(handlers_run=3)
        assert m.handlers_run == 3

    def test_config_info_model(self):
        from app.models.mvpcore_models import ConfigInfo
        m = ConfigInfo(config_count=5)
        assert m.config_count == 5

    def test_mvpcore_summary_model(self):
        from app.models.mvpcore_models import MVPCoreSummary
        m = MVPCoreSummary(running=True, ws_connections=3)
        assert m.running is True
        assert m.ws_connections == 3


# ==========================================
# Config Testleri
# ==========================================


class TestMVPCoreConfig:
    """Config testleri."""

    def test_mvpcore_config_defaults(self):
        from app.config import settings
        assert hasattr(settings, "mvpcore_enabled")
        assert settings.mvpcore_enabled is True
        assert settings.websocket_port == 8765
        assert settings.health_check_interval == 30
        assert settings.shutdown_timeout == 30
        assert settings.max_concurrent_tasks == 10
