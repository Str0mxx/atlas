"""ATLAS Bilgi Agi modulu.

Bilgi grafi, iliski esleme,
yayilim yollari, etki takibi, gorsellestirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeNetwork:
    """Bilgi agi.

    Bilgi iliskilerini graf olarak yonetir.

    Attributes:
        _nodes: Graf dugumleri.
        _edges: Graf kenarlari.
    """

    def __init__(self) -> None:
        """Bilgi agini baslatir."""
        self._nodes: dict[
            str, dict[str, Any]
        ] = {}
        self._edges: list[
            dict[str, Any]
        ] = []
        self._influence: dict[
            str, float
        ] = {}
        self._stats = {
            "nodes": 0,
            "edges": 0,
        }

        logger.info(
            "KnowledgeNetwork baslatildi",
        )

    def add_node(
        self,
        node_id: str,
        node_type: str = "system",
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Dugum ekler.

        Args:
            node_id: Dugum ID.
            node_type: Dugum tipi.
            properties: Ozellikler.

        Returns:
            Ekleme bilgisi.
        """
        self._nodes[node_id] = {
            "node_id": node_id,
            "node_type": node_type,
            "properties": properties or {},
            "created_at": time.time(),
        }
        self._influence[node_id] = 0.0
        self._stats["nodes"] += 1

        return {
            "node_id": node_id,
            "added": True,
        }

    def add_edge(
        self,
        source: str,
        target: str,
        relationship: str = "transfers_to",
        weight: float = 1.0,
    ) -> dict[str, Any]:
        """Kenar ekler.

        Args:
            source: Kaynak dugum.
            target: Hedef dugum.
            relationship: Iliski tipi.
            weight: Agirlik.

        Returns:
            Ekleme bilgisi.
        """
        if (
            source not in self._nodes
            or target not in self._nodes
        ):
            return {
                "error": "node_not_found",
            }

        edge = {
            "source": source,
            "target": target,
            "relationship": relationship,
            "weight": weight,
            "created_at": time.time(),
        }
        self._edges.append(edge)
        self._stats["edges"] += 1

        # Etki guncelle
        self._influence[source] = (
            self._influence.get(source, 0.0)
            + weight
        )

        return {
            "source": source,
            "target": target,
            "relationship": relationship,
            "added": True,
        }

    def find_propagation_paths(
        self,
        source: str,
        target: str,
        max_depth: int = 5,
    ) -> dict[str, Any]:
        """Yayilim yollarini bulur.

        Args:
            source: Kaynak dugum.
            target: Hedef dugum.
            max_depth: Maks derinlik.

        Returns:
            Yol bilgisi.
        """
        if (
            source not in self._nodes
            or target not in self._nodes
        ):
            return {
                "error": "node_not_found",
            }

        # BFS ile tum yollar
        paths: list[list[str]] = []
        queue: list[list[str]] = [[source]]

        while queue:
            path = queue.pop(0)
            current = path[-1]

            if len(path) > max_depth:
                continue

            if current == target:
                paths.append(path)
                continue

            neighbors = [
                e["target"]
                for e in self._edges
                if e["source"] == current
                and e["target"] not in path
            ]

            for n in neighbors:
                queue.append(path + [n])

        return {
            "source": source,
            "target": target,
            "paths": paths,
            "path_count": len(paths),
            "shortest_length": (
                min(len(p) for p in paths)
                if paths else 0
            ),
        }

    def get_relationships(
        self,
        node_id: str,
    ) -> dict[str, Any]:
        """Iliskileri getirir.

        Args:
            node_id: Dugum ID.

        Returns:
            Iliski bilgisi.
        """
        if node_id not in self._nodes:
            return {
                "error": "node_not_found",
            }

        outgoing = [
            {
                "target": e["target"],
                "relationship": e[
                    "relationship"
                ],
                "weight": e["weight"],
            }
            for e in self._edges
            if e["source"] == node_id
        ]
        incoming = [
            {
                "source": e["source"],
                "relationship": e[
                    "relationship"
                ],
                "weight": e["weight"],
            }
            for e in self._edges
            if e["target"] == node_id
        ]

        return {
            "node_id": node_id,
            "outgoing": outgoing,
            "incoming": incoming,
            "outgoing_count": len(outgoing),
            "incoming_count": len(incoming),
        }

    def get_influence(
        self,
        node_id: str,
    ) -> dict[str, Any]:
        """Etki bilgisi getirir.

        Args:
            node_id: Dugum ID.

        Returns:
            Etki bilgisi.
        """
        if node_id not in self._nodes:
            return {
                "error": "node_not_found",
            }

        score = self._influence.get(
            node_id, 0.0,
        )
        max_inf = max(
            self._influence.values(),
        ) if self._influence else 1.0

        return {
            "node_id": node_id,
            "influence_score": round(
                score, 3,
            ),
            "relative_influence": round(
                score / max(max_inf, 0.01)
                * 100, 1,
            ),
        }

    def get_visualization_data(
        self,
    ) -> dict[str, Any]:
        """Gorsellestirme verisi getirir.

        Returns:
            Graf verisi.
        """
        nodes = [
            {
                "id": nid,
                "type": n["node_type"],
                "influence": round(
                    self._influence.get(
                        nid, 0.0,
                    ), 3,
                ),
            }
            for nid, n in self._nodes.items()
        ]

        edges = [
            {
                "source": e["source"],
                "target": e["target"],
                "label": e["relationship"],
                "weight": e["weight"],
            }
            for e in self._edges
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def get_node(
        self,
        node_id: str,
    ) -> dict[str, Any]:
        """Dugum getirir.

        Args:
            node_id: Dugum ID.

        Returns:
            Dugum bilgisi.
        """
        n = self._nodes.get(node_id)
        if not n:
            return {
                "error": "node_not_found",
            }
        return dict(n)

    @property
    def node_count(self) -> int:
        """Dugum sayisi."""
        return self._stats["nodes"]

    @property
    def edge_count(self) -> int:
        """Kenar sayisi."""
        return self._stats["edges"]
