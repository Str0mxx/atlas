"""ATLAS Kriz Aksiyon Planı Üretici modülü.

Plan üretimi, görev atama,
zaman çizelgesi, kaynak tahsisi,
bağımlılık yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CrisisActionPlanGenerator:
    """Kriz aksiyon planı üretici.

    Kriz aksiyon planlarını üretir.

    Attributes:
        _plans: Plan kayıtları.
        _tasks: Görev kayıtları.
    """

    def __init__(self) -> None:
        """Üreticiyi başlatır."""
        self._plans: dict[
            str, dict[str, Any]
        ] = {}
        self._tasks: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._task_counter = 0
        self._stats = {
            "plans_generated": 0,
            "tasks_assigned": 0,
        }

        logger.info(
            "CrisisActionPlanGenerator "
            "baslatildi",
        )

    def generate_plan(
        self,
        crisis_id: str,
        crisis_type: str = "general",
        severity: str = "moderate",
    ) -> dict[str, Any]:
        """Plan üretir.

        Args:
            crisis_id: Kriz kimliği.
            crisis_type: Kriz tipi.
            severity: Şiddet.

        Returns:
            Üretim bilgisi.
        """
        self._counter += 1
        pid = f"pln_{self._counter}"

        templates = {
            "outage": [
                "Assess impact",
                "Notify stakeholders",
                "Activate backup systems",
                "Restore service",
                "Post-incident review",
            ],
            "security": [
                "Contain breach",
                "Assess damage",
                "Notify affected parties",
                "Remediate vulnerability",
                "Strengthen defenses",
            ],
            "general": [
                "Assess situation",
                "Activate response team",
                "Execute containment",
                "Communicate status",
                "Begin recovery",
            ],
        }

        steps = templates.get(
            crisis_type,
            templates["general"],
        )

        self._plans[crisis_id] = {
            "plan_id": pid,
            "crisis_id": crisis_id,
            "crisis_type": crisis_type,
            "severity": severity,
            "steps": steps,
            "status": "active",
            "timestamp": time.time(),
        }
        self._tasks[crisis_id] = []

        self._stats[
            "plans_generated"
        ] += 1

        return {
            "plan_id": pid,
            "step_count": len(steps),
            "steps": steps,
            "generated": True,
        }

    def assign_task(
        self,
        crisis_id: str,
        task_name: str,
        assignee: str = "",
        priority: str = "high",
    ) -> dict[str, Any]:
        """Görev atar.

        Args:
            crisis_id: Kriz kimliği.
            task_name: Görev adı.
            assignee: Atanan kişi.
            priority: Öncelik.

        Returns:
            Atama bilgisi.
        """
        self._task_counter += 1
        tid = f"tsk_{self._task_counter}"

        task = {
            "task_id": tid,
            "name": task_name,
            "assignee": assignee,
            "priority": priority,
            "status": "assigned",
            "dependencies": [],
            "timestamp": time.time(),
        }

        if crisis_id not in self._tasks:
            self._tasks[crisis_id] = []
        self._tasks[crisis_id].append(
            task,
        )

        self._stats[
            "tasks_assigned"
        ] += 1

        return {
            "task_id": tid,
            "assignee": assignee,
            "assigned": True,
        }

    def create_timeline(
        self,
        crisis_id: str,
    ) -> dict[str, Any]:
        """Zaman çizelgesi oluşturur.

        Args:
            crisis_id: Kriz kimliği.

        Returns:
            Çizelge bilgisi.
        """
        plan = self._plans.get(crisis_id)
        if not plan:
            return {
                "crisis_id": crisis_id,
                "found": False,
            }

        steps = plan.get("steps", [])
        timeline = []
        offset = 0

        for step in steps:
            timeline.append({
                "step": step,
                "start_minutes": offset,
                "duration_minutes": 30,
            })
            offset += 30

        return {
            "crisis_id": crisis_id,
            "timeline": timeline,
            "total_minutes": offset,
            "created": True,
        }

    def allocate_resources(
        self,
        crisis_id: str,
        resources: dict[str, int]
        | None = None,
    ) -> dict[str, Any]:
        """Kaynak tahsis eder.

        Args:
            crisis_id: Kriz kimliği.
            resources: Kaynaklar.

        Returns:
            Tahsis bilgisi.
        """
        resources = resources or {}

        plan = self._plans.get(crisis_id)
        if plan:
            plan["resources"] = resources

        total = sum(resources.values())

        return {
            "crisis_id": crisis_id,
            "resources": resources,
            "total_units": total,
            "allocated": True,
        }

    def add_dependency(
        self,
        crisis_id: str,
        task_id: str,
        depends_on: str,
    ) -> dict[str, Any]:
        """Bağımlılık ekler.

        Args:
            crisis_id: Kriz kimliği.
            task_id: Görev kimliği.
            depends_on: Bağımlı olduğu görev.

        Returns:
            Ekleme bilgisi.
        """
        tasks = self._tasks.get(
            crisis_id, [],
        )

        for task in tasks:
            if task["task_id"] == task_id:
                task["dependencies"].append(
                    depends_on,
                )
                return {
                    "task_id": task_id,
                    "depends_on": depends_on,
                    "added": True,
                }

        return {
            "task_id": task_id,
            "found": False,
        }

    @property
    def plan_count(self) -> int:
        """Plan sayısı."""
        return self._stats[
            "plans_generated"
        ]

    @property
    def task_count(self) -> int:
        """Görev sayısı."""
        return self._stats[
            "tasks_assigned"
        ]
