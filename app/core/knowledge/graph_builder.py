"""ATLAS Graf Olusturucu modulu.

Dugum olusturma, kenar olusturma, ozellik atama,
graf birlestirme ve tekrar tespiti.
"""

import logging
from typing import Any

from app.models.knowledge import (
    GraphEdge,
    GraphNode,
    KGEntity,
    KGRelation,
    NodeStatus,
)

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Graf olusturucu.

    Varlik ve iliskilerden graf yapisi olusturur.
    Dugum ve kenar yonetimi, birlestirme ve tekrar
    tespiti saglar.

    Attributes:
        _nodes: Dugum haritasi (id -> GraphNode).
        _edges: Kenar haritasi (id -> GraphEdge).
        _name_index: Ad -> dugum ID indeksi.
    """

    def __init__(self) -> None:
        """Graf olusturucuyu baslatir."""
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._name_index: dict[str, str] = {}

        logger.info("GraphBuilder baslatildi")

    def add_node(self, entity: KGEntity) -> GraphNode:
        """Dugum ekler.

        Args:
            entity: Varlik nesnesi.

        Returns:
            Olusturulan veya mevcut GraphNode.
        """
        # Tekrar kontrolu
        existing = self._find_duplicate_node(entity)
        if existing:
            logger.debug("Tekrar dugum tespit edildi: %s", entity.name)
            return existing

        node = GraphNode(entity=entity)
        self._nodes[node.id] = node
        self._name_index[entity.name.lower()] = node.id

        # Alias'lari da indeksle
        for alias in entity.aliases:
            self._name_index[alias.lower()] = node.id

        logger.info("Dugum eklendi: %s (%s)", entity.name, entity.entity_type.value)
        return node

    def add_edge(self, relation: KGRelation, source_node_id: str, target_node_id: str) -> GraphEdge | None:
        """Kenar ekler.

        Args:
            relation: Iliski nesnesi.
            source_node_id: Kaynak dugum ID.
            target_node_id: Hedef dugum ID.

        Returns:
            GraphEdge veya None (dugumler bulunamazsa).
        """
        if source_node_id not in self._nodes or target_node_id not in self._nodes:
            return None

        edge = GraphEdge(
            relation=relation,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
        )
        self._edges[edge.id] = edge

        # Dugumleri guncelle
        self._nodes[source_node_id].out_edges.append(edge.id)
        self._nodes[target_node_id].in_edges.append(edge.id)

        logger.info(
            "Kenar eklendi: %s -[%s]-> %s",
            source_node_id[:8], relation.relation_type.value, target_node_id[:8],
        )
        return edge

    def set_property(self, node_id: str, key: str, value: Any) -> bool:
        """Dugum ozelligi atar.

        Args:
            node_id: Dugum ID.
            key: Ozellik adi.
            value: Ozellik degeri.

        Returns:
            Basarili mi.
        """
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.entity.attributes[key] = value
        return True

    def merge_graphs(self, other: "GraphBuilder") -> int:
        """Baska bir grafi birlestirir.

        Args:
            other: Birlestirilecek graf.

        Returns:
            Eklenen dugum + kenar sayisi.
        """
        added = 0

        # Dugumleri ekle
        node_id_map: dict[str, str] = {}
        for old_id, node in other._nodes.items():
            existing = self._find_duplicate_node(node.entity)
            if existing:
                node_id_map[old_id] = existing.id
            else:
                new_node = self.add_node(node.entity)
                node_id_map[old_id] = new_node.id
                added += 1

        # Kenarlari ekle
        for edge in other._edges.values():
            src = node_id_map.get(edge.source_node_id)
            tgt = node_id_map.get(edge.target_node_id)
            if src and tgt:
                result = self.add_edge(edge.relation, src, tgt)
                if result:
                    added += 1

        logger.info("Graf birlestirme: %d oge eklendi", added)
        return added

    def detect_duplicates(self) -> list[tuple[str, str]]:
        """Tekrar dugumleri tespit eder.

        Returns:
            Olasi tekrar ciftleri (node_id_1, node_id_2).
        """
        duplicates: list[tuple[str, str]] = []
        nodes = list(self._nodes.values())

        for i, n1 in enumerate(nodes):
            for j in range(i + 1, len(nodes)):
                n2 = nodes[j]
                if self._are_similar(n1.entity, n2.entity):
                    duplicates.append((n1.id, n2.id))

        logger.info("Tekrar tespiti: %d cift bulundu", len(duplicates))
        return duplicates

    def merge_nodes(self, keep_id: str, remove_id: str) -> bool:
        """Iki dugumu birlestirir.

        Args:
            keep_id: Korunacak dugum ID.
            remove_id: Kaldirilacak dugum ID.

        Returns:
            Basarili mi.
        """
        keep = self._nodes.get(keep_id)
        remove = self._nodes.get(remove_id)
        if not keep or not remove:
            return False

        # Alias olarak ekle
        if remove.entity.name not in keep.entity.aliases:
            keep.entity.aliases.append(remove.entity.name)

        # Ozellikleri birle
        for k, v in remove.entity.attributes.items():
            if k not in keep.entity.attributes:
                keep.entity.attributes[k] = v

        # Kenarlari transfer et
        for edge_id in remove.out_edges:
            edge = self._edges.get(edge_id)
            if edge:
                edge.source_node_id = keep_id
                keep.out_edges.append(edge_id)

        for edge_id in remove.in_edges:
            edge = self._edges.get(edge_id)
            if edge:
                edge.target_node_id = keep_id
                keep.in_edges.append(edge_id)

        # Dugumu sil (merged olarak isaretle)
        remove.status = NodeStatus.MERGED
        remove.metadata["merged_into"] = keep_id
        del self._nodes[remove_id]

        logger.info("Dugumler birlestirildi: %s <- %s", keep.entity.name, remove.entity.name)
        return True

    def _find_duplicate_node(self, entity: KGEntity) -> GraphNode | None:
        """Tekrar dugum arar.

        Args:
            entity: Aranan varlik.

        Returns:
            Mevcut GraphNode veya None.
        """
        name_lower = entity.name.lower()
        node_id = self._name_index.get(name_lower)
        if node_id and node_id in self._nodes:
            return self._nodes[node_id]
        return None

    def _are_similar(self, e1: KGEntity, e2: KGEntity) -> bool:
        """Iki varligin benzer olup olmadigini kontrol eder.

        Args:
            e1: Birinci varlik.
            e2: Ikinci varlik.

        Returns:
            Benzer mi.
        """
        if e1.name.lower() == e2.name.lower():
            return True
        if e1.name.lower() in [a.lower() for a in e2.aliases]:
            return True
        if e2.name.lower() in [a.lower() for a in e1.aliases]:
            return True
        return False

    def get_node(self, node_id: str) -> GraphNode | None:
        """Dugum getirir."""
        return self._nodes.get(node_id)

    def get_node_by_name(self, name: str) -> GraphNode | None:
        """Ada gore dugum getirir."""
        node_id = self._name_index.get(name.lower())
        if node_id:
            return self._nodes.get(node_id)
        return None

    def get_edge(self, edge_id: str) -> GraphEdge | None:
        """Kenar getirir."""
        return self._edges.get(edge_id)

    @property
    def node_count(self) -> int:
        """Dugum sayisi."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Kenar sayisi."""
        return len(self._edges)

    @property
    def nodes(self) -> list[GraphNode]:
        """Tum dugumler."""
        return list(self._nodes.values())

    @property
    def edges(self) -> list[GraphEdge]:
        """Tum kenarlar."""
        return list(self._edges.values())
