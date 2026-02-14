"""ATLAS Denetim Kaydedici modulu.

Aksiyon kaydi, aktor tespiti,
onceki/sonraki durum, zaman damgasi
ve degismezlik.
"""

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AuditRecorder:
    """Denetim kaydedici.

    Degismez denetim kayitlari olusturur.

    Attributes:
        _records: Denetim kayitlari.
        _chain: Hash zinciri.
    """

    def __init__(self) -> None:
        """Denetim kaydediciyi baslatir."""
        self._records: list[
            dict[str, Any]
        ] = []
        self._chain_hash = "genesis"
        self._actors: dict[
            str, int
        ] = {}

        logger.info(
            "AuditRecorder baslatildi",
        )

    def record(
        self,
        action: str,
        actor: str,
        resource: str,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Denetim kaydi olusturur.

        Args:
            action: Aksiyon.
            actor: Aktor.
            resource: Kaynak.
            before: Onceki durum.
            after: Sonraki durum.
            metadata: Ek veri.

        Returns:
            Denetim kaydi.
        """
        ts = time.time()

        record = {
            "id": len(self._records),
            "action": action,
            "actor": actor,
            "resource": resource,
            "before": before or {},
            "after": after or {},
            "metadata": metadata or {},
            "timestamp": ts,
            "prev_hash": self._chain_hash,
        }

        # Hash zinciri
        record_str = (
            f"{record['id']}:"
            f"{action}:{actor}:{resource}:"
            f"{ts}:{self._chain_hash}"
        )
        record["hash"] = hashlib.sha256(
            record_str.encode(),
        ).hexdigest()[:16]
        self._chain_hash = record["hash"]

        self._records.append(record)

        # Aktor sayaci
        self._actors[actor] = (
            self._actors.get(actor, 0) + 1
        )

        return record

    def get_records(
        self,
        actor: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Kayitlari getirir.

        Args:
            actor: Aktor filtresi.
            action: Aksiyon filtresi.
            resource: Kaynak filtresi.
            limit: Sonuc limiti.

        Returns:
            Kayit listesi.
        """
        result = self._records
        if actor:
            result = [
                r for r in result
                if r["actor"] == actor
            ]
        if action:
            result = [
                r for r in result
                if r["action"] == action
            ]
        if resource:
            result = [
                r for r in result
                if r["resource"] == resource
            ]
        return result[-limit:]

    def verify_chain(self) -> dict[str, Any]:
        """Hash zincirini dogrular.

        Returns:
            Dogrulama sonucu.
        """
        if not self._records:
            return {"valid": True, "count": 0}

        prev_hash = "genesis"
        for i, record in enumerate(self._records):
            if record["prev_hash"] != prev_hash:
                return {
                    "valid": False,
                    "broken_at": i,
                    "count": len(self._records),
                }
            prev_hash = record["hash"]

        return {
            "valid": True,
            "count": len(self._records),
        }

    def get_actor_summary(
        self,
    ) -> dict[str, int]:
        """Aktor ozetini getirir.

        Returns:
            Aktor sayilari.
        """
        return dict(self._actors)

    def get_changes(
        self,
        resource: str,
    ) -> list[dict[str, Any]]:
        """Kaynak degisikliklerini getirir.

        Args:
            resource: Kaynak adi.

        Returns:
            Degisiklik listesi.
        """
        return [
            {
                "action": r["action"],
                "actor": r["actor"],
                "before": r["before"],
                "after": r["after"],
                "timestamp": r["timestamp"],
            }
            for r in self._records
            if r["resource"] == resource
        ]

    def get_timeline(
        self,
        start: float | None = None,
        end: float | None = None,
    ) -> list[dict[str, Any]]:
        """Zaman cetvelini getirir.

        Args:
            start: Baslangic zamani.
            end: Bitis zamani.

        Returns:
            Kayit listesi.
        """
        result = self._records
        if start is not None:
            result = [
                r for r in result
                if r["timestamp"] >= start
            ]
        if end is not None:
            result = [
                r for r in result
                if r["timestamp"] <= end
            ]
        return result

    @property
    def record_count(self) -> int:
        """Kayit sayisi."""
        return len(self._records)

    @property
    def actor_count(self) -> int:
        """Aktor sayisi."""
        return len(self._actors)

    @property
    def chain_valid(self) -> bool:
        """Zincir gecerli mi."""
        return self.verify_chain()["valid"]
