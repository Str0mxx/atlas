"""ATLAS GoalTree modulu.

Hiyerarsik hedef agaci yonetimi. AND/OR decomposition,
bagimlilik takibi ve ilerleme hesaplama islevleri.
"""

import logging
from typing import Any

from app.models.planning import (
    GoalNode,
    GoalNodeStatus,
    GoalTreeSnapshot,
    GoalType,
)

logger = logging.getLogger(__name__)


class GoalTree:
    """Hiyerarsik hedef agaci.

    AND/OR goal decomposition ile hedfleri alt hedeflere
    ayirir, bagimliliklari yonetir ve ilerlemeyi izler.

    Attributes:
        nodes: Tum dugumlerin sozlugu (id -> GoalNode).
        root_id: Kok dugum ID.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, GoalNode] = {}
        self.root_id: str | None = None

    async def add_goal(
        self,
        name: str,
        goal_type: GoalType = GoalType.LEAF,
        parent_id: str | None = None,
        priority: float = 0.5,
        dependencies: list[str] | None = None,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> GoalNode:
        """Yeni hedef ekler.

        Args:
            name: Hedef adi.
            goal_type: AND/OR/LEAF tipi.
            parent_id: Ust hedef ID.
            priority: Oncelik puani (0.0-1.0).
            dependencies: Bagimlilik ID listesi.
            description: Hedef aciklamasi.
            metadata: Ek veriler.

        Returns:
            Oluturulan GoalNode.

        Raises:
            ValueError: Gecersiz parent_id veya dependency ID.
        """
        if parent_id is not None and parent_id not in self.nodes:
            raise ValueError(f"Parent goal not found: {parent_id}")

        if dependencies:
            for dep_id in dependencies:
                if dep_id not in self.nodes:
                    raise ValueError(f"Dependency goal not found: {dep_id}")

        node = GoalNode(
            name=name,
            description=description,
            goal_type=goal_type,
            parent_id=parent_id,
            priority=priority,
            dependencies=dependencies or [],
            metadata=metadata or {},
        )

        self.nodes[node.id] = node

        # Kok dugum yoksa bu ilk dugum kok olur
        if self.root_id is None and parent_id is None:
            self.root_id = node.id

        # Ust dugume alt dugum olarak ekle
        if parent_id is not None and parent_id in self.nodes:
            self.nodes[parent_id].children_ids.append(node.id)

        logger.info("Hedef eklendi: %s (tip=%s)", name, goal_type.value)
        return node

    async def remove_goal(self, goal_id: str) -> bool:
        """Hedefi ve alt hedeflerini siler.

        Args:
            goal_id: Silinecek hedef ID.

        Returns:
            Silme basarili mi.
        """
        if goal_id not in self.nodes:
            return False

        # Alt hedefleri recursive sil
        node = self.nodes[goal_id]
        for child_id in list(node.children_ids):
            await self.remove_goal(child_id)

        # Ust dugumden referansi kaldir
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if goal_id in parent.children_ids:
                parent.children_ids.remove(goal_id)

        # Bagimliliklari temizle
        for other_node in self.nodes.values():
            if goal_id in other_node.dependencies:
                other_node.dependencies.remove(goal_id)

        del self.nodes[goal_id]

        if self.root_id == goal_id:
            self.root_id = None

        logger.info("Hedef silindi: %s", goal_id)
        return True

    async def update_status(
        self, goal_id: str, status: GoalNodeStatus
    ) -> GoalNode | None:
        """Hedef durumunu gunceller ve ilerlemeyi yeniden hesaplar.

        Args:
            goal_id: Hedef ID.
            status: Yeni durum.

        Returns:
            Guncellenmis GoalNode veya None.
        """
        if goal_id not in self.nodes:
            return None

        node = self.nodes[goal_id]
        node.status = status

        # Leaf tamamlandiysa progress %100
        if status == GoalNodeStatus.COMPLETED:
            node.progress = 1.0
        elif status == GoalNodeStatus.FAILED:
            node.progress = 0.0

        # Ust dugumlerin ilerlemesini yeniden hesapla
        await self._propagate_progress(goal_id)

        logger.info("Hedef durumu guncellendi: %s -> %s", goal_id, status.value)
        return node

    async def _propagate_progress(self, goal_id: str) -> None:
        """Ilerlemeyi ust dugumlere yayar.

        Args:
            goal_id: Baslangic dugum ID.
        """
        node = self.nodes.get(goal_id)
        if node is None or node.parent_id is None:
            return

        parent = self.nodes.get(node.parent_id)
        if parent is None or not parent.children_ids:
            return

        children = [
            self.nodes[cid]
            for cid in parent.children_ids
            if cid in self.nodes
        ]

        if not children:
            return

        if parent.goal_type == GoalType.AND:
            # AND: tum alt hedeflerin ortalamasi
            parent.progress = sum(c.progress for c in children) / len(children)
            # AND: tumu tamamsa tamamdir
            if all(c.status == GoalNodeStatus.COMPLETED for c in children):
                parent.status = GoalNodeStatus.COMPLETED
                parent.progress = 1.0
            elif any(c.status == GoalNodeStatus.FAILED for c in children):
                parent.status = GoalNodeStatus.FAILED
            elif any(c.status == GoalNodeStatus.IN_PROGRESS for c in children):
                parent.status = GoalNodeStatus.IN_PROGRESS
        elif parent.goal_type == GoalType.OR:
            # OR: en iyi alt hedefin ilerlemesi
            parent.progress = max(c.progress for c in children)
            # OR: herhangi biri tamamsa tamamdir
            if any(c.status == GoalNodeStatus.COMPLETED for c in children):
                parent.status = GoalNodeStatus.COMPLETED
                parent.progress = 1.0
            elif all(c.status == GoalNodeStatus.FAILED for c in children):
                parent.status = GoalNodeStatus.FAILED
            elif any(c.status == GoalNodeStatus.IN_PROGRESS for c in children):
                parent.status = GoalNodeStatus.IN_PROGRESS

        # Yukariya devam et
        await self._propagate_progress(parent.id)

    async def check_dependencies(self, goal_id: str) -> bool:
        """Hedefin bagimliliklerinin karsilanip karsilanmadigini kontrol eder.

        Args:
            goal_id: Kontrol edilecek hedef ID.

        Returns:
            Tum bagimliliklar karsilandi mi.
        """
        if goal_id not in self.nodes:
            return False

        node = self.nodes[goal_id]
        for dep_id in node.dependencies:
            dep = self.nodes.get(dep_id)
            if dep is None or dep.status != GoalNodeStatus.COMPLETED:
                return False

        return True

    async def get_actionable_goals(self) -> list[GoalNode]:
        """Uygulanabilir (bagimliliklari karsilanan LEAF) hedefleri dondurur.

        Returns:
            Aksiyona hazir hedef listesi.
        """
        actionable: list[GoalNode] = []
        for node in self.nodes.values():
            if node.goal_type != GoalType.LEAF:
                continue
            if node.status != GoalNodeStatus.PENDING:
                continue
            deps_met = await self.check_dependencies(node.id)
            if deps_met:
                actionable.append(node)

        # Oncelik sirasina gore sirala (yuksek once)
        actionable.sort(key=lambda n: n.priority, reverse=True)
        return actionable

    async def get_blocked_goals(self) -> list[GoalNode]:
        """Bagimliliklari karsilanmayan hedefleri dondurur.

        Returns:
            Engellenmis hedef listesi.
        """
        blocked: list[GoalNode] = []
        for node in self.nodes.values():
            if node.status != GoalNodeStatus.PENDING:
                continue
            if not node.dependencies:
                continue
            deps_met = await self.check_dependencies(node.id)
            if not deps_met:
                blocked.append(node)
        return blocked

    def get_subtree(self, goal_id: str) -> list[GoalNode]:
        """Belirtilen hedefin alt agacini dondurur.

        Args:
            goal_id: Baslangic dugum ID.

        Returns:
            Alt agac dugum listesi.
        """
        if goal_id not in self.nodes:
            return []

        result: list[GoalNode] = []
        stack = [goal_id]
        while stack:
            current_id = stack.pop()
            node = self.nodes.get(current_id)
            if node is None:
                continue
            result.append(node)
            stack.extend(node.children_ids)

        return result

    async def snapshot(self) -> GoalTreeSnapshot:
        """Agacin tam goruntusunu dondurur.

        Returns:
            GoalTreeSnapshot.
        """
        total_progress = 0.0
        if self.root_id and self.root_id in self.nodes:
            total_progress = self.nodes[self.root_id].progress

        return GoalTreeSnapshot(
            root_id=self.root_id,
            nodes=dict(self.nodes),
            total_progress=total_progress,
        )
