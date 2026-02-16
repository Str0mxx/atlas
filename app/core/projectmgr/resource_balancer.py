"""ATLAS Proje Kaynak Dengeleyici modülü.

İş yükü analizi, yeniden tahsis önerileri,
çatışma çözümü, kapasite planlama,
optimizasyon.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProjectResourceBalancer:
    """Proje kaynak dengeleyici.

    Proje kaynaklarını dengeler ve optimize eder.

    Attributes:
        _resources: Kaynak kayıtları.
        _allocations: Tahsis kayıtları.
    """

    def __init__(self) -> None:
        """Dengeleyiciyi başlatır."""
        self._resources: dict[
            str, dict[str, Any]
        ] = {}
        self._allocations: list[
            dict[str, Any]
        ] = []
        self._conflicts: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "analyses_done": 0,
            "reallocations": 0,
            "conflicts_resolved": 0,
            "optimizations": 0,
        }

        logger.info(
            "ProjectResourceBalancer "
            "baslatildi",
        )

    def analyze_workload(
        self,
        team_members: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """İş yükü analiz eder.

        Args:
            team_members: Takım üyeleri
                (name, tasks, capacity).

        Returns:
            Analiz bilgisi.
        """
        if not team_members:
            return {
                "members": 0,
                "balanced": True,
                "analyzed": False,
            }

        utilizations = []
        overloaded = []
        underloaded = []

        for member in team_members:
            name = member.get("name", "")
            tasks = member.get("tasks", 0)
            capacity = member.get(
                "capacity", 10,
            )

            util = round(
                tasks
                / max(capacity, 1) * 100,
                1,
            )
            utilizations.append(util)

            if util > 100:
                overloaded.append(name)
            elif util < 50:
                underloaded.append(name)

        avg_util = round(
            sum(utilizations)
            / max(len(utilizations), 1),
            1,
        )
        balanced = (
            len(overloaded) == 0
            and avg_util >= 50
        )

        self._stats["analyses_done"] += 1

        return {
            "members": len(team_members),
            "avg_utilization": avg_util,
            "overloaded": overloaded,
            "underloaded": underloaded,
            "balanced": balanced,
            "analyzed": True,
        }

    def suggest_reallocation(
        self,
        from_member: str,
        to_member: str,
        task_count: int = 1,
        reason: str = "",
    ) -> dict[str, Any]:
        """Yeniden tahsis önerir.

        Args:
            from_member: Kimden.
            to_member: Kime.
            task_count: Görev sayısı.
            reason: Sebep.

        Returns:
            Öneri bilgisi.
        """
        self._counter += 1
        aid = f"alloc_{self._counter}"

        allocation = {
            "allocation_id": aid,
            "from": from_member,
            "to": to_member,
            "task_count": task_count,
            "reason": reason,
            "status": "suggested",
            "created_at": time.time(),
        }
        self._allocations.append(
            allocation,
        )
        self._stats["reallocations"] += 1

        return {
            "allocation_id": aid,
            "from": from_member,
            "to": to_member,
            "task_count": task_count,
            "suggested": True,
        }

    def resolve_conflict(
        self,
        resource_name: str,
        projects: list[str],
        strategy: str = "priority",
    ) -> dict[str, Any]:
        """Kaynak çatışması çözer.

        Args:
            resource_name: Kaynak adı.
            projects: Çatışan projeler.
            strategy: Çözüm stratejisi.

        Returns:
            Çözüm bilgisi.
        """
        if len(projects) < 2:
            return {
                "resource": resource_name,
                "conflict": False,
                "resolved": False,
            }

        if strategy == "priority":
            winner = projects[0]
            resolution = "priority_based"
        elif strategy == "split":
            winner = "shared"
            resolution = "split_allocation"
        elif strategy == "queue":
            winner = projects[0]
            resolution = "queued_access"
        else:
            winner = projects[0]
            resolution = "default"

        conflict = {
            "resource": resource_name,
            "projects": projects,
            "strategy": strategy,
            "winner": winner,
            "resolution": resolution,
            "timestamp": time.time(),
        }
        self._conflicts.append(conflict)
        self._stats[
            "conflicts_resolved"
        ] += 1

        return {
            "resource": resource_name,
            "projects": projects,
            "winner": winner,
            "resolution": resolution,
            "conflict": True,
            "resolved": True,
        }

    def plan_capacity(
        self,
        current_members: int,
        planned_tasks: int,
        avg_capacity: float = 10.0,
        buffer_percent: float = 20.0,
    ) -> dict[str, Any]:
        """Kapasite planlar.

        Args:
            current_members: Mevcut üye.
            planned_tasks: Planlanan görev.
            avg_capacity: Ortalama kapasite.
            buffer_percent: Tampon yüzdesi.

        Returns:
            Kapasite bilgisi.
        """
        total_capacity = round(
            current_members * avg_capacity,
            1,
        )
        effective = round(
            total_capacity
            * (1 - buffer_percent / 100),
            1,
        )

        needed = round(
            planned_tasks / max(
                avg_capacity, 1,
            ), 1,
        )
        gap = round(
            needed - current_members, 1,
        )

        sufficient = (
            effective >= planned_tasks
        )

        return {
            "current_members": (
                current_members
            ),
            "total_capacity": total_capacity,
            "effective_capacity": effective,
            "planned_tasks": planned_tasks,
            "members_needed": max(
                needed, 0,
            ),
            "gap": max(gap, 0),
            "sufficient": sufficient,
        }

    def optimize(
        self,
        project_id: str,
        resources: list[dict[str, Any]]
        | None = None,
        constraints: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Kaynak optimizasyonu yapar.

        Args:
            project_id: Proje ID.
            resources: Kaynaklar.
            constraints: Kısıtlar.

        Returns:
            Optimizasyon bilgisi.
        """
        resources = resources or []
        constraints = constraints or {}

        total_cost = sum(
            r.get("cost", 0)
            for r in resources
        )
        total_capacity = sum(
            r.get("capacity", 0)
            for r in resources
        )

        # Basit optimizasyon önerileri
        suggestions = []
        for r in resources:
            util = r.get("utilization", 0)
            if util < 30:
                suggestions.append({
                    "resource": r.get(
                        "name", "",
                    ),
                    "action": "reduce",
                    "reason": "low_utilization",
                })
            elif util > 90:
                suggestions.append({
                    "resource": r.get(
                        "name", "",
                    ),
                    "action": "increase",
                    "reason": (
                        "high_utilization"
                    ),
                })

        efficiency = round(
            total_capacity
            / max(total_cost, 1) * 100,
            1,
        )

        self._stats["optimizations"] += 1

        return {
            "project_id": project_id,
            "resources_count": len(
                resources,
            ),
            "total_cost": total_cost,
            "total_capacity": (
                total_capacity
            ),
            "efficiency_score": efficiency,
            "suggestions": suggestions,
            "suggestion_count": len(
                suggestions,
            ),
            "optimized": True,
        }

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "analyses_done"
        ]

    @property
    def reallocation_count(self) -> int:
        """Yeniden tahsis sayısı."""
        return self._stats[
            "reallocations"
        ]
