"""ATLAS Ilerleme Sentezleyici modulu.

Rollup ilerleme, tamamlanma hesaplama,
engel tespiti, ETA sentezi, durum raporlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProgressSynthesizer:
    """Ilerleme sentezleyici.

    Gorev ilerlemelerini sentezler.

    Attributes:
        _progress: Ilerleme kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Ilerleme sentezleyiciyi baslatir."""
        self._progress: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "synthesized": 0,
        }

        logger.info(
            "ProgressSynthesizer baslatildi",
        )

    def synthesize_progress(
        self,
        goal_id: str,
        tasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Ilerleme sentezler.

        Args:
            goal_id: Hedef ID.
            tasks: Gorev listesi (status alani ile).

        Returns:
            Sentez sonucu.
        """
        total = len(tasks)
        if total == 0:
            result = {
                "goal_id": goal_id,
                "total_tasks": 0,
                "completed": 0,
                "in_progress": 0,
                "pending": 0,
                "failed": 0,
                "completion_pct": 0.0,
                "synthesized_at": time.time(),
            }
            self._progress[goal_id] = result
            self._stats["synthesized"] += 1
            return result

        completed = sum(
            1 for t in tasks
            if t.get("status") == "completed"
        )
        in_progress = sum(
            1 for t in tasks
            if t.get("status") == "in_progress"
        )
        failed = sum(
            1 for t in tasks
            if t.get("status") == "failed"
        )
        pending = total - completed - in_progress - failed

        completion_pct = round(
            completed / total * 100, 1,
        )

        result = {
            "goal_id": goal_id,
            "total_tasks": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "failed": failed,
            "completion_pct": completion_pct,
            "synthesized_at": time.time(),
        }

        self._progress[goal_id] = result
        self._stats["synthesized"] += 1

        return result

    def identify_blockers(
        self,
        goal_id: str,
        tasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Engelleri tespit eder.

        Args:
            goal_id: Hedef ID.
            tasks: Gorev listesi.

        Returns:
            Engel bilgisi.
        """
        blockers = []

        for task in tasks:
            status = task.get("status", "")
            if status == "failed":
                blockers.append({
                    "task_id": task.get(
                        "task_id", "",
                    ),
                    "type": "failed_task",
                    "description": (
                        f"Task failed: "
                        f"{task.get('title', '')}"
                    ),
                })

            # Uzun sure bekleyen
            if status == "in_progress":
                started = task.get(
                    "started_at", 0,
                )
                if started and (
                    time.time() - started > 86400
                ):
                    blockers.append({
                        "task_id": task.get(
                            "task_id", "",
                        ),
                        "type": "stuck_task",
                        "description": (
                            "Task stuck > 24h"
                        ),
                    })

        return {
            "goal_id": goal_id,
            "blockers": blockers,
            "blocker_count": len(blockers),
            "is_blocked": len(blockers) > 0,
        }

    def calculate_eta(
        self,
        goal_id: str,
        tasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """ETA hesaplar.

        Args:
            goal_id: Hedef ID.
            tasks: Gorev listesi.

        Returns:
            ETA bilgisi.
        """
        total = len(tasks)
        if total == 0:
            return {
                "goal_id": goal_id,
                "eta_hours": 0.0,
                "completed": True,
            }

        completed = sum(
            1 for t in tasks
            if t.get("status") == "completed"
        )

        if completed == total:
            return {
                "goal_id": goal_id,
                "eta_hours": 0.0,
                "completed": True,
            }

        # Kalan gorevlerin tahmini sureleri
        remaining_hours = sum(
            t.get("estimated_hours", 1.0)
            for t in tasks
            if t.get("status") != "completed"
        )

        return {
            "goal_id": goal_id,
            "eta_hours": round(
                remaining_hours, 2,
            ),
            "remaining_tasks": (
                total - completed
            ),
            "completed": False,
        }

    def generate_report(
        self,
        goal_id: str,
        tasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Durum raporu olusturur.

        Args:
            goal_id: Hedef ID.
            tasks: Gorev listesi.

        Returns:
            Rapor bilgisi.
        """
        progress = self.synthesize_progress(
            goal_id, tasks,
        )
        blockers = self.identify_blockers(
            goal_id, tasks,
        )
        eta = self.calculate_eta(
            goal_id, tasks,
        )

        # Oncelik dagilimi
        priority_dist: dict[str, int] = {}
        for task in tasks:
            p = task.get("priority", "medium")
            priority_dist[p] = (
                priority_dist.get(p, 0) + 1
            )

        return {
            "goal_id": goal_id,
            "progress": progress,
            "blockers": blockers,
            "eta": eta,
            "priority_distribution": (
                priority_dist
            ),
            "health": (
                "healthy"
                if not blockers["is_blocked"]
                else "at_risk"
            ),
            "generated_at": time.time(),
        }

    def get_progress(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Ilerleme getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Ilerleme bilgisi.
        """
        p = self._progress.get(goal_id)
        if not p:
            return {
                "error": "goal_not_found",
            }
        return dict(p)

    @property
    def synthesis_count(self) -> int:
        """Sentez sayisi."""
        return self._stats["synthesized"]
