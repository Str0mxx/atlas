"""ATLAS Snapshot Olusturucu modulu.

Durum snapshot, konfiguration snapshot,
veri snapshot, artimsal snapshot
ve sikistirma.
"""

import hashlib
import json
import logging
import time
from typing import Any

from app.models.versioning import (
    SnapshotRecord,
    SnapshotType,
)

logger = logging.getLogger(__name__)


class SnapshotCreator:
    """Snapshot olusturucu.

    Sistem durumu ve veri snapshot
    islemleri saglar.

    Attributes:
        _snapshots: Snapshot kayitlari.
        _compression_enabled: Sikistirma.
    """

    def __init__(
        self,
        compression_enabled: bool = True,
    ) -> None:
        """Snapshot olusturucuyu baslatir.

        Args:
            compression_enabled: Sikistirma aktif.
        """
        self._snapshots: dict[
            str, SnapshotRecord
        ] = {}
        self._compression_enabled = compression_enabled

        logger.info(
            "SnapshotCreator baslatildi",
        )

    def create_snapshot(
        self,
        source: str,
        data: dict[str, Any],
        snapshot_type: SnapshotType = SnapshotType.FULL,
        parent_id: str = "",
    ) -> SnapshotRecord:
        """Snapshot olusturur.

        Args:
            source: Kaynak adi.
            data: Snapshot verisi.
            snapshot_type: Snapshot turu.
            parent_id: Ebeveyn snapshot ID.

        Returns:
            Snapshot kaydi.
        """
        raw = json.dumps(data, default=str)
        size = len(raw.encode("utf-8"))

        record = SnapshotRecord(
            source=source,
            data=data,
            snapshot_type=snapshot_type,
            size_bytes=size,
            compressed=self._compression_enabled,
            parent_id=parent_id,
        )
        self._snapshots[
            record.snapshot_id
        ] = record
        return record

    def create_incremental(
        self,
        source: str,
        data: dict[str, Any],
        parent_id: str,
    ) -> SnapshotRecord:
        """Artimsal snapshot olusturur.

        Args:
            source: Kaynak adi.
            data: Degisen veri.
            parent_id: Ebeveyn snapshot ID.

        Returns:
            Snapshot kaydi.
        """
        parent = self._snapshots.get(parent_id)
        if not parent:
            return self.create_snapshot(
                source, data,
                SnapshotType.FULL,
            )

        # Sadece degisiklikleri kaydet
        diff: dict[str, Any] = {}
        for key, val in data.items():
            if key not in parent.data or parent.data[key] != val:
                diff[key] = val

        return self.create_snapshot(
            source, diff,
            SnapshotType.INCREMENTAL,
            parent_id,
        )

    def create_config_snapshot(
        self,
        config: dict[str, Any],
    ) -> SnapshotRecord:
        """Konfigurasyon snapshot olusturur.

        Args:
            config: Konfigurasyon verisi.

        Returns:
            Snapshot kaydi.
        """
        return self.create_snapshot(
            "configuration", config,
            SnapshotType.CONFIGURATION,
        )

    def create_data_snapshot(
        self,
        name: str,
        data: dict[str, Any],
    ) -> SnapshotRecord:
        """Veri snapshot olusturur.

        Args:
            name: Veri adi.
            data: Snapshot verisi.

        Returns:
            Snapshot kaydi.
        """
        return self.create_snapshot(
            f"data:{name}", data,
            SnapshotType.DATA,
        )

    def restore_snapshot(
        self,
        snapshot_id: str,
    ) -> dict[str, Any] | None:
        """Snapshot geri yukler.

        Args:
            snapshot_id: Snapshot ID.

        Returns:
            Snapshot verisi veya None.
        """
        record = self._snapshots.get(snapshot_id)
        if not record:
            return None

        # Artimsal ise ebeveynle birlestir
        if (
            record.snapshot_type
            == SnapshotType.INCREMENTAL
            and record.parent_id
        ):
            parent_data = self.restore_snapshot(
                record.parent_id,
            )
            if parent_data:
                merged = {**parent_data}
                merged.update(record.data)
                return merged

        return dict(record.data)

    def get_snapshot(
        self,
        snapshot_id: str,
    ) -> SnapshotRecord | None:
        """Snapshot getirir.

        Args:
            snapshot_id: Snapshot ID.

        Returns:
            Snapshot veya None.
        """
        return self._snapshots.get(snapshot_id)

    def get_chain(
        self,
        snapshot_id: str,
    ) -> list[SnapshotRecord]:
        """Snapshot zincirini getirir.

        Args:
            snapshot_id: Snapshot ID.

        Returns:
            Zincir listesi.
        """
        chain: list[SnapshotRecord] = []
        current_id = snapshot_id

        while current_id:
            record = self._snapshots.get(current_id)
            if not record:
                break
            chain.append(record)
            current_id = record.parent_id

        return list(reversed(chain))

    def delete_snapshot(
        self,
        snapshot_id: str,
    ) -> bool:
        """Snapshot siler.

        Args:
            snapshot_id: Snapshot ID.

        Returns:
            Basarili ise True.
        """
        if snapshot_id in self._snapshots:
            del self._snapshots[snapshot_id]
            return True
        return False

    def get_checksum(
        self,
        snapshot_id: str,
    ) -> str:
        """Snapshot checksum hesaplar.

        Args:
            snapshot_id: Snapshot ID.

        Returns:
            MD5 checksum.
        """
        record = self._snapshots.get(snapshot_id)
        if not record:
            return ""

        raw = json.dumps(
            record.data, sort_keys=True,
            default=str,
        )
        return hashlib.md5(
            raw.encode(),
        ).hexdigest()

    @property
    def snapshot_count(self) -> int:
        """Snapshot sayisi."""
        return len(self._snapshots)

    @property
    def total_size(self) -> int:
        """Toplam boyut (byte)."""
        return sum(
            s.size_bytes
            for s in self._snapshots.values()
        )
