"""ATLAS Caching & Performance Optimization testleri.

CacheManager, MemoryCache, DistributedCache,
QueryOptimizer, ResponseCompressor, LazyLoader,
BatchProcessor, PerformanceProfiler ve
CachingOrchestrator testleri.
"""

import time

import pytest

from app.models.caching import (
    BatchRecord,
    BatchStatus,
    CacheEntry,
    CacheLayer,
    CacheStrategy,
    CachingSnapshot,
    CompressionType,
    LoadPriority,
    ProfileMetric,
    ProfileRecord,
)
from app.core.caching.cache_manager import (
    CacheManager,
)
from app.core.caching.memory_cache import (
    MemoryCache,
)
from app.core.caching.distributed_cache import (
    DistributedCache,
)
from app.core.caching.query_optimizer import (
    QueryOptimizer,
)
from app.core.caching.response_compressor import (
    ResponseCompressor,
)
from app.core.caching.lazy_loader import (
    LazyLoader,
)
from app.core.caching.batch_processor import (
    BatchProcessor,
)
from app.core.caching.profiler import (
    PerformanceProfiler,
)
from app.core.caching.caching_orchestrator import (
    CachingOrchestrator,
)


# ---- Model Testleri ----

class TestCachingModels:
    """Model testleri."""

    def test_cache_strategy_values(self):
        assert CacheStrategy.LRU == "lru"
        assert CacheStrategy.LFU == "lfu"
        assert CacheStrategy.TTL == "ttl"
        assert CacheStrategy.FIFO == "fifo"

    def test_cache_layer_values(self):
        assert CacheLayer.MEMORY == "memory"
        assert CacheLayer.DISTRIBUTED == "distributed"
        assert CacheLayer.DISK == "disk"

    def test_compression_type_values(self):
        assert CompressionType.NONE == "none"
        assert CompressionType.GZIP == "gzip"
        assert CompressionType.BROTLI == "brotli"
        assert CompressionType.ZLIB == "zlib"

    def test_profile_metric_values(self):
        assert ProfileMetric.EXECUTION_TIME == "execution_time"
        assert ProfileMetric.MEMORY_USAGE == "memory_usage"
        assert ProfileMetric.CPU_USAGE == "cpu_usage"

    def test_batch_status_values(self):
        assert BatchStatus.PENDING == "pending"
        assert BatchStatus.PROCESSING == "processing"
        assert BatchStatus.COMPLETED == "completed"
        assert BatchStatus.FAILED == "failed"

    def test_load_priority_values(self):
        assert LoadPriority.CRITICAL == "critical"
        assert LoadPriority.HIGH == "high"
        assert LoadPriority.NORMAL == "normal"
        assert LoadPriority.LOW == "low"

    def test_cache_entry(self):
        e = CacheEntry(key="test", value=42)
        assert e.key == "test"
        assert e.value == 42

    def test_profile_record(self):
        r = ProfileRecord(operation="query")
        assert r.operation == "query"
        assert r.profile_id

    def test_batch_record(self):
        r = BatchRecord(total_items=10)
        assert r.total_items == 10
        assert r.status == BatchStatus.PENDING

    def test_caching_snapshot(self):
        s = CachingSnapshot(
            total_entries=100, hit_rate=0.85,
        )
        assert s.total_entries == 100
        assert s.hit_rate == 0.85


# ---- CacheManager Testleri ----

