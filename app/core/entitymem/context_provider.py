"""ATLAS Varlık Bağlam Sağlayıcı modulu.

İlgili bağlam, son etkileşimler,
bekleyen öğeler, ilişki bağlamı, hızlı özet.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EntityContextProvider:
    """Varlık bağlam sağlayıcı.

    Varlık hakkında ilgili bağlam sağlar.

    Attributes:
        _pending_items: Bekleyen öğeler.
        _notes: Varlık notları.
    """

    def __init__(self) -> None:
        """Sağlayıcıyı başlatır."""
        self._pending_items: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._notes: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "contexts_provided": 0,
            "pending_added": 0,
        }

        logger.info(
            "EntityContextProvider "
            "baslatildi",
        )

    def get_context(
        self,
        entity_id: str,
        interactions: list[
            dict[str, Any]
        ] | None = None,
        relationships: dict[
            str, Any
        ] | None = None,
        profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Tam bağlam sağlar.

        Args:
            entity_id: Varlık ID.
            interactions: Son etkileşimler.
            relationships: İlişkiler.
            profile: Profil bilgisi.

        Returns:
            Bağlam bilgisi.
        """
        pending = self._pending_items.get(
            entity_id, [],
        )
        active_pending = [
            p for p in pending
            if p["status"] == "pending"
        ]
        notes = self._notes.get(entity_id, [])

        self._stats["contexts_provided"] += 1

        return {
            "entity_id": entity_id,
            "profile_summary": (
                self._summarize_profile(profile)
            ),
            "recent_interactions": (
                interactions[:5]
                if interactions else []
            ),
            "relationship_context": (
                relationships or {}
            ),
            "pending_items": active_pending,
            "pending_count": len(active_pending),
            "notes": notes[-3:],
        }

    def add_pending_item(
        self,
        entity_id: str,
        item_type: str,
        description: str,
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Bekleyen öğe ekler.

        Args:
            entity_id: Varlık ID.
            item_type: Öğe tipi.
            description: Açıklama.
            priority: Öncelik.

        Returns:
            Ekleme bilgisi.
        """
        if entity_id not in self._pending_items:
            self._pending_items[entity_id] = []

        item = {
            "item_type": item_type,
            "description": description,
            "priority": priority,
            "status": "pending",
            "created_at": time.time(),
        }
        self._pending_items[entity_id].append(
            item,
        )
        self._stats["pending_added"] += 1

        return {
            "entity_id": entity_id,
            "item_type": item_type,
            "added": True,
        }

    def resolve_pending(
        self,
        entity_id: str,
        item_type: str,
    ) -> dict[str, Any]:
        """Bekleyen öğeyi çözer.

        Args:
            entity_id: Varlık ID.
            item_type: Öğe tipi.

        Returns:
            Çözüm bilgisi.
        """
        items = self._pending_items.get(
            entity_id, [],
        )
        for item in items:
            if (
                item["item_type"] == item_type
                and item["status"] == "pending"
            ):
                item["status"] = "resolved"
                item["resolved_at"] = time.time()
                return {
                    "entity_id": entity_id,
                    "item_type": item_type,
                    "resolved": True,
                }

        return {"error": "item_not_found"}

    def get_pending_items(
        self,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """Bekleyen öğeleri getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Bekleyen öğeler.
        """
        items = self._pending_items.get(
            entity_id, [],
        )
        return [
            i for i in items
            if i["status"] == "pending"
        ]

    def add_note(
        self,
        entity_id: str,
        note: str,
    ) -> dict[str, Any]:
        """Not ekler.

        Args:
            entity_id: Varlık ID.
            note: Not metni.

        Returns:
            Ekleme bilgisi.
        """
        if entity_id not in self._notes:
            self._notes[entity_id] = []

        self._notes[entity_id].append({
            "note": note,
            "created_at": time.time(),
        })

        return {
            "entity_id": entity_id,
            "note_added": True,
        }

    def get_quick_summary(
        self,
        entity_id: str,
        profile: dict[str, Any] | None = None,
        interaction_count: int = 0,
        relationship_count: int = 0,
    ) -> dict[str, Any]:
        """Hızlı özet getirir.

        Args:
            entity_id: Varlık ID.
            profile: Profil bilgisi.
            interaction_count: Etkileşim sayısı.
            relationship_count: İlişki sayısı.

        Returns:
            Özet bilgisi.
        """
        pending = self.get_pending_items(
            entity_id,
        )
        notes = self._notes.get(entity_id, [])

        name = "Unknown"
        if profile and "fields" in profile:
            name = profile["fields"].get(
                "name", "Unknown",
            )

        return {
            "entity_id": entity_id,
            "name": name,
            "interactions": interaction_count,
            "relationships": relationship_count,
            "pending_items": len(pending),
            "notes": len(notes),
        }

    def _summarize_profile(
        self,
        profile: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Profil özetler.

        Args:
            profile: Profil verisi.

        Returns:
            Profil özeti.
        """
        if not profile:
            return {}

        fields = profile.get("fields", {})
        return {
            "name": fields.get("name", ""),
            "company": fields.get("company", ""),
            "role": fields.get("role", ""),
            "completeness": profile.get(
                "completeness", 0.0,
            ),
        }

    @property
    def context_count(self) -> int:
        """Bağlam sayısı."""
        return self._stats[
            "contexts_provided"
        ]

    @property
    def pending_count(self) -> int:
        """Bekleyen öğe sayısı."""
        return self._stats["pending_added"]
