"""ATLAS Veri Senkronizasyonu modulu.

Cift yonlu senkronizasyon, catisma cozumu,
delta/full sync ve zamanlanmis sync.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.integration import SyncMode, SyncRecord

logger = logging.getLogger(__name__)


class DataSync:
    """Veri senkronizasyonu.

    Dis servisler arasinda veri
    senkronizasyonunu yonetir.

    Attributes:
        _syncs: Sync kayitlari.
        _schedules: Zamanlanmis sync'ler.
        _conflict_rules: Catisma cozum kurallari.
        _last_sync: Son sync zamanlari.
    """

    def __init__(self) -> None:
        """Veri senkronizasyonunu baslatir."""
        self._syncs: list[SyncRecord] = []
        self._schedules: list[dict[str, Any]] = []
        self._conflict_rules: dict[str, str] = {}
        self._last_sync: dict[str, str] = {}

        logger.info("DataSync baslatildi")

    def full_sync(
        self,
        source: str,
        target: str,
        data: list[dict[str, Any]],
    ) -> SyncRecord:
        """Tam senkronizasyon yapar.

        Args:
            source: Kaynak.
            target: Hedef.
            data: Sync verileri.

        Returns:
            Sync kaydi.
        """
        record = SyncRecord(
            source=source,
            target=target,
            mode=SyncMode.FULL,
            records_synced=len(data),
            success=True,
        )
        self._syncs.append(record)
        self._last_sync[f"{source}:{target}"] = (
            datetime.now(timezone.utc).isoformat()
        )

        logger.info(
            "Full sync tamamlandi: %s -> %s (%d kayit)",
            source, target, len(data),
        )
        return record

    def delta_sync(
        self,
        source: str,
        target: str,
        changes: list[dict[str, Any]],
    ) -> SyncRecord:
        """Delta senkronizasyon yapar.

        Args:
            source: Kaynak.
            target: Hedef.
            changes: Degisiklikler.

        Returns:
            Sync kaydi.
        """
        record = SyncRecord(
            source=source,
            target=target,
            mode=SyncMode.DELTA,
            records_synced=len(changes),
            success=True,
        )
        self._syncs.append(record)
        self._last_sync[f"{source}:{target}"] = (
            datetime.now(timezone.utc).isoformat()
        )

        logger.info(
            "Delta sync tamamlandi: %s -> %s (%d degisiklik)",
            source, target, len(changes),
        )
        return record

    def bidirectional_sync(
        self,
        service_a: str,
        service_b: str,
        data_a: list[dict[str, Any]],
        data_b: list[dict[str, Any]],
    ) -> SyncRecord:
        """Cift yonlu senkronizasyon yapar.

        Args:
            service_a: Servis A.
            service_b: Servis B.
            data_a: A verisi.
            data_b: B verisi.

        Returns:
            Sync kaydi.
        """
        # Catisma kontrolu
        conflicts = self._detect_conflicts(data_a, data_b)
        resolved = 0

        for conflict in conflicts:
            resolution = self._resolve_conflict(
                conflict, service_a, service_b,
            )
            if resolution.get("resolved"):
                resolved += 1

        total = len(data_a) + len(data_b)
        record = SyncRecord(
            source=service_a,
            target=service_b,
            mode=SyncMode.BIDIRECTIONAL,
            records_synced=total,
            conflicts=len(conflicts),
            success=True,
        )
        self._syncs.append(record)

        key_ab = f"{service_a}:{service_b}"
        key_ba = f"{service_b}:{service_a}"
        now = datetime.now(timezone.utc).isoformat()
        self._last_sync[key_ab] = now
        self._last_sync[key_ba] = now

        logger.info(
            "Bidirectional sync: %s <-> %s (%d kayit, %d catisma)",
            service_a, service_b, total, len(conflicts),
        )
        return record

    def set_conflict_rule(
        self,
        key: str,
        strategy: str,
    ) -> None:
        """Catisma cozum kurali ayarlar.

        Args:
            key: Alan adi.
            strategy: Strateji (source_wins/target_wins/latest/manual).
        """
        self._conflict_rules[key] = strategy

    def schedule_sync(
        self,
        source: str,
        target: str,
        mode: SyncMode,
        interval_minutes: int = 60,
    ) -> dict[str, Any]:
        """Zamanlanmis sync ekler.

        Args:
            source: Kaynak.
            target: Hedef.
            mode: Sync modu.
            interval_minutes: Aralik (dakika).

        Returns:
            Zamanlama bilgisi.
        """
        schedule = {
            "source": source,
            "target": target,
            "mode": mode.value,
            "interval_minutes": interval_minutes,
            "enabled": True,
            "last_run": None,
            "run_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._schedules.append(schedule)

        logger.info(
            "Sync zamanlandi: %s -> %s (her %d dk)",
            source, target, interval_minutes,
        )
        return schedule

    def get_due_syncs(self) -> list[dict[str, Any]]:
        """Zamani gelen sync'leri getirir.

        Returns:
            Sync listesi.
        """
        now = datetime.now(timezone.utc)
        due: list[dict[str, Any]] = []

        for schedule in self._schedules:
            if not schedule["enabled"]:
                continue
            if schedule["last_run"] is None:
                due.append(schedule)
                continue

            last = datetime.fromisoformat(schedule["last_run"])
            minutes_since = (now - last).total_seconds() / 60
            if minutes_since >= schedule["interval_minutes"]:
                due.append(schedule)

        return due

    def get_sync_history(
        self,
        source: str = "",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Sync gecmisini getirir.

        Args:
            source: Kaynak filtresi.
            limit: Maks kayit.

        Returns:
            Sync listesi.
        """
        syncs = self._syncs
        if source:
            syncs = [
                s for s in syncs
                if s.source == source
            ]
        return [
            {
                "sync_id": s.sync_id,
                "source": s.source,
                "target": s.target,
                "mode": s.mode.value,
                "records_synced": s.records_synced,
                "conflicts": s.conflicts,
                "success": s.success,
            }
            for s in syncs[-limit:]
        ]

    def get_last_sync_time(
        self,
        source: str,
        target: str,
    ) -> str | None:
        """Son sync zamanini getirir.

        Args:
            source: Kaynak.
            target: Hedef.

        Returns:
            ISO zaman veya None.
        """
        return self._last_sync.get(f"{source}:{target}")

    def _detect_conflicts(
        self,
        data_a: list[dict[str, Any]],
        data_b: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Catismalari tespit eder.

        Args:
            data_a: A verisi.
            data_b: B verisi.

        Returns:
            Catisma listesi.
        """
        conflicts: list[dict[str, Any]] = []
        ids_a = {d.get("id"): d for d in data_a if "id" in d}
        ids_b = {d.get("id"): d for d in data_b if "id" in d}

        for record_id in set(ids_a) & set(ids_b):
            if ids_a[record_id] != ids_b[record_id]:
                conflicts.append({
                    "id": record_id,
                    "data_a": ids_a[record_id],
                    "data_b": ids_b[record_id],
                })

        return conflicts

    def _resolve_conflict(
        self,
        conflict: dict[str, Any],
        source: str,
        target: str,
    ) -> dict[str, Any]:
        """Catismayi cozer.

        Args:
            conflict: Catisma bilgisi.
            source: Kaynak.
            target: Hedef.

        Returns:
            Cozum sonucu.
        """
        record_id = conflict.get("id", "")
        strategy = self._conflict_rules.get(
            record_id,
            "source_wins",
        )

        if strategy == "source_wins":
            winner = source
        elif strategy == "target_wins":
            winner = target
        else:
            winner = source

        return {
            "resolved": True,
            "strategy": strategy,
            "winner": winner,
            "record_id": record_id,
        }

    @property
    def sync_count(self) -> int:
        """Sync sayisi."""
        return len(self._syncs)

    @property
    def schedule_count(self) -> int:
        """Zamanlama sayisi."""
        return len(self._schedules)

    @property
    def conflict_rule_count(self) -> int:
        """Catisma kurali sayisi."""
        return len(self._conflict_rules)
