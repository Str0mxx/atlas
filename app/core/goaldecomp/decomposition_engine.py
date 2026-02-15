"""ATLAS Ayristirma Motoru modulu.

Yukari-asagi ayristirma, AND/OR agaclari,
bagimlilik tespiti, paralellik firsatlari, kritik yol.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DecompositionEngine:
    """Ayristirma motoru.

    Hedefleri alt gorevlere ayristirir.

    Attributes:
        _trees: Ayristirma agaclari.
        _nodes: Tum dugumler.
    """

    def __init__(
        self,
        max_depth: int = 5,
    ) -> None:
        """Ayristirma motorunu baslatir.

        Args:
            max_depth: Maksimum derinlik.
        """
        self._trees: dict[
            str, dict[str, Any]
        ] = {}
        self._nodes: dict[
            str, dict[str, Any]
        ] = {}
        self._max_depth = max_depth
        self._stats = {
            "decomposed": 0,
        }

        logger.info(
            "DecompositionEngine baslatildi",
        )

    def decompose(
        self,
        goal_id: str,
        description: str,
        subtasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Hedefi ayristirir.

        Args:
            goal_id: Hedef ID.
            description: Hedef aciklamasi.
            subtasks: Alt gorev tanimlari.

        Returns:
            Ayristirma sonucu.
        """
        root_id = f"node_{goal_id}_root"

        root = {
            "node_id": root_id,
            "goal_id": goal_id,
            "parent_id": None,
            "node_type": "and",
            "description": description,
            "children": [],
            "dependencies": [],
            "depth": 0,
            "is_leaf": len(subtasks) == 0,
        }

        self._nodes[root_id] = root
        children = []

        for i, sub in enumerate(subtasks):
            child_id = (
                f"node_{goal_id}_{i}"
            )
            node_type = sub.get(
                "type", "and",
            )
            deps = sub.get(
                "dependencies", [],
            )

            child = {
                "node_id": child_id,
                "goal_id": goal_id,
                "parent_id": root_id,
                "node_type": node_type,
                "description": sub.get(
                    "description", "",
                ),
                "children": [],
                "dependencies": deps,
                "depth": 1,
                "is_leaf": True,
            }

            self._nodes[child_id] = child
            children.append(child_id)
            root["children"].append(child_id)

        # Agac bilgisi
        tree = {
            "goal_id": goal_id,
            "root_id": root_id,
            "total_nodes": 1 + len(children),
            "leaf_count": len(children),
            "max_depth": (
                1 if children else 0
            ),
            "created_at": time.time(),
        }

        self._trees[goal_id] = tree
        self._stats["decomposed"] += 1

        return {
            "goal_id": goal_id,
            "root_id": root_id,
            "node_count": tree["total_nodes"],
            "leaf_count": tree["leaf_count"],
            "decomposed": True,
        }

    def add_subtask(
        self,
        parent_id: str,
        description: str,
        node_type: str = "and",
        dependencies: list[str] | None = None,
    ) -> dict[str, Any]:
        """Alt gorev ekler.

        Args:
            parent_id: Ust dugum ID.
            description: Aciklama.
            node_type: Dugum tipi.
            dependencies: Bagimliliklar.

        Returns:
            Ekleme bilgisi.
        """
        parent = self._nodes.get(parent_id)
        if not parent:
            return {
                "error": "parent_not_found",
            }

        if (
            parent["depth"] + 1
            > self._max_depth
        ):
            return {
                "error": "max_depth_exceeded",
            }

        child_id = (
            f"{parent_id}_"
            f"{len(parent['children'])}"
        )

        child = {
            "node_id": child_id,
            "goal_id": parent["goal_id"],
            "parent_id": parent_id,
            "node_type": node_type,
            "description": description,
            "children": [],
            "dependencies": (
                dependencies or []
            ),
            "depth": parent["depth"] + 1,
            "is_leaf": True,
        }

        self._nodes[child_id] = child
        parent["children"].append(child_id)
        parent["is_leaf"] = False

        # Agac guncelle
        goal_id = parent["goal_id"]
        if goal_id in self._trees:
            tree = self._trees[goal_id]
            tree["total_nodes"] += 1
            tree["leaf_count"] = sum(
                1 for n in self._nodes.values()
                if n["goal_id"] == goal_id
                and n["is_leaf"]
            )
            if child["depth"] > tree["max_depth"]:
                tree["max_depth"] = child["depth"]

        return {
            "node_id": child_id,
            "parent_id": parent_id,
            "depth": child["depth"],
            "added": True,
        }

    def find_parallel_opportunities(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Paralellik firsatlarini bulur.

        Args:
            goal_id: Hedef ID.

        Returns:
            Paralellik bilgisi.
        """
        if goal_id not in self._trees:
            return {
                "error": "goal_not_found",
            }

        leaves = [
            n for n in self._nodes.values()
            if n["goal_id"] == goal_id
            and n["is_leaf"]
        ]

        # Bagimliligi olmayan yapraklar
        # paralel calisabilir
        independent = [
            n for n in leaves
            if not n["dependencies"]
        ]
        dependent = [
            n for n in leaves
            if n["dependencies"]
        ]

        # Paralel gruplar
        groups = []
        if independent:
            groups.append({
                "type": "parallel",
                "nodes": [
                    n["node_id"]
                    for n in independent
                ],
                "count": len(independent),
            })

        return {
            "goal_id": goal_id,
            "total_leaves": len(leaves),
            "parallel_groups": groups,
            "independent_count": len(
                independent,
            ),
            "dependent_count": len(dependent),
            "parallelism_ratio": round(
                len(independent)
                / max(len(leaves), 1)
                * 100, 1,
            ),
        }

    def find_critical_path(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Kritik yolu bulur.

        Args:
            goal_id: Hedef ID.

        Returns:
            Kritik yol bilgisi.
        """
        if goal_id not in self._trees:
            return {
                "error": "goal_not_found",
            }

        leaves = [
            n for n in self._nodes.values()
            if n["goal_id"] == goal_id
            and n["is_leaf"]
        ]

        # En uzun bagimlilik zinciri
        max_chain: list[str] = []
        for leaf in leaves:
            chain = self._trace_deps(
                leaf, goal_id,
            )
            if len(chain) > len(max_chain):
                max_chain = chain

        return {
            "goal_id": goal_id,
            "critical_path": max_chain,
            "path_length": len(max_chain),
            "total_nodes": len(leaves),
        }

    def _trace_deps(
        self,
        node: dict[str, Any],
        goal_id: str,
    ) -> list[str]:
        """Bagimlilik zincirini izler.

        Args:
            node: Dugum.
            goal_id: Hedef ID.

        Returns:
            Zincir.
        """
        chain = [node["node_id"]]
        for dep_id in node["dependencies"]:
            dep = self._nodes.get(dep_id)
            if (
                dep
                and dep["goal_id"] == goal_id
            ):
                sub = self._trace_deps(
                    dep, goal_id,
                )
                if (
                    len(sub) + 1
                    > len(chain)
                ):
                    chain = sub + [
                        node["node_id"],
                    ]
        return chain

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

    def get_tree(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Agac bilgisi getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Agac bilgisi.
        """
        t = self._trees.get(goal_id)
        if not t:
            return {
                "error": "goal_not_found",
            }
        return dict(t)

    @property
    def decomposition_count(self) -> int:
        """Ayristirma sayisi."""
        return self._stats["decomposed"]

    @property
    def node_count(self) -> int:
        """Toplam dugum sayisi."""
        return len(self._nodes)
