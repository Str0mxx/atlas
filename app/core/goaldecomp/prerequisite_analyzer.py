"""ATLAS Onkosul Analizcisi modulu.

Bagimlilik analizi, siralama kisitlari,
engelleyici gorevler, etkinlestiriciler, risk bagimliliklari.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PrerequisiteAnalyzer:
    """Onkosul analizcisi.

    Gorev bagimliliklarini analiz eder.

    Attributes:
        _dependencies: Bagimlilik grafigi.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Onkosul analizcisini baslatir."""
        self._dependencies: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "analyzed": 0,
        }

        logger.info(
            "PrerequisiteAnalyzer baslatildi",
        )

    def analyze_dependencies(
        self,
        goal_id: str,
        tasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Bagimliliklari analiz eder.

        Args:
            goal_id: Hedef ID.
            tasks: Gorev listesi.

        Returns:
            Analiz sonucu.
        """
        dep_graph: dict[str, list[str]] = {}
        task_map: dict[str, dict[str, Any]] = {}

        for task in tasks:
            tid = task.get("task_id", "")
            deps = task.get(
                "dependencies", [],
            )
            dep_graph[tid] = deps
            task_map[tid] = task

        # Siralama kisitlari
        ordering = self._compute_ordering(
            dep_graph,
        )

        # Engelleyiciler
        blockers = self._find_blockers(
            dep_graph,
        )

        # Etkinlestiriciler
        enablers = self._find_enablers(
            dep_graph,
        )

        analysis = {
            "goal_id": goal_id,
            "task_count": len(tasks),
            "dependency_graph": dep_graph,
            "ordering": ordering,
            "blockers": blockers,
            "enablers": enablers,
            "has_cycle": self._detect_cycle(
                dep_graph,
            ),
        }

        self._dependencies[goal_id] = analysis
        self._stats["analyzed"] += 1

        return analysis

    def _compute_ordering(
        self,
        graph: dict[str, list[str]],
    ) -> list[str]:
        """Topolojik siralama hesaplar.

        Args:
            graph: Bagimlilik grafigi.

        Returns:
            Siralanmis gorev listesi.
        """
        in_degree: dict[str, int] = {
            k: 0 for k in graph
        }
        for deps in graph.values():
            for d in deps:
                if d in in_degree:
                    in_degree[d] += 1

        # Bagimliligi olmayanlardan basla
        queue = [
            k for k, v in in_degree.items()
            if v == 0
        ]
        ordering = []

        while queue:
            node = queue.pop(0)
            ordering.append(node)
            for dep in graph.get(node, []):
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

        return ordering

    def _find_blockers(
        self,
        graph: dict[str, list[str]],
    ) -> list[str]:
        """Engelleyici gorevleri bulur.

        Args:
            graph: Bagimlilik grafigi.

        Returns:
            Engelleyici gorev listesi.
        """
        # Baska gorevleri engelleyen gorevler
        blocked_by: dict[str, int] = {}
        for deps in graph.values():
            for d in deps:
                blocked_by[d] = (
                    blocked_by.get(d, 0) + 1
                )

        # En cok engelleyen gorevler
        return sorted(
            blocked_by,
            key=lambda x: blocked_by[x],
            reverse=True,
        )

    def _find_enablers(
        self,
        graph: dict[str, list[str]],
    ) -> list[str]:
        """Etkinlestiricileri bulur.

        Args:
            graph: Bagimlilik grafigi.

        Returns:
            Etkinlestirici listesi.
        """
        # Hic bagimliligi olmayanlar
        return [
            k for k, v in graph.items()
            if not v
        ]

    def _detect_cycle(
        self,
        graph: dict[str, list[str]],
    ) -> bool:
        """Dongu tespit eder.

        Args:
            graph: Bagimlilik grafigi.

        Returns:
            Dongu var mi.
        """
        visited: set[str] = set()
        in_stack: set[str] = set()

        def _dfs(node: str) -> bool:
            visited.add(node)
            in_stack.add(node)

            for dep in graph.get(node, []):
                if dep not in visited:
                    if _dfs(dep):
                        return True
                elif dep in in_stack:
                    return True

            in_stack.discard(node)
            return False

        for node in graph:
            if node not in visited:
                if _dfs(node):
                    return True
        return False

    def get_blocking_tasks(
        self,
        goal_id: str,
        task_id: str,
    ) -> dict[str, Any]:
        """Bir gorevi engelleyen gorevleri bulur.

        Args:
            goal_id: Hedef ID.
            task_id: Gorev ID.

        Returns:
            Engelleyici bilgisi.
        """
        analysis = self._dependencies.get(
            goal_id,
        )
        if not analysis:
            return {
                "error": "goal_not_found",
            }

        graph = analysis["dependency_graph"]
        deps = graph.get(task_id, [])

        return {
            "task_id": task_id,
            "blocked_by": deps,
            "blocker_count": len(deps),
        }

    def get_risk_dependencies(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Risk bagimliliklerini bulur.

        Args:
            goal_id: Hedef ID.

        Returns:
            Risk bilgisi.
        """
        analysis = self._dependencies.get(
            goal_id,
        )
        if not analysis:
            return {
                "error": "goal_not_found",
            }

        graph = analysis["dependency_graph"]

        # Yuksek fan-out (cok gorevi etkileyen)
        fan_out: dict[str, int] = {}
        for deps in graph.values():
            for d in deps:
                fan_out[d] = (
                    fan_out.get(d, 0) + 1
                )

        risky = [
            {
                "task_id": tid,
                "dependents": count,
                "risk": "high" if count >= 3
                else "medium",
            }
            for tid, count in fan_out.items()
            if count >= 2
        ]

        return {
            "goal_id": goal_id,
            "risk_dependencies": risky,
            "risk_count": len(risky),
        }

    def get_analysis(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Analiz sonucu getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Analiz bilgisi.
        """
        a = self._dependencies.get(goal_id)
        if not a:
            return {
                "error": "goal_not_found",
            }
        return dict(a)

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return self._stats["analyzed"]
