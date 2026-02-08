"""TaskManager testleri.

Gorev yasam dongusu, onceliklendirme, CRUD, retry,
bagimlillik takibi, crash recovery, zamanlama ve
uc katmanli hafiza entegrasyonunu test eder.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import BaseAgent, TaskResult
from app.core.decision_matrix import ActionType
from app.core.task_manager import (
    QueuedTask,
    TaskManager,
    TaskMetrics,
    TaskPriority,
    TaskSubmission,
    _ACTION_PRIORITY_MAP,
)
from app.models.task import TaskCreate, TaskResponse, TaskStatus


# === Yardimci fonksiyonlar ===


def _make_task_response(
    task_id: str = "test-id-1234",
    description: str = "test gorev",
    status: TaskStatus = TaskStatus.PENDING,
    agent: str | None = None,
    risk: str | None = "low",
    urgency: str | None = "low",
    result_message: str | None = None,
    result_success: bool | None = None,
) -> TaskResponse:
    """Test icin TaskResponse nesnesi olusturur."""
    now = datetime.now(timezone.utc)
    return TaskResponse(
        id=task_id,
        description=description,
        status=status,
        agent=agent,
        risk=risk,
        urgency=urgency,
        result_message=result_message,
        result_success=result_success,
        confidence=None,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _make_mock_long_term() -> MagicMock:
    """Mock LongTermMemory olusturur."""
    lt = MagicMock()
    lt.create_task = AsyncMock(
        return_value=_make_task_response()
    )
    lt.get_task = AsyncMock(return_value=None)
    lt.update_task = AsyncMock(return_value=_make_task_response())
    lt.list_tasks = AsyncMock(return_value=[])
    return lt


def _make_mock_short_term() -> MagicMock:
    """Mock ShortTermMemory olusturur."""
    st = MagicMock()
    st.store_task_status = AsyncMock()
    st.get_task_status = AsyncMock(return_value=None)
    st.delete_task_status = AsyncMock(return_value=True)
    return st


def _make_mock_semantic() -> MagicMock:
    """Mock SemanticMemory olusturur."""
    sem = MagicMock()
    sem.store = AsyncMock()
    sem.search = AsyncMock(return_value=[])
    return sem


def _make_mock_telegram() -> MagicMock:
    """Mock TelegramBot olusturur."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_buttons = AsyncMock()
    return bot


def _make_mock_master_agent() -> MagicMock:
    """Mock MasterAgent olusturur."""
    agent = MagicMock()
    agent.run = AsyncMock(
        return_value=TaskResult(success=True, message="gorev tamamlandi")
    )
    return agent


def _make_submission(
    description: str = "test gorev",
    risk: str = "low",
    urgency: str = "low",
    target_agent: str | None = None,
    source: str = "api",
    depends_on: list[str] | None = None,
    max_retries: int | None = None,
) -> TaskSubmission:
    """Test icin TaskSubmission olusturur."""
    return TaskSubmission(
        description=description,
        risk=risk,
        urgency=urgency,
        target_agent=target_agent,
        source=source,
        depends_on=depends_on or [],
        max_retries=max_retries,
    )


# === Fixtures ===


@pytest.fixture
def mock_long_term() -> MagicMock:
    """Mock LongTermMemory."""
    return _make_mock_long_term()


@pytest.fixture
def mock_short_term() -> MagicMock:
    """Mock ShortTermMemory."""
    return _make_mock_short_term()


@pytest.fixture
def mock_semantic() -> MagicMock:
    """Mock SemanticMemory."""
    return _make_mock_semantic()


@pytest.fixture
def mock_telegram() -> MagicMock:
    """Mock TelegramBot."""
    return _make_mock_telegram()


@pytest.fixture
def mock_master() -> MagicMock:
    """Mock MasterAgent."""
    return _make_mock_master_agent()


@pytest.fixture
def task_manager(
    mock_master: MagicMock,
    mock_long_term: MagicMock,
    mock_short_term: MagicMock,
    mock_semantic: MagicMock,
    mock_telegram: MagicMock,
) -> TaskManager:
    """Tam yapilandirilmis TaskManager."""
    return TaskManager(
        master_agent=mock_master,
        long_term=mock_long_term,
        short_term=mock_short_term,
        semantic=mock_semantic,
        telegram_bot=mock_telegram,
        max_retries=2,
        max_concurrent=3,
    )


@pytest.fixture
def minimal_manager(mock_master: MagicMock, mock_long_term: MagicMock) -> TaskManager:
    """Redis/Qdrant/Telegram olmadan minimal TaskManager."""
    return TaskManager(
        master_agent=mock_master,
        long_term=mock_long_term,
        short_term=None,
        semantic=None,
        telegram_bot=None,
        max_retries=1,
        max_concurrent=2,
    )


# === TestPydanticModels ===


class TestTaskPriority:
    """TaskPriority enum testleri."""

    def test_priority_values(self) -> None:
        """Oncelik degerleri dogru siralanir."""
        assert TaskPriority.CRITICAL < TaskPriority.HIGH
        assert TaskPriority.HIGH < TaskPriority.MEDIUM
        assert TaskPriority.MEDIUM < TaskPriority.LOW
        assert TaskPriority.LOW < TaskPriority.BACKGROUND

    def test_priority_int_values(self) -> None:
        """Int degerleri beklenildigi gibi."""
        assert TaskPriority.CRITICAL == 1
        assert TaskPriority.HIGH == 2
        assert TaskPriority.MEDIUM == 3
        assert TaskPriority.LOW == 4
        assert TaskPriority.BACKGROUND == 5


class TestTaskSubmission:
    """TaskSubmission model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler dogru."""
        sub = TaskSubmission(description="test")
        assert sub.risk == "low"
        assert sub.urgency == "low"
        assert sub.target_agent is None
        assert sub.source == "api"
        assert sub.metadata == {}
        assert sub.depends_on == []
        assert sub.max_retries is None

    def test_full_creation(self) -> None:
        """Tum alanlar ile olusturma."""
        sub = TaskSubmission(
            description="acil gorev",
            risk="high",
            urgency="high",
            target_agent="SecurityAgent",
            source="telegram",
            metadata={"chat_id": "123"},
            depends_on=["dep-1"],
            max_retries=5,
        )
        assert sub.description == "acil gorev"
        assert sub.risk == "high"
        assert sub.target_agent == "SecurityAgent"
        assert sub.metadata == {"chat_id": "123"}
        assert sub.depends_on == ["dep-1"]
        assert sub.max_retries == 5


