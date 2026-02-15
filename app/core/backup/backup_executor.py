"""ATLAS Yedekleme Yurutucu modulu.

Tam yedekleme, artimsal yedekleme,
diferansiyel yedekleme, paralel yurutme
ve ilerleme takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BackupExecutor:
    """Yedekleme yurutucu.

    Yedekleme islemlerini yurutur.

    Attributes:
        _backups: Yedekleme kayitlari.
        _running: Calisan yedeklemeler.
    """

    def __init__(self) -> None:
        """Yurutucuyu baslatir."""
        self._backups: dict[
            str, dict[str, Any]
        ] = {}
        self._running: dict[
            str, dict[str, Any]
        ] = {}
        self._last_full: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "full": 0,
            "incremental": 0,
            "differential": 0,
            "failed": 0,
            "total_bytes": 0,
        }

        logger.info(
            "BackupExecutor baslatildi",
        )

    def run_full(
        self,
        backup_id: str,
        target: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Tam yedekleme calistirir.

        Args:
            backup_id: Yedekleme ID.
            target: Hedef.
            data: Yedeklenecek veri.

        Returns:
            Yedekleme sonucu.
        """
        start = time.time()
        backup_data = data or {}
        size = len(str(backup_data))

        record = {
            "backup_id": backup_id,
            "type": "full",
            "target": target,
            "status": "completed",
            "size_bytes": size,
            "data": dict(backup_data),
            "started_at": start,
            "completed_at": time.time(),
            "duration": time.time() - start,
        }

        self._backups[backup_id] = record
        self._last_full[target] = record
        self._stats["full"] += 1
        self._stats["total_bytes"] += size

        return {
            "backup_id": backup_id,
            "type": "full",
            "status": "completed",
            "size_bytes": size,
        }

    def run_incremental(
        self,
        backup_id: str,
        target: str,
        data: dict[str, Any] | None = None,
        parent_id: str = "",
    ) -> dict[str, Any]:
        """Artimsal yedekleme calistirir.

        Args:
            backup_id: Yedekleme ID.
            target: Hedef.
            data: Degisen veri.
            parent_id: Ust yedekleme ID.

        Returns:
            Yedekleme sonucu.
        """
        if not parent_id and (
            target not in self._last_full
        ):
            return {
                "backup_id": backup_id,
                "status": "failed",
                "error": "no_parent_backup",
            }

        start = time.time()
        backup_data = data or {}
        size = len(str(backup_data))

        record = {
            "backup_id": backup_id,
            "type": "incremental",
            "target": target,
            "parent_id": parent_id or (
                self._last_full[target][
                    "backup_id"
                ]
            ),
            "status": "completed",
            "size_bytes": size,
            "data": dict(backup_data),
            "started_at": start,
            "completed_at": time.time(),
        }

        self._backups[backup_id] = record
        self._stats["incremental"] += 1
        self._stats["total_bytes"] += size

        return {
            "backup_id": backup_id,
            "type": "incremental",
            "status": "completed",
            "size_bytes": size,
        }

    def run_differential(
        self,
        backup_id: str,
        target: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Diferansiyel yedekleme calistirir.

        Args:
            backup_id: Yedekleme ID.
            target: Hedef.
            data: Son full'dan beri degisen veri.

        Returns:
            Yedekleme sonucu.
        """
        if target not in self._last_full:
            return {
                "backup_id": backup_id,
                "status": "failed",
                "error": "no_full_backup",
            }

        start = time.time()
        backup_data = data or {}
        size = len(str(backup_data))

        record = {
            "backup_id": backup_id,
            "type": "differential",
            "target": target,
            "base_full_id": (
                self._last_full[target][
                    "backup_id"
                ]
            ),
            "status": "completed",
            "size_bytes": size,
            "data": dict(backup_data),
            "started_at": start,
            "completed_at": time.time(),
        }

        self._backups[backup_id] = record
        self._stats["differential"] += 1
        self._stats["total_bytes"] += size

        return {
            "backup_id": backup_id,
            "type": "differential",
            "status": "completed",
            "size_bytes": size,
        }

    def run_parallel(
        self,
        jobs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Paralel yedekleme calistirir.

        Args:
            jobs: Yedekleme isleri.

        Returns:
            Toplu sonuc.
        """
        results: list[dict[str, Any]] = []
        completed = 0
        failed = 0

        for job in jobs:
            btype = job.get("type", "full")
            bid = job["backup_id"]
            target = job.get("target", "")
            data = job.get("data")

            if btype == "full":
                result = self.run_full(
                    bid, target, data,
                )
            elif btype == "incremental":
                result = self.run_incremental(
                    bid, target, data,
                )
            elif btype == "differential":
                result = self.run_differential(
                    bid, target, data,
                )
            else:
                result = {
                    "backup_id": bid,
                    "status": "failed",
                    "error": "unknown_type",
                }

            results.append(result)
            if result["status"] == "completed":
                completed += 1
            else:
                failed += 1

        return {
            "total": len(jobs),
            "completed": completed,
            "failed": failed,
            "results": results,
        }

    def get_backup(
        self,
        backup_id: str,
    ) -> dict[str, Any] | None:
        """Yedekleme getirir.

        Args:
            backup_id: Yedekleme ID.

        Returns:
            Yedekleme bilgisi veya None.
        """
        return self._backups.get(backup_id)

    def get_progress(
        self,
        backup_id: str,
    ) -> dict[str, Any]:
        """Ilerleme bilgisi getirir.

        Args:
            backup_id: Yedekleme ID.

        Returns:
            Ilerleme bilgisi.
        """
        backup = self._backups.get(backup_id)
        if not backup:
            running = self._running.get(backup_id)
            if running:
                return {
                    "backup_id": backup_id,
                    "status": "running",
                    "progress": running.get(
                        "progress", 0,
                    ),
                }
            return {
                "backup_id": backup_id,
                "status": "not_found",
            }

        return {
            "backup_id": backup_id,
            "status": backup["status"],
            "progress": 100,
        }

    def list_backups(
        self,
        target: str | None = None,
        backup_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Yedeklemeleri listeler.

        Args:
            target: Hedef filtresi.
            backup_type: Tip filtresi.
            limit: Limit.

        Returns:
            Yedekleme listesi.
        """
        backups = list(
            self._backups.values(),
        )
        if target:
            backups = [
                b for b in backups
                if b.get("target") == target
            ]
        if backup_type:
            backups = [
                b for b in backups
                if b.get("type") == backup_type
            ]
        return backups[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return dict(self._stats)

    @property
    def backup_count(self) -> int:
        """Yedekleme sayisi."""
        return len(self._backups)

    @property
    def full_count(self) -> int:
        """Tam yedekleme sayisi."""
        return self._stats["full"]

    @property
    def incremental_count(self) -> int:
        """Artimsal yedekleme sayisi."""
        return self._stats["incremental"]

    @property
    def total_bytes(self) -> int:
        """Toplam boyut."""
        return self._stats["total_bytes"]
