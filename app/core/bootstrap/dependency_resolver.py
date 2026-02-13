"""ATLAS bagimlilik cozumleme modulu.

Bagimlilik grafi olusturma, topolojik siralama,
dongusel bagimlilik tespiti ve surum catismasi cozumu.
"""

import logging
from collections import defaultdict, deque

from app.models.bootstrap import (
    DependencyGraph,
    DependencyNode,
    DependencyRelation,
)

logger = logging.getLogger(__name__)


class DependencyResolver:
    """Bagimlilik cozumleyici.

    Bagimlilik grafi olusturur, topolojik siralar,
    dongu tespit eder ve surum catismalarini bulur.

    Attributes:
        nodes: Bagimlilik dugumleri (ad -> DependencyNode).
    """

    def __init__(self) -> None:
        """DependencyResolver baslatir."""
        self.nodes: dict[str, DependencyNode] = {}
        logger.info("DependencyResolver olusturuldu")

    def add_dependency(
        self,
        name: str,
        version_spec: str = "",
        dependencies: list[str] | None = None,
        relation: DependencyRelation = DependencyRelation.REQUIRES,
    ) -> DependencyNode:
        """Bagimlilik ekler.

        Args:
            name: Bagimlilik adi.
            version_spec: Surum kisiti.
            dependencies: Alt bagimliliklar.
            relation: Bagimlilik iliskisi.

        Returns:
            Olusturulan dugum.
        """
        node = DependencyNode(
            name=name,
            version_spec=version_spec,
            dependencies=dependencies or [],
            relation=relation,
        )
        self.nodes[name] = node
        logger.debug("Bagimlilik eklendi: %s (deps=%s)", name, dependencies)
        return node

    def remove_dependency(self, name: str) -> bool:
        """Bagimlilik kaldirir.

        Args:
            name: Bagimlilik adi.

        Returns:
            Basarili mi.
        """
        if name in self.nodes:
            del self.nodes[name]
            # Diger dugumlerden de referanslari temizle
            for node in self.nodes.values():
                if name in node.dependencies:
                    node.dependencies.remove(name)
            logger.debug("Bagimlilik kaldirildi: %s", name)
            return True
        return False

    def resolve(self) -> DependencyGraph:
        """Bagimliliklari cozumler, graf olusturur.

        Returns:
            Cozumlenenmis bagimlilik grafi.
        """
        cycles = self.detect_cycles()
        conflicts = self.detect_conflicts()
        has_cycles = len(cycles) > 0

        install_order: list[str] = []
        if not has_cycles:
            install_order = self.topological_sort()

        graph = DependencyGraph(
            nodes=dict(self.nodes),
            install_order=install_order,
            has_cycles=has_cycles,
            conflicts=conflicts,
        )
        logger.info(
            "Bagimlilik cozumlendi: dugum=%d, dongu=%s, catisma=%d",
            len(self.nodes),
            has_cycles,
            len(conflicts),
        )
        return graph

    def topological_sort(self) -> list[str]:
        """Topolojik siralama (Kahn algoritmasi).

        Returns:
            Sirali bagimlilik listesi.

        Raises:
            ValueError: Dongusel bagimlilik varsa.
        """
        adj = self._build_adjacency_list()
        in_degree: dict[str, int] = defaultdict(int)

        for name in self.nodes:
            if name not in in_degree:
                in_degree[name] = 0

        for name, deps in adj.items():
            for dep in deps:
                in_degree[dep] += 1

        queue: deque[str] = deque()
        for name, degree in in_degree.items():
            if degree == 0:
                queue.append(name)

        result: list[str] = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for dep in adj.get(node, []):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

        if len(result) != len(self.nodes):
            raise ValueError("Dongusel bagimlilik tespit edildi")

        return result

    def detect_cycles(self) -> list[list[str]]:
        """Dongusel bagimliliklari tespit eder (DFS).

        Returns:
            Dongu listesi (her dongu bir isim listesi).
        """
        adj = self._build_adjacency_list()
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []

        for name in self.nodes:
            if name not in visited:
                self._dfs_cycle(name, adj, visited, rec_stack, [], cycles)

        return cycles

    def detect_conflicts(self) -> list[str]:
        """Surum catismalarini tespit eder.

        Returns:
            Catisma aciklamalari listesi.
        """
        conflicts: list[str] = []

        for node in self.nodes.values():
            if node.relation == DependencyRelation.CONFLICTS:
                for dep_name in node.dependencies:
                    if dep_name in self.nodes:
                        conflicts.append(
                            f"{node.name} <-> {dep_name} catismasi"
                        )

        return conflicts

    def get_install_order(self) -> list[str]:
        """Optimal kurulum sirasini dondurur.

        Returns:
            Topolojik sirali isim listesi. Dongu varsa bos liste.
        """
        try:
            return self.topological_sort()
        except ValueError:
            logger.warning("Dongu var, kurulum sirasi belirlenemiyor")
            return []

    def _build_adjacency_list(self) -> dict[str, list[str]]:
        """Komsuluk listesi olusturur.

        Returns:
            Ad -> bagimlilik listesi eslesmesi.
        """
        adj: dict[str, list[str]] = {}
        for name, node in self.nodes.items():
            adj[name] = list(node.dependencies)
        return adj

    def _dfs_cycle(
        self,
        node: str,
        adj: dict[str, list[str]],
        visited: set[str],
        rec_stack: set[str],
        path: list[str],
        cycles: list[list[str]],
    ) -> None:
        """Dongu tespiti icin DFS yardimcisi.

        Args:
            node: Mevcut dugum.
            adj: Komsuluk listesi.
            visited: Ziyaret edilen dugumler.
            rec_stack: Recursion stack.
            path: Mevcut yol.
            cycles: Bulunan donguler.
        """
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                self._dfs_cycle(neighbor, adj, visited, rec_stack, path, cycles)
            elif neighbor in rec_stack:
                # Dongu bulundu
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.discard(node)
