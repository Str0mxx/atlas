"""ATLAS Stream Processing testleri."""

import unittest

from app.models.streaming import (
    AlertLevel,
    CEPAlert,
    JoinType,
    ProcessingMode,
    SinkType,
    SourceType,
    StreamingSnapshot,
    StreamRecord,
    WindowRecord,
    WindowType,
)
from app.core.streaming.stream_source import (
    StreamSource,
)
from app.core.streaming.stream_processor import (
    StreamProcessor,
)
from app.core.streaming.window_manager import (
    WindowManager,
)
from app.core.streaming.aggregator import (
    StreamAggregator,
)
from app.core.streaming.stream_joiner import (
    StreamJoiner,
)
from app.core.streaming.cep_engine import (
    CEPEngine,
)
from app.core.streaming.stream_sink import (
    StreamSink,
)
from app.core.streaming.realtime_dashboard import (
    RealtimeDashboard,
)
from app.core.streaming.streaming_orchestrator import (
    StreamingOrchestrator,
)


# ── Models ──────────────────────────────────────


class TestModels(unittest.TestCase):
    def test_source_type_values(self):
        assert SourceType.KAFKA == "kafka"
        assert SourceType.WEBSOCKET == "websocket"
        assert SourceType.FILE == "file"
        assert SourceType.GENERATOR == "generator"

    def test_window_type_values(self):
        assert WindowType.TUMBLING == "tumbling"
        assert WindowType.SLIDING == "sliding"
        assert WindowType.SESSION == "session"
        assert WindowType.COUNT == "count"

    def test_join_type_values(self):
        assert JoinType.INNER == "inner"
        assert JoinType.LEFT == "left"
        assert JoinType.OUTER == "outer"
        assert JoinType.TEMPORAL == "temporal"

    def test_sink_type_values(self):
        assert SinkType.DATABASE == "database"
        assert SinkType.KAFKA == "kafka"
        assert SinkType.FILE == "file"

    def test_processing_mode_values(self):
        assert ProcessingMode.EXACTLY_ONCE == "exactly_once"
        assert ProcessingMode.BATCH == "batch"

    def test_alert_level_values(self):
        assert AlertLevel.INFO == "info"
        assert AlertLevel.CRITICAL == "critical"
        assert AlertLevel.EMERGENCY == "emergency"

    def test_stream_record(self):
        r = StreamRecord(name="clicks")
        assert r.name == "clicks"
        assert r.events_processed == 0
        assert len(r.stream_id) == 8

    def test_window_record(self):
        r = WindowRecord(size_seconds=30)
        assert r.size_seconds == 30
        assert r.window_type == WindowType.TUMBLING

    def test_cep_alert(self):
        r = CEPAlert(pattern="spike", level=AlertLevel.CRITICAL)
        assert r.pattern == "spike"
        assert r.level == AlertLevel.CRITICAL

    def test_streaming_snapshot(self):
        s = StreamingSnapshot(active_sources=3, total_events=100)
        assert s.active_sources == 3
        assert s.total_events == 100


# ── StreamSource ────────────────────────────────


class TestStreamSource(unittest.TestCase):
    def test_init(self):
        ss = StreamSource()
        assert ss.source_count == 0
        assert ss.total_received == 0

    def test_register(self):
        ss = StreamSource()
        r = ss.register("clicks", "kafka")
        assert r["name"] == "clicks"
        assert r["status"] == "active"
        assert ss.source_count == 1

    def test_emit(self):
        ss = StreamSource()
        ss.register("s1", "kafka")
        r = ss.emit("s1", {"key": "val"})
        assert r["buffered"] == 1
        assert ss.total_received == 1

    def test_emit_not_found(self):
        ss = StreamSource()
        r = ss.emit("nope", {})
        assert r.get("error") == "source_not_found"

    def test_emit_batch(self):
        ss = StreamSource()
        ss.register("s1", "kafka")
        r = ss.emit_batch("s1", [{"a": 1}, {"a": 2}])
        assert r["emitted"] == 2
        assert ss.total_received == 2

    def test_consume(self):
        ss = StreamSource()
        ss.register("s1", "kafka")
        ss.emit("s1", {"x": 1})
        ss.emit("s1", {"x": 2})
        events = ss.consume("s1", max_events=1)
        assert len(events) == 1
        assert ss.total_buffered == 1

    def test_consume_empty(self):
        ss = StreamSource()
        events = ss.consume("nope")
        assert events == []

    def test_register_generator(self):
        ss = StreamSource()
        ss.register_generator("gen", lambda: {"val": 42})
        events = ss.generate("gen", count=3)
        assert len(events) == 3
        assert ss.total_received == 3

    def test_generate_not_found(self):
        ss = StreamSource()
        assert ss.generate("nope") == []

    def test_pause_resume(self):
        ss = StreamSource()
        ss.register("s1", "kafka")
        assert ss.pause("s1") is True
        assert ss.active_count == 0
        assert ss.resume("s1") is True
        assert ss.active_count == 1

    def test_pause_not_found(self):
        ss = StreamSource()
        assert ss.pause("nope") is False
        assert ss.resume("nope") is False

    def test_remove(self):
        ss = StreamSource()
        ss.register("s1", "kafka")
        assert ss.remove("s1") is True
        assert ss.source_count == 0

    def test_remove_not_found(self):
        ss = StreamSource()
        assert ss.remove("nope") is False

    def test_get_source(self):
        ss = StreamSource()
        ss.register("s1", "api")
        src = ss.get_source("s1")
        assert src is not None
        assert src["type"] == "api"

    def test_get_stats(self):
        ss = StreamSource()
        ss.register("s1", "kafka")
        ss.emit("s1", {"a": 1})
        stats = ss.get_stats("s1")
        assert stats["received"] == 1