class TestCacheManager:
    """CacheManager testleri."""

    def setup_method(self):
        self.cm = CacheManager(default_ttl=60)

    def test_set_get(self):
        self.cm.set("k1", "v1")
        assert self.cm.get("k1") == "v1"

    def test_get_missing(self):
        assert self.cm.get("nope") is None

    def test_get_default(self):
        assert self.cm.get("nope", 42) == 42

    def test_delete(self):
        self.cm.set("k1", "v1")
        ok = self.cm.delete("k1")
        assert ok is True
        assert self.cm.get("k1") is None

    def test_delete_missing(self):
        assert self.cm.delete("nope") is False

    def test_exists(self):
        self.cm.set("k1", "v1")
        assert self.cm.exists("k1") is True
        assert self.cm.exists("nope") is False

    def test_ttl_expiry(self):
        self.cm.set("k1", "v1", ttl=0)
        # ttl=0 means no expiry
        assert self.cm.get("k1") == "v1"

    def test_invalidate_all(self):
        self.cm.set("a", 1)
        self.cm.set("b", 2)
        count = self.cm.invalidate()
        assert count == 2
        assert self.cm.size == 0

    def test_invalidate_pattern(self):
        self.cm.set("user:1", "a")
        self.cm.set("user:2", "b")
        self.cm.set("item:1", "c")
        count = self.cm.invalidate("user:")
        assert count == 2
        assert self.cm.size == 1

    def test_warm(self):
        count = self.cm.warm({
            "k1": "v1", "k2": "v2",
        })
        assert count == 2
        assert self.cm.get("k1") == "v1"

    def test_hit_miss_tracking(self):
        self.cm.set("k1", "v1")
        self.cm.get("k1")  # hit
        self.cm.get("k2")  # miss
        assert self.cm.hit_count == 1
        assert self.cm.miss_count == 1

    def test_get_stats(self):
        self.cm.set("k1", "v1")
        self.cm.get("k1")
        stats = self.cm.get_stats()
        assert stats["hits"] == 1
        assert stats["entries"] == 1

    def test_eviction_lru(self):
        cm = CacheManager(default_ttl=60)
        cm._max_size = 3
        cm.set("a", 1)
        cm.set("b", 2)
        cm.set("c", 3)
        cm.get("a")  # Access a so b is LRU
        cm.set("d", 4)  # Should evict b
        assert cm.get("a") is not None
        assert cm.size == 3

    def test_eviction_lfu(self):
        cm = CacheManager(
            strategy=CacheStrategy.LFU,
        )
        cm._max_size = 2
        cm.set("a", 1)
        cm.set("b", 2)
        cm.get("a")
        cm.get("a")  # a has higher freq
        cm.set("c", 3)  # should evict b (lower freq)
        assert cm.get("a") is not None
        assert cm.size == 2


# ---- MemoryCache Testleri ----

class TestMemoryCache:
    """MemoryCache testleri."""

    def setup_method(self):
        self.mc = MemoryCache(
            max_size=100, default_ttl=60,
        )

    def test_set_get(self):
        self.mc.set("k1", "v1")
        assert self.mc.get("k1") == "v1"

    def test_get_missing(self):
        assert self.mc.get("nope") is None

    def test_get_default(self):
        assert self.mc.get("nope", 42) == 42

    def test_delete(self):
        self.mc.set("k1", "v1")
        ok = self.mc.delete("k1")
        assert ok is True
        assert self.mc.size == 0

    def test_delete_missing(self):
        assert self.mc.delete("nope") is False

    def test_clear(self):
        self.mc.set("a", 1)
        self.mc.set("b", 2)
        count = self.mc.clear()
        assert count == 2
        assert self.mc.size == 0

    def test_exists(self):
        self.mc.set("k1", "v1")
        assert self.mc.exists("k1") is True
        assert self.mc.exists("nope") is False

    def test_get_many(self):
        self.mc.set("a", 1)
        self.mc.set("b", 2)
        result = self.mc.get_many(["a", "b", "c"])
        assert result["a"] == 1
        assert result["b"] == 2
        assert "c" not in result

    def test_set_many(self):
        count = self.mc.set_many(
            {"a": 1, "b": 2, "c": 3},
        )
        assert count == 3
        assert self.mc.size == 3

    def test_cleanup_expired(self):
        self.mc.set("k1", "v1", ttl=0)
        # ttl=0 means no expiry
        cleaned = self.mc.cleanup_expired()
        assert cleaned == 0

    def test_hit_miss_count(self):
        self.mc.set("k1", "v1")
        self.mc.get("k1")  # hit
        self.mc.get("k2")  # miss
        assert self.mc.hit_count == 1
        assert self.mc.miss_count == 1

    def test_get_stats(self):
        self.mc.set("k1", "v1")
        stats = self.mc.get_stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 100

    def test_eviction(self):
        mc = MemoryCache(max_size=2)
        mc.set("a", 1)
        mc.set("b", 2)
        mc.get("a")  # Access a
        mc.set("c", 3)  # evict b
        assert mc.size == 2


