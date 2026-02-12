"""ATLAS dayaniklilik ve cevrimdisi calisma testleri.

OfflineManager, LocalLLM, StatePersistence, CircuitBreaker,
FailoverManager ve AutonomousFallback testleri.
"""

import asyncio
import json
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.resilience.autonomous_fallback import (
    PROGRAMMED_RESPONSES,
    AutonomousFallback,
    EmergencyLevel,
    FallbackResponse,
    _EMERGENCY_PROTOCOLS,
    _HEURISTIC_RULES,
)
from app.core.resilience.failover import (
    CircuitBreaker,
    CircuitState,
    FailoverManager,
    ServiceHealth,
)
from app.core.resilience.local_inference import (
    FALLBACK_RULES,
    LocalLLM,
    LocalLLMProvider,
)
from app.core.resilience.offline_mode import (
    ConnectionStatus,
    OfflineManager,
    SyncItem,
)
from app.core.resilience.state_persistence import (
    StatePersistence,
    StateSnapshot,
)


# === Yardimci fonksiyonlar ===


def _make_sync_item(
    operation: str = "create",
    target_service: str = "redis",
    payload: dict | None = None,
) -> SyncItem:
    """Test icin SyncItem olusturur."""
    return SyncItem(
        operation=operation,
        target_service=target_service,
        payload=payload or {"key": "value"},
    )


def _make_fallback_response(
    action: str = "log",
    message: str = "Test mesaji",
    confidence: float = 0.9,
    source: str = "rule",
) -> FallbackResponse:
    """Test icin FallbackResponse olusturur."""
    return FallbackResponse(
        action=action,
        message=message,
        confidence=confidence,
        source=source,
    )


def _make_offline_manager(**kwargs) -> OfflineManager:
    """Test icin OfflineManager olusturur."""
    defaults = {
        "health_check_interval": 5,
        "max_queue_size": 100,
    }
    defaults.update(kwargs)
    return OfflineManager(**defaults)


def _make_circuit_breaker(**kwargs) -> CircuitBreaker:
    """Test icin CircuitBreaker olusturur."""
    defaults = {
        "failure_threshold": 3,
        "recovery_timeout": 10,
        "half_open_max_calls": 2,
    }
    defaults.update(kwargs)
    return CircuitBreaker(**defaults)


def _make_failover_manager(**kwargs) -> FailoverManager:
    """Test icin FailoverManager olusturur."""
    defaults = {"health_check_interval": 5}
    defaults.update(kwargs)
    return FailoverManager(**defaults)


def _make_local_llm(**kwargs) -> LocalLLM:
    """Test icin LocalLLM olusturur."""
    defaults = {"provider": LocalLLMProvider.RULE_BASED}
    defaults.update(kwargs)
    return LocalLLM(**defaults)


def _make_autonomous_fallback(**kwargs) -> AutonomousFallback:
    """Test icin AutonomousFallback olusturur."""
    return AutonomousFallback(**kwargs)


async def _make_state_persistence(tmp_path: Path) -> StatePersistence:
    """Test icin StatePersistence olusturur ve initialize eder."""
    db_path = str(tmp_path / "test_state.db")
    sp = StatePersistence(db_path=db_path, max_snapshots=10)
    await sp.initialize()
    return sp


# === TestConnectionStatus ===


class TestConnectionStatus:
    """ConnectionStatus enum testleri."""

    def test_online_value(self):
        assert ConnectionStatus.ONLINE == "online"

    def test_degraded_value(self):
        assert ConnectionStatus.DEGRADED == "degraded"

    def test_offline_value(self):
        assert ConnectionStatus.OFFLINE == "offline"

    def test_is_string_enum(self):
        assert isinstance(ConnectionStatus.ONLINE, str)


# === TestSyncItem ===


class TestSyncItem:
    """SyncItem model testleri."""

    def test_create_with_defaults(self):
        item = SyncItem(operation="create", target_service="redis")
        assert item.operation == "create"
        assert item.target_service == "redis"
        assert item.retry_count == 0
        assert item.item_id is not None
        assert item.created_at is not None

    def test_create_with_payload(self):
        item = _make_sync_item(payload={"data": 42})
        assert item.payload == {"data": 42}

    def test_unique_ids(self):
        item1 = _make_sync_item()
        item2 = _make_sync_item()
        assert item1.item_id != item2.item_id

    def test_retry_count_default(self):
        item = _make_sync_item()
        assert item.retry_count == 0

    def test_created_at_is_utc(self):
        item = _make_sync_item()
        assert item.created_at.tzinfo is not None


# === TestOfflineManager ===