# ── StreamProcessor ─────────────────────────────


class TestStreamProcessor(unittest.TestCase):
    def test_init(self):
        sp = StreamProcessor()
        assert sp.chain_count == 0
        assert sp.processed_count == 0

    def test_add_map(self):
        sp = StreamProcessor()
        sp.add_map("c1", "upper", lambda e: {**e, "name": e.get("name", "").upper()})
        assert sp.chain_count == 1
        assert sp.step_count == 1

    def test_add_filter(self):
        sp = StreamProcessor()
        sp.add_filter("c1", "positive", lambda e: e.get("val", 0) > 0)
        assert sp.step_count == 1

    def test_add_reduce(self):
        sp = StreamProcessor()
        sp.add_reduce("c1", "sum", lambda acc, e: (acc or 0) + e.get("val", 0))
        assert sp.step_count == 1

    def test_process_map(self):
        sp = StreamProcessor()
        sp.add_map("c1", "double", lambda e: {**e, "val": e.get("val", 0) * 2})
        r = sp.process("c1", {"val": 5})
        assert r["val"] == 10
        assert sp.processed_count == 1

    def test_process_filter_pass(self):
        sp = StreamProcessor()
        sp.add_filter("c1", "pos", lambda e: e.get("val", 0) > 0)
        r = sp.process("c1", {"val": 5})
        assert r is not None

    def test_process_filter_reject(self):
        sp = StreamProcessor()
        sp.add_filter("c1", "pos", lambda e: e.get("val", 0) > 0)
        r = sp.process("c1", {"val": -1})
        assert r is None

    def test_process_reduce(self):
        sp = StreamProcessor()
        sp.add_reduce("c1", "sum", lambda acc, e: (acc or 0) + e.get("val", 0))
        sp.process("c1", {"val": 10})
        sp.process("c1", {"val": 20})
        state = sp.get_state("reduce_c1_sum")
        assert state == 30

    def test_process_chain(self):
        sp = StreamProcessor()
        sp.add_filter("c1", "pos", lambda e: e.get("val", 0) > 0)
        sp.add_map("c1", "double", lambda e: {**e, "val": e["val"] * 2})
        r = sp.process("c1", {"val": 5})
        assert r["val"] == 10

    def test_process_batch(self):
        sp = StreamProcessor()
        sp.add_map("c1", "id", lambda e: e)
        results = sp.process_batch("c1", [{"a": 1}, {"a": 2}])
        assert len(results) == 2

    def test_process_error(self):
        sp = StreamProcessor()
        sp.add_map("c1", "bad", lambda e: 1 / 0)
        r = sp.process("c1", {"val": 1})
        assert r is None
        assert sp.error_count == 1

    def test_error_handler(self):
        errors = []
        sp = StreamProcessor()
        sp.add_map("c1", "bad", lambda e: 1 / 0)
        sp.set_error_handler("c1", lambda e, ex: errors.append(str(ex)))
        sp.process("c1", {"val": 1})
        assert len(errors) == 1

    def test_set_get_state(self):
        sp = StreamProcessor()
        sp.set_state("key", 42)
        assert sp.get_state("key") == 42

    def test_get_chain(self):
        sp = StreamProcessor()
        sp.add_map("c1", "step1", lambda e: e)
        chain = sp.get_chain("c1")
        assert len(chain) == 1
        assert chain[0]["name"] == "step1"

    def test_remove_chain(self):
        sp = StreamProcessor()
        sp.add_map("c1", "s", lambda e: e)
        assert sp.remove_chain("c1") is True
        assert sp.chain_count == 0

    def test_remove_chain_not_found(self):
        sp = StreamProcessor()
        assert sp.remove_chain("nope") is False

    def test_get_stats(self):
        sp = StreamProcessor()
        stats = sp.get_stats()
        assert "processed" in stats


