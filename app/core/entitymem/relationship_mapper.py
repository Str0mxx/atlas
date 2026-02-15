"""ATLAS İlişki Haritacısı modulu.

Varlık ilişkileri, ilişki tipleri,
güç puanlama, çift yönlü bağlantı, hiyerarşi tespiti.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RelationshipMapper:
    """İlişki haritacısı.

    Varlıklar arası ilişkileri yönetir.

    Attributes:
        _relationships: İlişki kayıtları.
        _hierarchy: Hiyerarşi verileri.
    """

    def __init__(self) -> None:
        """Haritacıyı başlatır."""
        self._relationships: list[
            dict[str, Any]
        ] = []
        self._hierarchy: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "relationships": 0,
        }

        logger.info(
            "RelationshipMapper baslatildi",
        )

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str = "collaborates",
        strength: float = 0.5,
        bidirectional: bool = False,
    ) -> dict[str, Any]:
        """İlişki ekler.

        Args:
            source_id: Kaynak varlık.
            target_id: Hedef varlık.
            rel_type: İlişki tipi.
            strength: Güç puanı (0-1).
            bidirectional: Çift yönlü mü.

        Returns:
            Ekleme bilgisi.
        """
        self._counter += 1
        rid = f"rel_{self._counter}"

        rel = {
            "relationship_id": rid,
            "source_id": source_id,
            "target_id": target_id,
            "rel_type": rel_type,
            "strength": max(
                0.0, min(1.0, strength),
            ),
            "bidirectional": bidirectional,
            "created_at": time.time(),
        }
        self._relationships.append(rel)
        self._stats["relationships"] += 1

        # Hiyerarşi güncelle
        if rel_type == "manages":
            if source_id not in self._hierarchy:
                self._hierarchy[source_id] = []
            self._hierarchy[source_id].append(
                target_id,
            )

        return {
            "relationship_id": rid,
            "source_id": source_id,
            "target_id": target_id,
            "rel_type": rel_type,
            "added": True,
        }

    def get_relationships(
        self,
        entity_id: str,
        direction: str = "both",
    ) -> dict[str, Any]:
        """İlişkileri getirir.

        Args:
            entity_id: Varlık ID.
            direction: Yön (outgoing/incoming/both).

        Returns:
            İlişki bilgisi.
        """
        outgoing = [
            {
                "target_id": r["target_id"],
                "rel_type": r["rel_type"],
                "strength": r["strength"],
            }
            for r in self._relationships
            if r["source_id"] == entity_id
        ]
        incoming = [
            {
                "source_id": r["source_id"],
                "rel_type": r["rel_type"],
                "strength": r["strength"],
            }
            for r in self._relationships
            if r["target_id"] == entity_id
        ]

        # Çift yönlü ilişkiler
        bidirectional_in = [
            {
                "source_id": r["source_id"],
                "rel_type": r["rel_type"],
                "strength": r["strength"],
            }
            for r in self._relationships
            if r["target_id"] == entity_id
            and r["bidirectional"]
        ]

        if direction == "outgoing":
            return {
                "entity_id": entity_id,
                "outgoing": outgoing,
                "count": len(outgoing),
            }
        if direction == "incoming":
            return {
                "entity_id": entity_id,
                "incoming": incoming,
                "count": len(incoming),
            }

        return {
            "entity_id": entity_id,
            "outgoing": outgoing,
            "incoming": incoming,
            "bidirectional": bidirectional_in,
            "total": len(outgoing) + len(
                incoming,
            ),
        }

    def update_strength(
        self,
        source_id: str,
        target_id: str,
        delta: float,
    ) -> dict[str, Any]:
        """İlişki gücünü günceller.

        Args:
            source_id: Kaynak varlık.
            target_id: Hedef varlık.
            delta: Değişim miktarı.

        Returns:
            Güncelleme bilgisi.
        """
        for r in self._relationships:
            if (
                r["source_id"] == source_id
                and r["target_id"] == target_id
            ):
                old = r["strength"]
                r["strength"] = max(
                    0.0,
                    min(1.0, old + delta),
                )
                return {
                    "source_id": source_id,
                    "target_id": target_id,
                    "old_strength": round(
                        old, 3,
                    ),
                    "new_strength": round(
                        r["strength"], 3,
                    ),
                    "updated": True,
                }

        return {"error": "relationship_not_found"}

    def find_connections(
        self,
        entity_id: str,
        max_depth: int = 3,
    ) -> dict[str, Any]:
        """Bağlantıları bulur (BFS).

        Args:
            entity_id: Varlık ID.
            max_depth: Maks derinlik.

        Returns:
            Bağlantı bilgisi.
        """
        visited: set[str] = {entity_id}
        queue: list[tuple[str, int]] = [
            (entity_id, 0),
        ]
        connections: list[dict[str, Any]] = []

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            neighbors = set()
            for r in self._relationships:
                if r["source_id"] == current:
                    neighbors.add(r["target_id"])
                if (
                    r["target_id"] == current
                    and r["bidirectional"]
                ):
                    neighbors.add(r["source_id"])

            for n in neighbors:
                if n not in visited:
                    visited.add(n)
                    connections.append({
                        "entity_id": n,
                        "depth": depth + 1,
                    })
                    queue.append(
                        (n, depth + 1),
                    )

        return {
            "entity_id": entity_id,
            "connections": connections,
            "connection_count": len(connections),
        }

    def detect_hierarchy(
        self,
        root_id: str,
    ) -> dict[str, Any]:
        """Hiyerarşi tespit eder.

        Args:
            root_id: Kök varlık.

        Returns:
            Hiyerarşi bilgisi.
        """
        children = self._hierarchy.get(
            root_id, [],
        )
        tree: dict[str, Any] = {
            "entity_id": root_id,
            "children": [],
        }
        for c in children:
            sub = self._hierarchy.get(c, [])
            tree["children"].append({
                "entity_id": c,
                "children": [
                    {"entity_id": s}
                    for s in sub
                ],
            })

        total = len(children) + sum(
            len(self._hierarchy.get(c, []))
            for c in children
        )

        return {
            "root": root_id,
            "tree": tree,
            "total_members": total,
        }

    def get_strongest(
        self,
        entity_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """En güçlü ilişkileri getirir.

        Args:
            entity_id: Varlık ID.
            limit: Maks sayı.

        Returns:
            İlişki listesi.
        """
        related = []
        for r in self._relationships:
            if r["source_id"] == entity_id:
                related.append({
                    "entity_id": r["target_id"],
                    "rel_type": r["rel_type"],
                    "strength": r["strength"],
                })
            elif (
                r["target_id"] == entity_id
                and r["bidirectional"]
            ):
                related.append({
                    "entity_id": r["source_id"],
                    "rel_type": r["rel_type"],
                    "strength": r["strength"],
                })

        related.sort(
            key=lambda x: x["strength"],
            reverse=True,
        )
        return related[:limit]

    @property
    def relationship_count(self) -> int:
        """İlişki sayısı."""
        return self._stats["relationships"]