class TestQueuedTask:
    """QueuedTask model testleri."""

    def test_lt_by_priority(self) -> None:
        """Dusuk priority degeri once gelir."""
        now = datetime.now(timezone.utc)
        high = QueuedTask(
            id="1", priority=TaskPriority.CRITICAL,
            submission=_make_submission(), created_at=now,
        )
        low = QueuedTask(
            id="2", priority=TaskPriority.LOW,
            submission=_make_submission(), created_at=now,
        )
        assert high < low
        assert not low < high

    def test_lt_same_priority_by_time(self) -> None:
        """Ayni oncelikte eski gorev once gelir."""
        from datetime import timedelta

        earlier = datetime(2026, 1, 1, tzinfo=timezone.utc)
        later = earlier + timedelta(hours=1)

        first = QueuedTask(
            id="1", priority=TaskPriority.MEDIUM,
            submission=_make_submission(), created_at=earlier,
        )
        second = QueuedTask(
            id="2", priority=TaskPriority.MEDIUM,
            submission=_make_submission(), created_at=later,
        )
        assert first < second

    def test_default_retry_count(self) -> None:
        """Retry sayaci 0'dan baslar."""
        q = QueuedTask(
            id="1", priority=TaskPriority.LOW,
            submission=_make_submission(),
        )
        assert q.retry_count == 0


class TestTaskMetrics:
    """TaskMetrics model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan metrikler sifir."""
        m = TaskMetrics()
        assert m.total_submitted == 0
        assert m.success_rate == 0.0
        assert m.by_agent == {}
        assert m.by_status == {}

    def test_custom_values(self) -> None:
        """Ozel degerlerle olusturma."""
        m = TaskMetrics(
            total_submitted=10,
            total_completed=7,
            total_failed=3,
            success_rate=0.7,
            by_agent={"SecurityAgent": 5},
        )
        assert m.total_submitted == 10
        assert m.success_rate == 0.7
        assert m.by_agent["SecurityAgent"] == 5


# === TestActionPriorityMap ===


class TestActionPriorityMap:
    """Aksiyon-oncelik esleme testleri."""

    def test_immediate_maps_to_critical(self) -> None:
        assert _ACTION_PRIORITY_MAP[ActionType.IMMEDIATE] == TaskPriority.CRITICAL

    def test_auto_fix_maps_to_high(self) -> None:
        assert _ACTION_PRIORITY_MAP[ActionType.AUTO_FIX] == TaskPriority.HIGH

    def test_notify_maps_to_medium(self) -> None:
        assert _ACTION_PRIORITY_MAP[ActionType.NOTIFY] == TaskPriority.MEDIUM

    def test_log_maps_to_low(self) -> None:
        assert _ACTION_PRIORITY_MAP[ActionType.LOG] == TaskPriority.LOW


# === TestTaskManagerInit ===


class TestTaskManagerInit:
    """TaskManager baslatma testleri."""

    def test_init_with_all_params(self, task_manager: TaskManager) -> None:
        """Tum parametrelerle baslatma."""
        assert task_manager.master_agent is not None
        assert task_manager.long_term is not None
        assert task_manager.short_term is not None
        assert task_manager.semantic is not None
        assert task_manager.telegram_bot is not None
        assert task_manager.max_retries == 2
        assert task_manager._running is False

    def test_init_minimal(self, minimal_manager: TaskManager) -> None:
        """Minimal parametrelerle baslatma."""
        assert minimal_manager.short_term is None
        assert minimal_manager.semantic is None
        assert minimal_manager.telegram_bot is None
        assert minimal_manager.max_retries == 1

    def test_init_counters_zero(self, task_manager: TaskManager) -> None:
        """Sayaclar sifirdan baslar."""
        assert task_manager._counters["submitted"] == 0
        assert task_manager._counters["completed"] == 0
        assert task_manager._counters["failed"] == 0
        assert task_manager._counters["cancelled"] == 0

    def test_init_empty_collections(self, task_manager: TaskManager) -> None:
        """Koleksiyonlar bos baslar."""
        assert task_manager._active_tasks == {}
        assert task_manager._dependencies == {}
        assert task_manager._dependents == {}
        assert task_manager._scheduled_tasks == {}
        assert task_manager._queue.qsize() == 0


# === TestCalculatePriority ===


class TestCalculatePriority:
    """Oncelik hesaplama testleri."""

    def test_high_high_is_critical(self, task_manager: TaskManager) -> None:
        """Yuksek risk + yuksek aciliyet = CRITICAL."""
        p = task_manager._calculate_priority("high", "high")
        assert p == TaskPriority.CRITICAL

    def test_high_medium_is_high(self, task_manager: TaskManager) -> None:
        """Yuksek risk + orta aciliyet = HIGH (AUTO_FIX)."""
        p = task_manager._calculate_priority("high", "medium")
        assert p == TaskPriority.HIGH

    def test_medium_low_is_medium(self, task_manager: TaskManager) -> None:
        """Orta risk + dusuk aciliyet = MEDIUM (NOTIFY)."""
        p = task_manager._calculate_priority("medium", "low")
        assert p == TaskPriority.MEDIUM

    def test_low_low_is_low(self, task_manager: TaskManager) -> None:
        """Dusuk risk + dusuk aciliyet = LOW (LOG)."""
        p = task_manager._calculate_priority("low", "low")
        assert p == TaskPriority.LOW

    def test_invalid_risk_falls_back_to_medium(self, task_manager: TaskManager) -> None:
        """Gecersiz risk degeri MEDIUM'a duser."""
        p = task_manager._calculate_priority("invalid", "low")
        assert p == TaskPriority.MEDIUM

    def test_invalid_urgency_falls_back_to_medium(self, task_manager: TaskManager) -> None:
        """Gecersiz aciliyet degeri MEDIUM'a duser."""
        p = task_manager._calculate_priority("low", "invalid")
        assert p == TaskPriority.MEDIUM


# === TestSubmitTask ===


