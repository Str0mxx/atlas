"""ServerMonitorAgent unit testleri.

SSHManager mock'lanarak agent davranislari test edilir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.agents.server_monitor_agent import ServerMonitorAgent
from app.core.decision_matrix import ActionType, RiskLevel, UrgencyLevel
from app.models.server import (
    CpuMetrics,
    DiskMetrics,
    MetricStatus,
    MetricThresholds,
    RamMetrics,
    ServerConfig,
    ServerMetrics,
    ServiceStatus,
)


# === Fixtures ===


@pytest.fixture
def server_config() -> ServerConfig:
    """Ornek sunucu yapilandirmasi."""
    return ServerConfig(
        host="192.168.1.100",
        user="root",
        key_path="~/.ssh/id_rsa",
        port=22,
        services=["nginx", "postgresql"],
    )


@pytest.fixture
def agent(server_config: ServerConfig) -> ServerMonitorAgent:
    """Yapilandirilmis ServerMonitorAgent."""
    return ServerMonitorAgent(
        servers=[server_config],
        thresholds=MetricThresholds(),
    )


@pytest.fixture
def healthy_metrics() -> ServerMetrics:
    """Sagliki sunucu metrikleri."""
    return ServerMetrics(
        host="192.168.1.100",
        reachable=True,
        cpu=CpuMetrics(usage_percent=25.0, load_1m=0.5, load_5m=0.4, load_15m=0.3),
        ram=RamMetrics(total_mb=8000, used_mb=3000, available_mb=5000, usage_percent=37.5),
        disks=[DiskMetrics(mount_point="/", total_gb=100, used_gb=40, available_gb=60, usage_percent=40.0)],
        services=[
            ServiceStatus(name="nginx", is_active=True, status=MetricStatus.NORMAL),
            ServiceStatus(name="postgresql", is_active=True, status=MetricStatus.NORMAL),
        ],
        overall_status=MetricStatus.NORMAL,
    )


@pytest.fixture
def warning_metrics() -> ServerMetrics:
    """Uyari seviyesinde sunucu metrikleri."""
    return ServerMetrics(
        host="192.168.1.100",
        reachable=True,
        cpu=CpuMetrics(usage_percent=75.0, load_1m=2.0, load_5m=1.8, load_15m=1.5),
        ram=RamMetrics(total_mb=8000, used_mb=6200, available_mb=1800, usage_percent=77.5),
        disks=[DiskMetrics(mount_point="/", total_gb=100, used_gb=82, available_gb=18, usage_percent=82.0)],
        services=[
            ServiceStatus(name="nginx", is_active=True, status=MetricStatus.NORMAL),
        ],
        overall_status=MetricStatus.WARNING,
    )


@pytest.fixture
def critical_metrics() -> ServerMetrics:
    """Kritik seviyede sunucu metrikleri (yuksek kaynak)."""
    return ServerMetrics(
        host="192.168.1.100",
        reachable=True,
        cpu=CpuMetrics(usage_percent=95.0, load_1m=8.0, load_5m=7.5, load_15m=6.0),
        ram=RamMetrics(total_mb=8000, used_mb=7500, available_mb=500, usage_percent=93.8),
        disks=[DiskMetrics(mount_point="/", total_gb=100, used_gb=95, available_gb=5, usage_percent=95.0)],
        services=[
            ServiceStatus(name="nginx", is_active=True, status=MetricStatus.NORMAL),
        ],
        overall_status=MetricStatus.CRITICAL,
    )


@pytest.fixture
def unreachable_metrics() -> ServerMetrics:
    """Erisilemez sunucu metrikleri."""
    return ServerMetrics(
        host="192.168.1.100",
        reachable=False,
        overall_status=MetricStatus.CRITICAL,
    )


# === Metrik siniflandirma testleri ===


class TestMetricClassification:
    """Metrik esik degeri siniflandirma testleri."""

    def test_classify_normal(self, agent: ServerMonitorAgent) -> None:
        """Normal deger NORMAL donmeli."""
        result = agent._classify_metric(50.0, 70.0, 90.0)
        assert result == MetricStatus.NORMAL

    def test_classify_warning(self, agent: ServerMonitorAgent) -> None:
        """Warning esiginde WARNING donmeli."""
        result = agent._classify_metric(75.0, 70.0, 90.0)
        assert result == MetricStatus.WARNING

    def test_classify_critical(self, agent: ServerMonitorAgent) -> None:
        """Critical esiginde CRITICAL donmeli."""
        result = agent._classify_metric(95.0, 70.0, 90.0)
        assert result == MetricStatus.CRITICAL

    def test_classify_at_exact_warning_boundary(self, agent: ServerMonitorAgent) -> None:
        """Tam warning esiginde WARNING donmeli."""
        result = agent._classify_metric(70.0, 70.0, 90.0)
        assert result == MetricStatus.WARNING

    def test_classify_at_exact_critical_boundary(self, agent: ServerMonitorAgent) -> None:
        """Tam critical esiginde CRITICAL donmeli."""
        result = agent._classify_metric(90.0, 70.0, 90.0)
        assert result == MetricStatus.CRITICAL

    def test_classify_zero(self, agent: ServerMonitorAgent) -> None:
        """Sifir deger NORMAL donmeli."""
        result = agent._classify_metric(0.0, 70.0, 90.0)
        assert result == MetricStatus.NORMAL


class TestWorstOf:
    """worst_of fonksiyonu testleri."""

    def test_normal_and_warning(self, agent: ServerMonitorAgent) -> None:
        result = agent._worst_of(MetricStatus.NORMAL, MetricStatus.WARNING)
        assert result == MetricStatus.WARNING

    def test_warning_and_critical(self, agent: ServerMonitorAgent) -> None:
        result = agent._worst_of(MetricStatus.WARNING, MetricStatus.CRITICAL)
        assert result == MetricStatus.CRITICAL

    def test_same_status(self, agent: ServerMonitorAgent) -> None:
        result = agent._worst_of(MetricStatus.WARNING, MetricStatus.WARNING)
        assert result == MetricStatus.WARNING

    def test_critical_and_normal(self, agent: ServerMonitorAgent) -> None:
        result = agent._worst_of(MetricStatus.CRITICAL, MetricStatus.NORMAL)
        assert result == MetricStatus.CRITICAL


# === Risk/Aciliyet eslestirme testleri ===


class TestRiskUrgencyMapping:
    """MetricStatus -> RiskLevel/UrgencyLevel eslestirme testleri."""

    def test_normal_maps_to_low(self) -> None:
        risk, urgency = ServerMonitorAgent._map_to_risk_urgency(
            MetricStatus.NORMAL, False, False,
        )
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_warning_maps_to_medium(self) -> None:
        risk, urgency = ServerMonitorAgent._map_to_risk_urgency(
            MetricStatus.WARNING, False, False,
        )
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.MEDIUM

    def test_critical_unreachable_maps_to_high_high(self) -> None:
        risk, urgency = ServerMonitorAgent._map_to_risk_urgency(
            MetricStatus.CRITICAL, True, False,
        )
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.HIGH

    def test_critical_service_down_maps_to_high_high(self) -> None:
        risk, urgency = ServerMonitorAgent._map_to_risk_urgency(
            MetricStatus.CRITICAL, False, True,
        )
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.HIGH

    def test_critical_high_resource_maps_to_high_medium(self) -> None:
        """Sadece yuksek kaynak kullanimi: HIGH risk, MEDIUM urgency."""
        risk, urgency = ServerMonitorAgent._map_to_risk_urgency(
            MetricStatus.CRITICAL, False, False,
        )
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.MEDIUM


# === Aksiyon belirleme testleri ===


class TestActionDetermination:
    """Aksiyon tipi belirleme testleri."""

    def test_low_low_logs(self) -> None:
        action = ServerMonitorAgent._determine_action(RiskLevel.LOW, UrgencyLevel.LOW)
        assert action == ActionType.LOG

    def test_medium_medium_notifies(self) -> None:
        action = ServerMonitorAgent._determine_action(RiskLevel.MEDIUM, UrgencyLevel.MEDIUM)
        assert action == ActionType.NOTIFY

    def test_high_high_immediate(self) -> None:
        action = ServerMonitorAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert action == ActionType.IMMEDIATE

    def test_high_medium_auto_fix(self) -> None:
        action = ServerMonitorAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.MEDIUM)
        assert action == ActionType.AUTO_FIX


# === Analiz testleri ===


class TestAnalyze:
    """analyze() metodu testleri."""

    @pytest.mark.asyncio
    async def test_healthy_analysis(
        self, agent: ServerMonitorAgent, healthy_metrics: ServerMetrics,
    ) -> None:
        """Sagliki sunucu: LOW risk, LOW urgency, LOG action."""
        result = await agent.analyze({"metrics": [healthy_metrics.model_dump()]})
        assert result["overall_status"] == MetricStatus.NORMAL.value
        assert result["risk"] == RiskLevel.LOW.value
        assert result["urgency"] == UrgencyLevel.LOW.value
        assert result["action"] == ActionType.LOG.value

    @pytest.mark.asyncio
    async def test_warning_analysis(
        self, agent: ServerMonitorAgent, warning_metrics: ServerMetrics,
    ) -> None:
        """Uyari seviyesi: MEDIUM risk, MEDIUM urgency, NOTIFY action."""
        result = await agent.analyze({"metrics": [warning_metrics.model_dump()]})
        assert result["overall_status"] == MetricStatus.WARNING.value
        assert result["risk"] == RiskLevel.MEDIUM.value
        assert result["urgency"] == UrgencyLevel.MEDIUM.value
        assert result["action"] == ActionType.NOTIFY.value

    @pytest.mark.asyncio
    async def test_critical_resource_analysis(
        self, agent: ServerMonitorAgent, critical_metrics: ServerMetrics,
    ) -> None:
        """Kritik kaynak kullanimi: HIGH risk, MEDIUM urgency, AUTO_FIX."""
        result = await agent.analyze({"metrics": [critical_metrics.model_dump()]})
        assert result["overall_status"] == MetricStatus.CRITICAL.value
        assert result["risk"] == RiskLevel.HIGH.value
        assert result["urgency"] == UrgencyLevel.MEDIUM.value
        assert result["action"] == ActionType.AUTO_FIX.value

    @pytest.mark.asyncio
    async def test_unreachable_analysis(
        self, agent: ServerMonitorAgent, unreachable_metrics: ServerMetrics,
    ) -> None:
        """Erisilemez sunucu: HIGH risk, HIGH urgency, IMMEDIATE."""
        result = await agent.analyze({"metrics": [unreachable_metrics.model_dump()]})
        assert result["overall_status"] == MetricStatus.CRITICAL.value
        assert result["risk"] == RiskLevel.HIGH.value
        assert result["urgency"] == UrgencyLevel.HIGH.value
        assert result["action"] == ActionType.IMMEDIATE.value

    @pytest.mark.asyncio
    async def test_service_down_analysis(self, agent: ServerMonitorAgent) -> None:
        """Durmus servis: HIGH risk, HIGH urgency, IMMEDIATE."""
        metrics = ServerMetrics(
            host="192.168.1.100",
            reachable=True,
            cpu=CpuMetrics(usage_percent=20.0),
            ram=RamMetrics(total_mb=8000, used_mb=2000, available_mb=6000, usage_percent=25.0),
            disks=[],
            services=[
                ServiceStatus(name="nginx", is_active=False, status=MetricStatus.CRITICAL),
            ],
        )
        result = await agent.analyze({"metrics": [metrics.model_dump()]})
        assert result["risk"] == RiskLevel.HIGH.value
        assert result["urgency"] == UrgencyLevel.HIGH.value
        assert result["action"] == ActionType.IMMEDIATE.value


# === Rapor format testleri ===


class TestReport:
    """report() metodu testleri."""

    @pytest.mark.asyncio
    async def test_report_contains_header(self, agent: ServerMonitorAgent) -> None:
        """Rapor baslik icermeli."""
        task_result = TaskResult(
            success=True,
            data={
                "analysis": {
                    "overall_status": "normal",
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "summary": "Tum sunucular sagliki.",
                    "details": [],
                },
            },
            message="ok",
        )
        report = await agent.report(task_result)
        assert "SUNUCU SAGLIK RAPORU" in report

    @pytest.mark.asyncio
    async def test_report_contains_host_details(self, agent: ServerMonitorAgent) -> None:
        """Rapor sunucu detaylarini icermeli."""
        task_result = TaskResult(
            success=True,
            data={
                "analysis": {
                    "overall_status": "warning",
                    "risk": "medium",
                    "urgency": "medium",
                    "action": "notify",
                    "summary": "1/1 sunucuda uyari.",
                    "details": [
                        {
                            "host": "192.168.1.100",
                            "status": "warning",
                            "issues": ["CPU: %75.0 (warning)"],
                        },
                    ],
                },
            },
            message="uyari",
        )
        report = await agent.report(task_result)
        assert "192.168.1.100" in report
        assert "CPU" in report

    @pytest.mark.asyncio
    async def test_report_contains_errors(self, agent: ServerMonitorAgent) -> None:
        """Rapor hatalari icermeli."""
        task_result = TaskResult(
            success=False,
            data={
                "analysis": {
                    "overall_status": "critical",
                    "risk": "high",
                    "urgency": "high",
                    "action": "immediate",
                    "summary": "Kritik durum!",
                    "details": [],
                },
            },
            message="hata",
            errors=["192.168.1.100: Baglanti zaman asimi"],
        )
        report = await agent.report(task_result)
        assert "HATALAR" in report
        assert "Baglanti zaman asimi" in report


# === Execute testleri (SSH mock ile) ===


class TestExecute:
    """execute() metodu testleri (SSH mock)."""

    @pytest.mark.asyncio
    async def test_execute_no_servers(self) -> None:
        """Sunucu listesi bos ise hata donmeli."""
        agent = ServerMonitorAgent(servers=[])
        result = await agent.execute({})
        assert result.success is False
        assert "bos" in result.errors[0].lower() or "yapilandirilmamis" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_with_mock_ssh(self, server_config: ServerConfig) -> None:
        """Mock SSH ile basarili metrik toplama."""
        agent = ServerMonitorAgent(servers=[server_config])

        mock_ssh_instance = AsyncMock()
        mock_ssh_instance.execute_command = AsyncMock(side_effect=[
            # CPU - top
            ("25.5", "", 0),
            # CPU - loadavg
            ("0.50 0.40 0.30 1/200 12345", "", 0),
            # RAM - free
            ("Mem:           8000       3000        200        100       4800       5000", "", 0),
            # Disk - df
            ("/              100G        40G        60G  40%", "", 0),
            # Service nginx
            ("active", "", 0),
            # Service postgresql
            ("active", "", 0),
        ])
        mock_ssh_instance.__aenter__ = AsyncMock(return_value=mock_ssh_instance)
        mock_ssh_instance.__aexit__ = AsyncMock(return_value=None)

        with patch.object(agent, "_check_ping", return_value=True):
            with patch(
                "app.agents.server_monitor_agent.SSHManager",
                return_value=mock_ssh_instance,
            ):
                result = await agent.execute({"description": "Sunucu kontrolu"})

        assert result.success is True
        assert "metrics" in result.data
        assert len(result.data["metrics"]) == 1
        assert result.data["metrics"][0]["reachable"] is True

    @pytest.mark.asyncio
    async def test_execute_unreachable_server(self, server_config: ServerConfig) -> None:
        """Erisilemez sunucu icin critical durum."""
        agent = ServerMonitorAgent(servers=[server_config])

        with patch.object(agent, "_check_ping", return_value=False):
            result = await agent.execute({"description": "Sunucu kontrolu"})

        assert "metrics" in result.data
        metrics = result.data["metrics"][0]
        assert metrics["reachable"] is False
        analysis = result.data["analysis"]
        assert analysis["overall_status"] == MetricStatus.CRITICAL.value

    @pytest.mark.asyncio
    async def test_execute_with_extra_servers_from_task(self) -> None:
        """Task'tan ek sunucu listesi alinabilmeli."""
        agent = ServerMonitorAgent(servers=[])

        mock_ssh_instance = AsyncMock()
        mock_ssh_instance.execute_command = AsyncMock(side_effect=[
            ("10.0", "", 0),
            ("0.10 0.20 0.15 1/100 1234", "", 0),
            ("Mem:           4000       1000        200         50       2800       3000", "", 0),
            ("/              50G        10G        40G  20%", "", 0),
        ])
        mock_ssh_instance.__aenter__ = AsyncMock(return_value=mock_ssh_instance)
        mock_ssh_instance.__aexit__ = AsyncMock(return_value=None)

        with patch.object(agent, "_check_ping", return_value=True):
            with patch(
                "app.agents.server_monitor_agent.SSHManager",
                return_value=mock_ssh_instance,
            ):
                result = await agent.execute({
                    "description": "Ek sunucu kontrolu",
                    "servers": [{"host": "10.0.0.1", "user": "admin"}],
                })

        assert result.success is True
        assert len(result.data["metrics"]) == 1


# === Model testleri ===


class TestModels:
    """Veri modeli testleri."""

    def test_server_config_defaults(self) -> None:
        """ServerConfig varsayilan degerler dogru olmali."""
        config = ServerConfig(host="1.2.3.4")
        assert config.user == "root"
        assert config.port == 22
        assert config.services == []

    def test_metric_thresholds_defaults(self) -> None:
        """MetricThresholds varsayilan esikler dogru olmali."""
        t = MetricThresholds()
        assert t.cpu_warning == 70.0
        assert t.cpu_critical == 90.0
        assert t.disk_warning == 80.0

    def test_server_metrics_default(self) -> None:
        """ServerMetrics varsayilan degerler dogru olmali."""
        m = ServerMetrics(host="test")
        assert m.reachable is True
        assert m.overall_status == MetricStatus.NORMAL
        assert m.disks == []
        assert m.services == []
