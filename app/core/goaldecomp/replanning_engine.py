"""ATLAS Yeniden Planlama Motoru modulu.

Plan ayarlama, hata kurtarma,
firsat degerlendirme, kapsam degisikligi, kaynak degisikligi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ReplanningEngine:
    """Yeniden planlama motoru.

    Basarisizlik veya degisikliklerde plani yeniden olusturur.

    Attributes:
        _replans: Yeniden planlama kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Yeniden planlama motorunu baslatir."""
        self._replans: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "replanned": 0,
        }

        logger.info(
            "ReplanningEngine baslatildi",
        )

    def replan(
        self,
        goal_id: str,
        reason: str,
        failed_tasks: list[str] | None = None,
        new_constraints: (
            dict[str, Any] | None
        ) = None,
    ) -> dict[str, Any]:
        """Yeniden planlama yapar.

        Args:
            goal_id: Hedef ID.
            reason: Neden.
            failed_tasks: Basarisiz gorevler.
            new_constraints: Yeni kisitlar.

        Returns:
            Yeniden planlama sonucu.
        """
        replan = {
            "goal_id": goal_id,
            "reason": reason,
            "failed_tasks": failed_tasks or [],
            "new_constraints": (
                new_constraints or {}
            ),
            "actions": [],
            "replanned_at": time.time(),
        }

        # Nedene gore aksiyon belirle
        if reason == "failure":
            actions = self._handle_failure(
                failed_tasks or [],
            )
        elif reason == "scope_change":
            actions = self._handle_scope_change(
                new_constraints or {},
            )
        elif reason == "resource_change":
            actions = (
                self._handle_resource_change(
                    new_constraints or {},
                )
            )
        elif reason == "opportunity":
            actions = (
                self._handle_opportunity(
                    new_constraints or {},
                )
            )
        elif reason == "timeout":
            actions = self._handle_timeout(
                failed_tasks or [],
            )
        else:
            actions = [{
                "type": "review",
                "description": (
                    "Manual review needed"
                ),
            }]

        replan["actions"] = actions

        if goal_id not in self._replans:
            self._replans[goal_id] = []
        self._replans[goal_id].append(replan)
        self._stats["replanned"] += 1

        return {
            "goal_id": goal_id,
            "reason": reason,
            "action_count": len(actions),
            "actions": actions,
            "replanned": True,
        }

    def _handle_failure(
        self,
        failed_tasks: list[str],
    ) -> list[dict[str, Any]]:
        """Hata kurtarma aksiyonlari.

        Args:
            failed_tasks: Basarisiz gorevler.

        Returns:
            Aksiyon listesi.
        """
        actions = []
        for tid in failed_tasks:
            actions.append({
                "type": "retry",
                "task_id": tid,
                "description": (
                    f"Retry task {tid}"
                ),
            })
        if not actions:
            actions.append({
                "type": "investigate",
                "description": (
                    "Investigate failure cause"
                ),
            })
        return actions

    def _handle_scope_change(
        self,
        constraints: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Kapsam degisikligi aksiyonlari.

        Args:
            constraints: Yeni kisitlar.

        Returns:
            Aksiyon listesi.
        """
        actions = []
        if "added_tasks" in constraints:
            actions.append({
                "type": "add_tasks",
                "description": (
                    "Add new tasks to plan"
                ),
                "count": len(
                    constraints["added_tasks"],
                ),
            })
        if "removed_tasks" in constraints:
            actions.append({
                "type": "remove_tasks",
                "description": (
                    "Remove tasks from plan"
                ),
                "count": len(
                    constraints["removed_tasks"],
                ),
            })
        if not actions:
            actions.append({
                "type": "reassess",
                "description": (
                    "Reassess scope"
                ),
            })
        return actions

    def _handle_resource_change(
        self,
        constraints: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Kaynak degisikligi aksiyonlari.

        Args:
            constraints: Yeni kisitlar.

        Returns:
            Aksiyon listesi.
        """
        actions = []
        if constraints.get("reduced_budget"):
            actions.append({
                "type": "reprioritize",
                "description": (
                    "Reprioritize with "
                    "reduced budget"
                ),
            })
        if constraints.get("reduced_time"):
            actions.append({
                "type": "parallelize",
                "description": (
                    "Parallelize tasks "
                    "for speed"
                ),
            })
        if not actions:
            actions.append({
                "type": "reallocate",
                "description": (
                    "Reallocate resources"
                ),
            })
        return actions

    def _handle_opportunity(
        self,
        constraints: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Firsat degerlendirme aksiyonlari.

        Args:
            constraints: Firsat bilgileri.

        Returns:
            Aksiyon listesi.
        """
        actions = [{
            "type": "evaluate",
            "description": (
                "Evaluate new opportunity"
            ),
        }]
        if constraints.get("shortcut"):
            actions.append({
                "type": "shortcut",
                "description": (
                    "Apply shortcut to "
                    "skip steps"
                ),
            })
        return actions

    def _handle_timeout(
        self,
        timed_out_tasks: list[str],
    ) -> list[dict[str, Any]]:
        """Zaman asimi aksiyonlari.

        Args:
            timed_out_tasks: Zaman asimina ugrayan gorevler.

        Returns:
            Aksiyon listesi.
        """
        actions = []
        for tid in timed_out_tasks:
            actions.append({
                "type": "simplify",
                "task_id": tid,
                "description": (
                    f"Simplify task {tid}"
                ),
            })
        if not actions:
            actions.append({
                "type": "extend_deadline",
                "description": (
                    "Request deadline extension"
                ),
            })
        return actions

    def get_replan_history(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Yeniden planlama gecmisi getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Gecmis bilgisi.
        """
        history = self._replans.get(
            goal_id, [],
        )

        return {
            "goal_id": goal_id,
            "replan_count": len(history),
            "replans": [
                {
                    "reason": r["reason"],
                    "action_count": len(
                        r["actions"],
                    ),
                    "replanned_at": r[
                        "replanned_at"
                    ],
                }
                for r in history
            ],
        }

    def get_latest_replan(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Son yeniden planlama getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Son planlama bilgisi.
        """
        history = self._replans.get(
            goal_id, [],
        )
        if not history:
            return {
                "error": "no_replans_found",
            }
        return dict(history[-1])

    @property
    def replan_count(self) -> int:
        """Yeniden planlama sayisi."""
        return self._stats["replanned"]