# ── WindowManager ───────────────────────────────


class TestWindowManager(unittest.TestCase):
    def test_init(self):
        wm = WindowManager()
        assert wm.window_count == 0
        assert wm.default_size == 60

    def test_create_tumbling(self):
        wm = WindowManager()
        r = wm.create_tumbling("w1", size=30)
        assert r["type"] == "tumbling"
        assert r["size"] == 30
        assert wm.window_count == 1

    def test_create_sliding(self):
        wm = WindowManager()
        r = wm.create_sliding("w1", size=60, slide=10)
        assert r["type"] == "sliding"

    def test_create_session(self):
        wm = WindowManager()
        r = wm.create_session("w1", gap=30)
        assert r["type"] == "session"
        assert r["gap"] == 30

    def test_create_count(self):
        wm = WindowManager()
        r = wm.create_count("w1", max_count=50)
        assert r["type"] == "count"
        assert r["max_count"] == 50

    def test_add_event(self):
        wm = WindowManager()
        wm.create_tumbling("w1", size=3600)
        r = wm.add_event("w1", {"val": 1})
        assert r["status"] == "added"
        assert r["count"] == 1
        assert wm.total_events == 1

    def test_add_event_not_found(self):
        wm = WindowManager()
        r = wm.add_event("nope", {})
        assert r.get("error") == "window_not_found"

    def test_add_event_count_window_full(self):
        wm = WindowManager()
        wm.create_count("w1", max_count=2)
        wm.add_event("w1", {"val": 1})
        r = wm.add_event("w1", {"val": 2})
        assert r["window_full"] is True

    def test_get_events(self):
        wm = WindowManager()
        wm.create_tumbling("w1", size=3600)
        wm.add_event("w1", {"val": 1})
        wm.add_event("w1", {"val": 2})
        events = wm.get_events("w1")
        assert len(events) == 2

    def test_get_events_not_found(self):
        wm = WindowManager()
        assert wm.get_events("nope") == []

    def test_close_window(self):
        wm = WindowManager()
        wm.create_tumbling("w1")
        wm.add_event("w1", {"val": 1})
        r = wm.close_window("w1")
        assert r["status"] == "closed"
        assert r["events"] == 1
        assert wm.window_count == 0
        assert wm.closed_count == 1

    def test_close_window_not_found(self):
        wm = WindowManager()
        r = wm.close_window("nope")
        assert r.get("error") == "window_not_found"

    def test_check_expired_count(self):
        wm = WindowManager()
        wm.create_count("w1", max_count=1)
        wm.add_event("w1", {"val": 1})
        expired = wm.check_expired()
        assert "w1" in expired

    def test_get_window(self):
        wm = WindowManager()
        wm.create_tumbling("w1")
        w = wm.get_window("w1")
        assert w is not None
        assert w["type"] == "tumbling"

    def test_get_closed(self):
        wm = WindowManager()
        wm.create_tumbling("w1")
        wm.close_window("w1")
        closed = wm.get_closed()
        assert len(closed) == 1


# ── StreamAggregator ────────────────────────────