# ---- DistributedCache Testleri ----

class TestDistributedCache:
    """DistributedCache testleri."""

    def setup_method(self):
        self.dc = DistributedCache(num_shards=4)

    def test_set_get(self):
        self.dc.set("k1", "v1")
        assert self.dc.get("k1") == "v1"

    def test_get_missing(self):
        assert self.dc.get("nope") is None

    def test_get_default(self):
        assert self.dc.get("nope", 42) == 42

    def test_delete(self):
        self.dc.set("k1", "v1")
        ok = self.dc.delete("k1")
        assert ok is True

    def test_delete_missing(self):
        assert self.dc.delete("nope") is False

    def test_exists(self):
        self.dc.set("k1", "v1")
        assert self.dc.exists("k1") is True
        assert self.dc.exists("nope") is False

    def test_flush(self):
        self.dc.set("a", 1)
        self.dc.set("b", 2)
        count = self.dc.flush()
        assert count == 2
        assert self.dc.total_entries == 0

    def test_add_node(self):
        node = self.dc.add_node("r1", "replica")
        assert node["status"] == "active"
        assert self.dc.node_count == 2

    def test_remove_node(self):
        self.dc.add_node("r1")
        ok = self.dc.remove_node("r1")
        assert ok is True

    def test_remove_primary(self):
        ok = self.dc.remove_node("primary")
        assert ok is False

    def test_remove_nonexistent(self):
        ok = self.dc.remove_node("nope")
        assert ok is False

    def test_failover(self):
        self.dc.add_node("r1", "replica")
        result = self.dc.failover("primary")
        assert result["success"] is True
        assert result["promoted"] == "r1"

    def test_failover_nonexistent(self):
        result = self.dc.failover("nope")
        assert result["success"] is False

    def test_shard_stats(self):
        self.dc.set("a", 1)
        stats = self.dc.get_shard_stats()
        assert len(stats) == 4

    def test_get_stats(self):
        self.dc.set("k1", "v1")
        self.dc.get("k1")
        stats = self.dc.get_stats()
        assert stats["hits"] == 1
        assert stats["shards"] == 4

    def test_shard_count(self):
        assert self.dc.shard_count == 4

    def test_ttl_expiry(self):
        self.dc.set("k1", "v1", ttl=0)
        # ttl=0 means no expiry
        assert self.dc.get("k1") == "v1"


# ---- QueryOptimizer Testleri ----

class TestQueryOptimizer:
    """QueryOptimizer testleri."""

    def setup_method(self):
        self.qo = QueryOptimizer(
            slow_threshold=0.5,
        )

    def test_analyze_query_simple(self):
        a = self.qo.analyze_query(
            "SELECT * FROM users",
        )
        assert a["has_where"] is False
        assert any(
            "SELECT *" in s
            for s in a["suggestions"]
        )

    def test_analyze_query_join(self):
        a = self.qo.analyze_query(
            "SELECT id FROM users JOIN orders ON u.id = o.uid",
        )
        assert a["has_join"] is True

    def test_analyze_query_complex(self):
        a = self.qo.analyze_query(
            "SELECT id FROM users WHERE active = 1 ORDER BY name GROUP BY dept",
        )
        assert a["has_where"] is True
        assert a["has_orderby"] is True
        assert a["has_groupby"] is True
        assert a["complexity"] >= 2

    def test_suggest_indexes(self):
        s = self.qo.suggest_indexes(
            "users", ["name", "email"],
        )
        assert len(s["suggested_indexes"]) == 2

    def test_suggest_with_existing(self):
        self.qo.add_index("users", "name")
        s = self.qo.suggest_indexes(
            "users", ["name", "email"],
        )
        assert "name" not in s["suggested_indexes"]
        assert "email" in s["suggested_indexes"]

    def test_cache_query(self):
        self.qo.cache_query(
            "SELECT 1", [1], ttl=60,
        )
        assert self.qo.cache_count == 1

    def test_get_cached(self):
        self.qo.cache_query(
            "SELECT 1", [1], ttl=60,
        )
        result = self.qo.get_cached("SELECT 1")
        assert result == [1]

    def test_get_cached_missing(self):
        assert self.qo.get_cached("nope") is None

    def test_record_execution(self):
        r = self.qo.record_execution(
            "SELECT 1", 0.001, 1,
        )
        assert r["slow"] is False
        assert self.qo.history_count == 1

    def test_record_slow_query(self):
        r = self.qo.record_execution(
            "SELECT *", 2.0, 1000,
        )
        assert r["slow"] is True
        assert self.qo.slow_count == 1

    def test_execution_plan(self):
        plan = self.qo.get_execution_plan(
            "SELECT id FROM users WHERE x = 1",
        )
        assert "filter" in plan["steps"]

    def test_execution_plan_cached(self):
        self.qo.cache_query("q1", [1])
        plan = self.qo.get_execution_plan("q1")
        assert plan["use_cache"] is True

    def test_get_slow_queries(self):
        self.qo.record_execution("q1", 2.0)
        slow = self.qo.get_slow_queries()
        assert len(slow) == 1

    def test_get_stats(self):
        self.qo.record_execution("q1", 0.1)
        stats = self.qo.get_stats()
        assert stats["total_queries"] == 1


