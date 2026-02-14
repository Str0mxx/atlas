"""ATLAS Soy Takipcisi modulu.

Veri soyu, donusum gecmisi,
etki analizi, denetim izi
ve hata ayiklama.
"""

import logging
import time
from typing import Any

from app.models.pipeline import LineageEntry

logger = logging.getLogger(__name__)


class LineageTracker:
    """Soy takipcisi.

    Veri kokenini ve donusum
    gecmisini takip eder.

    Attributes:
        _entries: Soy kayitlari.
        _graph: Soy grafi.
        _audit: Denetim kayitlari.
    """

    def __init__(
        self,
        retention_days: int = 90,
    ) -> None:
        """Soy takipcisini baslatir.

        Args:
            retention_days: Saklama suresi (gun).
        """
        self._entries: dict[
            str, LineageEntry
        ] = {}
        self._graph: dict[
            str, list[str]
        ] = {}
        self._audit: list[dict[str, Any]] = []
        self._retention_days = retention_days

        logger.info("LineageTracker baslatildi")

    def record(
        self,
        source: str,
        target: str,
        transformation: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> LineageEntry:
        """Soy kaydeder.

        Args:
            source: Kaynak.
            target: Hedef.
            transformation: Donusum aciklamasi.
            metadata: Ek bilgi.

        Returns:
            Soy kaydi.
        """
        entry = LineageEntry(
            source=source,
            target=target,
            transformation=transformation,
        )
        self._entries[entry.entry_id] = entry

        # Graf guncelle
        if source not in self._graph:
            self._graph[source] = []
        self._graph[source].append(target)

        # Denetim kaydi
        self._audit.append({
            "entry_id": entry.entry_id,
            "source": source,
            "target": target,
            "transformation": transformation,
            "metadata": metadata or {},
            "timestamp": time.time(),
        })

        logger.info(
            "Soy kaydedildi: %s -> %s",
            source, target,
        )
        return entry

    def get_lineage(
        self,
        entity: str,
        direction: str = "downstream",
    ) -> list[str]:
        """Soy zincirini getirir.

        Args:
            entity: Varlik adi.
            direction: Yon (downstream, upstream).

        Returns:
            Iliskili varliklar.
        """
        if direction == "downstream":
            return self._get_downstream(entity)
        return self._get_upstream(entity)

    def _get_downstream(
        self,
        entity: str,
    ) -> list[str]:
        """Asagi yondeki varliklari getirir.

        Args:
            entity: Varlik.

        Returns:
            Asagi yon varliklari.
        """
        result: list[str] = []
        visited: set[str] = set()

        def traverse(node: str) -> None:
            if node in visited:
                return
            visited.add(node)
            children = self._graph.get(node, [])
            for child in children:
                result.append(child)
                traverse(child)

        traverse(entity)
        return result

    def _get_upstream(
        self,
        entity: str,
    ) -> list[str]:
        """Yukari yondeki varliklari getirir.

        Args:
            entity: Varlik.

        Returns:
            Yukari yon varliklari.
        """
        result: list[str] = []
        for src, targets in self._graph.items():
            if entity in targets:
                result.append(src)
        return result

    def get_impact(
        self,
        entity: str,
    ) -> dict[str, Any]:
        """Etki analizi yapar.

        Args:
            entity: Varlik adi.

        Returns:
            Etki raporu.
        """
        downstream = self._get_downstream(entity)
        upstream = self._get_upstream(entity)

        return {
            "entity": entity,
            "downstream_count": len(downstream),
            "downstream": downstream,
            "upstream_count": len(upstream),
            "upstream": upstream,
        }

    def get_transformation_history(
        self,
        entity: str,
    ) -> list[dict[str, Any]]:
        """Donusum gecmisini getirir.

        Args:
            entity: Varlik adi.

        Returns:
            Donusum gecmisi.
        """
        return [
            a for a in self._audit
            if a["source"] == entity
            or a["target"] == entity
        ]

    def get_audit_trail(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Denetim izini getirir.

        Args:
            limit: Limit.

        Returns:
            Denetim kayitlari.
        """
        return self._audit[-limit:]

    def delete_entry(
        self,
        entry_id: str,
    ) -> bool:
        """Soy kaydini siler.

        Args:
            entry_id: Kayit ID.

        Returns:
            Basarili ise True.
        """
        entry = self._entries.get(entry_id)
        if not entry:
            return False

        # Graftan da kaldir
        targets = self._graph.get(
            entry.source, [],
        )
        if entry.target in targets:
            targets.remove(entry.target)

        del self._entries[entry_id]
        return True

    def clear_old(
        self,
        older_than_days: int = 0,
    ) -> int:
        """Eski kayitlari temizler.

        Args:
            older_than_days: Gun.

        Returns:
            Temizlenen kayit sayisi.
        """
        days = older_than_days or self._retention_days
        cutoff = time.time() - (days * 86400)
        to_remove: list[str] = []

        for eid, entry in self._entries.items():
            ts = entry.timestamp.timestamp()
            if ts < cutoff:
                to_remove.append(eid)

        for eid in to_remove:
            self.delete_entry(eid)

        return len(to_remove)

    @property
    def entry_count(self) -> int:
        """Kayit sayisi."""
        return len(self._entries)

    @property
    def entity_count(self) -> int:
        """Varlik sayisi."""
        entities: set[str] = set()
        for entry in self._entries.values():
            entities.add(entry.source)
            entities.add(entry.target)
        return len(entities)

    @property
    def audit_count(self) -> int:
        """Denetim sayisi."""
        return len(self._audit)
