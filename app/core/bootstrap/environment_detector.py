"""ATLAS ortam tespit modulu.

Isletim sistemi, yuklu yazilimlar, sistem kaynaklari
ve ag yeteneklerini tespit eder.
"""

import asyncio
import logging
import os
import platform
import shutil
import socket
import sys
from typing import Any

from app.models.bootstrap import (
    EnvironmentInfo,
    NetworkInfo,
    OSType,
    ResourceInfo,
    SoftwareInfo,
)

logger = logging.getLogger(__name__)

# Taranacak varsayilan yazilimlar
DEFAULT_SOFTWARE = [
    "python",
    "python3",
    "pip",
    "pip3",
    "node",
    "npm",
    "npx",
    "docker",
    "docker-compose",
    "git",
    "psql",
    "redis-cli",
    "curl",
    "wget",
]


class EnvironmentDetector:
    """Ortam tespit sinifi.

    Isletim sistemi, yuklu yazilimlar, sistem kaynaklari
    ve ag yeteneklerini tarar.

    Attributes:
        software_list: Taranacak yazilim listesi.
    """

    def __init__(
        self,
        software_list: list[str] | None = None,
    ) -> None:
        """EnvironmentDetector baslatir.

        Args:
            software_list: Taranacak yazilim isimleri. None ise DEFAULT_SOFTWARE kullanilir.
        """
        self.software_list = software_list or list(DEFAULT_SOFTWARE)
        logger.info(
            "EnvironmentDetector olusturuldu (yazilim_sayisi=%d)",
            len(self.software_list),
        )

    async def detect(self) -> EnvironmentInfo:
        """Tam ortam taramasi yapar.

        Returns:
            Ortam bilgisi.
        """
        os_type, os_version = self.detect_os()
        python_version = self.detect_python_version()
        software = self.detect_software()
        resources = await self.detect_resources()
        network = await self.detect_network()
        missing = self.detect_missing_dependencies()

        info = EnvironmentInfo(
            os_type=os_type,
            os_version=os_version,
            python_version=python_version,
            software=software,
            resources=resources,
            network=network,
            missing_dependencies=missing,
        )
        logger.info(
            "Ortam taramasi tamamlandi: os=%s, yazilim=%d, eksik=%d",
            os_type.value,
            len(software),
            len(missing),
        )
        return info

    def detect_os(self) -> tuple[OSType, str]:
        """Isletim sistemi tespit eder.

        Returns:
            (os_type, os_version) tuple.
        """
        system = platform.system().lower()
        version = platform.version()

        if system == "windows":
            os_type = OSType.WINDOWS
        elif system == "linux":
            os_type = OSType.LINUX
        elif system == "darwin":
            os_type = OSType.MACOS
        else:
            os_type = OSType.UNKNOWN

        return os_type, version

    def detect_python_version(self) -> str:
        """Python surumunu dondurur.

        Returns:
            Python surum stringi.
        """
        return sys.version.split()[0]

    def detect_software(
        self,
        names: list[str] | None = None,
    ) -> list[SoftwareInfo]:
        """Yuklu yazilimlari tespit eder.

        Args:
            names: Taranacak yazilim listesi. None ise self.software_list kullanilir.

        Returns:
            Yazilim bilgileri listesi.
        """
        targets = names or self.software_list
        results: list[SoftwareInfo] = []
        for name in targets:
            results.append(self._check_software(name))
        return results

    def _check_software(self, name: str) -> SoftwareInfo:
        """Tek yazilimi kontrol eder.

        Args:
            name: Yazilim adi.

        Returns:
            Yazilim bilgisi.
        """
        path = shutil.which(name)
        return SoftwareInfo(
            name=name,
            path=path,
            available=path is not None,
        )

    async def detect_resources(self) -> ResourceInfo:
        """Sistem kaynaklarini tespit eder.

        Returns:
            Kaynak bilgisi.
        """
        cpu_cores = os.cpu_count() or 0

        # Disk alani
        try:
            usage = shutil.disk_usage(os.getcwd())
            total_disk_mb = usage.total / (1024 * 1024)
            available_disk_mb = usage.free / (1024 * 1024)
        except OSError:
            total_disk_mb = 0.0
            available_disk_mb = 0.0

        # RAM — psutil opsiyonel
        total_ram_mb = 0.0
        available_ram_mb = 0.0
        try:
            import psutil

            mem = psutil.virtual_memory()
            total_ram_mb = mem.total / (1024 * 1024)
            available_ram_mb = mem.available / (1024 * 1024)
        except ImportError:
            logger.debug("psutil yuklu degil, RAM bilgisi alinamiyor")

        return ResourceInfo(
            cpu_cores=cpu_cores,
            total_ram_mb=round(total_ram_mb, 1),
            available_ram_mb=round(available_ram_mb, 1),
            total_disk_mb=round(total_disk_mb, 1),
            available_disk_mb=round(available_disk_mb, 1),
        )

    async def detect_network(
        self,
        ports_to_check: list[int] | None = None,
    ) -> NetworkInfo:
        """Ag yeteneklerini tespit eder.

        Args:
            ports_to_check: Kontrol edilecek portlar.

        Returns:
            Ag bilgisi.
        """
        internet = await self._check_internet()
        dns = await self._check_dns()

        checked_ports: dict[int, bool] = {}
        available_ports: list[int] = []
        for port in ports_to_check or []:
            avail = await self._check_port(port)
            checked_ports[port] = avail
            if avail:
                available_ports.append(port)

        return NetworkInfo(
            internet_access=internet,
            dns_available=dns,
            available_ports=available_ports,
            checked_ports=checked_ports,
        )

    async def _check_internet(self) -> bool:
        """Internet erisimini test eder.

        Returns:
            Internet erisilebilir mi.
        """
        try:
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: socket.create_connection(("8.8.8.8", 53), timeout=3),
                ),
                timeout=5,
            )
            return True
        except (OSError, asyncio.TimeoutError):
            return False

    async def _check_dns(self) -> bool:
        """DNS cozumlemeyi test eder.

        Returns:
            DNS calisiyor mu.
        """
        try:
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: socket.getaddrinfo("dns.google", 443),
                ),
                timeout=5,
            )
            return True
        except (OSError, asyncio.TimeoutError, socket.gaierror):
            return False

    async def _check_port(self, port: int, host: str = "localhost") -> bool:
        """Port kullanilabilirligini kontrol eder.

        Args:
            port: Port numarasi.
            host: Host adresi.

        Returns:
            Port kullanilabilir mi (bind yapilabiliyor mu).
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            # connect_ex basarili ise port acik (bir servis dinliyor)
            # Port "kullanilabilir" = bos = bind edilebilir
            return result != 0
        except OSError:
            return False

    def detect_missing_dependencies(
        self,
        required: list[str] | None = None,
    ) -> list[str]:
        """Eksik bagimliliklari tespit eder.

        Args:
            required: Zorunlu yazilim listesi. None ise software_list kullanilir.

        Returns:
            Eksik yazilim adlari.
        """
        targets = required or self.software_list
        missing: list[str] = []
        for name in targets:
            if shutil.which(name) is None:
                missing.append(name)
        return missing