class TestStreamAggregator(unittest.TestCase):
    def test_init(self):
        sa = StreamAggregator()
        assert sa.aggregation_count == 0

    def test_create_sum(self):
        sa = StreamAggregator()
        r = sa.create("total", "sum")
        assert r["type"] == "sum"
        assert sa.aggregation_count == 1

    def test_update_sum(self):
        sa = StreamAggregator()
        sa.create("total", "sum")
        sa.update("total", 10)
        sa.update("total", 20)
        assert sa.get_value("total") == 30

    def test_update_avg(self):
        sa = StreamAggregator()
        sa.create("avg", "avg")
        sa.update("avg", 10)
        sa.update("avg", 20)
        assert sa.get_value("avg") == 15.0

    def test_update_min(self):
        sa = StreamAggregator()
        sa.create("mn", "min")
        sa.update("mn", 10)
        sa.update("mn", 5)
        sa.update("mn", 20)
        assert sa.get_value("mn") == 5

    def test_update_max(self):
        sa = StreamAggregator()
        sa.create("mx", "max")
        sa.update("mx", 10)
        sa.update("mx", 30)
        assert sa.get_value("mx") == 30

    def test_update_count(self):
        sa = StreamAggregator()
        sa.create("cnt", "count")
        sa.update("cnt", 1)
        sa.update("cnt", 1)
        sa.update("cnt", 1)
        assert sa.get_value("cnt") == 3

    def test_update_not_found(self):
        sa = StreamAggregator()
        r = sa.update("nope", 1)
        assert r.get("error") == "not_found"

    def test_update_batch(self):
        sa = StreamAggregator()
        sa.create("total", "sum")
        sa.update_batch("total", [10, 20, 30])
        assert sa.get_value("total") == 60

    def test_get_value_not_found(self):
        sa = StreamAggregator()
        assert sa.get_value("nope") is None

    def test_get_summary(self):
        sa = StreamAggregator()
        sa.create("s", "sum")
        sa.update("s", 10)
        sa.update("s", 20)
        summary = sa.get_summary("s")
        assert summary["sum"] == 30
        assert summary["min"] == 10
        assert summary["max"] == 20
        assert summary["count"] == 2

    def test_get_summary_not_found(self):
        sa = StreamAggregator()
        assert sa.get_summary("nope") is None

    def test_percentile(self):
        sa = StreamAggregator()
        sa.create("p", "sum")
        for v in [10, 20, 30, 40, 50]:
            sa.update("p", v)
        p50 = sa.percentile("p", 50)
        assert p50 is not None
        assert p50 == 30.0

    def test_percentile_not_found(self):
        sa = StreamAggregator()
        assert sa.percentile("nope", 50) is None

    def test_count_distinct(self):
        sa = StreamAggregator()
        sa.count_distinct("users", "alice")
        sa.count_distinct("users", "bob")
        sa.count_distinct("users", "alice")
        assert sa.get_distinct_count("users") == 2
        assert sa.distinct_count == 1

    def test_custom_aggregation(self):
        sa = StreamAggregator()
        sa.register_custom("variance", lambda vals: sum((v - sum(vals)/len(vals))**2 for v in vals) / len(vals) if vals else 0)
        sa.update("variance", 10)
        sa.update("variance", 20)
        sa.update("variance", 30)
        result = sa.apply_custom("variance")
        assert result is not None
        assert sa.custom_count == 1

    def test_apply_custom_not_found(self):
        sa = StreamAggregator()
        assert sa.apply_custom("nope") is None

    def test_reset(self):
        sa = StreamAggregator()
        sa.create("s", "sum")
        sa.update("s", 100)
        assert sa.reset("s") is True
        assert sa.get_value("s") == 0.0

    def test_reset_not_found(self):
        sa = StreamAggregator()
        assert sa.reset("nope") is False


# ── StreamJoiner ────────────────────────────────


class TestStreamJoiner(unittest.TestCase):
    def test_init(self):
        sj = StreamJoiner()
        assert sj.stream_count == 0

    def test_register_stream(self):
        sj = StreamJoiner()
        r = sj.register_stream("orders")
        assert r["status"] == "registered"
        assert sj.stream_count == 1

    def test_add_event(self):
        sj = StreamJoiner()
        sj.register_stream("s1")
        r = sj.add_event("s1", {"id": 1, "val": "a"})
        assert r["buffered"] == 1

    def test_add_event_not_found(self):
        sj = StreamJoiner()
        r = sj.add_event("nope", {})
        assert r.get("error") == "stream_not_found"

    def test_inner_join(self):
        sj = StreamJoiner()
        sj.register_stream("left")
        sj.register_stream("right")
        sj.add_event("left", {"id": 1, "name": "a"})
        sj.add_event("left", {"id": 2, "name": "b"})
        sj.add_event("right", {"id": 1, "price": 10})
        sj.add_event("right", {"id": 3, "price": 30})
        results = sj.inner_join("left", "right", "id")
        assert len(results) == 1
        assert results[0]["join_key"] == 1

    def test_left_join(self):
        sj = StreamJoiner()
        sj.register_stream("left")
        sj.register_stream("right")
        sj.add_event("left", {"id": 1, "name": "a"})
        sj.add_event("left", {"id": 2, "name": "b"})
        sj.add_event("right", {"id": 1, "price": 10})
        results = sj.left_join("left", "right", "id")
        assert len(results) == 2

    def test_outer_join(self):
        sj = StreamJoiner()
        sj.register_stream("left")
        sj.register_stream("right")
        sj.add_event("left", {"id": 1, "name": "a"})
        sj.add_event("right", {"id": 2, "price": 20})
        results = sj.outer_join("left", "right", "id")
        assert len(results) == 2

    def test_temporal_join(self):
        sj = StreamJoiner()
        sj.register_stream("left")
        sj.register_stream("right")
        sj.add_event("left", {"id": 1, "timestamp": 100.0})
        sj.add_event("right", {"id": 1, "timestamp": 105.0})
        sj.add_event("right", {"id": 1, "timestamp": 200.0})
        results = sj.temporal_join("left", "right", "id", window_seconds=10)
        assert len(results) == 1

    def test_enrichment(self):
        sj = StreamJoiner()
        sj.register_stream("orders")
        sj.set_enrichment_table("products", {
            "p1": {"name": "Widget", "category": "tools"},
            "p2": {"name": "Gadget", "category": "tech"},
        })
        sj.add_event("orders", {"product_id": "p1", "qty": 5})
        sj.add_event("orders", {"product_id": "p3", "qty": 1})
        results = sj.enrich("orders", "products", "product_id")
        assert len(results) == 2
        assert results[0]["enriched"] is True
        assert results[1]["enriched"] is False

    def test_enrichment_table_count(self):
        sj = StreamJoiner()
        sj.set_enrichment_table("t1", {})
        assert sj.enrichment_table_count == 1

    def test_clear_buffer(self):
        sj = StreamJoiner()
        sj.register_stream("s1")
        sj.add_event("s1", {"a": 1})
        sj.add_event("s1", {"a": 2})
        cleared = sj.clear_buffer("s1")
        assert cleared == 2
        assert sj.total_buffered == 0

    def test_get_results(self):
        sj = StreamJoiner()
        sj.register_stream("l")
        sj.register_stream("r")
        sj.add_event("l", {"id": 1})
        sj.add_event("r", {"id": 1})
        sj.inner_join("l", "r", "id")
        assert sj.result_count >= 1


