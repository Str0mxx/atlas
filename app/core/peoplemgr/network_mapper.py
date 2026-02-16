"""ATLAS Ağ Haritacısı modülü.

Bağlantı haritalama, etki puanlama,
topluluk tespiti, yol bulma,
görselleştirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class NetworkMapper:
    """Ağ haritacısı.

    Kişi ağını haritalar.

    Attributes:
        _nodes: Düğüm kayıtları.
        _edges: Kenar kayıtları.
    """

    def __init__(self) -> None:
        """Haritacıyı başlatır."""
        self._nodes: dict[
            str, dict[str, Any]
        ] = {}
        self._edges: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "nodes_added": 0,
            "connections_mapped": 0,
            "communities_detected": 0,
        }

        logger.info(
            "NetworkMapper baslatildi",
        )

    def add_node(
        self,
        contact_id: str,
        name: str = "",
        role: str = "peripheral",
        influence: float = 0.5,
    ) -> dict[str, Any]:
        """Düğüm ekler.

        Args:
            contact_id: Kişi ID.
            name: İsim.
            role: Rol.
            influence: Etki puanı.

        Returns:
            Düğüm bilgisi.
        """
        self._nodes[contact_id] = {
            "contact_id": contact_id,
            "name": name,
            "role": role,
            "influence": influence,
            "connections": 0,
        }
        self._stats["nodes_added"] += 1

        return {
            "contact_id": contact_id,
            "name": name,
            "added": True,
        }

    def map_connection(
        self,
        from_id: str,
        to_id: str,
        strength: float = 0.5,
        relationship: str = "knows",
    ) -> dict[str, Any]:
        """Bağlantı haritalar.

        Args:
            from_id: Kaynak.
            to_id: Hedef.
            strength: Güç.
            relationship: İlişki tipi.

        Returns:
            Bağlantı bilgisi.
        """
        edge = {
            "from": from_id,
            "to": to_id,
            "strength": strength,
            "relationship": relationship,
            "timestamp": time.time(),
        }
        self._edges.append(edge)

        # Bağlantı sayılarını güncelle
        if from_id in self._nodes:
            self._nodes[from_id][
                "connections"
            ] += 1
        if to_id in self._nodes:
            self._nodes[to_id][
                "connections"
            ] += 1

        self._stats[
            "connections_mapped"
        ] += 1

        return {
            "from": from_id,
            "to": to_id,
            "strength": strength,
            "mapped": True,
        }

    def score_influence(
        self,
        contact_id: str,
    ) -> dict[str, Any]:
        """Etki puanlar.

        Args:
            contact_id: Kişi ID.

        Returns:
            Etki bilgisi.
        """
        node = self._nodes.get(
            contact_id,
        )
        if not node:
            return {
                "contact_id": contact_id,
                "influence": 0,
                "scored": False,
            }

        connections = node["connections"]
        base_influence = node["influence"]

        # Bağlantı sayısına göre bonus
        conn_bonus = min(
            connections * 0.05, 0.3,
        )

        # Bağlı kişilerin etkisi
        connected_influence = 0.0
        for edge in self._edges:
            if edge["from"] == contact_id:
                other = self._nodes.get(
                    edge["to"], {},
                )
                connected_influence += (
                    other.get(
                        "influence", 0,
                    ) * edge["strength"]
                    * 0.1
                )
            elif edge["to"] == contact_id:
                other = self._nodes.get(
                    edge["from"], {},
                )
                connected_influence += (
                    other.get(
                        "influence", 0,
                    ) * edge["strength"]
                    * 0.1
                )

        total = round(
            min(
                base_influence
                + conn_bonus
                + connected_influence,
                1.0,
            ), 3,
        )

        role = (
            "influencer"
            if total >= 0.8
            else "hub"
            if connections >= 5
            else "bridge"
            if connections >= 3
            else "peripheral"
        )

        node["influence"] = total
        node["role"] = role

        return {
            "contact_id": contact_id,
            "influence_score": total,
            "role": role,
            "connections": connections,
            "scored": True,
        }

    def detect_communities(
        self,
    ) -> dict[str, Any]:
        """Topluluk tespit eder.

        Returns:
            Topluluk bilgisi.
        """
        if not self._edges:
            return {
                "communities": [],
                "count": 0,
            }

        # Basit bağlantılı bileşen tespiti
        visited: set[str] = set()
        communities: list[list[str]] = []

        def _bfs(start: str) -> list[str]:
            queue = [start]
            component: list[str] = []
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                component.append(node)
                for edge in self._edges:
                    if edge["from"] == node:
                        if (
                            edge["to"]
                            not in visited
                        ):
                            queue.append(
                                edge["to"],
                            )
                    elif edge["to"] == node:
                        if (
                            edge["from"]
                            not in visited
                        ):
                            queue.append(
                                edge["from"],
                            )
            return component

        for node_id in self._nodes:
            if node_id not in visited:
                community = _bfs(node_id)
                if community:
                    communities.append(
                        community,
                    )

        self._stats[
            "communities_detected"
        ] = len(communities)

        return {
            "communities": communities,
            "count": len(communities),
        }

    def find_path(
        self,
        from_id: str,
        to_id: str,
    ) -> dict[str, Any]:
        """Yol bulur.

        Args:
            from_id: Başlangıç.
            to_id: Bitiş.

        Returns:
            Yol bilgisi.
        """
        if (
            from_id not in self._nodes
            or to_id not in self._nodes
        ):
            return {
                "path": [],
                "found": False,
            }

        # BFS ile en kısa yol
        visited: set[str] = set()
        queue: list[list[str]] = [
            [from_id],
        ]

        while queue:
            path = queue.pop(0)
            node = path[-1]

            if node == to_id:
                return {
                    "path": path,
                    "length": len(path) - 1,
                    "found": True,
                }

            if node in visited:
                continue
            visited.add(node)

            for edge in self._edges:
                next_node = None
                if edge["from"] == node:
                    next_node = edge["to"]
                elif edge["to"] == node:
                    next_node = edge["from"]

                if (
                    next_node
                    and next_node
                    not in visited
                ):
                    queue.append(
                        path + [next_node],
                    )

        return {
            "path": [],
            "found": False,
        }

    def get_visualization_data(
        self,
    ) -> dict[str, Any]:
        """Görselleştirme verisi döndürür.

        Returns:
            Görselleştirme bilgisi.
        """
        nodes = [
            {
                "id": n["contact_id"],
                "name": n["name"],
                "role": n["role"],
                "influence": n[
                    "influence"
                ],
                "connections": n[
                    "connections"
                ],
            }
            for n in self._nodes.values()
        ]

        edges = [
            {
                "from": e["from"],
                "to": e["to"],
                "strength": e["strength"],
                "type": e["relationship"],
            }
            for e in self._edges
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    @property
    def node_count(self) -> int:
        """Düğüm sayısı."""
        return self._stats["nodes_added"]

    @property
    def edge_count(self) -> int:
        """Kenar sayısı."""
        return self._stats[
            "connections_mapped"
        ]
