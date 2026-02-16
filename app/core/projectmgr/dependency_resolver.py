"""ATLAS Proje Bağımlılık Çözücü modülü.

Bağımlılık haritalama, kritik yol,
döngüsel tespit, etki analizi,
yeniden sıralama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProjectDependencyResolver:
    """Proje bağımlılık çözücü.

    Proje bağımlılıklarını çözümler.

    Attributes:
        _graph: Bağımlılık grafı.
        _tasks: Görev bilgileri.
    """

    def __init__(self) -> None:
        """Çözücüyü başlatır."""
        self._graph: dict[
            str, list[str]
        ] = {}
        self._tasks: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "dependencies_added": 0,
            "cycles_detected": 0,
            "paths_calculated": 0,
        }

        logger.info(
            "ProjectDependencyResolver "
            "baslatildi",
        )

    def add_task(
        self,
        task_id: str,
        name: str = "",
        duration: float = 1.0,
    ) -> dict[str, Any]:
        """Görev ekler.

        Args:
            task_id: Görev ID.
            name: Ad.
            duration: Süre (gün).

        Returns:
            Görev bilgisi.
        """
        self._tasks[task_id] = {
            "task_id": task_id,
            "name": name or task_id,
            "duration": duration,
        }
        if task_id not in self._graph:
            self._graph[task_id] = []

        return {
            "task_id": task_id,
            "name": name or task_id,
            "added": True,
        }

    def add_dependency(
        self,
        task_id: str,
        depends_on: str,
    ) -> dict[str, Any]:
        """Bağımlılık ekler.

        Args:
            task_id: Görev ID.
            depends_on: Bağımlı olunan.

        Returns:
            Bağımlılık bilgisi.
        """
        if task_id not in self._graph:
            self._graph[task_id] = []
        if depends_on not in self._graph:
            self._graph[depends_on] = []

        self._graph[task_id].append(
            depends_on,
        )
        self._stats[
            "dependencies_added"
        ] += 1

        return {
            "task_id": task_id,
            "depends_on": depends_on,
            "added": True,
        }

    def detect_circular(
        self,
    ) -> dict[str, Any]:
        """Döngüsel bağımlılık tespit eder.

        Returns:
            Tespit bilgisi.
        """
        visited: set[str] = set()
        in_stack: set[str] = set()
        cycles: list[list[str]] = []

        def _dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            in_stack.add(node)
            path.append(node)

            for dep in self._graph.get(
                node, [],
            ):
                if dep not in visited:
                    _dfs(dep, path[:])
                elif dep in in_stack:
                    idx = path.index(dep)
                    cycle = path[idx:] + [dep]
                    cycles.append(cycle)

            in_stack.discard(node)

        for node in self._graph:
            if node not in visited:
                _dfs(node, [])

        if cycles:
            self._stats[
                "cycles_detected"
            ] += len(cycles)

        return {
            "has_cycles": len(cycles) > 0,
            "cycles": cycles,
            "count": len(cycles),
        }

    def find_critical_path(
        self,
    ) -> dict[str, Any]:
        """Kritik yol bulur.

        Returns:
            Kritik yol bilgisi.
        """
        if not self._tasks:
            return {
                "path": [],
                "duration": 0,
            }

        # Topolojik sıralama
        order = self._topological_sort()
        if not order:
            return {
                "path": [],
                "duration": 0,
                "error": "cycle_detected",
            }

        # En uzun yol
        dist: dict[str, float] = {
            t: 0 for t in self._tasks
        }
        prev: dict[str, str] = {}

        for task in order:
            dur = self._tasks.get(
                task, {},
            ).get("duration", 1)
            for dep in self._graph.get(
                task, [],
            ):
                if (
                    dist[dep] + dur
                    > dist[task]
                ):
                    dist[task] = (
                        dist[dep] + dur
                    )
                    prev[task] = dep

        # En uzun yolun sonu
        end = max(dist, key=dist.get)
        path = [end]
        while end in prev:
            end = prev[end]
            path.append(end)
        path.reverse()

        total_dur = round(
            dist[path[-1]]
            + self._tasks.get(
                path[-1], {},
            ).get("duration", 1), 1,
        )

        self._stats[
            "paths_calculated"
        ] += 1

        return {
            "path": path,
            "duration": total_dur,
            "task_count": len(path),
        }

    def _topological_sort(
        self,
    ) -> list[str]:
        """Topolojik sıralama yapar."""
        in_degree: dict[str, int] = {
            t: 0 for t in self._graph
        }
        for node in self._graph:
            for dep in self._graph[node]:
                in_degree[dep] = (
                    in_degree.get(dep, 0)
                )
                in_degree[node] = (
                    in_degree.get(node, 0)
                )

        # Gelen bağımlılık sayısını hesapla
        for node in self._graph:
            for dep in self._graph[node]:
                pass  # deps are what node depends on

        queue = [
            n for n, d in in_degree.items()
            if d == 0
        ]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for other in self._graph:
                if node in self._graph[other]:
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)

        return result

    def analyze_impact(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        """Etki analizi yapar.

        Args:
            task_id: Görev ID.

        Returns:
            Etki bilgisi.
        """
        affected: list[str] = []

        # Bu göreve bağımlı olanları bul
        for other, deps in (
            self._graph.items()
        ):
            if task_id in deps:
                affected.append(other)

        # Dolaylı etki
        indirect: list[str] = []
        for a in affected:
            for other, deps in (
                self._graph.items()
            ):
                if (
                    a in deps
                    and other not in affected
                    and other != task_id
                ):
                    indirect.append(other)

        impact = (
            "high"
            if len(affected) >= 3
            else "medium"
            if len(affected) >= 1
            else "low"
        )

        return {
            "task_id": task_id,
            "directly_affected": affected,
            "indirectly_affected": indirect,
            "total_impact": (
                len(affected) + len(indirect)
            ),
            "impact_level": impact,
        }

    def get_execution_order(
        self,
    ) -> dict[str, Any]:
        """Yürütme sırası döndürür.

        Returns:
            Sıralama bilgisi.
        """
        order = self._topological_sort()
        return {
            "order": order,
            "count": len(order),
        }

    @property
    def dependency_count(self) -> int:
        """Bağımlılık sayısı."""
        return self._stats[
            "dependencies_added"
        ]

    @property
    def task_count(self) -> int:
        """Görev sayısı."""
        return len(self._tasks)