# ── CEPEngine ───────────────────────────────────


class TestCEPEngine(unittest.TestCase):
    def test_init(self):
        cep = CEPEngine()
        assert cep.pattern_count == 0
        assert cep.alert_count == 0

    def test_add_pattern(self):
        cep = CEPEngine()
        r = cep.add_pattern("spike", lambda e: e.get("val", 0) > 100)
        assert r["name"] == "spike"
        assert cep.pattern_count == 1

    def test_pattern_match(self):
        cep = CEPEngine()
        cep.add_pattern("spike", lambda e: e.get("val", 0) > 100)
        r = cep.process_event({"val": 200})
        assert "spike" in r["matches"]
        assert cep.alert_count == 1

    def test_pattern_no_match(self):
        cep = CEPEngine()
        cep.add_pattern("spike", lambda e: e.get("val", 0) > 100)
        r = cep.process_event({"val": 50})
        assert len(r["matches"]) == 0

    def test_add_sequence(self):
        cep = CEPEngine()
        r = cep.add_sequence("login_fail", [
            lambda e: e.get("type") == "login_fail",
            lambda e: e.get("type") == "login_fail",
            lambda e: e.get("type") == "login_fail",
        ])
        assert r["steps"] == 3
        assert cep.sequence_count == 1

    def test_sequence_detection(self):
        cep = CEPEngine()
        cep.add_sequence("brute", [
            lambda e: e.get("type") == "fail",
            lambda e: e.get("type") == "fail",
        ])
        cep.process_event({"type": "fail"})
        r = cep.process_event({"type": "fail"})
        assert any("seq:brute" in m for m in r["matches"])

    def test_add_correlation(self):
        cep = CEPEngine()
        r = cep.add_correlation(
            "multi_error", ["error", "timeout"],
            key_field="service", min_count=2,
        )
        assert r["types"] == 2
        assert cep.correlation_count == 1

    def test_correlation_match(self):
        cep = CEPEngine()
        cep.add_correlation(
            "alert", ["error"], key_field="svc",
            min_count=2, window_seconds=60,
        )
        cep.process_event({"type": "error", "svc": "api"})
        r = cep.process_event({"type": "error", "svc": "api"})
        assert any("corr:" in m for m in r["matches"])

    def test_get_alerts(self):
        cep = CEPEngine()
        cep.add_pattern("hi", lambda e: True)
        cep.process_event({"val": 1})
        alerts = cep.get_alerts()
        assert len(alerts) >= 1

    def test_get_alerts_filtered(self):
        cep = CEPEngine()
        cep.add_pattern("hi", lambda e: True, alert_level="critical")
        cep.process_event({})
        assert len(cep.get_alerts(level="critical")) >= 1
        assert len(cep.get_alerts(level="info")) == 0

    def test_reset_sequence(self):
        cep = CEPEngine()
        cep.add_sequence("seq", [lambda e: True, lambda e: True])
        cep.process_event({})
        assert cep.reset_sequence("seq") is True

    def test_reset_sequence_not_found(self):
        cep = CEPEngine()
        assert cep.reset_sequence("nope") is False

    def test_get_pattern(self):
        cep = CEPEngine()
        cep.add_pattern("p1", lambda e: False)
        p = cep.get_pattern("p1")
        assert p is not None
        assert p["match_count"] == 0

    def test_get_pattern_not_found(self):
        cep = CEPEngine()
        assert cep.get_pattern("nope") is None

    def test_get_stats(self):
        cep = CEPEngine()
        cep.process_event({})
        stats = cep.get_stats()
        assert stats["events_processed"] == 1

    def test_event_count(self):
        cep = CEPEngine()
        cep.process_event({})
        cep.process_event({})
        assert cep.event_count == 2


