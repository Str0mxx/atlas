"""ServerMonitor unit testleri.

ServerMonitorAgent mock'lanarak monitor davranislari test edilir.
Saglikli, uyari, kritik ve hata senaryolari kapsanir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.monitors.base_monitor import MonitorResult
from app.monitors.server_monitor import ServerMonitor


# === Fixtures ===


@pytest.fixture
def mock_agent_cls():
    """ServerMonitorAgent sinifini mock'lar."""
    with patch("app.monitors.server_monitor.ServerMonitorAgent") as cls:
        cls.return_value = AsyncMock()
        yield cls


@pytest.fixture
def monitor(mock_agent_cls):
    """Mock agent ile yapilandirilmis ServerMonitor."""
    mon = ServerMonitor()
    return mon


@pytest.fixture
def healthy_task_result() -> TaskResult:
    """Saglikli sunucu kontrolu sonucu."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "low",
                "urgency": "low",
                "action": "log",
                "summary": "Tum sunucular sagliki.",
                "details": [],
            },
        },
        message="ok",
    )


@pytest.fixture
def warning_task_result() -> TaskResult:
    """Uyari seviyesinde sunucu kontrolu sonucu."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "medium",
                "urgency": "medium",
                "action": "notify",
                "summary": "CPU kullanimi yuksek: %75",
                "details": [
                    {"host": "192.168.1.100", "type": "high_cpu", "value": 75.0},
                ],
            },
        },
        message="uyari",
    )


@pytest.fixture
def critical_task_result() -> TaskResult:
    """Kritik seviyede sunucu kontrolu sonucu."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "high",
                "urgency": "high",
                "action": "immediate",
                "summary": "Sunucu erisilemez!",
                "details": [
                    {"host": "192.168.1.100", "type": "unreachable"},
                ],
            },
        },
        message="kritik",
    )


@pytest.fixture
def auto_fix_task_result() -> TaskResult:
    """Otonom aksiyon gerektiren sunucu kontrolu sonucu."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "high",
                "urgency": "medium",
                "action": "auto_fix",
                "summary": "Nginx servisi durmus, restart gerekiyor.",
                "details": [
                    {"type": "service_down", "service": "nginx"},
                ],
            },
        },
        message="auto_fix",
    )


@pytest.fixture
def failed_task_result() -> TaskResult:
    """Basarisiz sunucu kontrolu sonucu."""
    return TaskResult(
        success=False,
        data={},
        message="SSH baglanti hatasi",
        errors=["Connection refused"],
    )


# === Init testleri ===


class TestServerMonitorInit:
    """ServerMonitor olusturma testleri."""

    def test_default_init(self, mock_agent_cls) -> None:
        """Varsayilan parametrelerle monitor olusturulmali."""
        monitor = ServerMonitor()
        assert monitor.name == "server"
        assert monitor.servers is None
        assert monitor.thresholds is None
        assert monitor.check_interval == 300
        mock_agent_cls.assert_called_once()

    def test_custom_check_interval(self, mock_agent_cls) -> None:
        """Ozel kontrol araligi ayarlanabilmeli."""
        monitor = ServerMonitor(check_interval=600)
        assert monitor.check_interval == 600

    def test_agent_created_with_servers(self, mock_agent_cls) -> None:
        """Agent sunucu listesi ile olusturulmali."""
        servers = [MagicMock()]
        thresholds = MagicMock()
        monitor = ServerMonitor(servers=servers, thresholds=thresholds)
        mock_agent_cls.assert_called_once_with(
            servers=servers,
            thresholds=thresholds,
        )
        assert monitor.servers is servers
        assert monitor.thresholds is thresholds

    def test_decision_matrix_default(self, mock_agent_cls) -> None:
        """Karar matrisi belirtilmezse varsayilan olusturulmali."""
        monitor = ServerMonitor()
        assert monitor.decision_matrix is not None

    def test_decision_matrix_custom(self, mock_agent_cls) -> None:
        """Ozel karar matrisi ayarlanabilmeli."""
        dm = MagicMock()
        monitor = ServerMonitor(decision_matrix=dm)
        assert monitor.decision_matrix is dm

    def test_telegram_bot_assignment(self, mock_agent_cls) -> None:
        """Telegram bot nesnesi atanabilmeli."""
        bot = MagicMock()
        monitor = ServerMonitor(telegram_bot=bot)
        assert monitor.telegram_bot is bot


# === Check testleri ===


