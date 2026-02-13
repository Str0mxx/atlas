"""ServiceProvisioner testleri.

Veritabani kontrolu, API anahtar uretimi,
SSL kontrolu ve port kontrolu testleri.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.bootstrap.service_provisioner import ServiceProvisioner
from app.models.bootstrap import (
    PortCheck,
    SSLInfo,
    ServiceCheck,
    ServiceType,
)


# === Yardimci Fonksiyonlar ===


def _make_provisioner() -> ServiceProvisioner:
    """Test icin ServiceProvisioner olusturur."""
    return ServiceProvisioner()


# === Enum Testleri ===


class TestServiceType:
    """ServiceType enum testleri."""

    def test_running(self) -> None:
        assert ServiceType.RUNNING == "running"

    def test_stopped(self) -> None:
        assert ServiceType.STOPPED == "stopped"

    def test_unreachable(self) -> None:
        assert ServiceType.UNREACHABLE == "unreachable"

    def test_not_installed(self) -> None:
        assert ServiceType.NOT_INSTALLED == "not_installed"

    def test_healthy(self) -> None:
        assert ServiceType.HEALTHY == "healthy"

    def test_degraded(self) -> None:
        assert ServiceType.DEGRADED == "degraded"


# === Model Testleri ===


class TestServiceCheck:
    """ServiceCheck model testleri."""

    def test_defaults(self) -> None:
        check = ServiceCheck(name="test")
        assert check.name == "test"
        assert check.status == ServiceType.UNREACHABLE
        assert check.host == "localhost"
        assert check.port == 0

    def test_custom(self) -> None:
        check = ServiceCheck(
            name="pg",
            status=ServiceType.HEALTHY,
            port=5432,
            response_time_ms=12.5,
        )
        assert check.status == ServiceType.HEALTHY
        assert check.response_time_ms == 12.5

    def test_timestamp(self) -> None:
        check = ServiceCheck(name="test")
        assert check.checked_at is not None


class TestPortCheck:
    """PortCheck model testleri."""

    def test_defaults(self) -> None:
        pc = PortCheck(port=8080)
        assert pc.port == 8080
        assert pc.available is True

    def test_in_use(self) -> None:
        pc = PortCheck(port=80, available=False, process_name="nginx")
        assert pc.available is False
        assert pc.process_name == "nginx"


class TestSSLInfo:
    """SSLInfo model testleri."""

    def test_defaults(self) -> None:
        info = SSLInfo(domain="example.com")
        assert info.domain == "example.com"
        assert info.valid is False
        assert info.issuer == ""

    def test_valid_cert(self) -> None:
        info = SSLInfo(
            domain="example.com",
            valid=True,
            issuer="Let's Encrypt",
            days_until_expiry=90,
        )
        assert info.valid is True
        assert info.days_until_expiry == 90


# === ServiceProvisioner Init Testleri ===


class TestServiceProvisionerInit:
    """ServiceProvisioner init testleri."""

    def test_create(self) -> None:
        sp = _make_provisioner()
        assert sp is not None


# === CheckPostgresql Testleri ===


class TestCheckPostgresql:
    """check_postgresql testleri."""

    async def test_healthy(self) -> None:
        sp = _make_provisioner()
        with patch.object(sp, "_tcp_connect", return_value=True):
            result = await sp.check_postgresql()
        assert result.name == "postgresql"
        assert result.status == ServiceType.HEALTHY
        assert result.port == 5432

    async def test_unreachable(self) -> None:
        sp = _make_provisioner()
        with patch.object(sp, "_tcp_connect", return_value=False):
            result = await sp.check_postgresql()
        assert result.status == ServiceType.UNREACHABLE

    async def test_custom_host(self) -> None:
        sp = _make_provisioner()
        with patch.object(sp, "_tcp_connect", return_value=True):
            result = await sp.check_postgresql(host="db.local", port=5433)
        assert result.host == "db.local"
        assert result.port == 5433


# === CheckRedis Testleri ===


class TestCheckRedis:
    """check_redis testleri."""

    async def test_healthy(self) -> None:
        sp = _make_provisioner()
        with patch.object(sp, "_tcp_connect", return_value=True):
            result = await sp.check_redis()
        assert result.name == "redis"
        assert result.status == ServiceType.HEALTHY

    async def test_unreachable(self) -> None:
        sp = _make_provisioner()
        with patch.object(sp, "_tcp_connect", return_value=False):
            result = await sp.check_redis()
        assert result.status == ServiceType.UNREACHABLE


# === CheckSqlite Testleri ===


class TestCheckSqlite:
    """check_sqlite testleri."""

    async def test_memory(self) -> None:
        sp = _make_provisioner()
        result = await sp.check_sqlite()
        assert result.name == "sqlite"
        assert result.status == ServiceType.HEALTHY

    async def test_custom_path(self) -> None:
        sp = _make_provisioner()
        result = await sp.check_sqlite(":memory:")
        assert result.details.get("db_path") == ":memory:"


# === GenerateApiKey Testleri ===


class TestGenerateApiKey:
    """generate_api_key testleri."""

    def test_default_length(self) -> None:
        sp = _make_provisioner()
        key = sp.generate_api_key()
        assert key.startswith("atlas_")
        assert len(key) > 10

    def test_custom_prefix(self) -> None:
        sp = _make_provisioner()
        key = sp.generate_api_key(prefix="myapp_")
        assert key.startswith("myapp_")

    def test_uniqueness(self) -> None:
        sp = _make_provisioner()
        keys = {sp.generate_api_key() for _ in range(10)}
        assert len(keys) == 10


# === GenerateSecretKey Testleri ===


class TestGenerateSecretKey:
    """generate_secret_key testleri."""

    def test_default_length(self) -> None:
        sp = _make_provisioner()
        key = sp.generate_secret_key()
        # token_hex(64) => 128 char
        assert len(key) == 128

    def test_uniqueness(self) -> None:
        sp = _make_provisioner()
        keys = {sp.generate_secret_key() for _ in range(10)}
        assert len(keys) == 10


# === CheckPort Testleri ===


class TestCheckPort:
    """check_port testleri."""

    async def test_available(self) -> None:
        sp = _make_provisioner()
        with patch(
            "app.core.bootstrap.service_provisioner.socket.socket"
        ) as mock_sock:
            instance = MagicMock()
            instance.connect_ex.return_value = 1  # baglanti basarisiz = port bos
            mock_sock.return_value = instance
            result = await sp.check_port(9999)
        assert result.available is True

    async def test_in_use(self) -> None:
        sp = _make_provisioner()
        with patch(
            "app.core.bootstrap.service_provisioner.socket.socket"
        ) as mock_sock:
            instance = MagicMock()
            instance.connect_ex.return_value = 0  # baglanti basarili = port dolu
            mock_sock.return_value = instance
            result = await sp.check_port(80)
        assert result.available is False

    async def test_check_multiple(self) -> None:
        sp = _make_provisioner()
        with patch.object(
            sp,
            "check_port",
            side_effect=[
                PortCheck(port=80, available=False),
                PortCheck(port=8080, available=True),
            ],
        ):
            results = await sp.check_ports([80, 8080])
        assert len(results) == 2
        assert results[0].available is False
        assert results[1].available is True


# === CheckSSL Testleri ===


class TestCheckSSL:
    """check_ssl_certificate testleri."""

    async def test_valid(self) -> None:
        sp = _make_provisioner()
        with patch.object(
            sp,
            "_get_ssl_cert",
            return_value={
                "notAfter": "Dec 31 23:59:59 2027 GMT",
                "issuer": (
                    (("organizationName", "Let's Encrypt"),),
                ),
            },
        ):
            result = await sp.check_ssl_certificate("example.com")
        assert result.valid is True
        assert result.days_until_expiry > 0

    async def test_expired(self) -> None:
        sp = _make_provisioner()
        with patch.object(sp, "_get_ssl_cert", return_value=None):
            result = await sp.check_ssl_certificate("bad.example.com")
        assert result.valid is False


# === VerifyServiceHealth Testleri ===


class TestVerifyServiceHealth:
    """verify_service_health testleri."""

    async def test_healthy(self) -> None:
        sp = _make_provisioner()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch.dict(
            "sys.modules",
            {"httpx": MagicMock(AsyncClient=MagicMock(return_value=mock_client))},
        ):
            result = await sp.verify_service_health("http://localhost/health")
        assert result.status == ServiceType.HEALTHY

    async def test_unhealthy(self) -> None:
        sp = _make_provisioner()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch.dict(
            "sys.modules",
            {"httpx": MagicMock(AsyncClient=MagicMock(return_value=mock_client))},
        ):
            result = await sp.verify_service_health("http://localhost/health")
        assert result.status == ServiceType.DEGRADED
