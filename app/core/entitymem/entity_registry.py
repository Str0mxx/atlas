"""ATLAS Varlık Kayıt Defteri modulu.

Varlık oluşturma, tiplendirme,
benzersiz tanımlama, alias yönetimi, yaşam döngüsü.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EntityRegistry:
    """Varlık kayıt defteri.

    Varlıkları oluşturur ve yönetir.

    Attributes:
        _entities: Kayıtlı varlıklar.
        _aliases: Alias eşlemeleri.
    """

    def __init__(self) -> None:
        """Kayıt defterini başlatır."""
        self._entities: dict[
            str, dict[str, Any]
        ] = {}
        self._aliases: dict[str, str] = {}
        self._counter = 0
        self._stats = {
            "created": 0,
            "updated": 0,
            "archived": 0,
        }

        logger.info(
            "EntityRegistry baslatildi",
        )

    def create_entity(
        self,
        name: str,
        entity_type: str = "person",
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Varlık oluşturur.

        Args:
            name: Varlık adı.
            entity_type: Varlık tipi.
            properties: Özellikler.

        Returns:
            Oluşturma bilgisi.
        """
        self._counter += 1
        eid = f"ent_{self._counter}"

        self._entities[eid] = {
            "entity_id": eid,
            "name": name,
            "entity_type": entity_type,
            "aliases": [],
            "properties": properties or {},
            "status": "active",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._stats["created"] += 1

        return {
            "entity_id": eid,
            "name": name,
            "entity_type": entity_type,
            "created": True,
        }

    def get_entity(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Varlık getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Varlık bilgisi.
        """
        # Alias kontrolü
        resolved = self._aliases.get(
            entity_id, entity_id,
        )
        e = self._entities.get(resolved)
        if not e:
            return {"error": "entity_not_found"}
        return dict(e)

    def update_entity(
        self,
        entity_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Varlık günceller.

        Args:
            entity_id: Varlık ID.
            updates: Güncellemeler.

        Returns:
            Güncelleme bilgisi.
        """
        e = self._entities.get(entity_id)
        if not e:
            return {"error": "entity_not_found"}

        for k, v in updates.items():
            if k not in ("entity_id", "created_at"):
                if k == "properties":
                    e["properties"].update(v)
                else:
                    e[k] = v

        e["updated_at"] = time.time()
        self._stats["updated"] += 1

        return {
            "entity_id": entity_id,
            "updated": True,
            "fields": list(updates.keys()),
        }

    def add_alias(
        self,
        entity_id: str,
        alias: str,
    ) -> dict[str, Any]:
        """Alias ekler.

        Args:
            entity_id: Varlık ID.
            alias: Alias.

        Returns:
            Ekleme bilgisi.
        """
        e = self._entities.get(entity_id)
        if not e:
            return {"error": "entity_not_found"}

        if alias in self._aliases:
            return {"error": "alias_exists"}

        self._aliases[alias] = entity_id
        e["aliases"].append(alias)

        return {
            "entity_id": entity_id,
            "alias": alias,
            "added": True,
        }

    def remove_alias(
        self,
        alias: str,
    ) -> dict[str, Any]:
        """Alias kaldırır.

        Args:
            alias: Alias.

        Returns:
            Kaldırma bilgisi.
        """
        eid = self._aliases.get(alias)
        if not eid:
            return {"error": "alias_not_found"}

        del self._aliases[alias]
        e = self._entities.get(eid)
        if e and alias in e["aliases"]:
            e["aliases"].remove(alias)

        return {
            "alias": alias,
            "removed": True,
        }

    def archive_entity(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Varlık arşivler.

        Args:
            entity_id: Varlık ID.

        Returns:
            Arşivleme bilgisi.
        """
        e = self._entities.get(entity_id)
        if not e:
            return {"error": "entity_not_found"}

        e["status"] = "archived"
        e["updated_at"] = time.time()
        self._stats["archived"] += 1

        return {
            "entity_id": entity_id,
            "archived": True,
        }

    def search_entities(
        self,
        query: str = "",
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Varlık arar.

        Args:
            query: Arama sorgusu.
            entity_type: Tip filtresi.

        Returns:
            Eşleşen varlıklar.
        """
        results = []
        q = query.lower()
        for e in self._entities.values():
            if e["status"] != "active":
                continue
            if entity_type and (
                e["entity_type"] != entity_type
            ):
                continue
            if q and q not in e["name"].lower():
                # Alias kontrolü
                alias_match = any(
                    q in a.lower()
                    for a in e["aliases"]
                )
                if not alias_match:
                    continue
            results.append({
                "entity_id": e["entity_id"],
                "name": e["name"],
                "entity_type": e["entity_type"],
            })
        return results

    def list_by_type(
        self,
        entity_type: str,
    ) -> list[dict[str, Any]]:
        """Tipe göre listeler.

        Args:
            entity_type: Varlık tipi.

        Returns:
            Varlık listesi.
        """
        return [
            {
                "entity_id": e["entity_id"],
                "name": e["name"],
                "status": e["status"],
            }
            for e in self._entities.values()
            if e["entity_type"] == entity_type
        ]

    @property
    def entity_count(self) -> int:
        """Varlık sayısı."""
        return self._stats["created"]

    @property
    def active_count(self) -> int:
        """Aktif varlık sayısı."""
        return sum(
            1
            for e in self._entities.values()
            if e["status"] == "active"
        )