class TestSubmitTask:
    """Gorev gonderme testleri."""

    @pytest.mark.asyncio
    async def test_submit_creates_db_record(self, task_manager: TaskManager) -> None:
        """Submit islemi PostgreSQL'e kayit olusturur."""
        sub = _make_submission(description="sunucu kontrolu")
        result = await task_manager.submit_task(sub)

        assert result.id == "test-id-1234"
        task_manager.long_term.create_task.assert_awaited_once()
        call_arg = task_manager.long_term.create_task.call_args[0][0]
        assert isinstance(call_arg, TaskCreate)
        assert call_arg.description == "sunucu kontrolu"

    @pytest.mark.asyncio
    async def test_submit_caches_to_redis(self, task_manager: TaskManager) -> None:
        """Submit islemi Redis'e cache kaydeder."""
        sub = _make_submission()
        await task_manager.submit_task(sub)

        task_manager.short_term.store_task_status.assert_awaited()

    @pytest.mark.asyncio
    async def test_submit_adds_to_queue(self, task_manager: TaskManager) -> None:
        """Submit islemi kuyruga gorev ekler."""
        sub = _make_submission()
        await task_manager.submit_task(sub)

        assert task_manager._queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_submit_increments_counter(self, task_manager: TaskManager) -> None:
        """Submit islemi sayaci arttirir."""
        sub = _make_submission()
        await task_manager.submit_task(sub)

        assert task_manager._counters["submitted"] == 1

    @pytest.mark.asyncio
    async def test_submit_empty_description_raises(self, task_manager: TaskManager) -> None:
        """Bos aciklama ValueError firlatir."""
        sub = _make_submission(description="   ")
        with pytest.raises(ValueError, match="bos olamaz"):
            await task_manager.submit_task(sub)

    @pytest.mark.asyncio
    async def test_submit_without_redis(self, minimal_manager: TaskManager) -> None:
        """Redis olmadan submit islemi basarili."""
        sub = _make_submission()
        result = await minimal_manager.submit_task(sub)

        assert result.id == "test-id-1234"
        assert minimal_manager._queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_submit_preserves_target_agent(self, task_manager: TaskManager) -> None:
        """Hedef agent korunur."""
        sub = _make_submission(target_agent="SecurityAgent")
        await task_manager.submit_task(sub)

        call_arg = task_manager.long_term.create_task.call_args[0][0]
        assert call_arg.agent == "SecurityAgent"

    @pytest.mark.asyncio
    async def test_submit_with_high_risk_gets_critical_priority(
        self, task_manager: TaskManager
    ) -> None:
        """Yuksek risk + yuksek aciliyet gorevi CRITICAL oncelik alir."""
        sub = _make_submission(risk="high", urgency="high")
        await task_manager.submit_task(sub)

        queued = await task_manager._queue.get()
        assert queued.priority == TaskPriority.CRITICAL

    @pytest.mark.asyncio
    async def test_submit_multiple_tasks_queued_in_order(
        self, task_manager: TaskManager
    ) -> None:
        """Birden fazla gorev oncelik sirasinda kuyruga eklenir."""
        # Dusuk oncelik
        task_manager.long_term.create_task = AsyncMock(
            return_value=_make_task_response(task_id="low-1")
        )
        await task_manager.submit_task(_make_submission(risk="low", urgency="low"))

        # Yuksek oncelik
        task_manager.long_term.create_task = AsyncMock(
            return_value=_make_task_response(task_id="high-1")
        )
        await task_manager.submit_task(_make_submission(risk="high", urgency="high"))

        # PriorityQueue yuksek onceligi once verir
        first = await task_manager._queue.get()
        assert first.id == "high-1"
        assert first.priority == TaskPriority.CRITICAL


# === TestGetTask ===


class TestGetTask:
    """Gorev sorgulama testleri."""

    @pytest.mark.asyncio
    async def test_get_existing_task(self, task_manager: TaskManager) -> None:
        """Mevcut gorev PostgreSQL'den getirilir."""
        expected = _make_task_response(task_id="abc-123")
        task_manager.long_term.get_task = AsyncMock(return_value=expected)

        result = await task_manager.get_task("abc-123")

        assert result is not None
        assert result.id == "abc-123"
        task_manager.long_term.get_task.assert_awaited_once_with("abc-123")

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, task_manager: TaskManager) -> None:
        """Mevcut olmayan gorev None dondurur."""
        task_manager.long_term.get_task = AsyncMock(return_value=None)

        result = await task_manager.get_task("yok-id")
        assert result is None


# === TestListTasks ===


class TestListTasks:
    """Gorev listeleme testleri."""

    @pytest.mark.asyncio
    async def test_list_delegates_to_long_term(self, task_manager: TaskManager) -> None:
        """list_tasks LongTermMemory'ye delege eder."""
        expected = [_make_task_response()]
        task_manager.long_term.list_tasks = AsyncMock(return_value=expected)

        result = await task_manager.list_tasks(status="pending", agent="SecurityAgent")

        assert len(result) == 1
        task_manager.long_term.list_tasks.assert_awaited_once_with(
            status="pending", agent="SecurityAgent", limit=50, offset=0,
        )

    @pytest.mark.asyncio
    async def test_list_empty(self, task_manager: TaskManager) -> None:
        """Bos sonuc listesi doner."""
        task_manager.long_term.list_tasks = AsyncMock(return_value=[])

        result = await task_manager.list_tasks()
        assert result == []


# === TestCancelTask ===


