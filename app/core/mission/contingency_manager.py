"""ATLAS Olasilik Yoneticisi modulu.

Plan B aktivasyonu, hata kurtarma, gorev iptal,
kademeli dususme ve alinan dersler.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.mission import ContingencyPlan, ContingencyType

logger = logging.getLogger(__name__)


class ContingencyManager:
    """Olasilik yoneticisi.

    Olasilik planlarini yonetir, hata kurtarma
    ve kademeli dususme stratejilerini uygular.

    Attributes:
        _plans: Olasilik planlari.
        _lessons: Alinan dersler.
        _abort_log: Iptal gecmisi.
    """

    def __init__(self) -> None:
        """Olasilik yoneticisini baslatir."""
        self._plans: dict[str, ContingencyPlan] = {}
        self._lessons: list[dict[str, Any]] = []
        self._abort_log: list[dict[str, Any]] = []
        self._recovery_actions: dict[str, list[str]] = {}

        logger.info("ContingencyManager baslatildi")

    def create_plan(
        self,
        mission_id: str,
        contingency_type: ContingencyType,
        trigger_condition: str,
        actions: list[str],
    ) -> ContingencyPlan:
        """Olasilik plani olusturur.

        Args:
            mission_id: Gorev ID.
            contingency_type: Plan tipi.
            trigger_condition: Tetiklenme kosulu.
            actions: Aksiyon listesi.

        Returns:
            ContingencyPlan nesnesi.
        """
        plan = ContingencyPlan(
            mission_id=mission_id,
            contingency_type=contingency_type,
            trigger_condition=trigger_condition,
            actions=actions,
        )
        self._plans[plan.plan_id] = plan

        logger.info(
            "Olasilik plani: %s (%s)",
            contingency_type.value, plan.plan_id,
        )
        return plan

    def activate_plan(self, plan_id: str) -> bool:
        """Plani aktiflestirir.

        Args:
            plan_id: Plan ID.

        Returns:
            Basarili ise True.
        """
        plan = self._plans.get(plan_id)
        if not plan or plan.activated:
            return False

        plan.activated = True
        plan.activated_at = datetime.now(timezone.utc)

        logger.warning(
            "Plan aktif: %s (%s)",
            plan.contingency_type.value, plan_id,
        )
        return True

    def deactivate_plan(self, plan_id: str) -> bool:
        """Plani deaktif eder.

        Args:
            plan_id: Plan ID.

        Returns:
            Basarili ise True.
        """
        plan = self._plans.get(plan_id)
        if not plan or not plan.activated:
            return False

        plan.activated = False
        return True

    def get_plans(
        self,
        mission_id: str,
        contingency_type: ContingencyType | None = None,
        active_only: bool = False,
    ) -> list[ContingencyPlan]:
        """Planlari getirir.

        Args:
            mission_id: Gorev ID.
            contingency_type: Tip filtresi.
            active_only: Sadece aktifler.

        Returns:
            Plan listesi.
        """
        plans = [
            p for p in self._plans.values()
            if p.mission_id == mission_id
        ]
        if contingency_type:
            plans = [
                p for p in plans
                if p.contingency_type == contingency_type
            ]
        if active_only:
            plans = [p for p in plans if p.activated]
        return plans

    def activate_plan_b(self, mission_id: str) -> ContingencyPlan | None:
        """Plan B'yi aktiflestirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Aktiflestirilen plan veya None.
        """
        plans = self.get_plans(mission_id, ContingencyType.PLAN_B)
        for plan in plans:
            if not plan.activated:
                self.activate_plan(plan.plan_id)
                return plan
        return None

    def initiate_recovery(
        self,
        mission_id: str,
        failure_description: str,
        recovery_steps: list[str],
    ) -> dict[str, Any]:
        """Kurtarma baslatir.

        Args:
            mission_id: Gorev ID.
            failure_description: Hata aciklamasi.
            recovery_steps: Kurtarma adimlari.

        Returns:
            Kurtarma kaydi.
        """
        self._recovery_actions[mission_id] = recovery_steps

        # Recovery planini aktifle
        recovery_plans = self.get_plans(
            mission_id, ContingencyType.RECOVERY,
        )
        activated = None
        for plan in recovery_plans:
            if not plan.activated:
                self.activate_plan(plan.plan_id)
                activated = plan
                break

        return {
            "mission_id": mission_id,
            "failure": failure_description,
            "steps": recovery_steps,
            "plan_activated": activated.plan_id if activated else "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def abort_mission(
        self,
        mission_id: str,
        reason: str,
        aborted_by: str = "",
    ) -> dict[str, Any]:
        """Gorevi iptal eder.

        Args:
            mission_id: Gorev ID.
            reason: Iptal nedeni.
            aborted_by: Iptal eden.

        Returns:
            Iptal kaydi.
        """
        record = {
            "mission_id": mission_id,
            "reason": reason,
            "aborted_by": aborted_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._abort_log.append(record)

        # Abort planlarini aktifle
        abort_plans = self.get_plans(
            mission_id, ContingencyType.ABORT,
        )
        for plan in abort_plans:
            if not plan.activated:
                self.activate_plan(plan.plan_id)

        logger.warning("Gorev iptal: %s - %s", mission_id, reason)
        return record

    def graceful_degradation(
        self,
        mission_id: str,
        degraded_features: list[str],
    ) -> dict[str, Any]:
        """Kademeli dususme uygular.

        Args:
            mission_id: Gorev ID.
            degraded_features: Dusurulen ozellikler.

        Returns:
            Dususme kaydi.
        """
        # Degradation planlarini aktifle
        deg_plans = self.get_plans(
            mission_id, ContingencyType.DEGRADATION,
        )
        activated_plans = []
        for plan in deg_plans:
            if not plan.activated:
                self.activate_plan(plan.plan_id)
                activated_plans.append(plan.plan_id)

        return {
            "mission_id": mission_id,
            "degraded_features": degraded_features,
            "activated_plans": activated_plans,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def record_lesson(
        self,
        mission_id: str,
        lesson: str,
        category: str = "general",
        severity: str = "info",
    ) -> None:
        """Ders kaydeder.

        Args:
            mission_id: Gorev ID.
            lesson: Alinan ders.
            category: Kategori.
            severity: Siddet.
        """
        self._lessons.append({
            "mission_id": mission_id,
            "lesson": lesson,
            "category": category,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_lessons(
        self,
        mission_id: str = "",
        category: str = "",
    ) -> list[dict[str, Any]]:
        """Dersleri getirir.

        Args:
            mission_id: Gorev filtresi.
            category: Kategori filtresi.

        Returns:
            Ders listesi.
        """
        lessons = list(self._lessons)
        if mission_id:
            lessons = [l for l in lessons if l["mission_id"] == mission_id]
        if category:
            lessons = [l for l in lessons if l["category"] == category]
        return lessons

    def get_abort_log(self) -> list[dict[str, Any]]:
        """Iptal gecmisini getirir.

        Returns:
            Iptal kayit listesi.
        """
        return list(self._abort_log)

    @property
    def total_plans(self) -> int:
        """Toplam plan sayisi."""
        return len(self._plans)

    @property
    def active_plan_count(self) -> int:
        """Aktif plan sayisi."""
        return sum(1 for p in self._plans.values() if p.activated)

    @property
    def total_lessons(self) -> int:
        """Toplam ders sayisi."""
        return len(self._lessons)