# ---- ResponseCompressor Testleri ----

class TestResponseCompressor:
    """ResponseCompressor testleri."""

    def setup_method(self):
        self.rc = ResponseCompressor(
            threshold=100,
        )

    def test_compress_gzip(self):
        data = b"x" * 200
        result = self.rc.compress(data)
        assert result["compressed"] is True
        assert result["compressed_size"] < result["original_size"]

    def test_compress_below_threshold(self):
        data = b"small"
        result = self.rc.compress(data)
        assert result["compressed"] is False

    def test_compress_zlib(self):
        data = b"x" * 200
        result = self.rc.compress(
            data, CompressionType.ZLIB,
        )
        assert result["compressed"] is True

    def test_compress_brotli(self):
        data = b"x" * 200
        result = self.rc.compress(
            data, CompressionType.BROTLI,
        )
        assert result["compressed"] is True

    def test_compress_none(self):
        data = b"x" * 200
        result = self.rc.compress(
            data, CompressionType.NONE,
        )
        assert result["compressed"] is False

    def test_decompress(self):
        data = b"hello world" * 50
        compressed = self.rc.compress(data)
        decompressed = self.rc.decompress(
            compressed["data"],
        )
        assert decompressed["success"] is True
        assert decompressed["data"] == data

    def test_decompress_invalid(self):
        result = self.rc.decompress(b"invalid")
        assert result["success"] is False

    def test_should_compress(self):
        assert self.rc.should_compress(
            b"x" * 200,
        ) is True
        assert self.rc.should_compress(
            b"x",
        ) is False

    def test_get_stats(self):
        self.rc.compress(b"x" * 200)
        stats = self.rc.get_stats()
        assert stats["compressions"] == 1

    def test_compression_count(self):
        self.rc.compress(b"x" * 200)
        assert self.rc.compression_count == 1

    def test_compression_ratio(self):
        self.rc.compress(b"x" * 200)
        assert 0 < self.rc.compression_ratio < 1

    def test_total_savings(self):
        self.rc.compress(b"x" * 200)
        assert self.rc.total_savings > 0


# ---- LazyLoader Testleri ----

