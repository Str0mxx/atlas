"""SecurityAgent unit testleri.

SSHManager mock'lanarak guvenlik agent davranislari test edilir.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.agents.security_agent import SecurityAgent
from app.core.decision_matrix import ActionType, RiskLevel, UrgencyLevel
from app.models.security import (
    BannedIPEntry,
    FailedLoginEntry,
    OpenPort,
    SecurityCheckType,
    SecurityScanConfig,
    SecurityScanResult,
    SSLCertInfo,
    SuspiciousProcess,
    ThreatLevel,
)
from app.models.server import ServerConfig


# === Fixtures ===


@pytest.fixture
def server_config() -> ServerConfig:
    """Ornek sunucu yapilandirmasi."""
    return ServerConfig(
        host="192.168.1.100",
        user="root",
        key_path="~/.ssh/id_rsa",
        port=22,
    )


@pytest.fixture
def scan_config() -> SecurityScanConfig:
    """Ornek tarama yapilandirmasi."""
    return SecurityScanConfig(
        failed_login_threshold=5,
        ssl_domains=["example.com"],
        allowed_ports=[22, 80, 443],
    )


@pytest.fixture
def agent(server_config: ServerConfig, scan_config: SecurityScanConfig) -> SecurityAgent:
    """Yapilandirilmis SecurityAgent."""
    return SecurityAgent(
        servers=[server_config],
        scan_config=scan_config,
    )


@pytest.fixture
def clean_scan_result() -> SecurityScanResult:
    """Temiz guvenlik tarama sonucu."""
    return SecurityScanResult(
        threat_level=ThreatLevel.NONE,
        fail2ban_active=True,
    )


@pytest.fixture
def risky_scan_result() -> SecurityScanResult:
    """Riskli guvenlik tarama sonucu."""
    return SecurityScanResult(
        threat_level=ThreatLevel.HIGH,
        failed_logins=[
            FailedLoginEntry(ip="10.0.0.1", username="root", count=50),
            FailedLoginEntry(ip="10.0.0.2", username="admin", count=30),
        ],
        total_failed_attempts=80,
        fail2ban_active=False,
        unexpected_ports=[
            OpenPort(port=4444, protocol="tcp", process="nc", is_expected=False),
        ],
        suspicious_processes=[
            SuspiciousProcess(
                pid=9999, user="nobody", command="xmrig",
                cpu_percent=95.0, reason="bilinen supehli komut: xmrig",
            ),
        ],
    )


# === Tehdit seviyesi karsilastirma testleri ===


class TestWorstThreat:
    """_worst_threat fonksiyonu testleri."""

    def test_none_and_low(self) -> None:
        result = SecurityAgent._worst_threat(ThreatLevel.NONE, ThreatLevel.LOW)
        assert result == ThreatLevel.LOW

    def test_low_and_medium(self) -> None:
        result = SecurityAgent._worst_threat(ThreatLevel.LOW, ThreatLevel.MEDIUM)
        assert result == ThreatLevel.MEDIUM

    def test_medium_and_high(self) -> None:
        result = SecurityAgent._worst_threat(ThreatLevel.MEDIUM, ThreatLevel.HIGH)
        assert result == ThreatLevel.HIGH

    def test_high_and_critical(self) -> None:
        result = SecurityAgent._worst_threat(ThreatLevel.HIGH, ThreatLevel.CRITICAL)
        assert result == ThreatLevel.CRITICAL

    def test_same_level(self) -> None:
        result = SecurityAgent._worst_threat(ThreatLevel.MEDIUM, ThreatLevel.MEDIUM)
        assert result == ThreatLevel.MEDIUM

    def test_critical_and_none(self) -> None:
        result = SecurityAgent._worst_threat(ThreatLevel.CRITICAL, ThreatLevel.NONE)
        assert result == ThreatLevel.CRITICAL


# === Risk/Aciliyet eslestirme testleri ===


class TestRiskUrgencyMapping:
    """Tehdit bulgulari -> RiskLevel/UrgencyLevel eslestirme testleri."""

    def test_no_threat_maps_to_low(self) -> None:
        risk, urgency = SecurityAgent._map_to_risk_urgency(
            worst_threat=ThreatLevel.NONE,
            total_failed_logins=0,
            total_unexpected_ports=0,
            total_suspicious_procs=0,
            has_ssl_issue=False,
            has_fail2ban_down=False,
        )
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_low_threat_maps_to_low(self) -> None:
        risk, urgency = SecurityAgent._map_to_risk_urgency(
            worst_threat=ThreatLevel.LOW,
            total_failed_logins=3,
            total_unexpected_ports=0,
            total_suspicious_procs=0,
            has_ssl_issue=False,
            has_fail2ban_down=False,
        )
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_medium_threat_maps_to_medium(self) -> None:
        risk, urgency = SecurityAgent._map_to_risk_urgency(
            worst_threat=ThreatLevel.MEDIUM,
            total_failed_logins=10,
            total_unexpected_ports=1,
            total_suspicious_procs=0,
            has_ssl_issue=False,
            has_fail2ban_down=False,
        )
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.MEDIUM

    def test_medium_with_fail2ban_down_escalates_urgency(self) -> None:
        """Fail2ban kapali + basarisiz giris varsa aciliyet yukselmeli."""
        risk, urgency = SecurityAgent._map_to_risk_urgency(
            worst_threat=ThreatLevel.MEDIUM,
            total_failed_logins=20,
            total_unexpected_ports=0,
            total_suspicious_procs=0,
            has_ssl_issue=False,
            has_fail2ban_down=True,
        )
        assert risk == RiskLevel.MEDIUM
        assert urgency == UrgencyLevel.HIGH

    def test_high_with_suspicious_procs_maps_to_high_high(self) -> None:
        risk, urgency = SecurityAgent._map_to_risk_urgency(
            worst_threat=ThreatLevel.HIGH,
            total_failed_logins=0,
            total_unexpected_ports=0,
            total_suspicious_procs=2,
            has_ssl_issue=False,
            has_fail2ban_down=False,
        )
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.HIGH

    def test_high_without_aggravation_maps_to_high_medium(self) -> None:
        """Sadece port/ssl sorunu: HIGH risk, MEDIUM urgency."""
        risk, urgency = SecurityAgent._map_to_risk_urgency(
            worst_threat=ThreatLevel.HIGH,
            total_failed_logins=50,
            total_unexpected_ports=3,
            total_suspicious_procs=0,
            has_ssl_issue=True,
            has_fail2ban_down=False,
        )
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.MEDIUM

    def test_critical_maps_to_high_high(self) -> None:
        risk, urgency = SecurityAgent._map_to_risk_urgency(
            worst_threat=ThreatLevel.CRITICAL,
            total_failed_logins=100,
            total_unexpected_ports=5,
            total_suspicious_procs=3,
            has_ssl_issue=True,
            has_fail2ban_down=True,
        )
        assert risk == RiskLevel.HIGH
        assert urgency == UrgencyLevel.HIGH


# === Aksiyon belirleme testleri ===


class TestActionDetermination:
    """Aksiyon tipi belirleme testleri."""

    def test_low_low_logs(self) -> None:
        action = SecurityAgent._determine_action(RiskLevel.LOW, UrgencyLevel.LOW)
        assert action == ActionType.LOG

    def test_medium_medium_notifies(self) -> None:
        action = SecurityAgent._determine_action(RiskLevel.MEDIUM, UrgencyLevel.MEDIUM)
        assert action == ActionType.NOTIFY

    def test_medium_high_auto_fix(self) -> None:
        action = SecurityAgent._determine_action(RiskLevel.MEDIUM, UrgencyLevel.HIGH)
        assert action == ActionType.AUTO_FIX

    def test_high_high_immediate(self) -> None:
        action = SecurityAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert action == ActionType.IMMEDIATE

    def test_high_medium_auto_fix(self) -> None:
        action = SecurityAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.MEDIUM)
        assert action == ActionType.AUTO_FIX


# === Tehdit seviyesi hesaplama testleri ===


class TestCalculateThreatLevel:
    """_calculate_threat_level testleri."""

    def test_clean_result_is_none(self, agent: SecurityAgent) -> None:
        """Temiz sonuc NONE donmeli."""
        result = SecurityScanResult(fail2ban_active=True)
        assert agent._calculate_threat_level(result) == ThreatLevel.NONE

    def test_few_failed_logins_is_low(self, agent: SecurityAgent) -> None:
        """Esik altinda basarisiz giris LOW donmeli."""
        result = SecurityScanResult(
            fail2ban_active=True,
            total_failed_attempts=3,
        )
        assert agent._calculate_threat_level(result) == ThreatLevel.LOW

    def test_many_failed_logins_is_medium(self, agent: SecurityAgent) -> None:
        """Esik uzerinde basarisiz giris MEDIUM donmeli."""
        result = SecurityScanResult(
            fail2ban_active=True,
            total_failed_attempts=10,
        )
        assert agent._calculate_threat_level(result) == ThreatLevel.MEDIUM

    def test_very_many_failed_logins_is_high(self, agent: SecurityAgent) -> None:
        """Esik*10 uzerinde basarisiz giris HIGH donmeli."""
        result = SecurityScanResult(
            fail2ban_active=True,
            total_failed_attempts=60,
        )
        assert agent._calculate_threat_level(result) == ThreatLevel.HIGH

    def test_fail2ban_down_is_medium(self, agent: SecurityAgent) -> None:
        """Fail2ban kapali MEDIUM donmeli."""
        result = SecurityScanResult(fail2ban_active=False)
        assert agent._calculate_threat_level(result) == ThreatLevel.MEDIUM

    def test_unexpected_port_is_medium(self, agent: SecurityAgent) -> None:
        """Tek beklenmeyen port MEDIUM donmeli."""
        result = SecurityScanResult(
            fail2ban_active=True,
            unexpected_ports=[OpenPort(port=4444, is_expected=False)],
        )
        assert agent._calculate_threat_level(result) == ThreatLevel.MEDIUM

    def test_many_unexpected_ports_is_high(self, agent: SecurityAgent) -> None:
        """3+ beklenmeyen port HIGH donmeli."""
        result = SecurityScanResult(
            fail2ban_active=True,
            unexpected_ports=[
                OpenPort(port=4444, is_expected=False),
                OpenPort(port=5555, is_expected=False),
                OpenPort(port=6666, is_expected=False),
            ],
        )
        assert agent._calculate_threat_level(result) == ThreatLevel.HIGH

    def test_invalid_ssl_is_high(self, agent: SecurityAgent) -> None:
        """Gecersiz SSL HIGH donmeli."""
        result = SecurityScanResult(
            fail2ban_active=True,
            ssl_certs=[SSLCertInfo(domain="test.com", is_valid=False, days_remaining=0)],
        )
        assert agent._calculate_threat_level(result) == ThreatLevel.HIGH

    def test_expiring_ssl_is_medium(self, agent: SecurityAgent) -> None:
        """30 gun icinde dolacak SSL MEDIUM donmeli."""
        result = SecurityScanResult(
            fail2ban_active=True,
            ssl_certs=[SSLCertInfo(domain="test.com", is_valid=True, days_remaining=15)],
        )
        assert agent._calculate_threat_level(result) == ThreatLevel.MEDIUM

    def test_known_suspicious_command_is_critical(self, agent: SecurityAgent) -> None:
        """Bilinen supehli komut CRITICAL donmeli."""
        result = SecurityScanResult(
            fail2ban_active=True,
            suspicious_processes=[
                SuspiciousProcess(
                    pid=1, command="xmrig", reason="bilinen supehli komut: xmrig",
                ),
            ],
        )
        assert agent._calculate_threat_level(result) == ThreatLevel.CRITICAL

    def test_high_cpu_process_is_medium(self, agent: SecurityAgent) -> None:
        """Yuksek CPU process (ama bilinen komut degil) MEDIUM donmeli."""
        result = SecurityScanResult(
            fail2ban_active=True,
            suspicious_processes=[
                SuspiciousProcess(
                    pid=1, command="python heavy.py",
                    cpu_percent=95.0, reason="yuksek CPU: %95.0",
                ),
            ],
        )
        assert agent._calculate_threat_level(result) == ThreatLevel.MEDIUM


# === Analiz testleri ===


class TestAnalyze:
    """analyze() metodu testleri."""

    @pytest.mark.asyncio
    async def test_clean_analysis(self, agent: SecurityAgent) -> None:
        """Temiz tarama: LOW risk, LOW urgency, LOG action."""
        clean = SecurityScanResult(
            threat_level=ThreatLevel.NONE,
            fail2ban_active=True,
        )
        result = await agent.analyze({
            "scan_results": {"192.168.1.100": clean.model_dump()},
        })
        assert result["threat_level"] == ThreatLevel.NONE.value
        assert result["risk"] == RiskLevel.LOW.value
        assert result["urgency"] == UrgencyLevel.LOW.value
        assert result["action"] == ActionType.LOG.value

    @pytest.mark.asyncio
    async def test_risky_analysis(
        self, agent: SecurityAgent, risky_scan_result: SecurityScanResult,
    ) -> None:
        """Riskli tarama: HIGH risk, HIGH urgency, IMMEDIATE action."""
        result = await agent.analyze({
            "scan_results": {"192.168.1.100": risky_scan_result.model_dump()},
        })
        assert result["risk"] == RiskLevel.HIGH.value
        assert result["urgency"] == UrgencyLevel.HIGH.value
        assert result["action"] == ActionType.IMMEDIATE.value

    @pytest.mark.asyncio
    async def test_analysis_summary_contains_count(self, agent: SecurityAgent) -> None:
        """Analiz ozeti sunucu sayisini icermeli."""
        clean = SecurityScanResult(threat_level=ThreatLevel.NONE, fail2ban_active=True)
        result = await agent.analyze({
            "scan_results": {
                "server1": clean.model_dump(),
                "server2": clean.model_dump(),
            },
        })
        assert "2/2" in result["summary"]

    @pytest.mark.asyncio
    async def test_analysis_details_per_host(self, agent: SecurityAgent) -> None:
        """Her sunucu icin detay bilgisi olmali."""
        clean = SecurityScanResult(threat_level=ThreatLevel.NONE, fail2ban_active=True)
        result = await agent.analyze({
            "scan_results": {
                "server-a": clean.model_dump(),
                "server-b": clean.model_dump(),
            },
        })
        hosts = [d["host"] for d in result["details"]]
        assert "server-a" in hosts
        assert "server-b" in hosts

    @pytest.mark.asyncio
    async def test_analysis_stats(
        self, agent: SecurityAgent, risky_scan_result: SecurityScanResult,
    ) -> None:
        """Analiz istatistikleri dogru olmali."""
        result = await agent.analyze({
            "scan_results": {"host1": risky_scan_result.model_dump()},
        })
        stats = result["stats"]
        assert stats["total_failed_logins"] == 80
        assert stats["total_unexpected_ports"] == 1
        assert stats["total_suspicious_procs"] == 1
        assert stats["has_fail2ban_down"] is True


# === Rapor format testleri ===


class TestReport:
    """report() metodu testleri."""

    @pytest.mark.asyncio
    async def test_report_contains_header(self, agent: SecurityAgent) -> None:
        """Rapor baslik icermeli."""
        task_result = TaskResult(
            success=True,
            data={
                "analysis": {
                    "threat_level": "none",
                    "risk": "low",
                    "urgency": "low",
                    "action": "log",
                    "summary": "Tum sunucular guvenli.",
                    "details": [],
                    "stats": {},
                },
            },
            message="ok",
        )
        report = await agent.report(task_result)
        assert "GUVENLIK TARAMA RAPORU" in report

    @pytest.mark.asyncio
    async def test_report_contains_host_details(self, agent: SecurityAgent) -> None:
        """Rapor sunucu detaylarini icermeli."""
        task_result = TaskResult(
            success=True,
            data={
                "analysis": {
                    "threat_level": "high",
                    "risk": "high",
                    "urgency": "high",
                    "action": "immediate",
                    "summary": "Yuksek tehdit!",
                    "details": [
                        {
                            "host": "192.168.1.100",
                            "threat_level": "high",
                            "issues": ["Basarisiz giris: 10.0.0.1 (50x)"],
                        },
                    ],
                    "stats": {
                        "total_failed_logins": 50,
                        "total_unexpected_ports": 0,
                        "total_suspicious_procs": 0,
                        "has_ssl_issue": False,
                        "has_fail2ban_down": False,
                    },
                },
            },
            message="tehdit",
        )
        report = await agent.report(task_result)
        assert "192.168.1.100" in report
        assert "Basarisiz giris" in report

    @pytest.mark.asyncio
    async def test_report_contains_stats(self, agent: SecurityAgent) -> None:
        """Rapor istatistikleri icermeli."""
        task_result = TaskResult(
            success=True,
            data={
                "analysis": {
                    "threat_level": "medium",
                    "risk": "medium",
                    "urgency": "medium",
                    "action": "notify",
                    "summary": "Orta tehdit.",
                    "details": [],
                    "stats": {
                        "total_failed_logins": 25,
                        "total_unexpected_ports": 2,
                        "total_suspicious_procs": 1,
                        "has_ssl_issue": True,
                        "has_fail2ban_down": True,
                    },
                },
            },
            message="orta",
        )
        report = await agent.report(task_result)
        assert "25" in report
        assert "KAPALI" in report

    @pytest.mark.asyncio
    async def test_report_contains_errors(self, agent: SecurityAgent) -> None:
        """Rapor hatalari icermeli."""
        task_result = TaskResult(
            success=False,
            data={
                "analysis": {
                    "threat_level": "high",
                    "risk": "high",
                    "urgency": "high",
                    "action": "immediate",
                    "summary": "Hata!",
                    "details": [],
                    "stats": {},
                },
            },
            message="hata",
            errors=["192.168.1.100: Baglanti zaman asimi"],
        )
        report = await agent.report(task_result)
        assert "HATALAR" in report
        assert "Baglanti zaman asimi" in report


# === Log analizi testleri (SSH mock) ===


class TestAuthLogAnalysis:
    """_analyze_auth_logs testleri."""

    @pytest.mark.asyncio
    async def test_parse_failed_logins(self, agent: SecurityAgent) -> None:
        """auth.log'dan basarisiz girisleri dogru ayristirmali."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(return_value=(
            "Feb  5 10:00:01 server sshd[1234]: Failed password for root from 10.0.0.1 port 22 ssh2\n"
            "Feb  5 10:00:02 server sshd[1235]: Failed password for root from 10.0.0.1 port 22 ssh2\n"
            "Feb  5 10:00:03 server sshd[1236]: Failed password for invalid user admin from 10.0.0.2 port 22 ssh2\n"
            "Feb  5 10:01:00 server sshd[1237]: Accepted password for deploy from 10.0.0.3 port 22 ssh2\n",
            "",
            0,
        ))

        result = SecurityScanResult()
        await agent._analyze_auth_logs(mock_ssh, result)

        assert result.total_failed_attempts == 3
        assert len(result.failed_logins) == 2

        ip_map = {entry.ip: entry for entry in result.failed_logins}
        assert ip_map["10.0.0.1"].count == 2
        assert "root" in ip_map["10.0.0.1"].username
        assert ip_map["10.0.0.2"].count == 1
        assert "admin" in ip_map["10.0.0.2"].username

    @pytest.mark.asyncio
    async def test_empty_auth_log(self, agent: SecurityAgent) -> None:
        """Bos auth.log hata vermemeli."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(return_value=("", "", 0))

        result = SecurityScanResult()
        await agent._analyze_auth_logs(mock_ssh, result)

        assert result.total_failed_attempts == 0
        assert len(result.failed_logins) == 0


# === Fail2ban testleri (SSH mock) ===


class TestFail2banCheck:
    """_check_fail2ban testleri."""

    @pytest.mark.asyncio
    async def test_fail2ban_active_with_bans(self, agent: SecurityAgent) -> None:
        """Aktif fail2ban ve engellenenmis IP'ler."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(side_effect=[
            # systemctl is-active fail2ban
            ("active", "", 0),
            # fail2ban-client status sshd
            (
                "Status for the jail: sshd\n"
                "|- Filter\n"
                "|  |- Currently failed: 3\n"
                "`- Actions\n"
                "   |- Currently banned: 2\n"
                "   `- Banned IP list:   10.0.0.1 10.0.0.2\n",
                "",
                0,
            ),
        ])

        result = SecurityScanResult()
        await agent._check_fail2ban(mock_ssh, result)

        assert result.fail2ban_active is True
        assert len(result.banned_ips) == 2
        assert result.banned_ips[0].ip == "10.0.0.1"
        assert result.banned_ips[1].ip == "10.0.0.2"

    @pytest.mark.asyncio
    async def test_fail2ban_inactive(self, agent: SecurityAgent) -> None:
        """Fail2ban aktif degil."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(return_value=("inactive", "", 3))

        result = SecurityScanResult()
        await agent._check_fail2ban(mock_ssh, result)

        assert result.fail2ban_active is False
        assert len(result.banned_ips) == 0


# === Port taramasi testleri (SSH mock) ===


class TestOpenPortScan:
    """_scan_open_ports testleri."""

    @pytest.mark.asyncio
    async def test_detect_expected_and_unexpected_ports(self, agent: SecurityAgent) -> None:
        """Beklenen ve beklenmeyen portlari ayirt etmeli."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(return_value=(
            "LISTEN  0  128  0.0.0.0:22  0.0.0.0:*  users:((\"sshd\",pid=1,fd=3))\n"
            "LISTEN  0  128  0.0.0.0:80  0.0.0.0:*  users:((\"nginx\",pid=100,fd=5))\n"
            "LISTEN  0  128  0.0.0.0:4444  0.0.0.0:*  users:((\"nc\",pid=9999,fd=4))\n",
            "",
            0,
        ))

        result = SecurityScanResult()
        await agent._scan_open_ports(mock_ssh, result)

        assert len(result.open_ports) == 3
        assert len(result.unexpected_ports) == 1
        assert result.unexpected_ports[0].port == 4444
        assert result.unexpected_ports[0].process == "nc"

    @pytest.mark.asyncio
    async def test_empty_port_output(self, agent: SecurityAgent) -> None:
        """Bos ss ciktisi hata vermemeli."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(return_value=("", "", 1))

        result = SecurityScanResult()
        await agent._scan_open_ports(mock_ssh, result)

        assert len(result.open_ports) == 0


# === SSL kontrolu testleri (SSH mock) ===


class TestSSLCertCheck:
    """_check_ssl_certs testleri."""

    @pytest.mark.asyncio
    async def test_valid_ssl_cert(self, agent: SecurityAgent) -> None:
        """Gecerli SSL sertifikasi."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(side_effect=[
            # openssl dates + issuer
            (
                "issuer= /CN=Let's Encrypt Authority X3\n"
                "notBefore=Jan  1 00:00:00 2026 GMT\n"
                "notAfter=Apr  1 00:00:00 2026 GMT\n",
                "",
                0,
            ),
            # days remaining
            ("Certificate will not expire\n54", "", 0),
        ])

        result = SecurityScanResult()
        await agent._check_ssl_certs(mock_ssh, result)

        assert len(result.ssl_certs) == 1
        cert = result.ssl_certs[0]
        assert cert.domain == "example.com"
        assert cert.is_valid is True
        assert cert.days_remaining == 54

    @pytest.mark.asyncio
    async def test_invalid_ssl_cert(self, agent: SecurityAgent) -> None:
        """Gecersiz/erisilemez SSL sertifikasi."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(return_value=("", "error", 1))

        result = SecurityScanResult()
        await agent._check_ssl_certs(mock_ssh, result)

        assert len(result.ssl_certs) == 1
        assert result.ssl_certs[0].is_valid is False

    @pytest.mark.asyncio
    async def test_no_domains_configured(self, agent: SecurityAgent) -> None:
        """Domain tanimlanmamissa kontrol atlamali."""
        agent.scan_config.ssl_domains = []
        mock_ssh = AsyncMock()

        result = SecurityScanResult()
        await agent._check_ssl_certs(mock_ssh, result)

        assert len(result.ssl_certs) == 0
        mock_ssh.execute_command.assert_not_called()


# === Supehli process testleri (SSH mock) ===


class TestSuspiciousProcessDetection:
    """_detect_suspicious_processes testleri."""

    @pytest.mark.asyncio
    async def test_detect_known_suspicious_command(self, agent: SecurityAgent) -> None:
        """Bilinen supehli komutu tespit etmeli."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(return_value=(
            "root      1  0.0  0.1  12345  1234 ?  Ss   10:00   0:00 /sbin/init\n"
            "nobody 9999 95.0  2.0  54321  4321 ?  R    10:05   5:00 /tmp/xmrig --donate=0\n"
            "www    1000  1.0  5.0  23456  2345 ?  S    10:01   0:10 nginx: worker process\n",
            "",
            0,
        ))

        result = SecurityScanResult()
        await agent._detect_suspicious_processes(mock_ssh, result)

        assert len(result.suspicious_processes) == 1
        proc = result.suspicious_processes[0]
        assert proc.pid == 9999
        assert "xmrig" in proc.command
        assert "bilinen supehli komut" in proc.reason

    @pytest.mark.asyncio
    async def test_detect_high_cpu_process(self, agent: SecurityAgent) -> None:
        """Yuksek CPU kullanan process'i tespit etmeli."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(return_value=(
            "user1  5000 95.5  10.0  99999  9999 ?  R  10:00  99:00 python3 heavy_task.py\n",
            "",
            0,
        ))

        result = SecurityScanResult()
        await agent._detect_suspicious_processes(mock_ssh, result)

        assert len(result.suspicious_processes) == 1
        proc = result.suspicious_processes[0]
        assert proc.pid == 5000
        assert "yuksek CPU" in proc.reason

    @pytest.mark.asyncio
    async def test_detect_high_memory_process(self, agent: SecurityAgent) -> None:
        """Yuksek bellek kullanan process'i tespit etmeli."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(return_value=(
            "user2  6000  5.0 85.0  99999  9999 ?  S  10:00  10:00 java -Xmx8g bigapp.jar\n",
            "",
            0,
        ))

        result = SecurityScanResult()
        await agent._detect_suspicious_processes(mock_ssh, result)

        assert len(result.suspicious_processes) == 1
        assert "yuksek bellek" in result.suspicious_processes[0].reason

    @pytest.mark.asyncio
    async def test_normal_processes_not_flagged(self, agent: SecurityAgent) -> None:
        """Normal process'ler supehli olarak isaretlenmemeli."""
        mock_ssh = AsyncMock()
        mock_ssh.execute_command = AsyncMock(return_value=(
            "root      1  0.0  0.1  12345  1234 ?  Ss   10:00   0:00 /sbin/init\n"
            "www    1000  2.0  5.0  23456  2345 ?  S    10:01   0:10 nginx: worker process\n"
            "pg     2000  1.5  3.0  34567  3456 ?  S    10:02   0:20 postgres: checkpointer\n",
            "",
            0,
        ))

        result = SecurityScanResult()
        await agent._detect_suspicious_processes(mock_ssh, result)

        assert len(result.suspicious_processes) == 0


