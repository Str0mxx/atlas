"""ATLAS Sorgulama Motoru modulu.

Yol bulma, alt graf cikarma, oruntu eslestirme,
toplamlama ve dogal dil sorgulari.
"""

import logging
import time
from collections import deque
from typing import Any

from app.models.knowledge import GraphEdge, GraphNode, QueryResult, QueryType

logger = logging.getLogger(__name__)


class QueryEngine:
    """Sorgulama motoru.

    Graf uzerinde yol bulma, alt graf cikarma,
    oruntu eslestirme ve dogal dil sorgulari yapar.

    Attributes:
        _nodes: Dugum referansi.
        _edges: Kenar referansi.
        _results: Sorgu sonuclari gecmisi.
    """

    def __init__(
        self,
        nodes: dict[str, GraphNode] | None = None,
        edges: dict[str, GraphEdge] | None = None,
    ) -> None:
        """Sorgulama motorunu baslatir.

        Args:
            nodes: Dugum haritasi referansi.
            edges: Kenar haritasi referansi.
        """
        self._nodes = nodes or {}
        self._edges = edges or {}
        self._results: list[QueryResult] = []

        logger.info("QueryEngine baslatildi")

    def set_data(self, nodes: dict[str, GraphNode], edges: dict[str, GraphEdge]) -> None:
        """Graf verisini ayarlar.

        Args:
            nodes: Dugum haritasi.
            edges: Kenar haritasi.
        """
        self._nodes = nodes
        self._edges = edges

    def find_path(self, start_id: str, end_id: str, max_depth: int = 10) -> QueryResult:
        """Iki dugum arasi en kisa yolu bulur (BFS).

        Args:
            start_id: Baslangic dugum ID.
            end_id: Hedef dugum ID.
            max_depth: Maksimum derinlik.

        Returns:
            QueryResult nesnesi.
        """
        start_time = time.monotonic()

        if start_id not in self._nodes or end_id not in self._nodes:
            return QueryResult(query_type=QueryType.PATH_FIND, query=f"{start_id}->{end_id}")

        if start_id == end_id:
            result = QueryResult(
                query_type=QueryType.PATH_FIND,
                query=f"{start_id}->{end_id}",
                paths=[[start_id]],
                result_count=1,
            )
            self._results.append(result)
            return result

        # BFS
        queue: deque[list[str]] = deque([[start_id]])
        visited: set[str] = {start_id}

        while queue:
            path = queue.popleft()
            if len(path) > max_depth:
                break

            current = path[-1]
            neighbors = self._get_neighbors(current)

            for neighbor in neighbors:
                if neighbor == end_id:
                    full_path = path + [neighbor]
                    result = QueryResult(
                        query_type=QueryType.PATH_FIND,
                        query=f"{start_id}->{end_id}",
                        paths=[full_path],
                        nodes=full_path,
                        result_count=1,
                        execution_time_ms=(time.monotonic() - start_time) * 1000,
                    )
                    self._results.append(result)
                    return result

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])

        # Yol bulunamadi
        result = QueryResult(
            query_type=QueryType.PATH_FIND,
            query=f"{start_id}->{end_id}",
            result_count=0,
            execution_time_ms=(time.monotonic() - start_time) * 1000,
        )
        self._results.append(result)
        return result

    def extract_subgraph(self, center_id: str, depth: int = 2) -> QueryResult:
        """Merkez dugumden alt graf cikarir.

        Args:
            center_id: Merkez dugum ID.
            depth: Cikarma derinligi.

        Returns:
            QueryResult nesnesi.
        """
        start_time = time.monotonic()

        if center_id not in self._nodes:
            return QueryResult(query_type=QueryType.SUBGRAPH, query=f"subgraph({center_id})")

        visited_nodes: set[str] = set()
        visited_edges: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(center_id, 0)])

        while queue:
            node_id, d = queue.popleft()
            if node_id in visited_nodes or d > depth:
                continue
            visited_nodes.add(node_id)

            node = self._nodes.get(node_id)
            if not node:
                continue

            for edge_id in node.out_edges + node.in_edges:
                edge = self._edges.get(edge_id)
                if not edge:
                    continue
                visited_edges.add(edge_id)
                neighbor = edge.target_node_id if edge.source_node_id == node_id else edge.source_node_id
                if neighbor not in visited_nodes:
                    queue.append((neighbor, d + 1))

        result = QueryResult(
            query_type=QueryType.SUBGRAPH,
            query=f"subgraph({center_id}, depth={depth})",
            nodes=list(visited_nodes),
            edges=list(visited_edges),
            result_count=len(visited_nodes),
            execution_time_ms=(time.monotonic() - start_time) * 1000,
        )
        self._results.append(result)
        return result

    def match_pattern(self, entity_type: str | None = None, relation_type: str | None = None) -> QueryResult:
        """Oruntu eslestirme yapar.

        Args:
            entity_type: Varlik tipi filtresi.
            relation_type: Iliski tipi filtresi.

        Returns:
            QueryResult nesnesi.
        """
        start_time = time.monotonic()
        matched_nodes: list[str] = []
        matched_edges: list[str] = []

        if entity_type:
            for nid, node in self._nodes.items():
                if node.entity.entity_type.value == entity_type:
                    matched_nodes.append(nid)

        if relation_type:
            for eid, edge in self._edges.items():
                if edge.relation.relation_type.value == relation_type:
                    matched_edges.append(eid)

        result = QueryResult(
            query_type=QueryType.PATTERN,
            query=f"pattern(type={entity_type}, rel={relation_type})",
            nodes=matched_nodes,
            edges=matched_edges,
            result_count=len(matched_nodes) + len(matched_edges),
            execution_time_ms=(time.monotonic() - start_time) * 1000,
        )
        self._results.append(result)
        return result

    def aggregate(self, group_by: str = "entity_type") -> QueryResult:
        """Toplamlama yapar.

        Args:
            group_by: Gruplama alani (entity_type veya relation_type).

        Returns:
            QueryResult nesnesi.
        """
        start_time = time.monotonic()
        aggregations: dict[str, Any] = {}

        if group_by == "entity_type":
            counts: dict[str, int] = {}
            for node in self._nodes.values():
                t = node.entity.entity_type.value
                counts[t] = counts.get(t, 0) + 1
            aggregations = {"entity_type_counts": counts, "total_nodes": len(self._nodes)}

        elif group_by == "relation_type":
            counts = {}
            for edge in self._edges.values():
                t = edge.relation.relation_type.value
                counts[t] = counts.get(t, 0) + 1
            aggregations = {"relation_type_counts": counts, "total_edges": len(self._edges)}

        result = QueryResult(
            query_type=QueryType.AGGREGATION,
            query=f"aggregate(group_by={group_by})",
            aggregations=aggregations,
            result_count=len(aggregations),
            execution_time_ms=(time.monotonic() - start_time) * 1000,
        )
        self._results.append(result)
        return result

    def natural_language_query(self, query: str) -> QueryResult:
        """Dogal dil sorgusu yapar.

        Args:
            query: Dogal dil sorgusu.

        Returns:
            QueryResult nesnesi.
        """
        start_time = time.monotonic()
        query_lower = query.lower()
        matched_nodes: list[str] = []

        # Anahtar kelime bazli arama
        for nid, node in self._nodes.items():
            name_lower = node.entity.name.lower()
            if name_lower in query_lower or any(w in name_lower for w in query_lower.split() if len(w) > 2):
                matched_nodes.append(nid)

        # Iliskili kenarlari bul
        matched_edges: list[str] = []
        node_set = set(matched_nodes)
        for eid, edge in self._edges.items():
            if edge.source_node_id in node_set or edge.target_node_id in node_set:
                matched_edges.append(eid)

        result = QueryResult(
            query_type=QueryType.NATURAL_LANGUAGE,
            query=query,
            nodes=matched_nodes,
            edges=matched_edges,
            result_count=len(matched_nodes),
            execution_time_ms=(time.monotonic() - start_time) * 1000,
        )
        self._results.append(result)
        return result

    def _get_neighbors(self, node_id: str) -> list[str]:
        """Komsu dugum ID'lerini getirir."""
        node = self._nodes.get(node_id)
        if not node:
            return []

        neighbors: list[str] = []
        for edge_id in node.out_edges:
            edge = self._edges.get(edge_id)
            if edge:
                neighbors.append(edge.target_node_id)
        for edge_id in node.in_edges:
            edge = self._edges.get(edge_id)
            if edge:
                neighbors.append(edge.source_node_id)
        return neighbors

    @property
    def results(self) -> list[QueryResult]:
        """Sorgu sonuclari gecmisi."""
        return list(self._results)

    @property
    def result_count(self) -> int:
        """Toplam sorgu sayisi."""
        return len(self._results)