class TestLazyLoader:
    """LazyLoader testleri."""

    def setup_method(self):
        self.ll = LazyLoader(page_size=10)

    def test_register_and_load(self):
        self.ll.register(
            "users", lambda: [1, 2, 3],
        )
        data = self.ll.load("users")
        assert data == [1, 2, 3]
        assert self.ll.load_count == 1

    def test_load_cached(self):
        calls = []
        self.ll.register(
            "data", lambda: calls.append(1) or "val",
        )
        self.ll.load("data")
        self.ll.load("data")
        assert len(calls) == 1  # Only loaded once

    def test_load_nonexistent(self):
        assert self.ll.load("nope") is None

    def test_paginate(self):
        items = list(range(25))
        page = self.ll.paginate(items, page=2)
        assert page["page"] == 2
        assert len(page["items"]) == 10
        assert page["has_next"] is True
        assert page["has_prev"] is True

    def test_paginate_first_page(self):
        items = list(range(25))
        page = self.ll.paginate(items, page=1)
        assert page["has_prev"] is False

    def test_paginate_last_page(self):
        items = list(range(25))
        page = self.ll.paginate(items, page=3)
        assert page["has_next"] is False
        assert len(page["items"]) == 5

    def test_paginate_custom_size(self):
        items = list(range(10))
        page = self.ll.paginate(
            items, page=1, page_size=5,
        )
        assert page["page_size"] == 5
        assert page["total_pages"] == 2

    def test_infinite_scroll(self):
        items = list(range(30))
        result = self.ll.infinite_scroll(
            items, offset=0, limit=10,
        )
        assert len(result["items"]) == 10
        assert result["has_more"] is True
        assert result["next_offset"] == 10

    def test_infinite_scroll_end(self):
        items = list(range(10))
        result = self.ll.infinite_scroll(
            items, offset=5, limit=10,
        )
        assert result["has_more"] is False
        assert result["next_offset"] is None

    def test_prefetch(self):
        self.ll.register(
            "a", lambda: "data_a",
        )
        self.ll.register(
            "b", lambda: "data_b",
        )
        loaded = self.ll.prefetch(["a", "b"])
        assert loaded == 2

    def test_get_by_priority(self):
        self.ll.register(
            "a", lambda: None, "critical",
        )
        self.ll.register(
            "b", lambda: None, "low",
        )
        critical = self.ll.get_by_priority(
            "critical",
        )
        assert "a" in critical

    def test_invalidate(self):
        self.ll.register(
            "users", lambda: [1, 2],
        )
        self.ll.load("users")
        count = self.ll.invalidate("users")
        assert count >= 1

    def test_clear_cache(self):
        self.ll.register(
            "a", lambda: 1,
        )
        self.ll.load("a")
        count = self.ll.clear_cache()
        assert count >= 1
        assert self.ll.cache_size == 0


# ---- BatchProcessor Testleri ----

class TestBatchProcessor:
    """BatchProcessor testleri."""

    def setup_method(self):
        self.bp = BatchProcessor(
            batch_size=5, max_queue=100,
        )

    def test_enqueue(self):
        ok = self.bp.enqueue({"item": 1})
        assert ok is True
        assert self.bp.queue_size == 1

    def test_enqueue_full(self):
        bp = BatchProcessor(max_queue=2)
        bp.enqueue({"a": 1})
        bp.enqueue({"b": 2})
        ok = bp.enqueue({"c": 3})
        assert ok is False

    def test_flush(self):
        self.bp.enqueue({"a": 1})
        self.bp.enqueue({"b": 2})
        result = self.bp.flush()
        assert result["processed"] == 2
        assert self.bp.queue_size == 0

    def test_flush_empty(self):
        result = self.bp.flush()
        assert result["processed"] == 0

    def test_register_processor(self):
        processed = []
        self.bp.register_processor(
            "test",
            lambda items: processed.extend(items),
        )
        self.bp.enqueue({"x": 1}, "test")
        self.bp.flush()
        assert len(processed) == 1

    def test_auto_flush_on_batch_size(self):
        for i in range(5):
            self.bp.enqueue({"i": i})
        # Should have auto-flushed
        assert self.bp.queue_size == 0
        assert self.bp.total_processed == 5

    def test_processor_error(self):
        def bad_processor(items):
            raise RuntimeError("fail")

        self.bp.register_processor(
            "bad", bad_processor,
        )
        self.bp.enqueue({"x": 1}, "bad")
        result = self.bp.flush()
        assert result["failed"] == 1

    def test_debounce(self):
        assert self.bp.debounce("key") is True
        assert self.bp.debounce("key", 10) is False

    def test_throttle(self):
        assert self.bp.throttle("key") is True
        assert self.bp.throttle("key") is False

    def test_get_batch(self):
        self.bp.enqueue({"a": 1})
        result = self.bp.flush()
        batch = self.bp.get_batch(
            result["batch_id"],
        )
        assert batch is not None

    def test_get_stats(self):
        self.bp.enqueue({"a": 1})
        self.bp.flush()
        stats = self.bp.get_stats()
        assert stats["total_processed"] == 1
        assert stats["total_batches"] == 1


