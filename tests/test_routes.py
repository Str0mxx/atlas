"""API routes endpoint'leri unit testleri.

FastAPI TestClient ile gorev CRUD, agent listesi,
metrikler ve semantik arama test edilir.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.routes import router
from app.main import app
from app.models.task import TaskResponse, TaskStatus


@pytest.fixture
def client() -> TestClient:
    """FastAPI test istemcisi."""
    return TestClient(app, raise_server_exceptions=False)


def _make_task_response(**overrides) -> TaskResponse:
    """Test icin TaskResponse olusturur."""
    defaults = {
        "id": "test-task-id-1234",
        "description": "Test gorevi",
        "status": TaskStatus.PENDING,
        "agent": None,
        "risk": "low",
        "urgency": "low",
        "result_message": None,
        "result_success": None,
        "confidence": None,
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "completed_at": None,
    }
    defaults.update(overrides)
    return TaskResponse(**defaults)


# === POST /api/tasks testleri ===


class TestCreateTask:
    """Gorev olusturma endpoint testleri."""

    def test_create_task_success(self, client: TestClient) -> None:
        """Basarili gorev olusturma (202 Accepted)."""
        mock_response = _make_task_response()

        mock_tm = AsyncMock()
        mock_tm.submit_task = AsyncMock(return_value=mock_response)

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.post(
                "/api/tasks",
                json={"description": "Test gorevi", "risk": "low"},
            )

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["task_id"] == "test-task-id-1234"
        assert data["task_status"] == "pending"

    def test_create_task_no_task_manager(self, client: TestClient) -> None:
        """TaskManager hazir degilse 503 doner."""
        with patch.object(app.state, "task_manager", None, create=True):
            resp = client.post(
                "/api/tasks",
                json={"description": "Test gorevi"},
            )

        assert resp.status_code == 503

    def test_create_task_with_target_agent(self, client: TestClient) -> None:
        """target_agent parametresi ile gorev olusturma."""
        mock_response = _make_task_response(agent="research")

        mock_tm = AsyncMock()
        mock_tm.submit_task = AsyncMock(return_value=mock_response)

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.post(
                "/api/tasks",
                json={
                    "description": "Arastirma gorevi",
                    "target_agent": "research",
                    "risk": "medium",
                    "urgency": "high",
                },
            )

        assert resp.status_code == 202
        # submit_task'a gonderilen TaskSubmission'i dogrula
        call_args = mock_tm.submit_task.call_args[0][0]
        assert call_args.target_agent == "research"
        assert call_args.risk == "medium"
        assert call_args.urgency == "high"


# === GET /api/tasks testleri ===


class TestListTasks:
    """Gorev listeleme endpoint testleri."""

    def test_list_tasks_empty(self, client: TestClient) -> None:
        """Bos gorev listesi."""
        mock_tm = AsyncMock()
        mock_tm.list_tasks = AsyncMock(return_value=[])

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.get("/api/tasks")

        assert resp.status_code == 200
        data = resp.json()
        assert data["tasks"] == []
        assert data["total"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_list_tasks_with_results(self, client: TestClient) -> None:
        """Sonuc iceren gorev listesi."""
        tasks = [
            _make_task_response(id="task-1", description="Gorev 1"),
            _make_task_response(id="task-2", description="Gorev 2"),
        ]

        mock_tm = AsyncMock()
        mock_tm.list_tasks = AsyncMock(return_value=tasks)

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.get("/api/tasks")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["tasks"]) == 2

    def test_list_tasks_with_status_filter(self, client: TestClient) -> None:
        """Durum filtresi ile listeleme."""
        mock_tm = AsyncMock()
        mock_tm.list_tasks = AsyncMock(return_value=[])

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.get("/api/tasks?status=completed")

        assert resp.status_code == 200
        mock_tm.list_tasks.assert_called_once_with(
            status="completed", agent=None, limit=50, offset=0,
        )

    def test_list_tasks_invalid_status(self, client: TestClient) -> None:
        """Gecersiz durum filtresi 400 doner."""
        mock_tm = AsyncMock()

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.get("/api/tasks?status=invalid_status")

        assert resp.status_code == 400

    def test_list_tasks_with_pagination(self, client: TestClient) -> None:
        """Sayfalama parametreleri."""
        mock_tm = AsyncMock()
        mock_tm.list_tasks = AsyncMock(return_value=[])

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.get("/api/tasks?limit=10&offset=20")

        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 10
        assert data["offset"] == 20
        mock_tm.list_tasks.assert_called_once_with(
            status=None, agent=None, limit=10, offset=20,
        )

    def test_list_tasks_with_agent_filter(self, client: TestClient) -> None:
        """Agent filtresi ile listeleme."""
        mock_tm = AsyncMock()
        mock_tm.list_tasks = AsyncMock(return_value=[])

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.get("/api/tasks?agent=research")

        assert resp.status_code == 200
        mock_tm.list_tasks.assert_called_once_with(
            status=None, agent="research", limit=50, offset=0,
        )

    def test_list_tasks_no_task_manager(self, client: TestClient) -> None:
        """TaskManager hazir degilse 503."""
        with patch.object(app.state, "task_manager", None, create=True):
            resp = client.get("/api/tasks")

        assert resp.status_code == 503


# === GET /api/tasks/{task_id} testleri ===


class TestGetTask:
    """Tek gorev getirme endpoint testleri."""

    def test_get_task_found(self, client: TestClient) -> None:
        """Gorev bulundu."""
        task = _make_task_response(description="Detay testi")

        mock_tm = AsyncMock()
        mock_tm.get_task = AsyncMock(return_value=task)

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.get("/api/tasks/test-task-id-1234")

        assert resp.status_code == 200
        data = resp.json()
        assert data["task"]["id"] == "test-task-id-1234"
        assert data["task"]["description"] == "Detay testi"

    def test_get_task_not_found(self, client: TestClient) -> None:
        """Gorev bulunamadi (404)."""
        mock_tm = AsyncMock()
        mock_tm.get_task = AsyncMock(return_value=None)

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.get("/api/tasks/nonexistent-id")

        assert resp.status_code == 404


# === POST /api/tasks/{task_id}/cancel testleri ===


class TestCancelTask:
    """Gorev iptal endpoint testleri."""

    def test_cancel_task_success(self, client: TestClient) -> None:
        """Basarili gorev iptali."""
        cancelled = _make_task_response(status=TaskStatus.CANCELLED)

        mock_tm = AsyncMock()
        mock_tm.cancel_task = AsyncMock(return_value=cancelled)

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.post("/api/tasks/test-task-id-1234/cancel")

        assert resp.status_code == 200
        data = resp.json()
        assert data["task"]["status"] == "cancelled"

    def test_cancel_task_not_found(self, client: TestClient) -> None:
        """Iptal edilecek gorev bulunamadi (404)."""
        mock_tm = AsyncMock()
        mock_tm.cancel_task = AsyncMock(return_value=None)

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.post("/api/tasks/nonexistent-id/cancel")

        assert resp.status_code == 404


# === POST /api/tasks/{task_id}/retry testleri ===


class TestRetryTask:
    """Gorev tekrar deneme endpoint testleri."""

    def test_retry_task_success(self, client: TestClient) -> None:
        """Basarili tekrar deneme."""
        retried = _make_task_response(status=TaskStatus.PENDING)

        mock_tm = AsyncMock()
        mock_tm.retry_task = AsyncMock(return_value=retried)

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.post("/api/tasks/test-task-id-1234/retry")

        assert resp.status_code == 200
        data = resp.json()
        assert data["task"]["status"] == "pending"

    def test_retry_task_not_found(self, client: TestClient) -> None:
        """Tekrar denenecek gorev bulunamadi (404)."""
        mock_tm = AsyncMock()
        mock_tm.retry_task = AsyncMock(return_value=None)

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.post("/api/tasks/nonexistent-id/retry")

        assert resp.status_code == 404


# === GET /api/agents testleri ===


class TestListAgents:
    """Agent listesi endpoint testleri."""

    def test_list_agents_with_agents(self, client: TestClient) -> None:
        """Kayitli agentlar ile liste."""
        mock_agents = [
            {"name": "research", "status": "idle", "capabilities": ["web_search"]},
            {"name": "security", "status": "idle", "capabilities": ["scan"]},
        ]

        mock_master = MagicMock()
        mock_master.get_registered_agents.return_value = mock_agents

        with patch.object(app.state, "master_agent", mock_master, create=True):
            resp = client.get("/api/agents")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["agents"]) == 2
        assert data["agents"][0]["name"] == "research"

    def test_list_agents_no_master(self, client: TestClient) -> None:
        """Master Agent hazir degilse bos liste."""
        with patch.object(app.state, "master_agent", None, create=True):
            resp = client.get("/api/agents")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["agents"] == []


# === GET /api/metrics testleri ===


class TestGetMetrics:
    """Metrik endpoint testleri."""

    def test_get_metrics_success(self, client: TestClient) -> None:
        """Basarili metrik getirme."""
        from app.core.task_manager import TaskMetrics

        mock_metrics = TaskMetrics(
            total_submitted=100,
            total_completed=80,
            total_failed=15,
            total_cancelled=5,
            queue_size=3,
            active_count=2,
            success_rate=0.842,
            by_agent={"research": 40, "security": 30, "coding": 10},
            by_status={"pending": 3, "running": 2, "completed": 80, "failed": 15},
        )

        mock_tm = AsyncMock()
        mock_tm.get_metrics = AsyncMock(return_value=mock_metrics)

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.get("/api/metrics")

        assert resp.status_code == 200
        data = resp.json()
        metrics = data["metrics"]
        assert metrics["total_submitted"] == 100
        assert metrics["total_completed"] == 80
        assert metrics["success_rate"] == pytest.approx(0.842)
        assert metrics["by_agent"]["research"] == 40

    def test_get_metrics_no_task_manager(self, client: TestClient) -> None:
        """TaskManager hazir degilse 503."""
        with patch.object(app.state, "task_manager", None, create=True):
            resp = client.get("/api/metrics")

        assert resp.status_code == 503


# === POST /api/memory/search testleri ===


class TestMemorySearch:
    """Semantik arama endpoint testleri."""

    def test_search_success(self, client: TestClient) -> None:
        """Basarili semantik arama."""
        mock_results = [
            {"id": "task-1", "description": "Benzer gorev", "score": 0.85},
            {"id": "task-2", "description": "Diger gorev", "score": 0.72},
        ]

        mock_tm = AsyncMock()
        mock_tm.search_similar_tasks = AsyncMock(return_value=mock_results)

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.post(
                "/api/memory/search",
                json={"query": "web scraping gorevi", "limit": 5},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert data["query"] == "web scraping gorevi"
        assert len(data["results"]) == 2

    def test_search_empty_results(self, client: TestClient) -> None:
        """Sonucsuz arama."""
        mock_tm = AsyncMock()
        mock_tm.search_similar_tasks = AsyncMock(return_value=[])

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.post(
                "/api/memory/search",
                json={"query": "var olmayan gorev"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["results"] == []

    def test_search_with_custom_params(self, client: TestClient) -> None:
        """Ozel parametreli arama."""
        mock_tm = AsyncMock()
        mock_tm.search_similar_tasks = AsyncMock(return_value=[])

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.post(
                "/api/memory/search",
                json={
                    "query": "test sorgusu",
                    "limit": 10,
                    "score_threshold": 0.5,
                },
            )

        assert resp.status_code == 200
        mock_tm.search_similar_tasks.assert_called_once_with(
            query="test sorgusu", limit=10, score_threshold=0.5,
        )

    def test_search_service_error(self, client: TestClient) -> None:
        """Semantik hafiza hata durumu (503)."""
        mock_tm = AsyncMock()
        mock_tm.search_similar_tasks = AsyncMock(
            side_effect=Exception("Qdrant baglanti hatasi"),
        )

        with patch.object(app.state, "task_manager", mock_tm, create=True):
            resp = client.post(
                "/api/memory/search",
                json={"query": "test"},
            )

        assert resp.status_code == 503

    def test_search_no_task_manager(self, client: TestClient) -> None:
        """TaskManager hazir degilse 503."""
        with patch.object(app.state, "task_manager", None, create=True):
            resp = client.post(
                "/api/memory/search",
                json={"query": "test"},
            )

        assert resp.status_code == 503
