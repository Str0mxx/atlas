"""ATLAS oto-kurulum modulu.

PackageManager ve DependencyResolver koordine ederek
guvenli kurulum, dogrulama ve geri alma saglar.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.core.bootstrap.dependency_resolver import DependencyResolver
from app.core.bootstrap.package_manager import PackageManager
from app.models.bootstrap import (
    InstallationPlan,
    InstallationRecord,
    InstallationResult,
    InstallationStatus,
    PackageManagerType,
    PackageStatus,
)

logger = logging.getLogger(__name__)


class AutoInstaller:
    """Oto-kurulum orkestratoru.

    PackageManager ve DependencyResolver'i koordine ederek
    guvenli, sirali kurulum gerceklestirir.

    Attributes:
        package_manager: Paket yonetici referansi.
        dependency_resolver: Bagimlilik cozumleyici referansi.
        require_approval: Kurulum icin onay gerekli mi.
        auto_install: Otomatik kuruluma izin var mi.
    """

    def __init__(
        self,
        package_manager: PackageManager | None = None,
        dependency_resolver: DependencyResolver | None = None,
        require_approval: bool | None = None,
        auto_install: bool | None = None,
    ) -> None:
        """AutoInstaller baslatir.

        Args:
            package_manager: Paket yoneticisi. None ise yeni olusturulur.
            dependency_resolver: Bagimlilik cozumleyici. None ise yeni olusturulur.
            require_approval: Onay gerekli mi. None ise config'den alinir.
            auto_install: Otomatik kurulum. None ise config'den alinir.
        """
        self.package_manager = package_manager or PackageManager()
        self.dependency_resolver = dependency_resolver or DependencyResolver()
        self.require_approval = (
            require_approval
            if require_approval is not None
            else settings.bootstrap_require_approval
        )
        self.auto_install = (
            auto_install
            if auto_install is not None
            else settings.bootstrap_auto_install
        )
        self._history: list[InstallationRecord] = []
        logger.info(
            "AutoInstaller olusturuldu (onay=%s, oto=%s)",
            self.require_approval,
            self.auto_install,
        )

    async def create_plan(
        self,
        packages: list[str],
        manager: PackageManagerType = PackageManagerType.PIP,
        dry_run: bool = False,
    ) -> InstallationPlan:
        """Kurulum plani olusturur.

        Args:
            packages: Kurulacak paket adlari.
            manager: Paket yoneticisi.
            dry_run: Kuru calistirma.

        Returns:
            Kurulum plani.
        """
        # Bagimliliklari cozumle
        for pkg in packages:
            self.dependency_resolver.add_dependency(pkg)

        graph = self.dependency_resolver.resolve()

        if graph.has_cycles:
            logger.warning("Dongusel bagimlilik tespit edildi")

        # Sirali kurulum kayitlari olustur
        install_order = graph.install_order if graph.install_order else packages
        records: list[InstallationRecord] = []
        for pkg_name in install_order:
            records.append(
                InstallationRecord(
                    package_name=pkg_name,
                    manager=manager,
                    dry_run=dry_run,
                )
            )

        plan = InstallationPlan(
            packages=records,
            total_packages=len(records),
            requires_approval=self.require_approval,
            dry_run=dry_run,
            estimated_duration=len(records) * 10.0,
        )
        logger.info(
            "Kurulum plani olusturuldu: %d paket, dry_run=%s",
            len(records),
            dry_run,
        )
        return plan

    async def execute_plan(
        self,
        plan: InstallationPlan,
        approved: bool = False,
    ) -> InstallationResult:
        """Kurulum planini calistirir.

        Args:
            plan: Calistirilacak plan.
            approved: Onaylanmis mi.

        Returns:
            Kurulum sonucu.
        """
        if not self._check_approval(plan, approved):
            return InstallationResult(
                plan_id=plan.id,
                success=False,
                failed=[r.package_name for r in plan.packages],
            )

        start_time = time.monotonic()
        installed: list[str] = []
        failed: list[str] = []

        plan.status = InstallationStatus.IN_PROGRESS

        for record in plan.packages:
            result = await self._install_with_progress(record)
            self._history.append(result)

            if result.status == InstallationStatus.COMPLETED:
                installed.append(result.package_name)
            else:
                failed.append(result.package_name)

        duration = time.monotonic() - start_time
        success = len(failed) == 0
        plan.status = (
            InstallationStatus.COMPLETED
            if success
            else InstallationStatus.FAILED
        )

        logger.info(
            "Kurulum plani tamamlandi: basarili=%d, basarisiz=%d",
            len(installed),
            len(failed),
        )
        return InstallationResult(
            plan_id=plan.id,
            success=success,
            installed=installed,
            failed=failed,
            total_duration=round(duration, 2),
        )

    async def install_single(
        self,
        package_name: str,
        version: str | None = None,
        manager: PackageManagerType = PackageManagerType.PIP,
    ) -> InstallationRecord:
        """Tek paket kurar.

        Args:
            package_name: Paket adi.
            version: Surum kisiti.
            manager: Paket yoneticisi.

        Returns:
            Kurulum kaydi.
        """
        record = await self.package_manager.install(
            package_name, version, manager
        )
        self._history.append(record)
        return record

    async def verify_installation(
        self,
        package_name: str,
        manager: PackageManagerType = PackageManagerType.PIP,
    ) -> bool:
        """Kurulumu dogrular.

        Args:
            package_name: Paket adi.
            manager: Paket yoneticisi.

        Returns:
            Yuklu mu.
        """
        info = await self.package_manager.check_installed(package_name, manager)
        return info.status == PackageStatus.INSTALLED

    async def rollback_plan(
        self,
        result: InstallationResult,
    ) -> list[str]:
        """Basarisiz plani geri alir.

        Args:
            result: Geri alinacak kurulum sonucu.

        Returns:
            Geri alinan paket adlari.
        """
        rolled_back: list[str] = []
        for pkg_name in result.installed:
            # Gecmisten kaydi bul
            record = None
            for r in reversed(self._history):
                if (
                    r.package_name == pkg_name
                    and r.status == InstallationStatus.COMPLETED
                ):
                    record = r
                    break

            if record:
                success = await self.package_manager.rollback(record)
                if success:
                    rolled_back.append(pkg_name)

        logger.info("Geri alma tamamlandi: %d paket", len(rolled_back))
        return rolled_back

    def get_history(self) -> list[InstallationRecord]:
        """Kurulum gecmisini dondurur.

        Returns:
            Kurulum kayitlari listesi.
        """
        return list(self._history)

    async def cleanup_failed(self) -> int:
        """Basarisiz kurulumlari temizler.

        Returns:
            Temizlenen kayit sayisi.
        """
        failed = [
            r
            for r in self._history
            if r.status == InstallationStatus.FAILED
        ]
        for record in failed:
            self._history.remove(record)
        logger.info("Basarisiz kayitlar temizlendi: %d", len(failed))
        return len(failed)

    def _check_approval(
        self,
        plan: InstallationPlan,
        approved: bool,
    ) -> bool:
        """Onay kontrolu yapar.

        Args:
            plan: Kontrol edilecek plan.
            approved: Kullanicidan gelen onay.

        Returns:
            Kuruluma devam edilebilir mi.
        """
        if plan.dry_run:
            return True
        if not plan.requires_approval:
            return True
        if approved:
            return True
        logger.warning("Kurulum onay bekliyor: %d paket", plan.total_packages)
        return False

    async def _install_with_progress(
        self,
        record: InstallationRecord,
    ) -> InstallationRecord:
        """Ilerleme takipli kurulum yapar.

        Args:
            record: Kurulum kaydi.

        Returns:
            Guncellenmis kurulum kaydi.
        """
        logger.info(
            "Kuruluyor: %s (%s)",
            record.package_name,
            record.manager.value,
        )
        result = await self.package_manager.install(
            record.package_name,
            record.version,
            record.manager,
            dry_run=record.dry_run,
        )
        return result