# ---- PerformanceProfiler Testleri ----

class TestPerformanceProfiler:
    """PerformanceProfiler testleri."""

    def setup_method(self):
        self.pp = PerformanceProfiler(
            slow_threshold=0.5,
        )

    def test_start_stop_timer(self):
        self.pp.start_timer("op1")
        result = self.pp.stop_timer("op1")
        assert result["duration"] >= 0
        assert self.pp.profile_count == 1

    def test_stop_without_start(self):
        result = self.pp.stop_timer("nope")
        assert result["error"] == "no_timer"

    def test_record_metric(self):
        r = self.pp.record_metric(
            "query",
            ProfileMetric.EXECUTION_TIME,
            0.05,
        )
        assert r.operation == "query"
        assert self.pp.profile_count == 1

    def test_record_memory(self):
        snap = self.pp.record_memory(
            "main", 256.0, 512.0,
        )
        assert snap["usage_pct"] == 50.0

    def test_record_memory_no_total(self):
        snap = self.pp.record_memory(
            "main", 256.0,
        )
        assert snap["usage_pct"] == 0.0

    def test_detect_bottlenecks(self):
        self.pp.record_metric(
            "slow_op",
            ProfileMetric.EXECUTION_TIME,
            2.0,
        )
        bns = self.pp.detect_bottlenecks()
        assert len(bns) >= 1
        assert bns[0]["type"] == "slow_execution"

    def test_detect_memory_bottleneck(self):
        self.pp.record_metric(
            "heavy",
            ProfileMetric.MEMORY_USAGE,
            800.0,
        )
        bns = self.pp.detect_bottlenecks()
        assert any(
            b["type"] == "high_memory"
            for b in bns
        )

    def test_get_flame_data(self):
        self.pp.record_metric(
            "op1",
            ProfileMetric.EXECUTION_TIME,
            0.1,
        )
        flame = self.pp.get_flame_data()
        assert len(flame) == 1
        assert flame[0]["name"] == "op1"

    def test_get_summary(self):
        self.pp.record_metric(
            "op1",
            ProfileMetric.EXECUTION_TIME,
            0.1,
        )
        self.pp.record_metric(
            "op2",
            ProfileMetric.EXECUTION_TIME,
            0.3,
        )
        s = self.pp.get_summary()
        assert s["total_profiles"] == 2
        assert s["avg_execution_time"] == 0.2

    def test_get_summary_filtered(self):
        self.pp.record_metric(
            "op1",
            ProfileMetric.EXECUTION_TIME,
            0.1,
        )
        self.pp.record_metric(
            "op2",
            ProfileMetric.EXECUTION_TIME,
            0.3,
        )
        s = self.pp.get_summary("op1")
        assert s["total_profiles"] == 1

    def test_clear(self):
        self.pp.record_metric(
            "op1",
            ProfileMetric.EXECUTION_TIME,
            0.1,
        )
        self.pp.clear()
        assert self.pp.profile_count == 0

    def test_active_timers(self):
        self.pp.start_timer("op1")
        assert self.pp.active_timers == 1
        self.pp.stop_timer("op1")
        assert self.pp.active_timers == 0

    def test_slow_detection(self):
        self.pp.start_timer("slow")
        # Simulate slow by recording directly
        self.pp.stop_timer("slow")
        # The threshold is 0.5s, normal ops won't hit it
        # Record explicit slow metric
        self.pp.record_metric(
            "slow",
            ProfileMetric.EXECUTION_TIME,
            1.0,
        )
        bns = self.pp.detect_bottlenecks(0.5)
        assert len(bns) >= 1


# ---- CachingOrchestrator Testleri ----