# === Execute testleri (tam SSH mock) ===


class TestExecute:
    """execute() metodu testleri."""

    @pytest.mark.asyncio
    async def test_execute_no_servers(self) -> None:
        """Sunucu listesi bos ise hata donmeli."""
        agent = SecurityAgent(servers=[])
        result = await agent.execute({})
        assert result.success is False
        assert "bos" in result.errors[0].lower() or "yapilandirilmamis" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_with_mock_ssh(self, server_config: ServerConfig) -> None:
        """Mock SSH ile basarili guvenlik taramasi."""
        agent = SecurityAgent(
            servers=[server_config],
            scan_config=SecurityScanConfig(
                checks=[SecurityCheckType.AUTH_LOG, SecurityCheckType.FAIL2BAN],
                ssl_domains=[],
            ),
        )

        mock_ssh_instance = AsyncMock()
        mock_ssh_instance.execute_command = AsyncMock(side_effect=[
            # auth log
            (
                "Feb 5 10:00:01 server sshd[1234]: Failed password for root from 10.0.0.1 port 22\n",
                "",
                0,
            ),
            # fail2ban is-active
            ("active", "", 0),
            # fail2ban status sshd
            ("Status for sshd\n   `- Banned IP list:   10.0.0.5\n", "", 0),
        ])
        mock_ssh_instance.__aenter__ = AsyncMock(return_value=mock_ssh_instance)
        mock_ssh_instance.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.agents.security_agent.SSHManager",
            return_value=mock_ssh_instance,
        ):
            result = await agent.execute({"description": "Guvenlik taramasi"})

        assert result.success is True
        assert "scan_results" in result.data
        assert "analysis" in result.data

    @pytest.mark.asyncio
    async def test_execute_ssh_failure(self, server_config: ServerConfig) -> None:
        """SSH baglanti hatasi durumunda graceful handling."""
        agent = SecurityAgent(servers=[server_config])

        mock_ssh_instance = AsyncMock()
        mock_ssh_instance.__aenter__ = AsyncMock(
            side_effect=ConnectionError("Baglanti reddedildi"),
        )
        mock_ssh_instance.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.agents.security_agent.SSHManager",
            return_value=mock_ssh_instance,
        ):
            result = await agent.execute({"description": "Guvenlik taramasi"})

        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_with_task_checks_override(self, server_config: ServerConfig) -> None:
        """Task'tan kontrol tipi override edilebilmeli."""
        agent = SecurityAgent(
            servers=[server_config],
            scan_config=SecurityScanConfig(ssl_domains=[]),
        )

        mock_ssh_instance = AsyncMock()
        mock_ssh_instance.execute_command = AsyncMock(side_effect=[
            # Only fail2ban checks
            ("active", "", 0),
            ("Status for sshd\n   `- Banned IP list:\n", "", 0),
        ])
        mock_ssh_instance.__aenter__ = AsyncMock(return_value=mock_ssh_instance)
        mock_ssh_instance.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.agents.security_agent.SSHManager",
            return_value=mock_ssh_instance,
        ):
            result = await agent.execute({
                "description": "Sadece fail2ban kontrolu",
                "checks": ["fail2ban"],
            })

        assert result.success is True


