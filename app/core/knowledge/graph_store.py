"""ATLAS Graf Depolama modulu.

In-memory graf, JSON persistence, indeksleme,
versiyonlama ve yedekleme/geri yukleme.
"""

import json
import logging
import time
from typing import Any

from app.models.knowledge import (
    GraphEdge,
    GraphNode,
    GraphStats,
    KGEntity,
    KGRelation,
)

logger = logging.getLogger(__name__)


class GraphStore:
    """Graf depolama sistemi.

    In-memory graf deposu ile indeksleme, versiyonlama
    ve JSON bazli kalicilik saglar.

    Attributes:
        _nodes: Dugum haritasi.
        _edges: Kenar haritasi.
        _type_index: Tip -> dugum ID'leri indeksi.
        _relation_index: Iliski tipi -> kenar ID'leri indeksi.
        _versions: Versiyon gecmisi.
        _current_version: Mevcut versiyon.
    """

    def __init__(self, persistence_path: str = "") -> None:
        """Graf deposunu baslatir.

        Args:
            persistence_path: Kalicilik dosya yolu. Bos ise sadece bellek.
        """
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._type_index: dict[str, list[str]] = {}
        self._relation_index: dict[str, list[str]] = {}
        self._versions: list[dict[str, Any]] = []
        self._current_version: int = 0
        self._persistence_path = persistence_path

        logger.info("GraphStore baslatildi (path=%s)", persistence_path or "memory")

    def store_node(self, node: GraphNode) -> None:
        """Dugum depolar.

        Args:
            node: Graf dugumu.
        """
        self._nodes[node.id] = node

        # Tip indeksini guncelle
        etype = node.entity.entity_type.value
        if etype not in self._type_index:
            self._type_index[etype] = []
        if node.id not in self._type_index[etype]:
            self._type_index[etype].append(node.id)

    def store_edge(self, edge: GraphEdge) -> None:
        """Kenar depolar.

        Args:
            edge: Graf kenari.
        """
        self._edges[edge.id] = edge

        # Iliski indeksini guncelle
        rtype = edge.relation.relation_type.value
        if rtype not in self._relation_index:
            self._relation_index[rtype] = []
        if edge.id not in self._relation_index[rtype]:
            self._relation_index[rtype].append(edge.id)

    def get_node(self, node_id: str) -> GraphNode | None:
        """Dugum getirir."""
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> GraphEdge | None:
        """Kenar getirir."""
        return self._edges.get(edge_id)

    def get_nodes_by_type(self, entity_type: str) -> list[GraphNode]:
        """Tipe gore dugumleri getirir.

        Args:
            entity_type: Varlik tipi degeri.

        Returns:
            Dugum listesi.
        """
        node_ids = self._type_index.get(entity_type, [])
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def get_edges_by_type(self, relation_type: str) -> list[GraphEdge]:
        """Tipe gore kenarlari getirir.

        Args:
            relation_type: Iliski tipi degeri.

        Returns:
            Kenar listesi.
        """
        edge_ids = self._relation_index.get(relation_type, [])
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def get_neighbors(self, node_id: str) -> list[str]:
        """Komsu dugum ID'lerini getirir.

        Args:
            node_id: Dugum ID.

        Returns:
            Komsu dugum ID listesi.
        """
        node = self._nodes.get(node_id)
        if not node:
            return []

        neighbors: set[str] = set()
        for edge_id in node.out_edges:
            edge = self._edges.get(edge_id)
            if edge:
                neighbors.add(edge.target_node_id)
        for edge_id in node.in_edges:
            edge = self._edges.get(edge_id)
            if edge:
                neighbors.add(edge.source_node_id)

        return list(neighbors)

    def remove_node(self, node_id: str) -> bool:
        """Dugumu siler.

        Args:
            node_id: Dugum ID.

        Returns:
            Basarili mi.
        """
        node = self._nodes.get(node_id)
        if not node:
            return False

        # Iliskili kenarlari sil
        for edge_id in list(node.out_edges) + list(node.in_edges):
            self.remove_edge(edge_id)

        # Indeksten cikar
        etype = node.entity.entity_type.value
        if etype in self._type_index:
            self._type_index[etype] = [nid for nid in self._type_index[etype] if nid != node_id]

        del self._nodes[node_id]
        return True

    def remove_edge(self, edge_id: str) -> bool:
        """Kenari siler.

        Args:
            edge_id: Kenar ID.

        Returns:
            Basarili mi.
        """
        edge = self._edges.get(edge_id)
        if not edge:
            return False

        # Dugumlerden cikar
        src = self._nodes.get(edge.source_node_id)
        tgt = self._nodes.get(edge.target_node_id)
        if src and edge_id in src.out_edges:
            src.out_edges.remove(edge_id)
        if tgt and edge_id in tgt.in_edges:
            tgt.in_edges.remove(edge_id)

        # Indeksten cikar
        rtype = edge.relation.relation_type.value
        if rtype in self._relation_index:
            self._relation_index[rtype] = [eid for eid in self._relation_index[rtype] if eid != edge_id]

        del self._edges[edge_id]
        return True

    def create_version(self, label: str = "") -> int:
        """Yeni versiyon olusturur (snapshot).

        Args:
            label: Versiyon etiketi.

        Returns:
            Versiyon numarasi.
        """
        self._current_version += 1
        snapshot = {
            "version": self._current_version,
            "label": label,
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "timestamp": time.time(),
            "node_ids": list(self._nodes.keys()),
            "edge_ids": list(self._edges.keys()),
        }
        self._versions.append(snapshot)
        logger.info("Versiyon olusturuldu: v%d (%s)", self._current_version, label)
        return self._current_version

    def export_json(self) -> str:
        """Grafi JSON olarak disari aktarir.

        Returns:
            JSON string.
        """
        data = {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.entity.name,
                    "type": n.entity.entity_type.value,
                    "attributes": n.entity.attributes,
                    "status": n.status.value,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_node_id,
                    "target": e.target_node_id,
                    "type": e.relation.relation_type.value,
                    "strength": e.relation.strength,
                }
                for e in self._edges.values()
            ],
            "version": self._current_version,
        }
        return json.dumps(data, ensure_ascii=False, default=str)

    def import_json(self, json_str: str) -> int:
        """JSON'dan graf icerir.

        Args:
            json_str: JSON string.

        Returns:
            Iceri alinan oge sayisi.
        """
        data = json.loads(json_str)
        count = 0

        for nd in data.get("nodes", []):
            entity = KGEntity(
                name=nd.get("name", ""),
                entity_type=nd.get("type", "concept"),
                attributes=nd.get("attributes", {}),
            )
            node = GraphNode(id=nd.get("id", entity.id), entity=entity)
            self.store_node(node)
            count += 1

        for ed in data.get("edges", []):
            relation = KGRelation(
                relation_type=ed.get("type", "related_to"),
                source_id=ed.get("source", ""),
                target_id=ed.get("target", ""),
                strength=ed.get("strength", 1.0),
            )
            edge = GraphEdge(
                id=ed.get("id", relation.id),
                relation=relation,
                source_node_id=ed.get("source", ""),
                target_node_id=ed.get("target", ""),
            )
            self.store_edge(edge)
            count += 1

        logger.info("JSON import: %d oge icerildi", count)
        return count

    def get_stats(self) -> GraphStats:
        """Graf istatistikleri.

        Returns:
            GraphStats nesnesi.
        """
        n = len(self._nodes)
        e = len(self._edges)

        entity_counts = {k: len(v) for k, v in self._type_index.items()}
        relation_counts = {k: len(v) for k, v in self._relation_index.items()}

        avg_degree = (2 * e) / n if n > 0 else 0.0
        max_edges = n * (n - 1) if n > 1 else 1
        density = e / max_edges if max_edges > 0 else 0.0

        return GraphStats(
            node_count=n,
            edge_count=e,
            entity_type_counts=entity_counts,
            relation_type_counts=relation_counts,
            avg_degree=avg_degree,
            density=density,
        )

    @property
    def node_count(self) -> int:
        """Dugum sayisi."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Kenar sayisi."""
        return len(self._edges)

    @property
    def version(self) -> int:
        """Mevcut versiyon."""
        return self._current_version

    @property
    def versions(self) -> list[dict[str, Any]]:
        """Versiyon gecmisi."""
        return list(self._versions)
