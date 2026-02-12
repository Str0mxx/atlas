"""ATLAS durum kaliciligi modulu.

SQLite tabanli yerel yedekleme, durum anlık goruntusu
ve kurtarma noktalari saglar.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class StateSnapshot(BaseModel):
    """Durum anlik goruntusu.

    Attributes:
        snapshot_id: Benzersiz kimlik.
        timestamp: Olusturulma zamani.
        state_type: Durum tipi (agent/monitor/decision/queue).
        data: Durum verisi.
        version: Sema versiyonu.
    """

    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    state_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    version: int = 1


class StatePersistence:
    """Durum kaliciligi sinifi.

    SQLite ile yerel yedekleme, anlik goruntuler
    ve kurtarma noktalari yonetir.

    Attributes:
        db_path: SQLite veritabani dosya yolu.
        max_snapshots: Maksimum anlik goruntu sayisi (tip basina).
    """

    def __init__(
        self,
        db_path: str | None = None,
        max_snapshots: int | None = None,
    ) -> None:
        """StatePersistence'i baslatir.

        Args:
            db_path: SQLite dosya yolu (varsayilan: settings'ten).
            max_snapshots: Maks. snapshot sayisi (varsayilan: settings'ten).
        """
        self.db_path = db_path or settings.state_persistence_db_path
        self.max_snapshots = (
            max_snapshots or settings.state_persistence_max_snapshots
        )
        self._initialized = False

        logger.info(
            "StatePersistence olusturuldu (path=%s, max=%d)",
            self.db_path, self.max_snapshots,
        )

    async def initialize(self) -> None:
        """Veritabani tablolarini olusturur."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    state_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    version INTEGER DEFAULT 1
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS recovery_points (
                    recovery_id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    snapshot_ids TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_type_time
                ON snapshots (state_type, timestamp DESC)
            """)
            await db.commit()

        self._initialized = True
        logger.info("StatePersistence tablolari olusturuldu")

    async def close(self) -> None:
        """Baglantilari kapatir (su an aiosqlite otomatik kapatir)."""
        self._initialized = False
        logger.info("StatePersistence kapatildi")

    async def save_snapshot(
        self,
        state_type: str,
        data: dict[str, Any],
    ) -> StateSnapshot:
        """Durum anlik goruntusu kaydeder.

        Args:
            state_type: Durum tipi (agent/monitor/decision/queue).
            data: Durum verisi.

        Returns:
            Kaydedilen anlik goruntu.
        """
        snapshot = StateSnapshot(state_type=state_type, data=data)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO snapshots (snapshot_id, timestamp, state_type, "
                "data, version) VALUES (?, ?, ?, ?, ?)",
                (
                    snapshot.snapshot_id,
                    snapshot.timestamp.isoformat(),
                    snapshot.state_type,
                    json.dumps(snapshot.data),
                    snapshot.version,
                ),
            )
            await db.commit()

        logger.info(
            "Snapshot kaydedildi: %s (tip=%s)",
            snapshot.snapshot_id, state_type,
        )
        return snapshot

    async def load_latest_snapshot(
        self, state_type: str,
    ) -> StateSnapshot | None:
        """Belirtilen tipin en son anlik goruntusunu yukler.

        Args:
            state_type: Durum tipi.

        Returns:
            En son anlik goruntu veya None.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM snapshots WHERE state_type = ? "
                "ORDER BY timestamp DESC LIMIT 1",
                (state_type,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        return StateSnapshot(
            snapshot_id=row["snapshot_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            state_type=row["state_type"],
            data=json.loads(row["data"]),
            version=row["version"],
        )

    async def load_snapshot(self, snapshot_id: str) -> StateSnapshot | None:
        """Belirtilen kimlikli anlik goruntuyu yukler.

        Args:
            snapshot_id: Anlik goruntu kimlik.

        Returns:
            Anlik goruntu veya None.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        return StateSnapshot(
            snapshot_id=row["snapshot_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            state_type=row["state_type"],
            data=json.loads(row["data"]),
            version=row["version"],
        )

    async def create_recovery_point(self, label: str) -> str:
        """Kurtarma noktasi olusturur.

        Tum tiplerin en son snapshot'larini birlestirerek
        bir kurtarma noktasi kaydeder.

        Args:
            label: Kurtarma noktasi etiketi.

        Returns:
            Kurtarma noktasi kimlik.
        """
        recovery_id = str(uuid.uuid4())
        snapshot_ids: list[str] = []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Her tip icin en son snapshot'i bul
            cursor = await db.execute(
                "SELECT snapshot_id, state_type FROM snapshots "
                "GROUP BY state_type "
                "HAVING timestamp = MAX(timestamp)",
            )
            rows = await cursor.fetchall()
            snapshot_ids = [row["snapshot_id"] for row in rows]

            await db.execute(
                "INSERT INTO recovery_points "
                "(recovery_id, label, snapshot_ids, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (
                    recovery_id,
                    label,
                    json.dumps(snapshot_ids),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()

        logger.info(
            "Kurtarma noktasi olusturuldu: %s (%s, %d snapshot)",
            recovery_id, label, len(snapshot_ids),
        )
        return recovery_id

    async def restore_from_recovery(
        self, recovery_id: str,
    ) -> dict[str, Any]:
        """Kurtarma noktasindan geri yukler.

        Args:
            recovery_id: Kurtarma noktasi kimlik.

        Returns:
            state_type -> data eslesmesi.

        Raises:
            ValueError: Kurtarma noktasi bulunamadi.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                "SELECT * FROM recovery_points WHERE recovery_id = ?",
                (recovery_id,),
            )
            row = await cursor.fetchone()

            if row is None:
                raise ValueError(
                    f"Kurtarma noktasi bulunamadi: {recovery_id}",
                )

            snapshot_ids = json.loads(row["snapshot_ids"])
            result: dict[str, Any] = {}

            for sid in snapshot_ids:
                cursor = await db.execute(
                    "SELECT state_type, data FROM snapshots "
                    "WHERE snapshot_id = ?",
                    (sid,),
                )
                snap_row = await cursor.fetchone()
                if snap_row:
                    result[snap_row["state_type"]] = json.loads(
                        snap_row["data"],
                    )

        logger.info(
            "Kurtarma noktasindan geri yuklendi: %s (%d tip)",
            recovery_id, len(result),
        )
        return result

    async def list_recovery_points(self) -> list[dict[str, Any]]:
        """Tum kurtarma noktalarini listeler.

        Returns:
            Kurtarma noktasi listesi.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT recovery_id, label, timestamp "
                "FROM recovery_points ORDER BY timestamp DESC",
            )
            rows = await cursor.fetchall()

        return [
            {
                "recovery_id": row["recovery_id"],
                "label": row["label"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    async def cleanup_old_snapshots(self, keep_last: int | None = None) -> int:
        """Eski anlik goruntulerini temizler.

        Her tip icin sadece son N tanesini tutar.

        Args:
            keep_last: Tutulacak snapshot sayisi (tip basina).

        Returns:
            Silinen snapshot sayisi.
        """
        keep = keep_last or self.max_snapshots
        deleted = 0

        async with aiosqlite.connect(self.db_path) as db:
            # Tum tipleri bul
            cursor = await db.execute(
                "SELECT DISTINCT state_type FROM snapshots",
            )
            types = [row[0] for row in await cursor.fetchall()]

            for state_type in types:
                cursor = await db.execute(
                    "SELECT snapshot_id FROM snapshots "
                    "WHERE state_type = ? "
                    "ORDER BY timestamp DESC LIMIT -1 OFFSET ?",
                    (state_type, keep),
                )
                old_ids = [row[0] for row in await cursor.fetchall()]

                if old_ids:
                    placeholders = ",".join(["?"] * len(old_ids))
                    await db.execute(
                        f"DELETE FROM snapshots WHERE snapshot_id IN ({placeholders})",
                        old_ids,
                    )
                    deleted += len(old_ids)

            await db.commit()

        if deleted > 0:
            logger.info("%d eski snapshot temizlendi", deleted)
        return deleted
