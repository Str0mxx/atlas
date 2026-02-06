"""LongTermMemory (PostgreSQL) unit testleri.

SQLAlchemy session mock'lanarak uzun sureli hafiza islemleri test edilir.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.memory.long_term import LongTermMemory
from app.models.agent_log import AgentLogCreate
from app.models.decision import DecisionCreate
from app.models.task import TaskCreate, TaskStatus


# === Fixtures ===


@pytest.fixture
def memory() -> LongTermMemory:
    """LongTermMemory instance'i."""
    return LongTermMemory()


def _make_mock_session() -> AsyncMock:
    """Ortak mock session olusturur."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    # async context manager destegi
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


def _make_task_mock(**kwargs) -> MagicMock:
    """Test icin TaskRecord mock'u olusturur."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": "task-001",
        "description": "Test gorevi",
        "status": TaskStatus.PENDING.value,
        "agent": None,
        "risk": "low",
        "urgency": "low",
        "result_message": None,
        "result_success": None,
        "confidence": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


def _make_decision_mock(**kwargs) -> MagicMock:
    """Test icin DecisionRecord mock'u olusturur."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": "dec-001",
        "task_id": "task-001",
        "risk": "high",
        "urgency": "high",
        "action": "immediate",
        "confidence": 0.9,
        "reason": "Test karari",
        "created_at": now,
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


def _make_agent_log_mock(**kwargs) -> MagicMock:
    """Test icin AgentLogRecord mock'u olusturur."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": "log-001",
        "agent_name": "test_agent",
        "action": "execute",
        "details": "Test detaylari",
        "status": "running",
        "created_at": now,
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


# === Gorev CRUD testleri ===


class TestTaskCRUD:
    """Gorev CRUD islemleri testleri."""

    @pytest.mark.asyncio
    async def test_create_task(self, memory: LongTermMemory) -> None:
        """Yeni gorev olusturulabilmeli."""
        mock_session = _make_mock_session()
        task_mock = _make_task_mock()

        # refresh cagirildiginda record'un alanlarini set et
        async def mock_refresh(record):
            record.id = task_mock.id
            record.description = task_mock.description
            record.status = task_mock.status
            record.agent = task_mock.agent
            record.risk = task_mock.risk
            record.urgency = task_mock.urgency
            record.result_message = task_mock.result_message
            record.result_success = task_mock.result_success
            record.confidence = task_mock.confidence
            record.created_at = task_mock.created_at
            record.updated_at = task_mock.updated_at
            record.completed_at = task_mock.completed_at

        mock_session.refresh = mock_refresh

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.create_task(
                TaskCreate(description="Test gorevi", risk="low", urgency="low")
            )

        assert result.description == "Test gorevi"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_task_found(self, memory: LongTermMemory) -> None:
        """Mevcut gorev ID ile getirilmeli."""
        mock_session = _make_mock_session()
        task_mock = _make_task_mock()
        mock_session.get = AsyncMock(return_value=task_mock)

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.get_task("task-001")

        assert result is not None
        assert result.id == "task-001"
        assert result.description == "Test gorevi"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, memory: LongTermMemory) -> None:
        """Olmayan gorev icin None donmeli."""
        mock_session = _make_mock_session()
        mock_session.get = AsyncMock(return_value=None)

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.get_task("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_task(self, memory: LongTermMemory) -> None:
        """Gorev guncellenmeli."""
        mock_session = _make_mock_session()
        task_mock = _make_task_mock()
        mock_session.get = AsyncMock(return_value=task_mock)

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.update_task(
                "task-001",
                {"status": TaskStatus.RUNNING.value, "agent": "server_monitor"},
            )

        assert result is not None
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, memory: LongTermMemory) -> None:
        """Olmayan gorev guncellendiginde None donmeli."""
        mock_session = _make_mock_session()
        mock_session.get = AsyncMock(return_value=None)

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.update_task("nonexistent", {"status": "running"})

        assert result is None

    @pytest.mark.asyncio
    async def test_update_task_sets_completed_at(self, memory: LongTermMemory) -> None:
        """Gorev completed olursa completed_at otomatik set edilmeli."""
        mock_session = _make_mock_session()
        task_mock = _make_task_mock()
        task_mock.completed_at = None
        mock_session.get = AsyncMock(return_value=task_mock)

        with patch.object(memory, "_get_session", return_value=mock_session):
            await memory.update_task("task-001", {"status": TaskStatus.COMPLETED.value})

        assert task_mock.completed_at is not None

    @pytest.mark.asyncio
    async def test_list_tasks(self, memory: LongTermMemory) -> None:
        """Gorevler listelenebilmeli."""
        mock_session = _make_mock_session()
        records = [_make_task_mock(id="t1"), _make_task_mock(id="t2")]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = records
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.list_tasks(limit=10)

        assert len(result) == 2
        assert result[0].id == "t1"

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, memory: LongTermMemory) -> None:
        """Filtreli gorev listesi calismali."""
        mock_session = _make_mock_session()
        records = [_make_task_mock(id="t1", agent="server_monitor")]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = records
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.list_tasks(
                status=TaskStatus.PENDING.value,
                agent="server_monitor",
                limit=5,
            )

        assert len(result) == 1
        mock_session.execute.assert_awaited_once()