# ── StreamSink ──────────────────────────────────


class TestStreamSink(unittest.TestCase):
    def test_init(self):
        ss = StreamSink()
        assert ss.sink_count == 0

    def test_register(self):
        ss = StreamSink()
        r = ss.register("db", "database")
        assert r["status"] == "active"
        assert ss.sink_count == 1

    def test_write(self):
        ss = StreamSink()
        ss.register("db", "database")
        r = ss.write("db", {"val": 1})
        assert r["buffered"] >= 1
        assert ss.total_written == 1

    def test_write_not_found(self):
        ss = StreamSink()
        r = ss.write("nope", {})
        assert r.get("error") == "sink_not_found"

    def test_write_inactive(self):
        ss = StreamSink()
        ss.register("db", "database")
        ss.pause("db")
        r = ss.write("db", {})
        assert r.get("error") == "sink_inactive"

    def test_write_batch(self):
        ss = StreamSink()
        ss.register("db", "database")
        r = ss.write_batch("db", [{"a": 1}, {"a": 2}])
        assert r["written"] == 2

    def test_flush(self):
        ss = StreamSink()
        ss.register("db", "database", batch_size=1000)
        ss.write("db", {"a": 1})
        ss.write("db", {"a": 2})
        r = ss.flush("db")
        assert r["flushed"] == 2
        assert ss.total_buffered == 0

    def test_flush_empty(self):
        ss = StreamSink()
        ss.register("db", "database")
        r = ss.flush("db")
        assert r["flushed"] == 0

    def test_flush_all(self):
        ss = StreamSink()
        ss.register("db1", "database", batch_size=1000)
        ss.register("db2", "file", batch_size=1000)
        ss.write("db1", {"a": 1})
        ss.write("db2", {"a": 2})
        result = ss.flush_all()
        assert result["db1"] == 1
        assert result["db2"] == 1

    def test_auto_flush(self):
        ss = StreamSink()
        ss.register("db", "database", batch_size=2)
        ss.write("db", {"a": 1})
        ss.write("db", {"a": 2})
        assert ss.total_buffered == 0

    def test_set_writer(self):
        written = []
        ss = StreamSink()
        ss.register("db", "database", batch_size=1000)
        ss.set_writer("db", lambda events: written.extend(events))
        ss.write("db", {"a": 1})
        ss.flush("db")
        assert len(written) == 1

    def test_set_writer_not_found(self):
        ss = StreamSink()
        assert ss.set_writer("nope", lambda e: None) is False

    def test_broadcast(self):
        ss = StreamSink()
        ss.register("db1", "database", batch_size=1000)
        ss.register("db2", "file", batch_size=1000)
        r = ss.broadcast({"val": 1})
        assert r["written"] == 2

    def test_broadcast_selective(self):
        ss = StreamSink()
        ss.register("db1", "database", batch_size=1000)
        ss.register("db2", "file", batch_size=1000)
        r = ss.broadcast({"val": 1}, sinks=["db1"])
        assert r["written"] == 1

    def test_pause_resume(self):
        ss = StreamSink()
        ss.register("db", "database")
        assert ss.pause("db") is True
        assert ss.active_count == 0
        assert ss.resume("db") is True
        assert ss.active_count == 1

    def test_remove(self):
        ss = StreamSink()
        ss.register("db", "database")
        assert ss.remove("db") is True
        assert ss.sink_count == 0

    def test_remove_not_found(self):
        ss = StreamSink()
        assert ss.remove("nope") is False

    def test_get_sink(self):
        ss = StreamSink()
        ss.register("db", "database")
        s = ss.get_sink("db")
        assert s is not None
        assert s["type"] == "database"

    def test_get_stats(self):
        ss = StreamSink()
        ss.register("db", "database")
        stats = ss.get_stats("db")
        assert stats["written"] == 0


# ── RealtimeDashboard ──────────────────────────