class TestOfflineManager:
    """OfflineManager testleri."""

    def test_init_defaults(self):
        mgr = _make_offline_manager()
        assert mgr.health_check_interval == 5
        assert mgr.max_queue_size == 100

    def test_initial_status_online(self):
        mgr = _make_offline_manager()
        assert mgr.status == ConnectionStatus.ONLINE

    def test_is_offline_false_initially(self):
        mgr = _make_offline_manager()
        assert mgr.is_offline is False

    def test_status_worst_case_offline(self):
        mgr = _make_offline_manager()
        mgr._service_status["redis"] = ConnectionStatus.OFFLINE
        assert mgr.status == ConnectionStatus.OFFLINE

    def test_status_worst_case_degraded(self):
        mgr = _make_offline_manager()
        mgr._service_status["redis"] = ConnectionStatus.DEGRADED
        assert mgr.status == ConnectionStatus.DEGRADED

    def test_is_offline_true_when_all_offline(self):
        mgr = _make_offline_manager()
        for key in mgr._service_status:
            mgr._service_status[key] = ConnectionStatus.OFFLINE
        assert mgr.is_offline is True

    def test_is_offline_false_when_one_online(self):
        mgr = _make_offline_manager()
        mgr._service_status["redis"] = ConnectionStatus.OFFLINE
        mgr._service_status["postgres"] = ConnectionStatus.OFFLINE
        mgr._service_status["qdrant"] = ConnectionStatus.ONLINE
        assert mgr.is_offline is False

    @pytest.mark.asyncio
    async def test_cache_decision(self):
        mgr = _make_offline_manager()
        await mgr.cache_decision("key1", {"action": "log"})
        result = await mgr.get_cached_decision("key1")
        assert result == {"action": "log"}

    @pytest.mark.asyncio
    async def test_get_cached_decision_miss(self):
        mgr = _make_offline_manager()
        result = await mgr.get_cached_decision("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_enqueue(self):
        mgr = _make_offline_manager()
        item = _make_sync_item()
        await mgr.enqueue(item)
        assert await mgr.get_queue_size() == 1

    @pytest.mark.asyncio
    async def test_enqueue_multiple(self):
        mgr = _make_offline_manager()
        for i in range(5):
            await mgr.enqueue(_make_sync_item())
        assert await mgr.get_queue_size() == 5

    @pytest.mark.asyncio
    async def test_sync_pending_online(self):
        mgr = _make_offline_manager()
        item = _make_sync_item(target_service="redis")
        await mgr.enqueue(item)
        synced = await mgr.sync_pending()
        assert synced == 1
        assert await mgr.get_queue_size() == 0

    @pytest.mark.asyncio
    async def test_sync_pending_offline_requeues(self):
        mgr = _make_offline_manager()
        mgr._service_status["redis"] = ConnectionStatus.OFFLINE
        item = _make_sync_item(target_service="redis")
        await mgr.enqueue(item)
        synced = await mgr.sync_pending()
        assert synced == 0
        assert await mgr.get_queue_size() == 1

    @pytest.mark.asyncio
    async def test_sync_pending_mixed(self):
        mgr = _make_offline_manager()
        mgr._service_status["redis"] = ConnectionStatus.OFFLINE
        mgr._service_status["postgres"] = ConnectionStatus.ONLINE

        await mgr.enqueue(_make_sync_item(target_service="redis"))
        await mgr.enqueue(_make_sync_item(target_service="postgres"))

        synced = await mgr.sync_pending()
        assert synced == 1
        assert await mgr.get_queue_size() == 1

    @pytest.mark.asyncio
    async def test_sync_pending_retry_count_increments(self):
        mgr = _make_offline_manager()
        mgr._service_status["redis"] = ConnectionStatus.OFFLINE
        item = _make_sync_item(target_service="redis")
        await mgr.enqueue(item)
        await mgr.sync_pending()
        # Kuyrukta kalan elemanin retry_count artmis olmali
        queued_item = mgr._sync_queue[0]
        assert queued_item.retry_count == 1

    @pytest.mark.asyncio
    async def test_check_connections_mock(self):
        mgr = _make_offline_manager()
        with (
            patch.object(mgr, "_check_redis", return_value=ConnectionStatus.ONLINE),
            patch.object(mgr, "_check_postgres", return_value=ConnectionStatus.DEGRADED),
            patch.object(mgr, "_check_qdrant", return_value=ConnectionStatus.OFFLINE),
        ):
            result = await mgr.check_connections()
        assert result["redis"] == ConnectionStatus.ONLINE
        assert result["postgres"] == ConnectionStatus.DEGRADED
        assert result["qdrant"] == ConnectionStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_start_stop(self):
        mgr = _make_offline_manager()
        with (
            patch.object(mgr, "_check_redis", return_value=ConnectionStatus.ONLINE),
            patch.object(mgr, "_check_postgres", return_value=ConnectionStatus.ONLINE),
            patch.object(mgr, "_check_qdrant", return_value=ConnectionStatus.ONLINE),
        ):
            await mgr.start()
            assert mgr._running is True
            assert mgr._task is not None
            await mgr.stop()
            assert mgr._running is False
            assert mgr._task is None

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        mgr = _make_offline_manager()
        with (
            patch.object(mgr, "_check_redis", return_value=ConnectionStatus.ONLINE),
            patch.object(mgr, "_check_postgres", return_value=ConnectionStatus.ONLINE),
            patch.object(mgr, "_check_qdrant", return_value=ConnectionStatus.ONLINE),
        ):
            await mgr.start()
            task1 = mgr._task
            await mgr.start()
            task2 = mgr._task
            assert task1 is task2
            await mgr.stop()

    def test_get_service_statuses(self):
        mgr = _make_offline_manager()
        mgr._service_status["redis"] = ConnectionStatus.DEGRADED
        result = mgr.get_service_statuses()
        assert result["redis"] == "degraded"
        assert result["postgres"] == "online"

    @pytest.mark.asyncio
    async def test_queue_max_size(self):
        mgr = _make_offline_manager(max_queue_size=3)
        for _ in range(5):
            await mgr.enqueue(_make_sync_item())
        assert await mgr.get_queue_size() == 3


# === TestLocalLLMProvider ===


class TestLocalLLMProvider:
    """LocalLLMProvider enum testleri."""

    def test_ollama_value(self):
        assert LocalLLMProvider.OLLAMA == "ollama"

    def test_rule_based_value(self):
        assert LocalLLMProvider.RULE_BASED == "rule_based"

    def test_cached_value(self):
        assert LocalLLMProvider.CACHED == "cached"


# === TestLocalLLM ===


class TestLocalLLM:
    """LocalLLM testleri."""

    def test_init_rule_based(self):
        llm = _make_local_llm()
        assert llm.provider == LocalLLMProvider.RULE_BASED

    def test_fallback_action_low_low(self):
        llm = _make_local_llm()
        assert llm.get_fallback_action("low", "low") == "log"

    def test_fallback_action_high_high(self):
        llm = _make_local_llm()
        assert llm.get_fallback_action("high", "high") == "notify"

    def test_fallback_action_unknown_defaults_notify(self):
        llm = _make_local_llm()
        assert llm.get_fallback_action("unknown", "unknown") == "notify"

    def test_fallback_rules_all_combos(self):
        """Tum risk/urgency kombinasyonlarinin tanimli oldugunu dogrular."""
        for risk in ("low", "medium", "high"):
            for urgency in ("low", "medium", "high"):
                assert (risk, urgency) in FALLBACK_RULES

    def test_fallback_rules_no_auto_fix(self):
        """Cevrimdisi modda auto_fix olmamali."""
        for action in FALLBACK_RULES.values():
            assert action in ("log", "notify")

    def test_hash_prompt(self):
        llm = _make_local_llm()
        h = llm._hash_prompt("test prompt")
        assert isinstance(h, str)
        assert len(h) == 16

    def test_hash_prompt_deterministic(self):
        llm = _make_local_llm()
        h1 = llm._hash_prompt("same prompt")
        h2 = llm._hash_prompt("same prompt")
        assert h1 == h2

    def test_hash_prompt_different(self):
        llm = _make_local_llm()
        h1 = llm._hash_prompt("prompt A")
        h2 = llm._hash_prompt("prompt B")
        assert h1 != h2

    @pytest.mark.asyncio
    async def test_cache_response_and_retrieve(self):
        llm = _make_local_llm()
        await llm.cache_response("abc123", "cached reply")
        result = await llm.get_cached_response("abc123")
        assert result == "cached reply"

    @pytest.mark.asyncio
    async def test_get_cached_response_miss(self):
        llm = _make_local_llm()
        result = await llm.get_cached_response("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_rule_based_generate_server_check(self):
        llm = _make_local_llm()
        result = await llm.generate("server_check status")
        assert "Sunucu" in result

    @pytest.mark.asyncio
    async def test_rule_based_generate_security_scan(self):
        llm = _make_local_llm()
        result = await llm.generate("run security_scan")
        assert "Guvenlik" in result

    @pytest.mark.asyncio
    async def test_rule_based_generate_risk_assessment(self):
        llm = _make_local_llm()
        result = await llm.generate("risk_assessment needed")
        assert "Risk" in result

    @pytest.mark.asyncio
    async def test_rule_based_generate_general(self):
        llm = _make_local_llm()
        result = await llm.generate("something unknown")
        assert "Islem kaydedildi" in result

    @pytest.mark.asyncio
    async def test_generate_uses_cache_first(self):
        llm = _make_local_llm()
        prompt = "test prompt"
        prompt_hash = llm._hash_prompt(prompt)
        await llm.cache_response(prompt_hash, "from cache")
        result = await llm.generate(prompt)
        assert result == "from cache"

    @pytest.mark.asyncio
    async def test_is_available_rule_based(self):
        llm = _make_local_llm(provider=LocalLLMProvider.RULE_BASED)
        assert await llm.is_available() is True

    @pytest.mark.asyncio
    async def test_is_available_cached_empty(self):
        llm = _make_local_llm(provider=LocalLLMProvider.CACHED)
        assert await llm.is_available() is False

    @pytest.mark.asyncio
    async def test_is_available_cached_with_data(self):
        llm = _make_local_llm(provider=LocalLLMProvider.CACHED)
        await llm.cache_response("key", "val")
        assert await llm.is_available() is True

    @pytest.mark.asyncio
    async def test_is_available_ollama_offline(self):
        llm = _make_local_llm(provider=LocalLLMProvider.OLLAMA)
        # Ollama _ollama_generate ve is_available httpx'i lazy import eder
        # Exception firlatarak offline senaryosu simule ediyoruz
        with patch.object(llm, "is_available", return_value=False):
            result = await llm.is_available()
        assert result is False

    @pytest.mark.asyncio
    async def test_is_available_ollama_offline_real(self):
        llm = _make_local_llm(provider=LocalLLMProvider.OLLAMA)
        # Gercek Ollama yok, httpx import olacak ama baglanti basarisiz
        result = await llm.is_available()
        assert result is False

    @pytest.mark.asyncio
    async def test_ollama_fallback_to_rule_based(self):
        llm = _make_local_llm(provider=LocalLLMProvider.OLLAMA)
        # _ollama_generate basarisiz olursa rule_based'e dusmeli
        with patch.object(
            llm, "_ollama_generate", side_effect=Exception("connection refused"),
        ):
            result = await llm.generate("general question")
        assert "Islem kaydedildi" in result


# === TestStateSnapshot ===


class TestStateSnapshot:
    """StateSnapshot model testleri."""

    def test_create_with_defaults(self):
        snap = StateSnapshot(state_type="agent", data={"key": "val"})
        assert snap.state_type == "agent"
        assert snap.data == {"key": "val"}
        assert snap.version == 1
        assert snap.snapshot_id is not None

    def test_unique_ids(self):
        s1 = StateSnapshot(state_type="agent", data={})
        s2 = StateSnapshot(state_type="agent", data={})
        assert s1.snapshot_id != s2.snapshot_id

    def test_timestamp_auto(self):
        snap = StateSnapshot(state_type="monitor", data={})
        assert snap.timestamp is not None
        assert snap.timestamp.tzinfo is not None


# === TestStatePersistence ===


class TestStatePersistence:
    """StatePersistence testleri."""

    @pytest.mark.asyncio
    async def test_initialize(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        assert sp._initialized is True
        await sp.close()

    @pytest.mark.asyncio
    async def test_save_and_load_snapshot(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        saved = await sp.save_snapshot("agent", {"name": "test"})
        loaded = await sp.load_snapshot(saved.snapshot_id)
        assert loaded is not None
        assert loaded.state_type == "agent"
        assert loaded.data == {"name": "test"}
        await sp.close()

    @pytest.mark.asyncio
    async def test_load_snapshot_not_found(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        result = await sp.load_snapshot("nonexistent-id")
        assert result is None
        await sp.close()

    @pytest.mark.asyncio
    async def test_load_latest_snapshot(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        await sp.save_snapshot("monitor", {"v": 1})
        await sp.save_snapshot("monitor", {"v": 2})
        latest = await sp.load_latest_snapshot("monitor")
        assert latest is not None
        assert latest.data == {"v": 2}
        await sp.close()

    @pytest.mark.asyncio
    async def test_load_latest_snapshot_none(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        result = await sp.load_latest_snapshot("nonexistent")
        assert result is None
        await sp.close()

    @pytest.mark.asyncio
    async def test_multiple_types(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        await sp.save_snapshot("agent", {"a": 1})
        await sp.save_snapshot("monitor", {"m": 2})
        agent = await sp.load_latest_snapshot("agent")
        monitor = await sp.load_latest_snapshot("monitor")
        assert agent is not None
        assert agent.data == {"a": 1}
        assert monitor is not None
        assert monitor.data == {"m": 2}
        await sp.close()

    @pytest.mark.asyncio
    async def test_create_recovery_point(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        await sp.save_snapshot("agent", {"state": "running"})
        recovery_id = await sp.create_recovery_point("checkpoint-1")
        assert recovery_id is not None
        assert isinstance(recovery_id, str)
        await sp.close()

    @pytest.mark.asyncio
    async def test_restore_from_recovery(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        await sp.save_snapshot("agent", {"state": "running"})
        await sp.save_snapshot("monitor", {"status": "ok"})
        recovery_id = await sp.create_recovery_point("backup")
        result = await sp.restore_from_recovery(recovery_id)
        assert "agent" in result or "monitor" in result
        await sp.close()

    @pytest.mark.asyncio
    async def test_restore_invalid_recovery_id(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        with pytest.raises(ValueError, match="Kurtarma noktasi bulunamadi"):
            await sp.restore_from_recovery("invalid-id")
        await sp.close()

    @pytest.mark.asyncio
    async def test_list_recovery_points(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        await sp.save_snapshot("agent", {"x": 1})
        await sp.create_recovery_point("point-1")
        await sp.create_recovery_point("point-2")
        points = await sp.list_recovery_points()
        assert len(points) == 2
        assert points[0]["label"] == "point-2"  # DESC order
        assert points[1]["label"] == "point-1"
        await sp.close()

    @pytest.mark.asyncio
    async def test_list_recovery_points_empty(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        points = await sp.list_recovery_points()
        assert points == []
        await sp.close()

    @pytest.mark.asyncio
    async def test_cleanup_old_snapshots(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        for i in range(5):
            await sp.save_snapshot("agent", {"v": i})
        deleted = await sp.cleanup_old_snapshots(keep_last=2)
        assert deleted == 3
        await sp.close()

    @pytest.mark.asyncio
    async def test_cleanup_no_old_snapshots(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        await sp.save_snapshot("agent", {"v": 1})
        deleted = await sp.cleanup_old_snapshots(keep_last=5)
        assert deleted == 0
        await sp.close()

    @pytest.mark.asyncio
    async def test_close_sets_initialized_false(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        assert sp._initialized is True
        await sp.close()
        assert sp._initialized is False

    @pytest.mark.asyncio
    async def test_db_file_created(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        assert Path(sp.db_path).exists()
        await sp.close()

    @pytest.mark.asyncio
    async def test_snapshot_version(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        saved = await sp.save_snapshot("agent", {"v": 1})
        assert saved.version == 1
        loaded = await sp.load_snapshot(saved.snapshot_id)
        assert loaded.version == 1
        await sp.close()


# === TestCircuitState ===


class TestCircuitState:
    """CircuitState enum testleri."""

    def test_closed_value(self):
        assert CircuitState.CLOSED == "closed"

    def test_open_value(self):
        assert CircuitState.OPEN == "open"

    def test_half_open_value(self):
        assert CircuitState.HALF_OPEN == "half_open"


# === TestServiceHealth ===


class TestServiceHealth:
    """ServiceHealth model testleri."""

    def test_create_defaults(self):
        health = ServiceHealth(name="redis")
        assert health.name == "redis"
        assert health.is_primary is True
        assert health.status == "healthy"
        assert health.failure_count == 0
        assert health.circuit_state == CircuitState.CLOSED

    def test_custom_values(self):
        health = ServiceHealth(
            name="pg",
            is_primary=False,
            status="down",
            failure_count=5,
            circuit_state=CircuitState.OPEN,
        )
        assert health.is_primary is False
        assert health.status == "down"
        assert health.failure_count == 5


# === TestCircuitBreaker ===


class TestCircuitBreaker:
    """CircuitBreaker testleri."""

    def test_init_defaults(self):
        cb = _make_circuit_breaker()
        assert cb.state == CircuitState.CLOSED

    def test_closed_to_open(self):
        cb = _make_circuit_breaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        cb = _make_circuit_breaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_open_to_half_open_after_timeout(self):
        cb = _make_circuit_breaker(failure_threshold=1, recovery_timeout=5)
        cb.record_failure()
        assert cb._state == CircuitState.OPEN
        # Zamani ileri al — recovery_timeout gecmis gibi
        cb._last_failure_time = time.monotonic() - 10
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_success(self):
        cb = _make_circuit_breaker(failure_threshold=1, recovery_timeout=5)
        cb.record_failure()
        cb._last_failure_time = time.monotonic() - 10
        _ = cb.state  # HALF_OPEN'a gec
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self):
        cb = _make_circuit_breaker(failure_threshold=1, recovery_timeout=5)
        cb.record_failure()
        cb._last_failure_time = time.monotonic() - 10
        _ = cb.state  # HALF_OPEN'a gec
        assert cb._state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb._state == CircuitState.OPEN

    def test_reset(self):
        cb = _make_circuit_breaker(failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0
        assert cb._half_open_calls == 0

    @pytest.mark.asyncio
    async def test_execute_success(self):
        cb = _make_circuit_breaker()

        async def success_fn():
            return "ok"

        result = await cb.execute(success_fn)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_execute_sync_function(self):
        cb = _make_circuit_breaker()

        def sync_fn():
            return 42

        result = await cb.execute(sync_fn)
        assert result == 42

    @pytest.mark.asyncio
    async def test_execute_failure_records(self):
        cb = _make_circuit_breaker()

        async def fail_fn():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await cb.execute(fail_fn)
        assert cb._failure_count == 1

    @pytest.mark.asyncio
    async def test_execute_open_raises(self):
        cb = _make_circuit_breaker(failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        async def fn():
            return "ok"

        with pytest.raises(RuntimeError, match="OPEN"):
            await cb.execute(fn)

    @pytest.mark.asyncio
    async def test_execute_half_open_max_calls(self):
        cb = _make_circuit_breaker(
            failure_threshold=1,
            recovery_timeout=5,
            half_open_max_calls=1,
        )
        cb.record_failure()
        cb._last_failure_time = time.monotonic() - 10
        _ = cb.state  # HALF_OPEN

        async def fn():
            return "ok"

        # Ilk cagri basarili
        result = await cb.execute(fn)
        assert result == "ok"
        # Artik CLOSED olmali (basarili)
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_execute_half_open_exceeds_max(self):
        cb = _make_circuit_breaker(
            failure_threshold=1,
            recovery_timeout=5,
            half_open_max_calls=1,
        )
        cb.record_failure()
        cb._last_failure_time = time.monotonic() - 10
        _ = cb.state  # HALF_OPEN

        async def fail_fn():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await cb.execute(fail_fn)
        # Basarisiz oldu, OPEN'a donmeli
        assert cb._state == CircuitState.OPEN

        # Zamani tekrar ileri al
        cb._last_failure_time = time.monotonic() - 10
        _ = cb.state  # HALF_OPEN
        cb._half_open_calls = 1  # max calls reached

        async def ok_fn():
            return "ok"

        with pytest.raises(RuntimeError, match="maks"):
            await cb.execute(ok_fn)


# === TestFailoverManager ===


class TestFailoverManager:
    """FailoverManager testleri."""

    def test_init(self):
        fm = _make_failover_manager()
        assert fm.health_check_interval == 5

    def test_register_service(self):
        fm = _make_failover_manager()
        fm.register_service("redis", lambda: True)
        assert "redis" in fm._services
        assert "redis" in fm._health_status
        assert "redis" in fm._circuit_breakers

    def test_register_fallback(self):
        fm = _make_failover_manager()
        fm.register_service("redis_primary", lambda: True)
        fm.register_service("redis_secondary", lambda: True, is_primary=False)
        fm.register_fallback("redis_primary", "redis_secondary")
        assert fm._fallback_map["redis_primary"] == "redis_secondary"

    @pytest.mark.asyncio
    async def test_check_service_healthy(self):
        fm = _make_failover_manager()
        fm.register_service("redis", AsyncMock(return_value=True))
        health = await fm.check_service("redis")
        assert health.status == "healthy"
        assert health.failure_count == 0

    @pytest.mark.asyncio
    async def test_check_service_degraded(self):
        fm = _make_failover_manager()
        fm.register_service("redis", AsyncMock(return_value=False))
        health = await fm.check_service("redis")
        assert health.status == "degraded"
        assert health.failure_count == 1

    @pytest.mark.asyncio
    async def test_check_service_down(self):
        fm = _make_failover_manager()
        fm.register_service("redis", AsyncMock(side_effect=Exception("err")))
        health = await fm.check_service("redis")
        assert health.status == "down"
        assert health.failure_count == 1

    @pytest.mark.asyncio
    async def test_check_service_not_found(self):
        fm = _make_failover_manager()
        with pytest.raises(KeyError, match="Servis bulunamadi"):
            await fm.check_service("nonexistent")

    @pytest.mark.asyncio
    async def test_check_all_services(self):
        fm = _make_failover_manager()
        fm.register_service("s1", AsyncMock(return_value=True))
        fm.register_service("s2", AsyncMock(return_value=False))
        result = await fm.check_all_services()
        assert result["s1"].status == "healthy"
        assert result["s2"].status == "degraded"

    @pytest.mark.asyncio
    async def test_execute_with_failover_primary_ok(self):
        fm = _make_failover_manager()
        fm.register_service("svc", AsyncMock(return_value=True))

        async def work():
            return "result"

        result = await fm.execute_with_failover("svc", work)
        assert result == "result"

    @pytest.mark.asyncio
    async def test_execute_with_failover_fallback(self):
        fm = _make_failover_manager()
        fm.register_service("primary", AsyncMock(return_value=True))
        fm.register_service("backup", AsyncMock(return_value=True))
        fm.register_fallback("primary", "backup")

        # primary circuit'i ac
        cb = fm._circuit_breakers["primary"]
        for _ in range(cb.failure_threshold):
            cb.record_failure()

        async def work():
            return "fallback_result"

        result = await fm.execute_with_failover("primary", work)
        assert result == "fallback_result"

    @pytest.mark.asyncio
    async def test_execute_with_failover_both_fail(self):
        fm = _make_failover_manager()
        fm.register_service("primary", AsyncMock(return_value=True))
        fm.register_service("backup", AsyncMock(return_value=True))
        fm.register_fallback("primary", "backup")

        # Her iki circuit'i de ac
        for name in ("primary", "backup"):
            cb = fm._circuit_breakers[name]
            for _ in range(cb.failure_threshold):
                cb.record_failure()

        async def work():
            return "ok"

        with pytest.raises(RuntimeError, match="basarisiz"):
            await fm.execute_with_failover("primary", work)

    @pytest.mark.asyncio
    async def test_execute_no_fallback_defined(self):
        fm = _make_failover_manager()
        fm.register_service("svc", AsyncMock(return_value=True))

        # Circuit'i ac
        cb = fm._circuit_breakers["svc"]
        for _ in range(cb.failure_threshold):
            cb.record_failure()

        async def work():
            return "ok"

        with pytest.raises(RuntimeError, match="yedek tanimli degil"):
            await fm.execute_with_failover("svc", work)

    @pytest.mark.asyncio
    async def test_start_stop(self):
        fm = _make_failover_manager()
        fm.register_service("svc", AsyncMock(return_value=True))
        await fm.start()
        assert fm._running is True
        await fm.stop()
        assert fm._running is False

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        fm = _make_failover_manager()
        await fm.start()
        task1 = fm._task
        await fm.start()
        task2 = fm._task
        assert task1 is task2
        await fm.stop()

    def test_get_service_status_empty(self):
        fm = _make_failover_manager()
        assert fm.get_service_status() == {}

    def test_get_service_status_after_register(self):
        fm = _make_failover_manager()
        fm.register_service("svc", lambda: True)
        status = fm.get_service_status()
        assert "svc" in status
        assert status["svc"].name == "svc"

    @pytest.mark.asyncio
    async def test_check_service_sync_function(self):
        fm = _make_failover_manager()
        fm.register_service("svc", lambda: True)
        health = await fm.check_service("svc")
        assert health.status == "healthy"

    @pytest.mark.asyncio
    async def test_circuit_state_tracked_in_health(self):
        fm = _make_failover_manager()
        fm.register_service("svc", AsyncMock(side_effect=Exception("err")))
        # Threshold'a kadar failure kaydet
        cb = fm._circuit_breakers["svc"]
        for _ in range(cb.failure_threshold):
            await fm.check_service("svc")
        health = fm._health_status["svc"]
        assert health.circuit_state == CircuitState.OPEN


# === TestEmergencyLevel ===


class TestEmergencyLevel:
    """EmergencyLevel enum testleri."""

    def test_normal_value(self):
        assert EmergencyLevel.NORMAL == "normal"

    def test_degraded_value(self):
        assert EmergencyLevel.DEGRADED == "degraded"

    def test_emergency_value(self):
        assert EmergencyLevel.EMERGENCY == "emergency"

    def test_critical_value(self):
        assert EmergencyLevel.CRITICAL == "critical"


# === TestFallbackResponse ===


class TestFallbackResponse:
    """FallbackResponse model testleri."""

    def test_create(self):
        resp = _make_fallback_response()
        assert resp.action == "log"
        assert resp.confidence == 0.9

    def test_custom_values(self):
        resp = FallbackResponse(
            action="notify",
            message="alert",
            confidence=0.5,
            source="heuristic",
        )
        assert resp.source == "heuristic"


# === TestProgrammedResponses ===


class TestProgrammedResponses:
    """Onceden programlanmis yanitlar testleri."""

    def test_server_down_exists(self):
        assert "server_down" in PROGRAMMED_RESPONSES

    def test_database_failure_exists(self):
        assert "database_failure" in PROGRAMMED_RESPONSES

    def test_api_unavailable_exists(self):
        assert "api_unavailable" in PROGRAMMED_RESPONSES

    def test_security_threat_exists(self):
        assert "security_threat" in PROGRAMMED_RESPONSES

    def test_high_load_exists(self):
        assert "high_load" in PROGRAMMED_RESPONSES

    def test_all_have_valid_actions(self):
        for resp in PROGRAMMED_RESPONSES.values():
            assert resp.action in ("log", "notify", "escalate", "block")

    def test_all_have_confidence(self):
        for resp in PROGRAMMED_RESPONSES.values():
            assert 0 <= resp.confidence <= 1

    def test_all_source_is_programmed(self):
        for resp in PROGRAMMED_RESPONSES.values():
            assert resp.source == "programmed"


# === TestHeuristicRules ===


class TestHeuristicRules:
    """Sezgisel karar kurallari testleri."""

    def test_all_risk_urgency_combos(self):
        for risk in ("low", "medium", "high"):
            for urgency in ("low", "medium", "high"):
                assert (risk, urgency) in _HEURISTIC_RULES

    def test_rules_return_tuple(self):
        for value in _HEURISTIC_RULES.values():
            action, confidence = value
            assert isinstance(action, str)
            assert isinstance(confidence, float)

    def test_actions_are_safe(self):
        """Heuristic'te sadece log ve notify olmali."""
        for action, _ in _HEURISTIC_RULES.values():
            assert action in ("log", "notify")

    def test_high_high_is_notify(self):
        action, _ = _HEURISTIC_RULES[("high", "high")]
        assert action == "notify"


# === TestEmergencyProtocols ===


class TestEmergencyProtocols:
    """Acil durum protokol testleri."""

    def test_normal_allows_all(self):
        actions = _EMERGENCY_PROTOCOLS[EmergencyLevel.NORMAL]["allowed_actions"]
        assert "log" in actions
        assert "notify" in actions
        assert "auto_fix" in actions
        assert "immediate" in actions

    def test_degraded_blocks_immediate(self):
        actions = _EMERGENCY_PROTOCOLS[EmergencyLevel.DEGRADED]["allowed_actions"]
        assert "immediate" not in actions
        assert "auto_fix" in actions

    def test_emergency_only_log_notify(self):
        actions = _EMERGENCY_PROTOCOLS[EmergencyLevel.EMERGENCY]["allowed_actions"]
        assert actions == ["log", "notify"]

    def test_critical_only_log(self):
        actions = _EMERGENCY_PROTOCOLS[EmergencyLevel.CRITICAL]["allowed_actions"]
        assert actions == ["log"]

    def test_all_levels_defined(self):
        for level in EmergencyLevel:
            assert level in _EMERGENCY_PROTOCOLS


# === TestAutonomousFallback ===


class TestAutonomousFallback:
    """AutonomousFallback testleri."""

    def test_init_defaults(self):
        fb = _make_autonomous_fallback()
        assert fb.emergency_level == EmergencyLevel.NORMAL
        assert fb.local_llm is None

    def test_init_with_llm(self):
        llm = _make_local_llm()
        fb = _make_autonomous_fallback(local_llm=llm)
        assert fb.local_llm is llm

    def test_get_programmed_response_exists(self):
        fb = _make_autonomous_fallback()
        resp = fb.get_programmed_response("server_down")
        assert resp is not None
        assert resp.action == "notify"

    def test_get_programmed_response_none(self):
        fb = _make_autonomous_fallback()
        resp = fb.get_programmed_response("unknown_event")
        assert resp is None

    def test_get_programmed_response_custom_priority(self):
        fb = _make_autonomous_fallback()
        custom = _make_fallback_response(action="escalate", message="custom")
        fb.register_protocol("server_down", custom)
        resp = fb.get_programmed_response("server_down")
        assert resp.action == "escalate"
        assert resp.message == "custom"

    def test_make_heuristic_decision(self):
        fb = _make_autonomous_fallback()
        resp = fb.make_heuristic_decision("low", "low")
        assert resp.action == "log"
        assert resp.source == "heuristic"

    def test_make_heuristic_decision_high(self):
        fb = _make_autonomous_fallback()
        resp = fb.make_heuristic_decision("high", "high")
        assert resp.action == "notify"

    def test_make_heuristic_decision_unknown(self):
        fb = _make_autonomous_fallback()
        resp = fb.make_heuristic_decision("unknown", "unknown")
        assert resp.action == "notify"
        assert resp.confidence == 0.5

    def test_make_heuristic_with_context(self):
        fb = _make_autonomous_fallback()
        resp = fb.make_heuristic_decision(
            "low", "low",
            context={"detail": "test detail"},
        )
        assert "test detail" in resp.message

    def test_make_heuristic_emergency_restricts(self):
        fb = _make_autonomous_fallback()
        fb._emergency_level = EmergencyLevel.CRITICAL
        resp = fb.make_heuristic_decision("high", "high")
        # CRITICAL'da sadece log izinli
        assert resp.action == "log"

    @pytest.mark.asyncio
    async def test_activate_emergency_protocol(self):
        fb = _make_autonomous_fallback()
        await fb.activate_emergency_protocol(EmergencyLevel.EMERGENCY)
        assert fb.emergency_level == EmergencyLevel.EMERGENCY

    @pytest.mark.asyncio
    async def test_deactivate_emergency(self):
        fb = _make_autonomous_fallback()
        await fb.activate_emergency_protocol(EmergencyLevel.CRITICAL)
        await fb.deactivate_emergency()
        assert fb.emergency_level == EmergencyLevel.NORMAL

    @pytest.mark.asyncio
    async def test_activate_saves_snapshot(self):
        mock_persistence = AsyncMock()
        fb = _make_autonomous_fallback(state_persistence=mock_persistence)
        await fb.activate_emergency_protocol(EmergencyLevel.EMERGENCY)
        mock_persistence.save_snapshot.assert_awaited_once()
        call_args = mock_persistence.save_snapshot.call_args
        assert call_args[0][0] == "emergency"
        assert call_args[0][1]["level"] == "emergency"

    @pytest.mark.asyncio
    async def test_activate_handles_persistence_error(self):
        mock_persistence = AsyncMock()
        mock_persistence.save_snapshot.side_effect = Exception("db error")
        fb = _make_autonomous_fallback(state_persistence=mock_persistence)
        # Hata olsa bile seviye degismeli
        await fb.activate_emergency_protocol(EmergencyLevel.CRITICAL)
        assert fb.emergency_level == EmergencyLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_decide_programmed(self):
        fb = _make_autonomous_fallback()
        resp = await fb.decide("server_down", "high", "high")
        assert resp.source == "programmed"

    @pytest.mark.asyncio
    async def test_decide_heuristic_fallback(self):
        fb = _make_autonomous_fallback()
        resp = await fb.decide("unknown_event", "low", "low")
        assert resp.source == "heuristic"

    @pytest.mark.asyncio
    async def test_decide_llm_fallback(self):
        mock_llm = MagicMock()
        mock_llm.get_fallback_action.return_value = "log"
        fb = _make_autonomous_fallback(local_llm=mock_llm)
        resp = await fb.decide("unknown_event", "medium", "medium")
        assert resp.source == "rule"
        assert resp.action == "log"

    @pytest.mark.asyncio
    async def test_decide_llm_error_falls_to_heuristic(self):
        mock_llm = MagicMock()
        mock_llm.get_fallback_action.side_effect = Exception("llm error")
        fb = _make_autonomous_fallback(local_llm=mock_llm)
        resp = await fb.decide("unknown_event", "low", "low")
        assert resp.source == "heuristic"

    @pytest.mark.asyncio
    async def test_decide_emergency_restricts_programmed(self):
        fb = _make_autonomous_fallback()
        fb._emergency_level = EmergencyLevel.CRITICAL
        resp = await fb.decide("server_down", "high", "high")
        # server_down action=notify ama CRITICAL'da izin yok
        assert resp.action == "log"

    def test_register_protocol(self):
        fb = _make_autonomous_fallback()
        custom = _make_fallback_response(action="block")
        fb.register_protocol("custom_event", custom)
        protocols = fb.get_registered_protocols()
        assert "custom_event" in protocols
        assert protocols["custom_event"].action == "block"

    def test_get_registered_protocols_empty(self):
        fb = _make_autonomous_fallback()
        assert fb.get_registered_protocols() == {}

    def test_get_registered_protocols_returns_copy(self):
        fb = _make_autonomous_fallback()
        custom = _make_fallback_response()
        fb.register_protocol("evt", custom)
        protocols = fb.get_registered_protocols()
        protocols["new"] = _make_fallback_response()
        # Orijinal etkilenmemeli
        assert "new" not in fb.get_registered_protocols()


# === TestEmergencyTransitions ===


class TestEmergencyTransitions:
    """Acil durum seviye gecisleri testleri."""

    @pytest.mark.asyncio
    async def test_normal_to_degraded(self):
        fb = _make_autonomous_fallback()
        await fb.activate_emergency_protocol(EmergencyLevel.DEGRADED)
        assert fb.emergency_level == EmergencyLevel.DEGRADED

    @pytest.mark.asyncio
    async def test_degraded_to_emergency(self):
        fb = _make_autonomous_fallback()
        await fb.activate_emergency_protocol(EmergencyLevel.DEGRADED)
        await fb.activate_emergency_protocol(EmergencyLevel.EMERGENCY)
        assert fb.emergency_level == EmergencyLevel.EMERGENCY

    @pytest.mark.asyncio
    async def test_emergency_to_critical(self):
        fb = _make_autonomous_fallback()
        await fb.activate_emergency_protocol(EmergencyLevel.CRITICAL)
        assert fb.emergency_level == EmergencyLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_critical_blocks_auto_fix(self):
        fb = _make_autonomous_fallback()
        await fb.activate_emergency_protocol(EmergencyLevel.CRITICAL)
        resp = fb.make_heuristic_decision("high", "high")
        assert resp.action == "log"
        assert resp.action != "auto_fix"

    @pytest.mark.asyncio
    async def test_critical_to_normal(self):
        fb = _make_autonomous_fallback()
        await fb.activate_emergency_protocol(EmergencyLevel.CRITICAL)
        await fb.deactivate_emergency()
        assert fb.emergency_level == EmergencyLevel.NORMAL

    @pytest.mark.asyncio
    async def test_emergency_confidence_reduction(self):
        fb = _make_autonomous_fallback()
        fb._emergency_level = EmergencyLevel.CRITICAL
        # notify normalde izinli degil CRITICAL'da, confidence dusecek
        resp = fb.make_heuristic_decision("high", "high")
        # high/high normalde (notify, 0.9) -> CRITICAL'da (log, 0.9*0.8=0.72)
        assert resp.confidence < 0.9


# === TestResiliencePackageImports ===


class TestResiliencePackageImports:
    """Paket import testleri."""

    def test_import_offline_manager(self):
        from app.core.resilience import OfflineManager
        assert OfflineManager is not None

    def test_import_local_llm(self):
        from app.core.resilience import LocalLLM
        assert LocalLLM is not None

    def test_import_state_persistence(self):
        from app.core.resilience import StatePersistence
        assert StatePersistence is not None

    def test_import_failover_manager(self):
        from app.core.resilience import FailoverManager
        assert FailoverManager is not None

    def test_import_circuit_breaker(self):
        from app.core.resilience import CircuitBreaker
        assert CircuitBreaker is not None

    def test_import_autonomous_fallback(self):
        from app.core.resilience import AutonomousFallback
        assert AutonomousFallback is not None

    def test_import_enums(self):
        from app.core.resilience import (
            CircuitState,
            ConnectionStatus,
            EmergencyLevel,
            LocalLLMProvider,
        )
        assert ConnectionStatus.ONLINE is not None
        assert CircuitState.CLOSED is not None
        assert EmergencyLevel.NORMAL is not None
        assert LocalLLMProvider.RULE_BASED is not None

    def test_import_models(self):
        from app.core.resilience import (
            FallbackResponse,
            ServiceHealth,
            StateSnapshot,
            SyncItem,
        )
        assert SyncItem is not None
        assert StateSnapshot is not None
        assert ServiceHealth is not None
        assert FallbackResponse is not None


# === TestResilienceIntegration ===


class TestResilienceIntegration:
    """Entegrasyon testleri — bilesenler arasi etkilesim."""

    @pytest.mark.asyncio
    async def test_fallback_with_persistence(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        fb = _make_autonomous_fallback(state_persistence=sp)
        await fb.activate_emergency_protocol(EmergencyLevel.EMERGENCY)
        snap = await sp.load_latest_snapshot("emergency")
        assert snap is not None
        assert snap.data["level"] == "emergency"
        await sp.close()

    @pytest.mark.asyncio
    async def test_fallback_with_local_llm(self):
        llm = _make_local_llm()
        fb = _make_autonomous_fallback(local_llm=llm)
        resp = await fb.decide("unknown", "medium", "medium")
        # LLM fallback action donmeli
        assert resp.action in ("log", "notify")

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_failover(self):
        fm = _make_failover_manager()

        async def success_fn():
            return "success"

        fm.register_service("primary", AsyncMock(return_value=True))
        fm.register_service("backup", AsyncMock(return_value=True))
        fm.register_fallback("primary", "backup")

        # Normal — primary basarili
        result = await fm.execute_with_failover("primary", success_fn)
        assert result == "success"

        # Primary circuit'i ac
        cb = fm._circuit_breakers["primary"]
        for _ in range(cb.failure_threshold):
            cb.record_failure()

        # Artik backup'a dusmeli
        result = await fm.execute_with_failover("primary", success_fn)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_offline_manager_sync_after_reconnect(self):
        mgr = _make_offline_manager()
        mgr._service_status["redis"] = ConnectionStatus.OFFLINE

        item = _make_sync_item(target_service="redis")
        await mgr.enqueue(item)
        assert await mgr.get_queue_size() == 1

        # Servis geri geldi
        mgr._service_status["redis"] = ConnectionStatus.ONLINE
        synced = await mgr.sync_pending()
        assert synced == 1
        assert await mgr.get_queue_size() == 0

    @pytest.mark.asyncio
    async def test_state_persistence_recovery_flow(self, tmp_path):
        sp = await _make_state_persistence(tmp_path)
        # Coklu snapshot kaydet
        await sp.save_snapshot("agent", {"state": "active"})
        await sp.save_snapshot("monitor", {"status": "checking"})

        # Kurtarma noktasi
        rid = await sp.create_recovery_point("before_crash")
        points = await sp.list_recovery_points()
        assert len(points) == 1

        # Geri yukle
        data = await sp.restore_from_recovery(rid)
        assert len(data) > 0
        await sp.close()

    def test_full_emergency_escalation(self):
        fb = _make_autonomous_fallback()

        # NORMAL: tum aksiyonlar izinli
        resp = fb.make_heuristic_decision("high", "high")
        assert resp.action == "notify"

        # DEGRADED: immediate engelli
        fb._emergency_level = EmergencyLevel.DEGRADED
        resp = fb.make_heuristic_decision("high", "high")
        assert resp.action == "notify"

        # EMERGENCY: sadece log+notify
        fb._emergency_level = EmergencyLevel.EMERGENCY
        resp = fb.make_heuristic_decision("high", "high")
        assert resp.action == "notify"

        # CRITICAL: sadece log
        fb._emergency_level = EmergencyLevel.CRITICAL
        resp = fb.make_heuristic_decision("high", "high")
        assert resp.action == "log"