# === Karar gecmisi testleri ===


class TestDecisionCRUD:
    """Karar kayit islemleri testleri."""

    @pytest.mark.asyncio
    async def test_save_decision(self, memory: LongTermMemory) -> None:
        """Karar kaydedilebilmeli."""
        mock_session = _make_mock_session()
        decision_mock = _make_decision_mock()

        async def mock_refresh(record):
            record.id = decision_mock.id
            record.task_id = decision_mock.task_id
            record.risk = decision_mock.risk
            record.urgency = decision_mock.urgency
            record.action = decision_mock.action
            record.confidence = decision_mock.confidence
            record.reason = decision_mock.reason
            record.created_at = decision_mock.created_at

        mock_session.refresh = mock_refresh

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.save_decision(
                DecisionCreate(
                    task_id="task-001",
                    risk="high",
                    urgency="high",
                    action="immediate",
                    confidence=0.9,
                    reason="Test karari",
                )
            )

        assert result.risk == "high"
        assert result.action == "immediate"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_decisions(self, memory: LongTermMemory) -> None:
        """Karar kayitlari sorgulanabilmeli."""
        mock_session = _make_mock_session()
        records = [_make_decision_mock()]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = records
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.query_decisions(task_id="task-001")

        assert len(result) == 1
        assert result[0].task_id == "task-001"

    @pytest.mark.asyncio
    async def test_query_decisions_with_risk_filter(
        self, memory: LongTermMemory,
    ) -> None:
        """Risk filtresi ile karar sorgulama calismali."""
        mock_session = _make_mock_session()
        records = [_make_decision_mock(risk="high")]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = records
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.query_decisions(risk="high", limit=10)

        assert len(result) == 1
        assert result[0].risk == "high"


# === Agent log testleri ===


class TestAgentLogCRUD:
    """Agent log islemleri testleri."""

    @pytest.mark.asyncio
    async def test_save_agent_log(self, memory: LongTermMemory) -> None:
        """Agent log kaydedilebilmeli."""
        mock_session = _make_mock_session()
        log_mock = _make_agent_log_mock()

        async def mock_refresh(record):
            record.id = log_mock.id
            record.agent_name = log_mock.agent_name
            record.action = log_mock.action
            record.details = log_mock.details
            record.status = log_mock.status
            record.created_at = log_mock.created_at

        mock_session.refresh = mock_refresh

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.save_agent_log(
                AgentLogCreate(
                    agent_name="test_agent",
                    action="execute",
                    details="Test detaylari",
                    status="running",
                )
            )

        assert result.agent_name == "test_agent"
        assert result.action == "execute"
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_agent_logs(self, memory: LongTermMemory) -> None:
        """Agent loglari sorgulanabilmeli."""
        mock_session = _make_mock_session()
        records = [
            _make_agent_log_mock(id="log-1"),
            _make_agent_log_mock(id="log-2", action="analyze"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = records
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.query_agent_logs(agent_name="test_agent")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_query_agent_logs_with_status_filter(
        self, memory: LongTermMemory,
    ) -> None:
        """Durum filtresi ile agent log sorgulama calismali."""
        mock_session = _make_mock_session()
        records = [_make_agent_log_mock(status="error")]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = records
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(memory, "_get_session", return_value=mock_session):
            result = await memory.query_agent_logs(status="error", limit=50)

        assert len(result) == 1
        assert result[0].status == "error"


# === LongTermMemory baglanti testleri ===


class TestConnection:
    """Veritabani baglanti kontrol testleri."""

    @pytest.mark.asyncio
    async def test_get_session_raises_when_not_initialized(
        self, memory: LongTermMemory,
    ) -> None:
        """Veritabani baslatilmamissa RuntimeError firlatmali."""
        with patch("app.core.memory.long_term.db") as mock_db:
            mock_db.async_session_factory = None

            with pytest.raises(RuntimeError, match="Veritabani baslatilmamis"):
                await memory._get_session()