class TestRealtimeDashboard(unittest.TestCase):
    def test_init(self):
        rd = RealtimeDashboard()
        assert rd.dashboard_count == 0

    def test_create_dashboard(self):
        rd = RealtimeDashboard()
        r = rd.create_dashboard("main", "Main Dashboard")
        assert r["name"] == "main"
        assert rd.dashboard_count == 1

    def test_add_widget(self):
        rd = RealtimeDashboard()
        rd.create_dashboard("main")
        r = rd.add_widget("main", "chart", "Sales", "sales_data")
        assert r["type"] == "chart"
        assert rd.widget_count == 1

    def test_add_widget_not_found(self):
        rd = RealtimeDashboard()
        r = rd.add_widget("nope", "chart", "X")
        assert r.get("error") == "dashboard_not_found"

    def test_update_metric(self):
        rd = RealtimeDashboard()
        r = rd.update_metric("cpu", 75.5)
        assert r["value"] == 75.5
        assert rd.metric_count == 1

    def test_update_metric_history(self):
        rd = RealtimeDashboard()
        rd.update_metric("cpu", 70)
        rd.update_metric("cpu", 80)
        history = rd.get_metric_history("cpu")
        assert len(history) == 2

    def test_push_data(self):
        rd = RealtimeDashboard()
        rd.create_dashboard("main")
        rd.add_widget("main", "chart", "Sales")
        r = rd.push_data("main", 0, {"value": 100})
        assert r["data_points"] == 1

    def test_push_data_not_found(self):
        rd = RealtimeDashboard()
        rd.create_dashboard("main")
        r = rd.push_data("main", 99, {})
        assert r.get("error") == "widget_not_found"

    def test_add_alert(self):
        rd = RealtimeDashboard()
        r = rd.add_alert("CPU High", "CPU > 90%", "critical")
        assert r["level"] == "critical"
        assert rd.alert_display_count == 1

    def test_acknowledge_alert(self):
        rd = RealtimeDashboard()
        rd.add_alert("Test", "msg")
        assert rd.acknowledge_alert(0) is True
        unacked = rd.get_alerts(unacknowledged_only=True)
        assert len(unacked) == 0

    def test_acknowledge_alert_invalid(self):
        rd = RealtimeDashboard()
        assert rd.acknowledge_alert(99) is False

    def test_get_alerts(self):
        rd = RealtimeDashboard()
        rd.add_alert("A1", "m1")
        rd.add_alert("A2", "m2")
        assert len(rd.get_alerts()) == 2

    def test_get_metric(self):
        rd = RealtimeDashboard()
        rd.update_metric("mem", 60)
        m = rd.get_metric("mem")
        assert m is not None
        assert m["current"] == 60

    def test_get_metric_not_found(self):
        rd = RealtimeDashboard()
        assert rd.get_metric("nope") is None

    def test_get_metric_history_not_found(self):
        rd = RealtimeDashboard()
        assert rd.get_metric_history("nope") == []

    def test_share_dashboard(self):
        rd = RealtimeDashboard()
        rd.create_dashboard("main")
        r = rd.share_dashboard("main", "user1", "edit")
        assert r["permission"] == "edit"
        assert rd.share_count == 1

    def test_share_not_found(self):
        rd = RealtimeDashboard()
        r = rd.share_dashboard("nope", "user1")
        assert r.get("error") == "dashboard_not_found"

    def test_get_dashboard(self):
        rd = RealtimeDashboard()
        rd.create_dashboard("main")
        rd.add_widget("main", "chart", "W1")
        d = rd.get_dashboard("main")
        assert d is not None
        assert d["widgets"] == 1

    def test_get_dashboard_not_found(self):
        rd = RealtimeDashboard()
        assert rd.get_dashboard("nope") is None

    def test_delete_dashboard(self):
        rd = RealtimeDashboard()
        rd.create_dashboard("main")
        assert rd.delete_dashboard("main") is True
        assert rd.dashboard_count == 0

    def test_delete_dashboard_not_found(self):
        rd = RealtimeDashboard()
        assert rd.delete_dashboard("nope") is False


# ── StreamingOrchestrator ───────────────────────