class TestCancelTask:
    """Gorev iptal testleri."""

    @pytest.mark.asyncio
    async def test_cancel_pending_task(self, task_manager: TaskManager) -> None:
        """PENDING gorev iptal edilir."""
        task_manager.long_term.get_task = AsyncMock(
            return_value=_make_task_response(status=TaskStatus.PENDING)
        )
        cancelled = _make_task_response(status=TaskStatus.CANCELLED)
        task_manager.long_term.update_task = AsyncMock(return_value=cancelled)

        result = await task_manager.cancel_task("test-id-1234")

        assert result is not None
        assert result.status == TaskStatus.CANCELLED
        task_manager.long_term.update_task.assert_awaited_once()
        assert task_manager._counters["cancelled"] == 1

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, task_manager: TaskManager) -> None:
        """Mevcut olmayan gorev None dondurur."""
        task_manager.long_term.get_task = AsyncMock(return_value=None)

        result = await task_manager.cancel_task("yok-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_already_completed(self, task_manager: TaskManager) -> None:
        """Tamamlanmis gorev iptal edilmez, oldugu gibi doner."""
        completed = _make_task_response(status=TaskStatus.COMPLETED)
        task_manager.long_term.get_task = AsyncMock(return_value=completed)

        result = await task_manager.cancel_task("test-id-1234")

        assert result is not None
        assert result.status == TaskStatus.COMPLETED
        task_manager.long_term.update_task.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cancel_already_failed(self, task_manager: TaskManager) -> None:
        """Basarisiz gorev iptal edilmez."""
        failed = _make_task_response(status=TaskStatus.FAILED)
        task_manager.long_term.get_task = AsyncMock(return_value=failed)

        result = await task_manager.cancel_task("test-id-1234")
        assert result.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_cancel_clears_redis_cache(self, task_manager: TaskManager) -> None:
        """Iptal edilen gorev Redis'ten silinir."""
        task_manager.long_term.get_task = AsyncMock(
            return_value=_make_task_response(status=TaskStatus.PENDING)
        )
        task_manager.long_term.update_task = AsyncMock(
            return_value=_make_task_response(status=TaskStatus.CANCELLED)
        )

        await task_manager.cancel_task("test-id-1234")

        task_manager.short_term.delete_task_status.assert_awaited()


# === TestRetryTask ===


class TestRetryTask:
    """Gorev tekrar deneme testleri."""

    @pytest.mark.asyncio
    async def test_retry_failed_task(self, task_manager: TaskManager) -> None:
        """FAILED gorev tekrar kuyruga eklenir."""
        task_manager.long_term.get_task = AsyncMock(
            return_value=_make_task_response(status=TaskStatus.FAILED)
        )
        task_manager.long_term.update_task = AsyncMock(
            return_value=_make_task_response(status=TaskStatus.PENDING)
        )

        result = await task_manager.retry_task("test-id-1234")

        assert result is not None
        assert result.status == TaskStatus.PENDING
        assert task_manager._queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_retry_nonexistent_task(self, task_manager: TaskManager) -> None:
        """Mevcut olmayan gorev None dondurur."""
        task_manager.long_term.get_task = AsyncMock(return_value=None)

        result = await task_manager.retry_task("yok-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_retry_non_failed_task(self, task_manager: TaskManager) -> None:
        """FAILED olmayan gorev tekrar denmez, oldugu gibi doner."""
        running = _make_task_response(status=TaskStatus.RUNNING)
        task_manager.long_term.get_task = AsyncMock(return_value=running)

        result = await task_manager.retry_task("test-id-1234")

        assert result.status == TaskStatus.RUNNING
        assert task_manager._queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_retry_resets_db_fields(self, task_manager: TaskManager) -> None:
        """Retry DB alanlarini sifirlar."""
        task_manager.long_term.get_task = AsyncMock(
            return_value=_make_task_response(
                status=TaskStatus.FAILED,
                result_message="hata oldu",
                result_success=False,
            )
        )
        task_manager.long_term.update_task = AsyncMock(
            return_value=_make_task_response(status=TaskStatus.PENDING)
        )

        await task_manager.retry_task("test-id-1234")

        update_call = task_manager.long_term.update_task.call_args
        updates = update_call[0][1]
        assert updates["status"] == TaskStatus.PENDING.value
        assert updates["result_message"] is None
        assert updates["result_success"] is None
        assert updates["completed_at"] is None


# === TestScheduling ===


class TestScheduling:
    """Zamanlama testleri."""

    @pytest.mark.asyncio
    async def test_schedule_task(self, task_manager: TaskManager) -> None:
        """Gorev zamanlanir ve kayit oluşturulur."""
        sub = _make_submission(description="periyodik kontrol")
        sid = await task_manager.schedule_task(sub, "every_30m")

        assert sid in task_manager._scheduled_tasks
        sched = task_manager._scheduled_tasks[sid]
        assert sched["interval_seconds"] == 1800
        assert sched["last_run"] is None

    @pytest.mark.asyncio
    async def test_schedule_with_custom_id(self, task_manager: TaskManager) -> None:
        """Ozel ID ile zamanlama."""
        sub = _make_submission()
        sid = await task_manager.schedule_task(sub, "every_1h", schedule_id="custom-id")

        assert sid == "custom-id"
        assert "custom-id" in task_manager._scheduled_tasks

    @pytest.mark.asyncio
    async def test_unschedule_existing(self, task_manager: TaskManager) -> None:
        """Mevcut zamanlamayi iptal eder."""
        sub = _make_submission()
        sid = await task_manager.schedule_task(sub, "every_5m")

        result = await task_manager.unschedule_task(sid)

        assert result is True
        assert sid not in task_manager._scheduled_tasks

    @pytest.mark.asyncio
    async def test_unschedule_nonexistent(self, task_manager: TaskManager) -> None:
        """Mevcut olmayan zamanlamayi iptal False dondurur."""
        result = await task_manager.unschedule_task("yok-id")
        assert result is False


class TestParseInterval:
    """Zamanlama ifadesi parse testleri."""

    def test_minutes(self) -> None:
        """Dakika bazli ifade."""
        assert TaskManager._parse_interval("every_30m") == 1800

    def test_hours(self) -> None:
        """Saat bazli ifade."""
        assert TaskManager._parse_interval("every_2h") == 7200

    def test_single_minute(self) -> None:
        """Tek dakika."""
        assert TaskManager._parse_interval("every_1m") == 60

    def test_case_insensitive(self) -> None:
        """Buyuk/kucuk harf duyarsiz."""
        assert TaskManager._parse_interval("Every_10M") == 600

    def test_invalid_format_raises(self) -> None:
        """Gecersiz format ValueError firlatir."""
        with pytest.raises(ValueError, match="Gecersiz"):
            TaskManager._parse_interval("cron_invalid")

    def test_no_prefix_raises(self) -> None:
        """Prefix olmadan ValueError firlatir."""
        with pytest.raises(ValueError, match="Gecersiz"):
            TaskManager._parse_interval("30m")


# === TestGetMetrics ===


class TestGetMetrics:
    """Metrik sorgulama testleri."""

    @pytest.mark.asyncio
    async def test_initial_metrics_zero(self, task_manager: TaskManager) -> None:
        """Baslangic metrikleri sifir."""
        metrics = await task_manager.get_metrics()

        assert metrics.total_submitted == 0
        assert metrics.total_completed == 0
        assert metrics.total_failed == 0
        assert metrics.queue_size == 0
        assert metrics.active_count == 0
        assert metrics.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_metrics_after_submit(self, task_manager: TaskManager) -> None:
        """Submit sonrasi metrikler guncellenir."""
        await task_manager.submit_task(_make_submission())
        metrics = await task_manager.get_metrics()

        assert metrics.total_submitted == 1
        assert metrics.queue_size == 1

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self, task_manager: TaskManager) -> None:
        """Basari orani dogru hesaplanir."""
        task_manager._counters["completed"] = 7
        task_manager._counters["failed"] = 3

        metrics = await task_manager.get_metrics()
        assert metrics.success_rate == pytest.approx(0.7)

    @pytest.mark.asyncio
    async def test_success_rate_no_division_by_zero(
        self, task_manager: TaskManager
    ) -> None:
        """Hic gorev yokken sifira bolme olmaz."""
        metrics = await task_manager.get_metrics()
        assert metrics.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_metrics_by_status(self, task_manager: TaskManager) -> None:
        """Durum bazli sayilar doğru."""
        task_manager._counters["completed"] = 5
        task_manager._counters["failed"] = 2
        task_manager._counters["cancelled"] = 1

        metrics = await task_manager.get_metrics()

        assert metrics.by_status["completed"] == 5
        assert metrics.by_status["failed"] == 2
        assert metrics.by_status["cancelled"] == 1

    @pytest.mark.asyncio
    async def test_metrics_by_agent(self, task_manager: TaskManager) -> None:
        """Agent bazli sayilar dogru."""
        task_manager._agent_counters = {"SecurityAgent": 3, "CodingAgent": 5}

        metrics = await task_manager.get_metrics()

        assert metrics.by_agent["SecurityAgent"] == 3
        assert metrics.by_agent["CodingAgent"] == 5


# === TestSearchSimilarTasks ===


class TestSearchSimilarTasks:
    """Semantik arama testleri."""

    @pytest.mark.asyncio
    async def test_search_with_semantic(self, task_manager: TaskManager) -> None:
        """Qdrant varken arama sonuc dondurur."""
        mock_result = MagicMock()
        mock_result.id = "r-1"
        mock_result.text = "sunucu kontrolu"
        mock_result.score = 0.85
        mock_result.metadata = {"agent": "SecurityAgent"}
        task_manager.semantic.search = AsyncMock(return_value=[mock_result])

        results = await task_manager.search_similar_tasks("sunucu")

        assert len(results) == 1
        assert results[0]["id"] == "r-1"
        assert results[0]["score"] == 0.85

    @pytest.mark.asyncio
    async def test_search_without_semantic(self, minimal_manager: TaskManager) -> None:
        """Qdrant yokken bos liste doner."""
        results = await minimal_manager.search_similar_tasks("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_error_returns_empty(self, task_manager: TaskManager) -> None:
        """Qdrant hatasi bos liste dondurur."""
        task_manager.semantic.search = AsyncMock(
            side_effect=Exception("baglanti hatasi")
        )

        results = await task_manager.search_similar_tasks("test")
        assert results == []


# === TestGetQueueSnapshot ===


class TestGetQueueSnapshot:
    """Kuyruk snapshot testleri."""

    @pytest.mark.asyncio
    async def test_empty_queue_snapshot(self, task_manager: TaskManager) -> None:
        """Bos kuyruk bos liste dondurur."""
        snapshot = await task_manager.get_queue_snapshot()
        assert snapshot == []

    @pytest.mark.asyncio
    async def test_snapshot_after_submit(self, task_manager: TaskManager) -> None:
        """Submit sonrasi kuyruk snapshot gorev icerir."""
        await task_manager.submit_task(_make_submission(description="test gorev"))

        snapshot = await task_manager.get_queue_snapshot()

        assert len(snapshot) == 1
        assert snapshot[0]["id"] == "test-id-1234"
        assert "description" in snapshot[0]
        assert "priority" in snapshot[0]


# === TestExecuteTask ===


class TestExecuteTask:
    """Gorev calistirma testleri."""

    @pytest.mark.asyncio
    async def test_execute_success(self, task_manager: TaskManager) -> None:
        """Basarili gorev calistirma."""
        queued = QueuedTask(
            id="exec-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(description="basarili gorev"),
        )

        await task_manager._execute_task(queued)

        # MasterAgent.run cagirildi
        task_manager.master_agent.run.assert_awaited_once()
        call_arg = task_manager.master_agent.run.call_args[0][0]
        assert call_arg["description"] == "basarili gorev"

        # DB RUNNING'e guncellendi
        task_manager.long_term.update_task.assert_awaited()

    @pytest.mark.asyncio
    async def test_execute_failure_with_retries(
        self, task_manager: TaskManager
    ) -> None:
        """Basarisiz gorev retry kuyruguna eklenir."""
        task_manager.master_agent.run = AsyncMock(
            return_value=TaskResult(success=False, message="hata")
        )

        queued = QueuedTask(
            id="fail-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(max_retries=1),
            retry_count=0,
        )
        task_manager._running = True

        with patch("app.core.task_manager.asyncio.sleep", new_callable=AsyncMock):
            await task_manager._execute_task(queued)

        # Retry: kuyruga tekrar eklendi
        assert task_manager._queue.qsize() == 1
        requeued = await task_manager._queue.get()
        assert requeued.retry_count == 1

    @pytest.mark.asyncio
    async def test_execute_failure_max_retries_exceeded(
        self, task_manager: TaskManager
    ) -> None:
        """Max retry asildiginda gorev FAILED olarak kaydedilir."""
        task_manager.master_agent.run = AsyncMock(
            return_value=TaskResult(success=False, message="kalici hata")
        )

        queued = QueuedTask(
            id="final-fail-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(max_retries=1),
            retry_count=1,  # Zaten 1 kez denenmis
        )

        await task_manager._execute_task(queued)

        # DB FAILED olarak guncellendi
        update_calls = task_manager.long_term.update_task.call_args_list
        failed_call = [
            c for c in update_calls
            if c[0][1].get("status") == TaskStatus.FAILED.value
        ]
        assert len(failed_call) > 0

        # Telegram bildirim gonderildi
        task_manager.telegram_bot.send_buttons.assert_awaited_once()

        # Sayac arttirildi
        assert task_manager._counters["failed"] == 1

    @pytest.mark.asyncio
    async def test_execute_master_agent_exception(
        self, task_manager: TaskManager
    ) -> None:
        """MasterAgent exception atarsa TaskResult(success=False) olusturulur."""
        task_manager.master_agent.run = AsyncMock(
            side_effect=RuntimeError("beklenmeyen patlama")
        )

        # max_retries=2 (task_manager fixture), retry_count=2 -> final fail
        queued = QueuedTask(
            id="exc-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(),
            retry_count=2,
        )

        await task_manager._execute_task(queued)

        # Final fail islenir
        assert task_manager._counters["failed"] == 1

    @pytest.mark.asyncio
    async def test_execute_updates_redis_to_running(
        self, task_manager: TaskManager
    ) -> None:
        """Calistirma sirasinda Redis RUNNING'e guncellenir."""
        queued = QueuedTask(
            id="redis-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(),
        )

        await task_manager._execute_task(queued)

        # store_task_status en az bir kez RUNNING ile cagirildi
        calls = task_manager.short_term.store_task_status.call_args_list
        running_calls = [
            c for c in calls
            if c[0][1].get("status") == TaskStatus.RUNNING.value
        ]
        assert len(running_calls) >= 1


# === TestOnTaskSuccess ===


class TestOnTaskSuccess:
    """Basarili gorev sonrasi islem testleri."""

    @pytest.mark.asyncio
    async def test_success_updates_db(self, task_manager: TaskManager) -> None:
        """Basarili gorev DB'yi COMPLETED olarak gunceller."""
        queued = QueuedTask(
            id="ok-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(target_agent="CodingAgent"),
        )
        result = TaskResult(success=True, message="tamam")

        await task_manager._on_task_success(queued, result)

        task_manager.long_term.update_task.assert_awaited_once_with(
            "ok-1",
            {
                "status": TaskStatus.COMPLETED.value,
                "result_message": "tamam",
                "result_success": True,
            },
        )

    @pytest.mark.asyncio
    async def test_success_stores_semantic(self, task_manager: TaskManager) -> None:
        """Basarili gorev Qdrant'a kaydedilir."""
        queued = QueuedTask(
            id="sem-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(description="analiz gorevi"),
        )
        result = TaskResult(success=True, message="analiz tamamlandi")

        await task_manager._on_task_success(queued, result)

        task_manager.semantic.store.assert_awaited_once()
        call_kwargs = task_manager.semantic.store.call_args[1]
        assert call_kwargs["collection"] == "task_history"
        assert "analiz gorevi" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_success_increments_counters(self, task_manager: TaskManager) -> None:
        """Basarili gorev sayaclari gunceller."""
        queued = QueuedTask(
            id="cnt-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(target_agent="SecurityAgent"),
        )
        result = TaskResult(success=True, message="ok")

        await task_manager._on_task_success(queued, result)

        assert task_manager._counters["completed"] == 1
        assert task_manager._agent_counters["SecurityAgent"] == 1

    @pytest.mark.asyncio
    async def test_success_agent_counter_accumulates(
        self, task_manager: TaskManager
    ) -> None:
        """Ayni agent icin sayac birikir."""
        for _ in range(3):
            queued = QueuedTask(
                id=f"acc-{_}",
                priority=TaskPriority.LOW,
                submission=_make_submission(target_agent="CodingAgent"),
            )
            await task_manager._on_task_success(
                queued, TaskResult(success=True, message="ok")
            )

        assert task_manager._agent_counters["CodingAgent"] == 3

    @pytest.mark.asyncio
    async def test_success_without_semantic(self, minimal_manager: TaskManager) -> None:
        """Qdrant olmadan basarili gorev hatasz calisir."""
        queued = QueuedTask(
            id="no-sem-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(),
        )
        result = TaskResult(success=True, message="ok")

        await minimal_manager._on_task_success(queued, result)

        assert minimal_manager._counters["completed"] == 1


# === TestOnTaskFailure ===


class TestOnTaskFailure:
    """Basarisiz gorev sonrasi islem testleri."""

    @pytest.mark.asyncio
    async def test_failure_retries(self, task_manager: TaskManager) -> None:
        """Retry limiti icinde tekrar kuyruga eklenir."""
        queued = QueuedTask(
            id="retry-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(max_retries=2),
            retry_count=0,
        )
        result = TaskResult(success=False, message="gecici hata")
        task_manager._running = True

        with patch("app.core.task_manager.asyncio.sleep", new_callable=AsyncMock):
            await task_manager._on_task_failure(queued, result)

        assert task_manager._queue.qsize() == 1
        assert queued.retry_count == 1

    @pytest.mark.asyncio
    async def test_failure_final_updates_db(self, task_manager: TaskManager) -> None:
        """Max retry sonrasi DB FAILED olarak guncellenir."""
        queued = QueuedTask(
            id="final-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(max_retries=1),
            retry_count=1,
        )
        result = TaskResult(success=False, message="kalici hata", errors=["err1"])

        await task_manager._on_task_failure(queued, result)

        task_manager.long_term.update_task.assert_awaited()
        update_args = task_manager.long_term.update_task.call_args[0]
        assert update_args[1]["status"] == TaskStatus.FAILED.value
        assert update_args[1]["result_success"] is False

    @pytest.mark.asyncio
    async def test_failure_final_notifies_telegram(
        self, task_manager: TaskManager
    ) -> None:
        """Max retry sonrasi Telegram bildirim gonderilir."""
        # task_manager.max_retries=2, retry_count=2 -> final fail
        queued = QueuedTask(
            id="notify-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(),
            retry_count=2,
        )
        result = TaskResult(success=False, message="hata oldu")

        await task_manager._on_task_failure(queued, result)

        task_manager.telegram_bot.send_buttons.assert_awaited_once()
        call_kwargs = task_manager.telegram_bot.send_buttons.call_args[1]
        assert "BASARISIZ" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_failure_final_without_telegram(
        self, minimal_manager: TaskManager
    ) -> None:
        """Telegram olmadan final basarisizlik hatasz calisir."""
        # minimal_manager.max_retries=1, retry_count=1 -> final fail
        queued = QueuedTask(
            id="no-tg-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(),
            retry_count=1,
        )
        result = TaskResult(success=False, message="hata")

        await minimal_manager._on_task_failure(queued, result)

        assert minimal_manager._counters["failed"] == 1

    @pytest.mark.asyncio
    async def test_failure_stores_semantic(self, task_manager: TaskManager) -> None:
        """Final basarisizlik Qdrant'a kaydedilir."""
        # task_manager.max_retries=2, retry_count=2 -> final fail
        queued = QueuedTask(
            id="sem-fail-1",
            priority=TaskPriority.LOW,
            submission=_make_submission(description="test gorevi"),
            retry_count=2,
        )
        result = TaskResult(success=False, message="hata oldu")

        await task_manager._on_task_failure(queued, result)

        task_manager.semantic.store.assert_awaited_once()
        call_kwargs = task_manager.semantic.store.call_args[1]
        assert "BASARISIZ" in call_kwargs["text"]


# === TestDependencies ===


class TestDependencies:
    """Gorev bagimlillik testleri."""

    @pytest.mark.asyncio
    async def test_no_dependencies(self, task_manager: TaskManager) -> None:
        """Bagimlilik yoksa False doner."""
        result = await task_manager._register_dependencies("t-1", [])
        assert result is False

    @pytest.mark.asyncio
    async def test_all_dependencies_completed(self, task_manager: TaskManager) -> None:
        """Tum bagimliliklar tamamlanmissa False doner."""
        task_manager.long_term.get_task = AsyncMock(
            return_value=_make_task_response(status=TaskStatus.COMPLETED)
        )

        result = await task_manager._register_dependencies("t-2", ["dep-1"])
        assert result is False

    @pytest.mark.asyncio
    async def test_unmet_dependencies_tracked(self, task_manager: TaskManager) -> None:
        """Karsilanmamis bagimliliklar izlenir."""
        # dep-1 pending, dep-2 tamamlanmis
        task_manager.long_term.get_task = AsyncMock(
            side_effect=[
                _make_task_response(task_id="dep-1", status=TaskStatus.PENDING),
                _make_task_response(task_id="dep-2", status=TaskStatus.COMPLETED),
            ]
        )

        result = await task_manager._register_dependencies("t-3", ["dep-1", "dep-2"])

        assert result is True
        assert "dep-1" in task_manager._dependencies["t-3"]
        assert "dep-2" not in task_manager._dependencies["t-3"]
        assert "t-3" in task_manager._dependents["dep-1"]

    @pytest.mark.asyncio
    async def test_submit_with_unmet_dependency_not_queued(
        self, task_manager: TaskManager
    ) -> None:
        """Karsilanmamis bagimliligi olan gorev kuyruga eklenmez."""
        # Bagimli gorev henuz tamamlanmamis
        task_manager.long_term.get_task = AsyncMock(
            return_value=_make_task_response(task_id="dep-1", status=TaskStatus.RUNNING)
        )

        sub = _make_submission(depends_on=["dep-1"])
        await task_manager.submit_task(sub)

        # Kuyrukta olmamali
        assert task_manager._queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_unblock_dependents(self, task_manager: TaskManager) -> None:
        """Tamamlanan bagimlilik sonrasi gorev kuyruga eklenir."""
        # Senaryo: t-2 -> t-1 bekliyor, t-1 tamamlaninca t-2 acilir
        queued_data = QueuedTask(
            id="t-2",
            priority=TaskPriority.MEDIUM,
            submission=_make_submission(description="bagimli gorev"),
        ).model_dump(mode="json")

        task_manager._dependencies["t-2"] = {"t-1"}
        task_manager._dependents["t-1"] = {"t-2"}
        task_manager.short_term.get_task_status = AsyncMock(return_value=queued_data)

        await task_manager._unblock_dependents("t-1")

        assert "t-2" not in task_manager._dependencies
        assert "t-1" not in task_manager._dependents
        assert task_manager._queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_cascade_cancel(self, task_manager: TaskManager) -> None:
        """Basarisiz gorev bagimli gorevleri iptal eder."""
        task_manager._dependencies["t-2"] = {"t-1"}
        task_manager._dependents["t-1"] = {"t-2"}

        await task_manager._cascade_cancel("t-1")

        task_manager.long_term.update_task.assert_awaited()
        update_call = task_manager.long_term.update_task.call_args
        assert update_call[0][0] == "t-2"
        assert update_call[0][1]["status"] == TaskStatus.CANCELLED.value
        assert task_manager._counters["cancelled"] == 1


# === TestCrashRecovery ===


class TestCrashRecovery:
    """Crash recovery testleri."""

    @pytest.mark.asyncio
    async def test_recover_running_tasks(self, task_manager: TaskManager) -> None:
        """RUNNING gorevler PENDING'e dusurulur."""
        running_task = _make_task_response(task_id="r-1", status=TaskStatus.RUNNING)
        task_manager.long_term.list_tasks = AsyncMock(
            side_effect=[
                [running_task],  # RUNNING sorgusunun sonucu
                [_make_task_response(task_id="r-1", status=TaskStatus.PENDING)],  # PENDING sorgusunun sonucu
            ]
        )

        await task_manager._recover_tasks()

        # RUNNING -> PENDING guncellendi
        task_manager.long_term.update_task.assert_awaited_once_with(
            "r-1", {"status": TaskStatus.PENDING.value}
        )
        # Kuyruga eklendi
        assert task_manager._queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_recover_pending_tasks(self, task_manager: TaskManager) -> None:
        """PENDING gorevler kuyruga eklenir."""
        pending = _make_task_response(
            task_id="p-1",
            status=TaskStatus.PENDING,
            risk="high",
            urgency="high",
        )
        task_manager.long_term.list_tasks = AsyncMock(
            side_effect=[
                [],         # RUNNING: yok
                [pending],  # PENDING: 1 gorev
            ]
        )

        await task_manager._recover_tasks()

        assert task_manager._queue.qsize() == 1
        queued = await task_manager._queue.get()
        assert queued.id == "p-1"
        assert queued.priority == TaskPriority.CRITICAL
        assert queued.submission.source == "recovery"

    @pytest.mark.asyncio
    async def test_recover_empty_db(self, task_manager: TaskManager) -> None:
        """DB'de tamamlanmamis gorev yoksa kuyruk bos kalir."""
        task_manager.long_term.list_tasks = AsyncMock(return_value=[])

        await task_manager._recover_tasks()

        assert task_manager._queue.qsize() == 0


# === TestCacheHelpers ===


class TestCacheHelpers:
    """Redis cache yardimci metot testleri."""

    @pytest.mark.asyncio
    async def test_cache_task_status(self, task_manager: TaskManager) -> None:
        """Redis'e gorev durumu kaydedilir."""
        await task_manager._cache_task_status("t-1", {"status": "pending"})

        task_manager.short_term.store_task_status.assert_awaited_once_with(
            "t-1", {"status": "pending"}
        )

    @pytest.mark.asyncio
    async def test_cache_task_status_no_redis(
        self, minimal_manager: TaskManager
    ) -> None:
        """Redis yokken cache yazma sessizce atlanir."""
        await minimal_manager._cache_task_status("t-1", {"status": "pending"})
        # Hata firlatmamali

    @pytest.mark.asyncio
    async def test_cache_task_status_redis_error(
        self, task_manager: TaskManager
    ) -> None:
        """Redis hatasi sessizce loglanir."""
        task_manager.short_term.store_task_status = AsyncMock(
            side_effect=Exception("Redis baglanti hatasi")
        )

        await task_manager._cache_task_status("t-1", {"status": "pending"})
        # Hata firlatmamali

    @pytest.mark.asyncio
    async def test_delete_task_cache(self, task_manager: TaskManager) -> None:
        """Redis'ten gorev durumu silinir."""
        await task_manager._delete_task_cache("t-1")

        # Hem task hem queued key silinir
        assert task_manager.short_term.delete_task_status.await_count == 2

    @pytest.mark.asyncio
    async def test_delete_task_cache_no_redis(
        self, minimal_manager: TaskManager
    ) -> None:
        """Redis yokken silme sessizce atlanir."""
        await minimal_manager._delete_task_cache("t-1")


# === TestSemanticHelpers ===


class TestSemanticHelpers:
    """Qdrant yardimci metot testleri."""

    @pytest.mark.asyncio
    async def test_store_semantic(self, task_manager: TaskManager) -> None:
        """Qdrant'a semantik kayit yapilir."""
        await task_manager._store_semantic(
            task_id="t-1",
            description="sunucu kontrolu",
            result_message="basarili",
            metadata={"agent": "SecurityAgent"},
        )

        task_manager.semantic.store.assert_awaited_once()
        call_kwargs = task_manager.semantic.store.call_args[1]
        assert call_kwargs["collection"] == "task_history"
        assert call_kwargs["point_id"] == "t-1"
        assert call_kwargs["source"] == "task_manager"
        assert "sunucu kontrolu -> basarili" == call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_store_semantic_no_qdrant(
        self, minimal_manager: TaskManager
    ) -> None:
        """Qdrant yokken sessizce atlanir."""
        await minimal_manager._store_semantic(
            task_id="t-1",
            description="test",
            result_message="ok",
            metadata={},
        )

    @pytest.mark.asyncio
    async def test_store_semantic_error(self, task_manager: TaskManager) -> None:
        """Qdrant hatasi sessizce loglanir."""
        task_manager.semantic.store = AsyncMock(
            side_effect=Exception("Qdrant hatasi")
        )

        await task_manager._store_semantic(
            task_id="t-1",
            description="test",
            result_message="ok",
            metadata={},
        )
        # Hata firlatmamali


# === TestTelegramNotification ===


class TestTelegramNotification:
    """Telegram bildirim testleri."""

    @pytest.mark.asyncio
    async def test_notify_on_failure(self, task_manager: TaskManager) -> None:
        """Basarisiz gorevde butonlu Telegram mesaji gonderilir."""
        await task_manager._notify_telegram(
            task_id="t-1",
            description="sunucu kontrolu",
            status="failed",
            message="baglanti hatasi",
        )

        task_manager.telegram_bot.send_buttons.assert_awaited_once()
        call_kwargs = task_manager.telegram_bot.send_buttons.call_args[1]
        assert "BASARISIZ" in call_kwargs["text"]
        assert len(call_kwargs["buttons"]) == 2

    @pytest.mark.asyncio
    async def test_notify_on_high_risk_success(
        self, task_manager: TaskManager
    ) -> None:
        """Yuksek riskli basarili gorevde mesaj gonderilir."""
        await task_manager._notify_telegram(
            task_id="t-1",
            description="kritik islem",
            status="completed",
            message="tamamlandi",
            risk="high",
        )

        task_manager.telegram_bot.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_notify_on_low_risk_success(
        self, task_manager: TaskManager
    ) -> None:
        """Dusuk riskli basarili gorevde bildirim gonderilmez."""
        await task_manager._notify_telegram(
            task_id="t-1",
            description="rutin kontrol",
            status="completed",
            message="tamamlandi",
            risk="low",
        )

        task_manager.telegram_bot.send_message.assert_not_awaited()
        task_manager.telegram_bot.send_buttons.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_notify_without_telegram(
        self, minimal_manager: TaskManager
    ) -> None:
        """Telegram bot yokken bildirim hatasz atlanir."""
        await minimal_manager._notify_telegram(
            task_id="t-1",
            description="test",
            status="failed",
            message="hata",
        )

    @pytest.mark.asyncio
    async def test_notify_telegram_error_handled(
        self, task_manager: TaskManager
    ) -> None:
        """Telegram hatasi sessizce loglanir."""
        task_manager.telegram_bot.send_buttons = AsyncMock(
            side_effect=Exception("Telegram hatasi")
        )

        await task_manager._notify_telegram(
            task_id="t-1",
            description="test",
            status="failed",
            message="hata",
        )
        # Hata firlatmamali


# === TestLifecycle ===


class TestLifecycle:
    """TaskManager yasam dongusu testleri."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self, task_manager: TaskManager) -> None:
        """Start _running'i True yapar."""
        await task_manager.start()

        assert task_manager._running is True
        assert task_manager._worker_task is not None
        assert task_manager._scheduler_task is not None

        await task_manager.stop()

    @pytest.mark.asyncio
    async def test_stop_sets_not_running(self, task_manager: TaskManager) -> None:
        """Stop _running'i False yapar."""
        await task_manager.start()
        await task_manager.stop()

        assert task_manager._running is False

    @pytest.mark.asyncio
    async def test_start_recovers_tasks(self, task_manager: TaskManager) -> None:
        """Start crash recovery calistirir."""
        pending = _make_task_response(task_id="rec-1", status=TaskStatus.PENDING)
        task_manager.long_term.list_tasks = AsyncMock(
            side_effect=[
                [],         # RUNNING: yok
                [pending],  # PENDING: 1 gorev
            ]
        )

        await task_manager.start()

        assert task_manager._queue.qsize() == 1

        await task_manager.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_background_tasks(
        self, task_manager: TaskManager
    ) -> None:
        """Stop arkaplan dongulerini iptal eder."""
        await task_manager.start()

        worker = task_manager._worker_task
        scheduler = task_manager._scheduler_task

        await task_manager.stop()

        assert worker.done()
        assert scheduler.done()


# === TestCoreExport ===


class TestCoreExport:
    """app.core export testleri."""

    def test_task_manager_export(self) -> None:
        """TaskManager core'dan export edilir."""
        from app.core import TaskManager

        assert TaskManager is not None

    def test_task_manager_is_correct_class(self) -> None:
        """Export edilen sinif dogru."""
        from app.core import TaskManager as ExportedTM
        from app.core.task_manager import TaskManager as DirectTM

        assert ExportedTM is DirectTM