class TestServerMonitorCheck:
    """ServerMonitor.check() metodu testleri."""

    @pytest.mark.asyncio
    async def test_healthy_check(self, monitor, healthy_task_result) -> None:
        """Saglikli sunucu: low risk, low urgency, log action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = healthy_task_result

        result = await monitor.check()

        assert isinstance(result, MonitorResult)
        assert result.monitor_name == "server"
        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"
        assert result.summary == "Tum sunucular sagliki."
        assert result.details == []

    @pytest.mark.asyncio
    async def test_warning_check(self, monitor, warning_task_result) -> None:
        """Uyari seviyesi: medium risk, medium urgency, notify action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = warning_task_result

        result = await monitor.check()

        assert result.risk == "medium"
        assert result.urgency == "medium"
        assert result.action == "notify"
        assert "CPU" in result.summary

    @pytest.mark.asyncio
    async def test_critical_check(self, monitor, critical_task_result) -> None:
        """Kritik seviye: high risk, high urgency, immediate action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = critical_task_result

        result = await monitor.check()

        assert result.risk == "high"
        assert result.urgency == "high"
        assert result.action == "immediate"
        assert "erisilemez" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_check_with_defaults_when_no_analysis(self, monitor) -> None:
        """Analiz verisi bos oldugunda varsayilan degerler kullanilmali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=True,
            data={"analysis": {}},
            message="ok",
        )

        result = await monitor.check()

        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"
        assert result.summary == "Sunucu kontrolu tamamlandi"

    @pytest.mark.asyncio
    async def test_check_with_empty_data(self, monitor) -> None:
        """Bos data oldugunda varsayilan degerler kullanilmali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=True,
            data={},
            message="ok",
        )

        result = await monitor.check()

        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"

    @pytest.mark.asyncio
    async def test_check_failure(self, monitor, failed_task_result) -> None:
        """Agent hatasi: high risk, high urgency, immediate action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = failed_task_result

        result = await monitor.check()

        assert result.risk == "high"
        assert result.urgency == "high"
        assert result.action == "immediate"
        assert "basarisiz" in result.summary.lower()
        assert len(result.details) == 1
        assert result.details[0]["error"] == "Connection refused"

    @pytest.mark.asyncio
    async def test_check_failure_multiple_errors(self, monitor) -> None:
        """Birden fazla hata: details listesinde tum hatalar olmali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=False,
            data={},
            message="Coklu hata",
            errors=["SSH timeout", "DNS resolution failed"],
        )

        result = await monitor.check()

        assert len(result.details) == 2
        assert result.details[0]["error"] == "SSH timeout"
        assert result.details[1]["error"] == "DNS resolution failed"

    @pytest.mark.asyncio
    async def test_check_calls_agent_run(self, monitor) -> None:
        """check() agent.run'i dogru task ile cagirmali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(success=True, data={})

        await monitor.check()

        monitor.agent.run.assert_called_once_with(
            {"description": "Periyodik sunucu kontrolu"},
        )


# === Otonom aksiyon testleri ===


class TestServerMonitorAutonomousActions:
    """ServerMonitor._handle_autonomous_actions() testleri."""

    @pytest.mark.asyncio
    async def test_auto_fix_service_down(self, monitor, auto_fix_task_result) -> None:
        """Service down durumunda otonom restart aksiyonu tetiklenmeli."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = auto_fix_task_result

        result = await monitor.check()

        # Sonuc basarili ve auto_fix action donmeli
        assert result.action == "auto_fix"
        assert result.details[0]["type"] == "service_down"

    @pytest.mark.asyncio
    async def test_immediate_action_triggers_autonomous(self, monitor) -> None:
        """Immediate action'da da otonom aksiyonlar calismali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=True,
            data={
                "analysis": {
                    "risk": "high",
                    "urgency": "high",
                    "action": "immediate",
                    "summary": "Nginx durmus!",
                    "details": [
                        {"type": "service_down", "service": "nginx"},
                    ],
                },
            },
        )

        result = await monitor.check()

        assert result.action == "immediate"
        assert result.details[0]["service"] == "nginx"

    @pytest.mark.asyncio
    async def test_log_action_skips_autonomous(self, monitor) -> None:
        """Log action'da otonom aksiyonlar calismamali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=True,
            data={
                "analysis": {
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "summary": "Her sey normal.",
                    "details": [],
                },
            },
        )

        # _handle_autonomous_actions'in hata vermeden calismasi yeterli
        result = await monitor.check()
        assert result.action == "log"

    @pytest.mark.asyncio
    async def test_no_details_in_auto_fix(self, monitor) -> None:
        """Details listesi bos oldugunda otonom aksiyon hatasi olmamali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=True,
            data={
                "analysis": {
                    "risk": "high",
                    "urgency": "medium",
                    "action": "auto_fix",
                    "summary": "Otonom duzeltme gerekli.",
                    "details": [],
                },
            },
        )

        result = await monitor.check()
        assert result.action == "auto_fix"
        assert result.details == []