class TestStreamingOrchestrator(unittest.TestCase):
    def test_init(self):
        so = StreamingOrchestrator()
        assert so.is_initialized is False
        assert so.topology_count == 0

    def test_initialize(self):
        so = StreamingOrchestrator()
        r = so.initialize()
        assert r["status"] == "initialized"
        assert so.is_initialized is True

    def test_create_topology(self):
        so = StreamingOrchestrator()
        so.source.register("src", "kafka")
        so.processor.add_map("chain", "id", lambda e: e)
        so.sink.register("out", "database", batch_size=1000)
        r = so.create_topology("t1", "src", "chain", "out")
        assert r["status"] == "active"
        assert so.topology_count == 1

    def test_process_event(self):
        so = StreamingOrchestrator()
        so.source.register("src", "kafka")
        so.processor.add_map("chain", "id", lambda e: e)
        so.sink.register("out", "database", batch_size=1000)
        so.create_topology("t1", "src", "chain", "out")
        r = so.process_event("t1", {"val": 42})
        assert r["status"] == "processed"

    def test_process_event_not_found(self):
        so = StreamingOrchestrator()
        r = so.process_event("nope", {})
        assert r.get("error") == "topology_not_found"

    def test_process_event_filtered(self):
        so = StreamingOrchestrator()
        so.source.register("src", "kafka")
        so.processor.add_filter("chain", "reject", lambda e: False)
        so.sink.register("out", "database", batch_size=1000)
        so.create_topology("t1", "src", "chain", "out")
        r = so.process_event("t1", {"val": 1})
        assert r["status"] == "filtered"

    def test_process_batch(self):
        so = StreamingOrchestrator()
        so.source.register("src", "kafka")
        so.processor.add_map("chain", "id", lambda e: e)
        so.sink.register("out", "database", batch_size=1000)
        so.create_topology("t1", "src", "chain", "out")
        r = so.process_batch("t1", [{"v": 1}, {"v": 2}])
        assert r["processed"] == 2

    def test_checkpoint(self):
        so = StreamingOrchestrator()
        r = so.checkpoint()
        assert r["status"] == "saved"
        assert so.checkpoint_count == 1

    def test_recover(self):
        so = StreamingOrchestrator()
        so.processor.set_state("key", "value")
        so.checkpoint()
        so.processor.set_state("key", "changed")
        r = so.recover()
        assert r["status"] == "recovered"
        assert so.processor.get_state("key") == "value"

    def test_recover_no_checkpoints(self):
        so = StreamingOrchestrator()
        r = so.recover()
        assert r.get("error") == "no_checkpoints"

    def test_get_topology(self):
        so = StreamingOrchestrator()
        so.source.register("src", "kafka")
        so.processor.add_map("c", "id", lambda e: e)
        so.sink.register("out", "file", batch_size=1000)
        so.create_topology("t1", "src", "c", "out")
        t = so.get_topology("t1")
        assert t is not None
        assert t["name"] == "t1"

    def test_stop_topology(self):
        so = StreamingOrchestrator()
        so.source.register("src", "kafka")
        so.processor.add_map("c", "id", lambda e: e)
        so.sink.register("out", "file", batch_size=1000)
        so.create_topology("t1", "src", "c", "out")
        assert so.stop_topology("t1") is True
        assert so.get_topology("t1")["status"] == "stopped"

    def test_stop_topology_not_found(self):
        so = StreamingOrchestrator()
        assert so.stop_topology("nope") is False

    def test_get_snapshot(self):
        so = StreamingOrchestrator()
        snap = so.get_snapshot()
        assert "sources" in snap
        assert "sinks" in snap
        assert "topologies" in snap
        assert "initialized" in snap

    def test_get_analytics(self):
        so = StreamingOrchestrator()
        a = so.get_analytics()
        assert "sources" in a
        assert "processing" in a
        assert "windows" in a
        assert "cep" in a
        assert "sinks" in a
        assert "dashboards" in a

    def test_full_workflow(self):
        so = StreamingOrchestrator()
        so.initialize()
        so.source.register("src", "kafka")
        so.processor.add_map("pipe", "enrich", lambda e: {**e, "processed": True})
        so.sink.register("out", "database", batch_size=1000)
        so.create_topology("flow", "src", "pipe", "out")
        so.process_event("flow", {"key": "val"})
        so.checkpoint()
        snap = so.get_snapshot()
        assert snap["topologies"] == 1
        assert snap["checkpoints"] == 1


# ── Config ──────────────────────────────────────


class TestConfigSettings(unittest.TestCase):
    def test_streaming_settings(self):
        from app.config import Settings
        s = Settings()
        assert hasattr(s, "streaming_enabled")
        assert hasattr(s, "default_window_size")
        assert hasattr(s, "checkpoint_interval")
        assert hasattr(s, "max_lateness")
        assert hasattr(s, "parallelism")

    def test_streaming_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.streaming_enabled is True
        assert s.default_window_size == 60
        assert s.checkpoint_interval == 300
        assert s.max_lateness == 10
        assert s.parallelism == 4


if __name__ == "__main__":
    unittest.main()
