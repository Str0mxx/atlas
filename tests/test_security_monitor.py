"""SecurityMonitor unit testleri.

SecurityAgent mock'lanarak guvenlik izleme davranislari test edilir.
Temiz tarama, tehdit tespiti, SSL sorunu ve otonom aksiyon senaryolari kapsanir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.monitors.base_monitor import MonitorResult
from app.monitors.security_monitor import SecurityMonitor


# === Fixtures ===


@pytest.fixture
def mock_agent_cls():
    """SecurityAgent sinifini mock'lar."""
    with patch("app.monitors.security_monitor.SecurityAgent") as cls:
        cls.return_value = AsyncMock()
        yield cls


@pytest.fixture
def monitor(mock_agent_cls):
    """Mock agent ile yapilandirilmis SecurityMonitor."""
    mon = SecurityMonitor()
    return mon


@pytest.fixture
def clean_scan_result() -> TaskResult:
    """Temiz guvenlik taramasi sonucu."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "low",
                "urgency": "low",
                "action": "log",
                "summary": "Guvenlik taramasi temiz.",
                "details": [],
            },
        },
        message="ok",
    )


@pytest.fixture
def threat_detected_result() -> TaskResult:
    """Tehdit tespiti iceren sonuc."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "high",
                "urgency": "high",
                "action": "immediate",
                "summary": "Basarisiz giris limiti asildi!",
                "details": [
                    {"type": "failed_login_threshold", "ip": "10.0.0.99", "attempts": 150},
                ],
            },
        },
        message="tehdit",
    )


@pytest.fixture
def ssl_issue_result() -> TaskResult:
    """SSL sertifika sorunu iceren sonuc."""
    return TaskResult(
        success=True,
        data={
            "analysis": {
                "risk": "high",
                "urgency": "medium",
                "action": "auto_fix",
                "summary": "SSL sertifikasi 3 gune sona eriyor.",
                "details": [
                    {"type": "ssl_expiring", "domain": "mapahealth.com", "days_left": 3},
                ],
            },
        },
        message="ssl_uyari",
    )


@pytest.fixture
def scan_failure_result() -> TaskResult:
    """Basarisiz guvenlik taramasi sonucu."""
    return TaskResult(
        success=False,
        data={},
        message="SSH baglanti hatasi",
        errors=["Permission denied"],
    )


# === Init testleri ===


class TestSecurityMonitorInit:
    """SecurityMonitor olusturma testleri."""

    def test_default_init(self, mock_agent_cls) -> None:
        """Varsayilan parametrelerle monitor olusturulmali."""
        monitor = SecurityMonitor()
        assert monitor.name == "security"
        assert monitor.servers is None
        assert monitor.scan_config is None
        assert monitor.check_interval == 3600
        mock_agent_cls.assert_called_once()

    def test_custom_check_interval(self, mock_agent_cls) -> None:
        """Ozel kontrol araligi ayarlanabilmeli."""
        monitor = SecurityMonitor(check_interval=7200)
        assert monitor.check_interval == 7200

    def test_agent_created_with_params(self, mock_agent_cls) -> None:
        """Agent sunucu ve scan_config ile olusturulmali."""
        servers = [MagicMock()]
        scan_config = MagicMock()
        monitor = SecurityMonitor(servers=servers, scan_config=scan_config)
        mock_agent_cls.assert_called_once_with(
            servers=servers,
            scan_config=scan_config,
        )
        assert monitor.servers is servers
        assert monitor.scan_config is scan_config

    def test_decision_matrix_default(self, mock_agent_cls) -> None:
        """Karar matrisi belirtilmezse varsayilan olusturulmali."""
        monitor = SecurityMonitor()
        assert monitor.decision_matrix is not None

    def test_telegram_bot_assignment(self, mock_agent_cls) -> None:
        """Telegram bot nesnesi atanabilmeli."""
        bot = MagicMock()
        monitor = SecurityMonitor(telegram_bot=bot)
        assert monitor.telegram_bot is bot


# === Check testleri ===


