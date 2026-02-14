"""ATLAS Migrasyon Yoneticisi modulu.

Ileri migrasyon, geri migrasyon,
veri migrasyon, sema migrasyon
ve migrasyon testi.
"""

import logging
import time
from typing import Any, Callable

from app.models.versioning import (
    MigrationRecord,
    MigrationStatus,
)

logger = logging.getLogger(__name__)


class MigrationManager:
    """Migrasyon yoneticisi.

    Veri ve sema migrasyonlarini
    yonetir ve calistirir.

    Attributes:
        _migrations: Migrasyon kayitlari.
        _forward_fns: Ileri fonksiyonlari.
        _backward_fns: Geri fonksiyonlari.
    """

    def __init__(self) -> None:
        """Migrasyon yoneticisini baslatir."""
        self._migrations: dict[
            str, MigrationRecord
        ] = {}
        self._forward_fns: dict[
            str, Callable[[], Any]
        ] = {}
        self._backward_fns: dict[
            str, Callable[[], Any]
        ] = {}
        self._order: list[str] = []
        self._applied: list[str] = []

        logger.info(
            "MigrationManager baslatildi",
        )

    def register_migration(
        self,
        name: str,
        forward_fn: Callable[[], Any],
        backward_fn: Callable[[], Any] | None = None,
    ) -> MigrationRecord:
        """Migrasyon kaydeder.

        Args:
            name: Migrasyon adi.
            forward_fn: Ileri fonksiyon.
            backward_fn: Geri fonksiyon.

        Returns:
            Migrasyon kaydi.
        """
        record = MigrationRecord(name=name)
        self._migrations[
            record.migration_id
        ] = record
        self._forward_fns[
            record.migration_id
        ] = forward_fn
        if backward_fn:
            self._backward_fns[
                record.migration_id
            ] = backward_fn
        self._order.append(record.migration_id)
        return record

    def run_forward(
        self,
        migration_id: str,
    ) -> dict[str, Any]:
        """Ileri migrasyon calistirir.

        Args:
            migration_id: Migrasyon ID.

        Returns:
            Calistirma sonucu.
        """
        record = self._migrations.get(
            migration_id,
        )
        if not record:
            return {
                "success": False,
                "reason": "migration_not_found",
            }

        fn = self._forward_fns.get(migration_id)
        if not fn:
            return {
                "success": False,
                "reason": "no_forward_function",
            }

        record.status = MigrationStatus.RUNNING
        record.direction = "forward"
        start = time.time()

        try:
            fn()
            record.status = MigrationStatus.COMPLETED
            record.duration = time.time() - start
            self._applied.append(migration_id)
            return {
                "success": True,
                "migration_id": migration_id,
                "direction": "forward",
                "duration": record.duration,
            }
        except Exception as e:
            record.status = MigrationStatus.FAILED
            record.duration = time.time() - start
            return {
                "success": False,
                "error": str(e),
                "duration": record.duration,
            }

    def run_backward(
        self,
        migration_id: str,
    ) -> dict[str, Any]:
        """Geri migrasyon calistirir.

        Args:
            migration_id: Migrasyon ID.

        Returns:
            Calistirma sonucu.
        """
        record = self._migrations.get(
            migration_id,
        )
        if not record:
            return {
                "success": False,
                "reason": "migration_not_found",
            }

        fn = self._backward_fns.get(migration_id)
        if not fn:
            return {
                "success": False,
                "reason": "no_backward_function",
            }

        record.status = MigrationStatus.RUNNING
        record.direction = "backward"
        start = time.time()

        try:
            fn()
            record.status = (
                MigrationStatus.ROLLED_BACK
            )
            record.duration = time.time() - start
            if migration_id in self._applied:
                self._applied.remove(migration_id)
            return {
                "success": True,
                "migration_id": migration_id,
                "direction": "backward",
                "duration": record.duration,
            }
        except Exception as e:
            record.status = MigrationStatus.FAILED
            record.duration = time.time() - start
            return {
                "success": False,
                "error": str(e),
                "duration": record.duration,
            }

    def run_all_pending(
        self,
    ) -> list[dict[str, Any]]:
        """Bekleyen migrasyonlari calistirir.

        Returns:
            Calistirma sonuclari.
        """
        results: list[dict[str, Any]] = []

        for mid in self._order:
            if mid not in self._applied:
                result = self.run_forward(mid)
                results.append(result)
                if not result["success"]:
                    break

        return results

    def rollback_last(
        self,
    ) -> dict[str, Any]:
        """Son migrasyonu geri alir.

        Returns:
            Geri alma sonucu.
        """
        if not self._applied:
            return {
                "success": False,
                "reason": "no_applied_migrations",
            }

        last_id = self._applied[-1]
        return self.run_backward(last_id)

    def test_migration(
        self,
        migration_id: str,
    ) -> dict[str, Any]:
        """Migrasyonu test eder.

        Args:
            migration_id: Migrasyon ID.

        Returns:
            Test sonucu.
        """
        record = self._migrations.get(
            migration_id,
        )
        if not record:
            return {
                "success": False,
                "reason": "migration_not_found",
            }

        has_forward = (
            migration_id in self._forward_fns
        )
        has_backward = (
            migration_id in self._backward_fns
        )

        return {
            "migration_id": migration_id,
            "name": record.name,
            "has_forward": has_forward,
            "has_backward": has_backward,
            "reversible": has_backward,
            "status": record.status.value,
        }

    def get_migration(
        self,
        migration_id: str,
    ) -> MigrationRecord | None:
        """Migrasyon getirir.

        Args:
            migration_id: Migrasyon ID.

        Returns:
            Migrasyon veya None.
        """
        return self._migrations.get(migration_id)

    def get_pending(
        self,
    ) -> list[MigrationRecord]:
        """Bekleyen migrasyonlari getirir.

        Returns:
            Bekleyen migrasyonlar.
        """
        return [
            self._migrations[mid]
            for mid in self._order
            if mid not in self._applied
            and mid in self._migrations
        ]

    def get_applied(
        self,
    ) -> list[MigrationRecord]:
        """Uygulanmis migrasyonlari getirir.

        Returns:
            Uygulanmis migrasyonlar.
        """
        return [
            self._migrations[mid]
            for mid in self._applied
            if mid in self._migrations
        ]

    @property
    def migration_count(self) -> int:
        """Migrasyon sayisi."""
        return len(self._migrations)

    @property
    def applied_count(self) -> int:
        """Uygulanmis sayisi."""
        return len(self._applied)

    @property
    def pending_count(self) -> int:
        """Bekleyen sayisi."""
        return len(self._order) - len(
            self._applied,
        )