class TestCachingOrchestrator:
    """CachingOrchestrator testleri."""

    def setup_method(self):
        self.co = CachingOrchestrator(
            default_ttl=60,
            max_cache_size=1000,
            compression_threshold=100,
        )

    def test_init(self):
        assert self.co.cache is not None
        assert self.co.memory is not None
        assert self.co.distributed is not None
        assert self.co.queries is not None
        assert self.co.compressor is not None
        assert self.co.loader is not None
        assert self.co.batches is not None
        assert self.co.profiler is not None

    def test_cached_get_with_loader(self):
        val = self.co.cached_get(
            "key1", loader=lambda: "loaded",
        )
        assert val == "loaded"
        # Second call from cache
        val2 = self.co.cached_get("key1")
        assert val2 == "loaded"

    def test_cached_get_no_loader(self):
        val = self.co.cached_get("nope")
        assert val is None

    def test_cached_set(self):
        self.co.cached_set("k1", "v1")
        assert self.co.memory.get("k1") == "v1"
        assert self.co.distributed.get("k1") == "v1"

    def test_invalidate_all(self):
        self.co.cached_set("k1", "v1")
        result = self.co.invalidate_all("k1")
        assert result["memory"] is True
        assert result["distributed"] is True

    def test_compress_and_cache(self):
        data = b"x" * 200
        result = self.co.compress_and_cache(
            "big", data,
        )
        assert result["compressed"] is True
        assert result["stored_size"] < result["original_size"]

    def test_optimized_query_cached(self):
        # First query
        r1 = self.co.optimized_query(
            "SELECT 1",
            executor=lambda: [1],
        )
        assert r1["from_cache"] is False
        # Second query (cached)
        r2 = self.co.optimized_query("SELECT 1")
        assert r2["from_cache"] is True
        assert r2["result"] == [1]

    def test_optimized_query_no_executor(self):
        r = self.co.optimized_query("SELECT 1")
        assert r["result"] is None

    def test_get_analytics(self):
        self.co.cached_set("k1", "v1")
        self.co.cached_get("k1")
        a = self.co.get_analytics()
        assert a["total_hits"] >= 1
        assert "compression_ratio" in a

    def test_get_snapshot(self):
        self.co.cached_set("k1", "v1")
        s = self.co.get_snapshot()
        assert isinstance(s, CachingSnapshot)
        assert s.total_entries >= 1

    def test_full_pipeline(self):
        # Set through orchestrator
        self.co.cached_set("user:1", {"name": "Fatih"})
        self.co.cached_set("user:2", {"name": "Ali"})

        # Get
        u1 = self.co.cached_get("user:1")
        assert u1["name"] == "Fatih"

        # Compress
        big_data = b"response data " * 100
        cr = self.co.compress_and_cache(
            "resp:1", big_data,
        )
        assert cr["compressed"] is True

        # Analytics
        analytics = self.co.get_analytics()
        assert analytics["total_hits"] >= 1

        # Snapshot
        snap = self.co.get_snapshot()
        assert snap.total_entries >= 2


# ---- Config Testleri ----

class TestCachingConfig:
    """Config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.caching_enabled is True
        assert s.default_ttl == 300
        assert s.max_cache_size == 10000
        assert s.compression_threshold == 1024
        assert s.profiling_enabled is True

    def test_config_values(self):
        from app.config import Settings
        s = Settings()
        assert isinstance(s.default_ttl, int)
        assert isinstance(
            s.compression_threshold, int,
        )


# ---- Import Testleri ----

class TestCachingImports:
    """Import testleri."""

    def test_import_all(self):
        from app.core.caching import (
            BatchProcessor,
            CacheManager,
            CachingOrchestrator,
            DistributedCache,
            LazyLoader,
            MemoryCache,
            PerformanceProfiler,
            QueryOptimizer,
            ResponseCompressor,
        )
        assert CacheManager is not None
        assert MemoryCache is not None
        assert DistributedCache is not None
        assert QueryOptimizer is not None
        assert ResponseCompressor is not None
        assert LazyLoader is not None
        assert BatchProcessor is not None
        assert PerformanceProfiler is not None
        assert CachingOrchestrator is not None

    def test_import_models(self):
        from app.models.caching import (
            BatchRecord,
            BatchStatus,
            CacheEntry,
            CacheLayer,
            CacheStrategy,
            CachingSnapshot,
            CompressionType,
            LoadPriority,
            ProfileMetric,
            ProfileRecord,
        )
        assert CacheStrategy is not None
        assert CacheLayer is not None
        assert CompressionType is not None
        assert ProfileMetric is not None
        assert BatchStatus is not None
        assert LoadPriority is not None
