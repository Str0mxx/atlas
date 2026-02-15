"""ATLAS Gorev Uretici modulu.

Atomik gorev olusturma, spesifikasyon,
kabul kriterleri, kaynak gereksinimleri, zaman tahminleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TaskGenerator:
    """Gorev uretici.

    Ayristirma dugumlerinden atomik gorevler uretir.

    Attributes:
        _tasks: Uretilen gorevler.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Gorev ureticiyi baslatir."""
        self._tasks: dict[
            str, dict[str, Any]
        ] = {}
        self._task_counter = 0
        self._stats = {
            "generated": 0,
        }

        logger.info(
            "TaskGenerator baslatildi",
        )

    def generate_task(
        self,
        goal_id: str,
        node_id: str,
        title: str,
        description: str = "",
        priority: str = "medium",
    ) -> dict[str, Any]:
        """Atomik gorev olusturur.

        Args:
            goal_id: Hedef ID.
            node_id: Dugum ID.
            title: Baslik.
            description: Aciklama.
            priority: Oncelik.

        Returns:
            Gorev bilgisi.
        """
        self._task_counter += 1
        task_id = (
            f"task_{goal_id}"
            f"_{self._task_counter}"
        )

        task = {
            "task_id": task_id,
            "goal_id": goal_id,
            "node_id": node_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": "pending",
            "acceptance_criteria": [],
            "resources": [],
            "estimated_hours": 0.0,
            "assigned_to": "",
            "created_at": time.time(),
        }

        self._tasks[task_id] = task
        self._stats["generated"] += 1

        return {
            "task_id": task_id,
            "goal_id": goal_id,
            "title": title,
            "generated": True,
        }

    def set_acceptance_criteria(
        self,
        task_id: str,
        criteria: list[str],
    ) -> dict[str, Any]:
        """Kabul kriterleri belirler.

        Args:
            task_id: Gorev ID.
            criteria: Kriter listesi.

        Returns:
            Guncelleme bilgisi.
        """
        task = self._tasks.get(task_id)
        if not task:
            return {
                "error": "task_not_found",
            }

        task["acceptance_criteria"] = criteria

        return {
            "task_id": task_id,
            "criteria_count": len(criteria),
            "updated": True,
        }

    def set_resources(
        self,
        task_id: str,
        resources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Kaynak gereksinimlerini belirler.

        Args:
            task_id: Gorev ID.
            resources: Kaynak listesi.

        Returns:
            Guncelleme bilgisi.
        """
        task = self._tasks.get(task_id)
        if not task:
            return {
                "error": "task_not_found",
            }

        task["resources"] = resources

        return {
            "task_id": task_id,
            "resource_count": len(resources),
            "updated": True,
        }

    def estimate_time(
        self,
        task_id: str,
        hours: float,
        confidence: float = 0.7,
    ) -> dict[str, Any]:
        """Zaman tahmini yapar.

        Args:
            task_id: Gorev ID.
            hours: Tahmini saat.
            confidence: Guven orani.

        Returns:
            Tahmin bilgisi.
        """
        task = self._tasks.get(task_id)
        if not task:
            return {
                "error": "task_not_found",
            }

        task["estimated_hours"] = hours
        task["time_confidence"] = confidence

        # Optimistik/pessimistik
        optimistic = round(
            hours * 0.7, 2,
        )
        pessimistic = round(
            hours * 1.5, 2,
        )

        return {
            "task_id": task_id,
            "estimated_hours": hours,
            "optimistic": optimistic,
            "pessimistic": pessimistic,
            "confidence": confidence,
        }

    def generate_from_nodes(
        self,
        goal_id: str,
        nodes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Dugumlerden toplu gorev uretir.

        Args:
            goal_id: Hedef ID.
            nodes: Dugum listesi.

        Returns:
            Uretim sonucu.
        """
        generated = []
        for node in nodes:
            if node.get("is_leaf", False):
                result = self.generate_task(
                    goal_id=goal_id,
                    node_id=node.get(
                        "node_id", "",
                    ),
                    title=node.get(
                        "description", "",
                    ),
                )
                generated.append(
                    result["task_id"],
                )

        return {
            "goal_id": goal_id,
            "tasks_generated": len(generated),
            "task_ids": generated,
        }

    def get_task(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        """Gorev getirir.

        Args:
            task_id: Gorev ID.

        Returns:
            Gorev bilgisi.
        """
        t = self._tasks.get(task_id)
        if not t:
            return {
                "error": "task_not_found",
            }
        return dict(t)

    def get_tasks_by_goal(
        self,
        goal_id: str,
    ) -> list[dict[str, Any]]:
        """Hedefe ait gorevleri getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Gorev listesi.
        """
        return [
            dict(t)
            for t in self._tasks.values()
            if t["goal_id"] == goal_id
        ]

    def update_status(
        self,
        task_id: str,
        status: str,
    ) -> dict[str, Any]:
        """Gorev durumunu gunceller.

        Args:
            task_id: Gorev ID.
            status: Yeni durum.

        Returns:
            Guncelleme bilgisi.
        """
        task = self._tasks.get(task_id)
        if not task:
            return {
                "error": "task_not_found",
            }

        task["status"] = status
        if status == "completed":
            task["completed_at"] = time.time()

        return {
            "task_id": task_id,
            "status": status,
            "updated": True,
        }

    @property
    def task_count(self) -> int:
        """Gorev sayisi."""
        return self._stats["generated"]

    @property
    def pending_count(self) -> int:
        """Bekleyen gorev sayisi."""
        return sum(
            1 for t in self._tasks.values()
            if t["status"] == "pending"
        )
