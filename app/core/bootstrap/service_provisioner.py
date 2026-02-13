"""ATLAS servis provizyon modulu.

Veritabani baglanti testi, API anahtar uretimi,
SSL sertifika kontrolu, port ve servis saglik dogrulama.
"""

import asyncio
import logging
import secrets
import socket
import ssl
import time
from datetime import datetime, timezone
from typing import Any

from app.models.bootstrap import (
    PortCheck,
    SSLInfo,
    ServiceCheck,
    ServiceType,
)

logger = logging.getLogger(__name__)


class ServiceProvisioner:
    """Servis provizyon sinifi.

    Servislerin saglik kontrolu, port kontrolu,
    API key uretimi ve SSL dogrulamasi.
    """

    def __init__(self) -> None:
        """ServiceProvisioner baslatir."""
        logger.info("ServiceProvisioner olusturuldu")

    async def check_postgresql(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "atlas_db",
    ) -> ServiceCheck:
        """PostgreSQL baglanti testi.

        Args:
            host: Sunucu adresi.
            port: Port numarasi.
            database: Veritabani adi.

        Returns:
            Servis kontrol sonucu.
        """
        start = time.monotonic()
        connected = await self._tcp_connect(host, port)
        elapsed = (time.monotonic() - start) * 1000

        status = ServiceType.HEALTHY if connected else ServiceType.UNREACHABLE
        return ServiceCheck(
            name="postgresql",
            status=status,
            host=host,
            port=port,
            response_time_ms=round(elapsed, 2),
            details={"database": database},
        )

    async def check_redis(
        self,
        host: str = "localhost",
        port: int = 6379,
    ) -> ServiceCheck:
        """Redis baglanti testi.

        Args:
            host: Sunucu adresi.
            port: Port numarasi.

        Returns:
            Servis kontrol sonucu.
        """
        start = time.monotonic()
        connected = await self._tcp_connect(host, port)
        elapsed = (time.monotonic() - start) * 1000

        status = ServiceType.HEALTHY if connected else ServiceType.UNREACHABLE
        return ServiceCheck(
            name="redis",
            status=status,
            host=host,
            port=port,
            response_time_ms=round(elapsed, 2),
        )

    async def check_sqlite(
        self,
        db_path: str = ":memory:",
    ) -> ServiceCheck:
        """SQLite baglanti testi.

        Args:
            db_path: Veritabani dosya yolu.

        Returns:
            Servis kontrol sonucu.
        """
        start = time.monotonic()
        try:
            import aiosqlite

            async with aiosqlite.connect(db_path) as db:
                await db.execute("SELECT 1")
            elapsed = (time.monotonic() - start) * 1000
            return ServiceCheck(
                name="sqlite",
                status=ServiceType.HEALTHY,
                host="local",
                response_time_ms=round(elapsed, 2),
                details={"db_path": db_path},
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            logger.error("SQLite kontrol hatasi: %s", exc)
            return ServiceCheck(
                name="sqlite",
                status=ServiceType.UNREACHABLE,
                host="local",
                response_time_ms=round(elapsed, 2),
                details={"error": str(exc)},
            )

    def generate_api_key(
        self,
        length: int = 32,
        prefix: str = "atlas_",
    ) -> str:
        """Guvenli API anahtari uretir.

        Args:
            length: Anahtar uzunlugu (prefix haric).
            prefix: Anahtar oneki.

        Returns:
            Uretilen API anahtari.
        """
        key = secrets.token_urlsafe(length)
        return f"{prefix}{key}"

    def generate_secret_key(
        self,
        length: int = 64,
    ) -> str:
        """Guvenli gizli anahtar uretir.

        Args:
            length: Anahtar uzunlugu (byte).

        Returns:
            Hex formatinda gizli anahtar.
        """
        return secrets.token_hex(length)

    async def check_ssl_certificate(
        self,
        domain: str,
        port: int = 443,
    ) -> SSLInfo:
        """SSL sertifika bilgisini kontrol eder.

        Args:
            domain: Alan adi.
            port: SSL portu.

        Returns:
            SSL sertifika bilgisi.
        """
        try:
            loop = asyncio.get_event_loop()
            cert_info = await asyncio.wait_for(
                loop.run_in_executor(
                    None, self._get_ssl_cert, domain, port
                ),
                timeout=10,
            )
            if cert_info is None:
                return SSLInfo(domain=domain)

            # Sertifika son kullanma tarihi
            not_after = cert_info.get("notAfter", "")
            expires_at = None
            days_until = 0
            if not_after:
                try:
                    expires_at = datetime.strptime(
                        not_after, "%b %d %H:%M:%S %Y %Z"
                    ).replace(tzinfo=timezone.utc)
                    days_until = (
                        expires_at - datetime.now(timezone.utc)
                    ).days
                except (ValueError, TypeError):
                    pass

            issuer_parts = cert_info.get("issuer", ())
            issuer = ""
            for part in issuer_parts:
                for key, value in part:
                    if key == "organizationName":
                        issuer = value

            return SSLInfo(
                domain=domain,
                valid=True,
                expires_at=expires_at,
                issuer=issuer,
                days_until_expiry=days_until,
            )
        except Exception as exc:
            logger.error("SSL kontrol hatasi (%s): %s", domain, exc)
            return SSLInfo(domain=domain)

    def _get_ssl_cert(
        self,
        domain: str,
        port: int,
    ) -> dict[str, Any] | None:
        """SSL sertifika bilgisini alir (senkron).

        Args:
            domain: Alan adi.
            port: SSL portu.

        Returns:
            Sertifika bilgi sozlugu veya None.
        """
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    return ssock.getpeercert()  # type: ignore[return-value]
        except Exception:
            return None

    async def check_port(
        self,
        port: int,
        host: str = "localhost",
    ) -> PortCheck:
        """Port kullanilabilirligini kontrol eder.

        Args:
            port: Port numarasi.
            host: Host adresi.

        Returns:
            Port kontrol sonucu.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            # result == 0 ise port acik (biri kullaniyur)
            return PortCheck(port=port, available=result != 0)
        except OSError:
            return PortCheck(port=port, available=False)

    async def check_ports(
        self,
        ports: list[int],
        host: str = "localhost",
    ) -> list[PortCheck]:
        """Birden fazla portu kontrol eder.

        Args:
            ports: Port numaralari.
            host: Host adresi.

        Returns:
            Port kontrol sonuclari.
        """
        results: list[PortCheck] = []
        for port in ports:
            result = await self.check_port(port, host)
            results.append(result)
        return results

    async def verify_service_health(
        self,
        url: str,
        timeout: float = 5.0,
    ) -> ServiceCheck:
        """HTTP endpointi ile servis sagligini dogrular.

        Args:
            url: Kontrol edilecek URL.
            timeout: Zaman asimi (saniye).

        Returns:
            Servis kontrol sonucu.
        """
        start = time.monotonic()
        try:
            import httpx

            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
                elapsed = (time.monotonic() - start) * 1000
                status = (
                    ServiceType.HEALTHY
                    if resp.status_code < 400
                    else ServiceType.DEGRADED
                )
                return ServiceCheck(
                    name=url,
                    status=status,
                    response_time_ms=round(elapsed, 2),
                    details={"status_code": resp.status_code},
                )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return ServiceCheck(
                name=url,
                status=ServiceType.UNREACHABLE,
                response_time_ms=round(elapsed, 2),
                details={"error": str(exc)},
            )

    async def _tcp_connect(
        self,
        host: str,
        port: int,
        timeout: float = 3.0,
    ) -> bool:
        """TCP baglanti testi.

        Args:
            host: Sunucu adresi.
            port: Port numarasi.
            timeout: Zaman asimi.

        Returns:
            Baglanti basarili mi.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except OSError:
            return False
