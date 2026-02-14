"""ATLAS Aksiyon Koordinatoru modulu.

Plan calistirma, coklu sistem koordinasyonu,
kaynak orkestrasyonu, zamanlama yonetimi
ve geri bildirim isleme.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ActionCoordinator:
    """Aksiyon koordinatoru.

    Kararlari aksiyonlara donusturur ve
    birden fazla sistemi koordine eder.

    Attributes:
        _actions: Aksiyon kayitlari.
        _plans: Yurume planlari.
        _resources: Tahsis edilen kaynaklar.
        _feedback: Geri bildirim kayitlari.
        _execution_log: Calistirma gecmisi.
    """

    def __init__(self) -> None:
        """Aksiyon koordinatorunu baslatir."""
        self._actions: dict[str, dict[str, Any]] = {}
        self._plans: dict[str, dict[str, Any]] = {}
        self._resources: dict[str, dict[str, Any]] = {}
        self._feedback: list[dict[str, Any]] = []
        self._execution_log: list[dict[str, Any]] = []
        self._action_counter = 0

        logger.info("ActionCoordinator baslatildi")

    def create_action(
        self,
        name: str,
        target_systems: list[str] | None = None,
        parameters: dict[str, Any] | None = None,
        priority: int = 5,
        timeout: int = 60,
    ) -> dict[str, Any]:
        """Aksiyon olusturur.

        Args:
            name: Aksiyon adi.
            target_systems: Hedef sistemler.
            parameters: Parametreler.
            priority: Oncelik (1-10).
            timeout: Zaman asimi (saniye).

        Returns:
            Aksiyon kaydi.
        """
        self._action_counter += 1
        action_id = f"act-{self._action_counter}"

        action = {
            "action_id": action_id,
            "name": name,
            "target_systems": target_systems or [],
            "parameters": parameters or {},
            "priority": max(1, min(10, priority)),
            "timeout": timeout,
            "state": "created",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._actions[action_id] = action

        return action

    def execute_action(self, action_id: str) -> dict[str, Any]:
        """Aksiyonu calistirir.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Calistirma sonucu.
        """
        action = self._actions.get(action_id)
        if not action:
            return {"success": False, "reason": "Aksiyon bulunamadi"}

        if action["state"] not in ("created", "planned"):
            return {
                "success": False,
                "reason": f"Gecersiz durum: {action['state']}",
            }

        action["state"] = "executing"
        action["started_at"] = datetime.now(timezone.utc).isoformat()

        # Simulasyon: her hedef sistem icin
        results = []
        for system in action["target_systems"]:
            results.append({
                "system": system,
                "status": "completed",
            })

        action["state"] = "completed"
        action["completed_at"] = datetime.now(timezone.utc).isoformat()
        action["results"] = results

        self._execution_log.append({
            "action_id": action_id,
            "name": action["name"],
            "systems": action["target_systems"],
            "state": "completed",
            "timestamp": action["completed_at"],
        })

        logger.info("Aksiyon tamamlandi: %s", action["name"])
        return {"success": True, "action_id": action_id, "results": results}

    def create_plan(
        self,
        name: str,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Yurume plani olusturur.

        Args:
            name: Plan adi.
            steps: Adimlar (sirali).

        Returns:
            Plan kaydi.
        """
        plan_id = f"plan-{len(self._plans)}"

        plan = {
            "plan_id": plan_id,
            "name": name,
            "steps": steps,
            "current_step": 0,
            "state": "created",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._plans[plan_id] = plan

        return plan

    def execute_plan(self, plan_id: str) -> dict[str, Any]:
        """Plani calistirir.

        Args:
            plan_id: Plan ID.

        Returns:
            Calistirma sonucu.
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return {"success": False, "reason": "Plan bulunamadi"}

        plan["state"] = "executing"
        completed_steps = []

        for i, step in enumerate(plan["steps"]):
            plan["current_step"] = i

            # Adim aksiyonu olustur ve calistir
            action = self.create_action(
                name=step.get("name", f"step-{i}"),
                target_systems=step.get("systems", []),
                parameters=step.get("parameters", {}),
            )
            result = self.execute_action(action["action_id"])

            if not result["success"]:
                plan["state"] = "failed"
                plan["failed_at_step"] = i
                return {
                    "success": False,
                    "plan_id": plan_id,
                    "failed_step": i,
                    "completed_steps": completed_steps,
                }

            completed_steps.append(i)

        plan["state"] = "completed"
        plan["completed_at"] = datetime.now(timezone.utc).isoformat()

        return {
            "success": True,
            "plan_id": plan_id,
            "completed_steps": completed_steps,
        }

    def allocate_resource(
        self,
        resource_id: str,
        action_id: str,
        amount: float = 1.0,
    ) -> bool:
        """Kaynak tahsis eder.

        Args:
            resource_id: Kaynak ID.
            action_id: Aksiyon ID.
            amount: Miktar.

        Returns:
            Basarili ise True.
        """
        if action_id not in self._actions:
            return False

        self._resources[f"{resource_id}:{action_id}"] = {
            "resource_id": resource_id,
            "action_id": action_id,
            "amount": amount,
            "allocated_at": datetime.now(timezone.utc).isoformat(),
        }
        return True

    def release_resource(
        self,
        resource_id: str,
        action_id: str,
    ) -> bool:
        """Kaynagi serbest birakir.

        Args:
            resource_id: Kaynak ID.
            action_id: Aksiyon ID.

        Returns:
            Basarili ise True.
        """
        key = f"{resource_id}:{action_id}"
        if key in self._resources:
            del self._resources[key]
            return True
        return False

    def add_feedback(
        self,
        action_id: str,
        feedback_type: str,
        content: str,
        score: float = 0.5,
    ) -> dict[str, Any]:
        """Geri bildirim ekler.

        Args:
            action_id: Aksiyon ID.
            feedback_type: Geri bildirim turu.
            content: Icerik.
            score: Puan (0-1).

        Returns:
            Geri bildirim kaydi.
        """
        fb = {
            "action_id": action_id,
            "type": feedback_type,
            "content": content,
            "score": max(0.0, min(1.0, score)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._feedback.append(fb)

        return fb

    def get_action(
        self,
        action_id: str,
    ) -> dict[str, Any] | None:
        """Aksiyon getirir.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Aksiyon kaydi veya None.
        """
        return self._actions.get(action_id)

    def get_plan(
        self,
        plan_id: str,
    ) -> dict[str, Any] | None:
        """Plan getirir.

        Args:
            plan_id: Plan ID.

        Returns:
            Plan kaydi veya None.
        """
        return self._plans.get(plan_id)

    def get_execution_log(
        self,
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Calistirma gecmisini getirir.

        Args:
            limit: Maks kayit.

        Returns:
            Gecmis listesi.
        """
        if limit > 0:
            return self._execution_log[-limit:]
        return list(self._execution_log)

    def get_feedback(
        self,
        action_id: str = "",
    ) -> list[dict[str, Any]]:
        """Geri bildirimleri getirir.

        Args:
            action_id: Aksiyon filtresi.

        Returns:
            Geri bildirim listesi.
        """
        if action_id:
            return [
                f for f in self._feedback
                if f["action_id"] == action_id
            ]
        return list(self._feedback)

    @property
    def total_actions(self) -> int:
        """Toplam aksiyon sayisi."""
        return len(self._actions)

    @property
    def total_plans(self) -> int:
        """Toplam plan sayisi."""
        return len(self._plans)

    @property
    def completed_actions(self) -> int:
        """Tamamlanan aksiyon sayisi."""
        return sum(
            1 for a in self._actions.values()
            if a["state"] == "completed"
        )

    @property
    def resource_count(self) -> int:
        """Tahsis edilen kaynak sayisi."""
        return len(self._resources)

    @property
    def feedback_count(self) -> int:
        """Geri bildirim sayisi."""
        return len(self._feedback)
