"""ATLAS paket yonetim modulu.

pip, npm, apt/brew/choco ve docker icin birlesik paket yonetim arayuzu.
Kurulum, kaldirma, surum kontrolu ve geri alma destegi.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.models.bootstrap import (
    InstallationRecord,
    InstallationStatus,
    PackageInfo,
    PackageManagerType,
    PackageStatus,
)

logger = logging.getLogger(__name__)


class PackageManager:
    """Birlesik paket yoneticisi.

    Farkli paket yoneticileri icin tek arayuz saglar.
    Kuru calistirma (dry-run) ve geri alma destegi.

    Attributes:
        allowed_managers: Izin verilen paket yoneticileri.
        sandbox_mode: Sandbox modu (gercek kurulum engellensin mi).
        dry_run: Varsayilan kuru calistirma modu.
    """

    def __init__(
        self,
        allowed_managers: list[str] | None = None,
        sandbox_mode: bool | None = None,
        dry_run: bool = False,
    ) -> None:
        """PackageManager baslatir.

        Args:
            allowed_managers: Izin verilen paket yoneticisi adlari.
            sandbox_mode: Sandbox modu. None ise config'den alinir.
            dry_run: Varsayilan dry-run modu.
        """
        if allowed_managers is not None:
            self.allowed_managers = allowed_managers
        else:
            self.allowed_managers = [
                m.strip()
                for m in settings.bootstrap_allowed_installers.split(",")
                if m.strip()
            ]
        self.sandbox_mode = (
            sandbox_mode
            if sandbox_mode is not None
            else settings.bootstrap_sandbox_mode
        )
        self.dry_run = dry_run
        self._history: list[InstallationRecord] = []
        logger.info(
            "PackageManager olusturuldu (izin=%s, sandbox=%s)",
            self.allowed_managers,
            self.sandbox_mode,
        )

    async def install(
        self,
        package_name: str,
        version: str | None = None,
        manager: PackageManagerType = PackageManagerType.PIP,
        dry_run: bool | None = None,
    ) -> InstallationRecord:
        """Paket kurar.

        Args:
            package_name: Paket adi.
            version: Surum kisiti.
            manager: Paket yoneticisi.
            dry_run: Kuru calistirma. None ise self.dry_run kullanilir.

        Returns:
            Kurulum kaydi.
        """
        is_dry = dry_run if dry_run is not None else self.dry_run

        record = InstallationRecord(
            package_name=package_name,
            manager=manager,
            version=version,
            dry_run=is_dry,
        )

        if not self.is_manager_allowed(manager):
            record.status = InstallationStatus.FAILED
            record.error_message = f"{manager.value} paket yoneticisi izinli degil"
            self._history.append(record)
            return record

        if self.sandbox_mode or is_dry:
            record.status = InstallationStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)
            logger.info(
                "Paket kurulumu (dry-run): %s (%s)", package_name, manager.value
            )
            self._history.append(record)
            return record

        cmd = self._build_install_command(package_name, version, manager)
        record.status = InstallationStatus.IN_PROGRESS

        try:
            returncode, stdout, stderr = await self._run_command(cmd)
            if returncode == 0:
                record.status = InstallationStatus.COMPLETED
                record.completed_at = datetime.now(timezone.utc)
                record.rollback_info = {
                    "command": self._build_uninstall_command(package_name, manager),
                }
                logger.info("Paket kuruldu: %s", package_name)
            else:
                record.status = InstallationStatus.FAILED
                record.error_message = stderr or stdout
                logger.error("Paket kurulum hatasi: %s — %s", package_name, stderr)
        except Exception as exc:
            record.status = InstallationStatus.FAILED
            record.error_message = str(exc)
            logger.error("Paket kurulum istisnasi: %s — %s", package_name, exc)

        self._history.append(record)
        return record

    async def uninstall(
        self,
        package_name: str,
        manager: PackageManagerType = PackageManagerType.PIP,
        dry_run: bool | None = None,
    ) -> InstallationRecord:
        """Paket kaldirir.

        Args:
            package_name: Paket adi.
            manager: Paket yoneticisi.
            dry_run: Kuru calistirma.

        Returns:
            Islem kaydi.
        """
        is_dry = dry_run if dry_run is not None else self.dry_run

        record = InstallationRecord(
            package_name=package_name,
            manager=manager,
            dry_run=is_dry,
        )

        if self.sandbox_mode or is_dry:
            record.status = InstallationStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)
            self._history.append(record)
            return record

        cmd = self._build_uninstall_command(package_name, manager)
        try:
            returncode, stdout, stderr = await self._run_command(cmd)
            if returncode == 0:
                record.status = InstallationStatus.COMPLETED
                record.completed_at = datetime.now(timezone.utc)
            else:
                record.status = InstallationStatus.FAILED
                record.error_message = stderr or stdout
        except Exception as exc:
            record.status = InstallationStatus.FAILED
            record.error_message = str(exc)

        self._history.append(record)
        return record

    async def check_installed(
        self,
        package_name: str,
        manager: PackageManagerType = PackageManagerType.PIP,
    ) -> PackageInfo:
        """Paketin yuklu olup olmadigini kontrol eder.

        Args:
            package_name: Paket adi.
            manager: Paket yoneticisi.

        Returns:
            Paket bilgisi.
        """
        if manager == PackageManagerType.PIP:
            try:
                returncode, stdout, _ = await self._run_command(
                    ["pip", "show", package_name]
                )
                if returncode == 0:
                    version = None
                    for line in stdout.splitlines():
                        if line.startswith("Version:"):
                            version = line.split(":", 1)[1].strip()
                            break
                    return PackageInfo(
                        name=package_name,
                        version=version,
                        manager=manager,
                        status=PackageStatus.INSTALLED,
                    )
            except Exception:
                pass
            return PackageInfo(
                name=package_name,
                manager=manager,
                status=PackageStatus.NOT_INSTALLED,
            )

        # Diger paket yoneticileri icin basit kontrol
        return PackageInfo(
            name=package_name,
            manager=manager,
            status=PackageStatus.UNKNOWN,
        )

    async def check_version(
        self,
        package_name: str,
        manager: PackageManagerType = PackageManagerType.PIP,
    ) -> PackageInfo:
        """Paket surumunu kontrol eder.

        Args:
            package_name: Paket adi.
            manager: Paket yoneticisi.

        Returns:
            Paket bilgisi.
        """
        return await self.check_installed(package_name, manager)

    async def rollback(
        self,
        record: InstallationRecord,
    ) -> bool:
        """Kurulumu geri alir.

        Args:
            record: Geri alinacak kurulum kaydi.

        Returns:
            Basarili mi.
        """
        if record.status == InstallationStatus.ROLLED_BACK:
            return True

        if record.status != InstallationStatus.COMPLETED:
            logger.warning(
                "Geri alinamaz durum: %s (%s)",
                record.package_name,
                record.status.value,
            )
            return False

        result = await self.uninstall(record.package_name, record.manager)
        if result.status == InstallationStatus.COMPLETED:
            record.status = InstallationStatus.ROLLED_BACK
            return True
        return False

    def is_manager_allowed(
        self,
        manager: PackageManagerType,
    ) -> bool:
        """Paket yoneticisinin izinli olup olmadigini kontrol eder.

        Args:
            manager: Paket yoneticisi.

        Returns:
            Izinli mi.
        """
        return manager.value in self.allowed_managers

    async def _run_command(
        self,
        command: list[str],
        timeout: int = 120,
    ) -> tuple[int, str, str]:
        """Alt sureci calistirir.

        Args:
            command: Komut ve argumanlari.
            timeout: Zaman asimi (saniye).

        Returns:
            (return_code, stdout, stderr) tuple.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return (
                proc.returncode or 0,
                stdout_bytes.decode(errors="replace"),
                stderr_bytes.decode(errors="replace"),
            )
        except asyncio.TimeoutError:
            return (-1, "", "Zaman asimi")

    def _build_install_command(
        self,
        package_name: str,
        version: str | None,
        manager: PackageManagerType,
    ) -> list[str]:
        """Paket yoneticisine gore kurulum komutunu olusturur.

        Args:
            package_name: Paket adi.
            version: Surum kisiti.
            manager: Paket yoneticisi.

        Returns:
            Komut listesi.
        """
        pkg = f"{package_name}=={version}" if version else package_name

        commands: dict[PackageManagerType, list[str]] = {
            PackageManagerType.PIP: ["pip", "install", pkg],
            PackageManagerType.NPM: ["npm", "install", pkg],
            PackageManagerType.APT: ["apt-get", "install", "-y", package_name],
            PackageManagerType.BREW: ["brew", "install", package_name],
            PackageManagerType.CHOCO: ["choco", "install", package_name, "-y"],
            PackageManagerType.DOCKER: ["docker", "pull", package_name],
        }
        return commands.get(manager, ["echo", "unsupported"])

    def _build_uninstall_command(
        self,
        package_name: str,
        manager: PackageManagerType,
    ) -> list[str]:
        """Paket yoneticisine gore kaldirma komutunu olusturur.

        Args:
            package_name: Paket adi.
            manager: Paket yoneticisi.

        Returns:
            Komut listesi.
        """
        commands: dict[PackageManagerType, list[str]] = {
            PackageManagerType.PIP: ["pip", "uninstall", "-y", package_name],
            PackageManagerType.NPM: ["npm", "uninstall", package_name],
            PackageManagerType.APT: ["apt-get", "remove", "-y", package_name],
            PackageManagerType.BREW: ["brew", "uninstall", package_name],
            PackageManagerType.CHOCO: ["choco", "uninstall", package_name, "-y"],
            PackageManagerType.DOCKER: ["docker", "rmi", package_name],
        }
        return commands.get(manager, ["echo", "unsupported"])

    def get_installation_history(self) -> list[InstallationRecord]:
        """Kurulum gecmisini dondurur.

        Returns:
            Kurulum kayitlari listesi.
        """
        return list(self._history)