# === Model testleri ===


class TestModels:
    """Guvenlik veri modeli testleri."""

    def test_security_scan_config_defaults(self) -> None:
        """SecurityScanConfig varsayilan degerler dogru olmali."""
        config = SecurityScanConfig()
        assert len(config.checks) == 5
        assert config.failed_login_threshold == 5
        assert 22 in config.allowed_ports

    def test_security_scan_result_defaults(self) -> None:
        """SecurityScanResult varsayilan degerler dogru olmali."""
        result = SecurityScanResult()
        assert result.threat_level == ThreatLevel.NONE
        assert result.total_failed_attempts == 0
        assert result.fail2ban_active is False
        assert result.failed_logins == []

    def test_failed_login_entry(self) -> None:
        """FailedLoginEntry dogru olusturulmali."""
        entry = FailedLoginEntry(ip="10.0.0.1", username="root", count=10)
        assert entry.ip == "10.0.0.1"
        assert entry.count == 10

    def test_open_port(self) -> None:
        """OpenPort dogru olusturulmali."""
        port = OpenPort(port=8080, process="nginx", is_expected=False)
        assert port.port == 8080
        assert port.is_expected is False

    def test_ssl_cert_info(self) -> None:
        """SSLCertInfo dogru olusturulmali."""
        cert = SSLCertInfo(domain="test.com", days_remaining=30, is_valid=True)
        assert cert.domain == "test.com"
        assert cert.days_remaining == 30

    def test_suspicious_process(self) -> None:
        """SuspiciousProcess dogru olusturulmali."""
        proc = SuspiciousProcess(pid=1234, command="nmap", reason="bilinen supehli komut")
        assert proc.pid == 1234
        assert proc.command == "nmap"

    def test_threat_level_ordering(self) -> None:
        """ThreatLevel siralama dogru olmali."""
        levels = [ThreatLevel.NONE, ThreatLevel.LOW, ThreatLevel.MEDIUM,
                  ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        for i in range(len(levels) - 1):
            result = SecurityAgent._worst_threat(levels[i], levels[i + 1])
            assert result == levels[i + 1]