class TestSecurityMonitorCheck:
    """SecurityMonitor.check() metodu testleri."""

    @pytest.mark.asyncio
    async def test_clean_scan(self, monitor, clean_scan_result) -> None:
        """Temiz tarama: low risk, low urgency, log action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = clean_scan_result

        result = await monitor.check()

        assert isinstance(result, MonitorResult)
        assert result.monitor_name == "security"
        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"
        assert "temiz" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_threat_detected(self, monitor, threat_detected_result) -> None:
        """Tehdit tespiti: high risk, high urgency, immediate action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = threat_detected_result

        result = await monitor.check()

        assert result.risk == "high"
        assert result.urgency == "high"
        assert result.action == "immediate"
        assert "giris" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_ssl_issue(self, monitor, ssl_issue_result) -> None:
        """SSL sorunu: high risk, medium urgency, auto_fix action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = ssl_issue_result

        result = await monitor.check()

        assert result.risk == "high"
        assert result.urgency == "medium"
        assert result.action == "auto_fix"
        assert "ssl" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_scan_failure(self, monitor, scan_failure_result) -> None:
        """Tarama hatasi: high risk, high urgency, immediate action."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = scan_failure_result

        result = await monitor.check()

        assert result.risk == "high"
        assert result.urgency == "high"
        assert result.action == "immediate"
        assert "basarisiz" in result.summary.lower()
        assert len(result.details) == 1
        assert result.details[0]["error"] == "Permission denied"

    @pytest.mark.asyncio
    async def test_check_with_defaults_when_no_analysis(self, monitor) -> None:
        """Analiz verisi bos oldugunda varsayilan degerler kullanilmali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=True,
            data={"analysis": {}},
        )

        result = await monitor.check()

        assert result.risk == "low"
        assert result.urgency == "low"
        assert result.action == "log"
        assert result.summary == "Guvenlik taramasi tamamlandi"

    @pytest.mark.asyncio
    async def test_check_calls_agent_run(self, monitor) -> None:
        """check() agent.run'i dogru task ile cagirmali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(success=True, data={})

        await monitor.check()

        monitor.agent.run.assert_called_once_with(
            {"description": "Periyodik guvenlik taramasi"},
        )

    @pytest.mark.asyncio
    async def test_scan_failure_multiple_errors(self, monitor) -> None:
        """Birden fazla hata: details listesinde tum hatalar olmali."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = TaskResult(
            success=False,
            data={},
            message="Coklu hata",
            errors=["Permission denied", "Host unreachable"],
        )

        result = await monitor.check()

        assert len(result.details) == 2
        assert result.details[0]["error"] == "Permission denied"
        assert result.details[1]["error"] == "Host unreachable"


# === Otonom aksiyon testleri ===


class TestSecurityMonitorAutonomousActions:
    """SecurityMonitor._handle_autonomous_actions() testleri."""

    @pytest.mark.asyncio
    async def test_ip_blocking_on_failed_login(
        self, monitor, threat_detected_result,
    ) -> None:
        """Basarisiz giris esigi asildiginda IP engelleme aksiyonu tetiklenmeli."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = threat_detected_result

        result = await monitor.check()

        assert result.action == "immediate"
        assert result.details[0]["type"] == "failed_login_threshold"
        assert result.details[0]["ip"] == "10.0.0.99"

    @pytest.mark.asyncio
    async def test_ssl_renewal_on_expiry(self, monitor, ssl_issue_result) -> None:
        """SSL sona ermek uzereyken yenileme aksiyonu tetiklenmeli."""
        monitor.agent = AsyncMock()
        monitor.agent.run.return_value = ssl_issue_result

        result = await monitor.check()

        assert result.action == "auto_fix"
        assert result.details[0]["type"] == "ssl_expiring"
        assert result.details[0]["domain"] == "mapahealth.com"

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
                    "summary": "Guvenlik taramasi temiz.",
                    "details": [],
                },
            },
        )

        result = await monitor.check()
        assert result.action == "log"

    @pytest.mark.asyncio
    async def test_empty_details_in_auto_fix(self, monitor) -> None:
        """Details bos oldugunda otonom aksiyon hatasi olmamali."""
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
