"""ATLAS kendi kendini guncelleme modulu.

Surum kontrolu, indirme yonetimi, hot-reload takibi,
migrasyon planlama ve geri alma.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.bootstrap import (
    MigrationPlan,
    UpgradeRecord,
    UpgradeStatus,
    VersionInfo,
)

logger = logging.getLogger(__name__)

# Mevcut ATLAS surumu
CURRENT_VERSION = "0.1.0"


class SelfUpgrade:
    """Kendi kendini guncelleme sinifi.

    Surum karsilastirma, indirme yonetimi, migrasyon planlama
    ve geri alma destegi saglar.

    Attributes:
        current_version: Mevcut ATLAS surumu.
    """

    def __init__(
        self,
        current_version: str | None = None,
    ) -> None:
        """SelfUpgrade baslatir.

        Args:
            current_version: Mevcut surum. None ise CURRENT_VERSION kullanilir.
        """
        self.current_version = current_version or CURRENT_VERSION
        self._history: list[UpgradeRecord] = []
        logger.info(
            "SelfUpgrade olusturuldu (surum=%s)", self.current_version
        )

    async def check_for_updates(
        self,
        source_url: str | None = None,
        latest_version: str | None = None,
    ) -> VersionInfo:
        """Guncelleme kontrol eder.

        Args:
            source_url: Guncelleme kaynak URL. (gelecek kullanim icin)
            latest_version: Test/mock icin en son surum.

        Returns:
            Surum bilgisi.
        """
        if latest_version is None:
            # Gercek uygulamada URL'den cekilir
            latest_version = self.current_version

        update_available = self.compare_versions(
            self.current_version, latest_version
        ) < 0
        breaking = self._is_breaking_change(
            self.current_version, latest_version
        )

        info = VersionInfo(
            current_version=self.current_version,
            latest_version=latest_version,
            update_available=update_available,
            breaking_changes=["Major surum degisikligi"] if breaking else [],
        )
        logger.info(
            "Guncelleme kontrolu: mevcut=%s, son=%s, guncelleme=%s",
            self.current_version,
            latest_version,
            update_available,
        )
        return info

    def compare_versions(
        self,
        version_a: str,
        version_b: str,
    ) -> int:
        """Surumleri karsilastirir.

        Args:
            version_a: Birinci surum.
            version_b: Ikinci surum.

        Returns:
            -1 (a < b), 0 (a == b), 1 (a > b).
        """
        parts_a = self.parse_version(version_a)
        parts_b = self.parse_version(version_b)

        for a, b in zip(parts_a, parts_b):
            if a < b:
                return -1
            if a > b:
                return 1

        if len(parts_a) < len(parts_b):
            return -1
        if len(parts_a) > len(parts_b):
            return 1
        return 0

    def parse_version(
        self,
        version: str,
    ) -> tuple[int, ...]:
        """Surum stringini tuple'a cevirir.

        Args:
            version: Surum stringi (orn: '1.2.3').

        Returns:
            Surum parcalari tuple.
        """
        parts: list[int] = []
        for part in version.split("."):
            try:
                parts.append(int(part))
            except ValueError:
                # Alfa/beta sonekleri icin 0 kullan
                numeric = ""
                for c in part:
                    if c.isdigit():
                        numeric += c
                    else:
                        break
                parts.append(int(numeric) if numeric else 0)
        return tuple(parts)

    async def plan_migration(
        self,
        from_version: str,
        to_version: str,
    ) -> MigrationPlan:
        """Migrasyon plani olusturur.

        Args:
            from_version: Baslangic surumu.
            to_version: Hedef surum.

        Returns:
            Migrasyon plani.
        """
        breaking = self._is_breaking_change(from_version, to_version)
        steps: list[str] = []
        config_changes: dict[str, Any] = {}

        from_parts = self.parse_version(from_version)
        to_parts = self.parse_version(to_version)

        if to_parts[0] > from_parts[0]:
            steps.append(f"Major guncelleme: {from_version} -> {to_version}")
            steps.append("Veritabani migrasyonu gerekli")
            config_changes["major_upgrade"] = True
        elif len(to_parts) > 1 and len(from_parts) > 1 and to_parts[1] > from_parts[1]:
            steps.append(f"Minor guncelleme: {from_version} -> {to_version}")
            steps.append("Yapilandirma kontrolu gerekli")
        else:
            steps.append(f"Patch guncelleme: {from_version} -> {to_version}")

        plan = MigrationPlan(
            db_migrations=steps,
            config_changes=config_changes,
            estimated_downtime=30.0 if breaking else 0.0,
            reversible=not breaking,
        )
        logger.info(
            "Migrasyon plani olusturuldu: %s -> %s (adim=%d)",
            from_version,
            to_version,
            len(steps),
        )
        return plan

    async def apply_upgrade(
        self,
        version_info: VersionInfo,
    ) -> UpgradeRecord:
        """Guncellemeyi uygular.

        Args:
            version_info: Uygulanacak surum bilgisi.

        Returns:
            Guncelleme kaydi.
        """
        record = UpgradeRecord(
            from_version=self.current_version,
            to_version=version_info.latest_version,
            status=UpgradeStatus.APPLYING,
        )

        if not version_info.update_available:
            record.status = UpgradeStatus.UP_TO_DATE
            record.completed_at = datetime.now(timezone.utc)
            self._history.append(record)
            return record

        try:
            # Gercek uygulamada dosya indirme, migrasyon vb. yapilir
            migration = await self.plan_migration(
                self.current_version, version_info.latest_version
            )

            record.migration_steps = migration.db_migrations
            record.status = UpgradeStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)
            self.current_version = version_info.latest_version

            logger.info(
                "Guncelleme tamamlandi: %s -> %s",
                record.from_version,
                record.to_version,
            )
        except Exception as exc:
            record.status = UpgradeStatus.FAILED
            record.completed_at = datetime.now(timezone.utc)
            logger.error("Guncelleme hatasi: %s", exc)

        self._history.append(record)
        return record

    async def rollback(
        self,
        upgrade_record: UpgradeRecord,
    ) -> bool:
        """Guncellemeyi geri alir.

        Args:
            upgrade_record: Geri alinacak guncelleme kaydi.

        Returns:
            Basarili mi.
        """
        if not upgrade_record.rollback_available:
            logger.warning("Geri alma kullanilabilir degil")
            return False

        if upgrade_record.status == UpgradeStatus.ROLLED_BACK:
            return True

        try:
            self.current_version = upgrade_record.from_version
            upgrade_record.status = UpgradeStatus.ROLLED_BACK
            logger.info(
                "Guncelleme geri alindi: %s -> %s",
                upgrade_record.to_version,
                upgrade_record.from_version,
            )
            return True
        except Exception as exc:
            logger.error("Geri alma hatasi: %s", exc)
            return False

    def check_hot_reload_capable(self) -> bool:
        """Hot-reload uygunlugunu kontrol eder.

        Returns:
            Hot-reload destekleniyor mu.
        """
        # Hot-reload sadece development ortaminda
        try:
            from app.config import settings as app_settings

            return app_settings.app_debug
        except ImportError:
            return False

    def get_upgrade_history(self) -> list[UpgradeRecord]:
        """Guncelleme gecmisini dondurur.

        Returns:
            Guncelleme kayitlari.
        """
        return list(self._history)

    def _is_breaking_change(
        self,
        from_version: str,
        to_version: str,
    ) -> bool:
        """Kirilici degisiklik olup olmadigini kontrol eder.

        Args:
            from_version: Mevcut surum.
            to_version: Hedef surum.

        Returns:
            Major surum degisikligi var mi.
        """
        from_parts = self.parse_version(from_version)
        to_parts = self.parse_version(to_version)

        if not from_parts or not to_parts:
            return False

        return to_parts[0] > from_parts[0]
