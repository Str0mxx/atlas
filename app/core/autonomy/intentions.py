"""ATLAS Intention sistemi modulu.

Taahhut edilmis planlari yonetir. Plan kutuphanesi, plan secimi,
plan yurutme izleme ve yeniden planlama islemlerini saglar.
"""

import logging
from typing import Any

from app.agents.base_agent import TaskResult
from app.models.autonomy import (
    CommitmentStrategy,
    Desire,
    Intention,
    Plan,
    PlanStatus,
    PlanStep,
)

logger = logging.getLogger("atlas.autonomy.intentions")


class IntentionBase:
    """Taahhut edilmis planlari yoneten sinif.

    Plan kutuphanesini tutar, hedefe uygun plan secer,
    yurutme ilerlemesini izler ve gerektiginde yeniden planlama yapar.

    Attributes:
        intentions: Aktif intention'lar (id -> Intention).
        plan_library: Kayitli plan sablonlari (id -> Plan).
    """

    def __init__(self) -> None:
        """IntentionBase'i baslatir."""
        self.intentions: dict[str, Intention] = {}
        self.plan_library: dict[str, Plan] = {}
        logger.info("IntentionBase olusturuldu")

    def register_plan(self, plan: Plan) -> None:
        """Plan kutuphanesine yeni plan ekler.

        Args:
            plan: Kaydedilecek plan sablonu.
        """
        self.plan_library[plan.id] = plan
        logger.info("Plan kaydedildi: %s", plan.name)

    def register_plans(self, plans: list[Plan]) -> None:
        """Birden fazla plani toplu olarak kaydeder.

        Args:
            plans: Plan sablonlari listesi.
        """
        for plan in plans:
            self.register_plan(plan)

    async def select_plan(
        self,
        desire: Desire,
        beliefs: dict[str, Any],
    ) -> Plan | None:
        """Hedefe uygun en iyi plani secer.

        Plan kutuphanesinden hedef adina eslesen,
        on kosullari saglanan ve en yuksek basari oranli plani secer.

        Args:
            desire: Hedef.
            beliefs: Mevcut belief durumu.

        Returns:
            Secilen plan veya None (uygun plan yoksa).
        """
        candidates: list[Plan] = []

        for plan in self.plan_library.values():
            # Hedef adina eslesme kontrolu
            if plan.goal_name and plan.goal_name != desire.name:
                continue

            # On kosul kontrolu
            if plan.preconditions:
                all_met = all(
                    beliefs.get(k) == v
                    for k, v in plan.preconditions.items()
                )
                if not all_met:
                    continue

            candidates.append(plan)

        if not candidates:
            logger.info(
                "Hedef icin uygun plan bulunamadi: %s", desire.name,
            )
            return None

        # En yuksek basari oranli plani sec
        best = max(candidates, key=lambda p: p.success_rate)
        logger.info(
            "Plan secildi: %s (basari=%.2f) -> hedef: %s",
            best.name, best.success_rate, desire.name,
        )
        return best

    async def commit(
        self,
        desire: Desire,
        plan: Plan,
        commitment: CommitmentStrategy = CommitmentStrategy.SINGLE_MINDED,
    ) -> Intention:
        """Hedefe yonelik plan taahhut eder (intention olusturur).

        Args:
            desire: Hedef.
            plan: Secilen plan.
            commitment: Taahhut stratejisi.

        Returns:
            Olusturulan intention.
        """
        plan.status = PlanStatus.EXECUTING
        intention = Intention(
            desire_id=desire.id,
            plan_id=plan.id,
            status=PlanStatus.EXECUTING,
            commitment=commitment,
        )
        self.intentions[intention.id] = intention
        logger.info(
            "Intention olusturuldu: hedef=%s, plan=%s",
            desire.name, plan.name,
        )
        return intention

    async def get_next_step(
        self,
        intention_id: str,
    ) -> PlanStep | None:
        """Intention'in siradaki adimini dondurur.

        Args:
            intention_id: Intention ID.

        Returns:
            Siradaki plan adimi veya None (tum adimlar tamamsa).
        """
        intention = self.intentions.get(intention_id)
        if intention is None:
            return None

        plan = self.plan_library.get(intention.plan_id)
        if plan is None:
            return None

        # Sirali adimlari al
        sorted_steps = sorted(plan.steps, key=lambda s: s.order)

        if intention.current_step >= len(sorted_steps):
            return None

        step = sorted_steps[intention.current_step]
        if step.completed:
            return None

        return step

    async def advance(
        self,
        intention_id: str,
        result: TaskResult,
    ) -> PlanStatus:
        """Plan adimini tamamlar ve bir sonrakine gecer.

        Args:
            intention_id: Intention ID.
            result: Tamamlanan adimin sonucu.

        Returns:
            Guncellenmis plan durumu.
        """
        intention = self.intentions.get(intention_id)
        if intention is None:
            return PlanStatus.FAILED

        plan = self.plan_library.get(intention.plan_id)
        if plan is None:
            return PlanStatus.FAILED

        sorted_steps = sorted(plan.steps, key=lambda s: s.order)

        if result.success:
            # Adimi tamamla ve ilerle
            if intention.current_step < len(sorted_steps):
                sorted_steps[intention.current_step].completed = True
            intention.current_step += 1

            # Tum adimlar tamamlandi mi?
            if intention.current_step >= len(sorted_steps):
                intention.status = PlanStatus.SUCCEEDED
                plan.status = PlanStatus.SUCCEEDED
                logger.info(
                    "Plan tamamlandi: %s", plan.name,
                )
            return intention.status

        # Basarisiz adim
        intention.retry_count += 1
        if intention.retry_count >= intention.max_retries:
            intention.status = PlanStatus.FAILED
            plan.status = PlanStatus.FAILED
            logger.warning(
                "Plan basarisiz: %s (max retry asildi)",
                plan.name,
            )

        return intention.status

    async def replan(
        self,
        intention_id: str,
        desire: Desire,
        beliefs: dict[str, Any],
    ) -> Plan | None:
        """Basarisiz plan sonrasi yeniden plan secer.

        Mevcut intention'i FAILED yapar ve
        yeni bir plan secmeyi dener.

        Args:
            intention_id: Basarisiz intention ID.
            desire: Yeniden planlanacak hedef.
            beliefs: Mevcut belief durumu.

        Returns:
            Yeni plan veya None (alternatif yoksa).
        """
        old_intention = self.intentions.get(intention_id)
        failed_plan_id: str | None = None
        if old_intention is not None:
            old_intention.status = PlanStatus.FAILED
            failed_plan_id = old_intention.plan_id

        # Basarisiz plani disla
        original_plan: Plan | None = None
        if failed_plan_id and failed_plan_id in self.plan_library:
            original_plan = self.plan_library.pop(failed_plan_id)

        new_plan = await self.select_plan(desire, beliefs)

        # Basarisiz plani geri ekle (kutuphaneyi bozma)
        if original_plan is not None:
            self.plan_library[original_plan.id] = original_plan

        if new_plan is None:
            logger.info(
                "Yeniden planlama basarisiz: %s icin alternatif yok",
                desire.name,
            )
            return None

        # Yeni intention olustur
        commitment = CommitmentStrategy.SINGLE_MINDED
        if old_intention is not None:
            commitment = old_intention.commitment

        await self.commit(desire, new_plan, commitment)
        logger.info(
            "Yeniden planlama basarili: %s -> %s",
            desire.name, new_plan.name,
        )
        return new_plan

    async def abort(
        self,
        intention_id: str,
        reason: str = "",
    ) -> Intention | None:
        """Intention'i iptal eder.

        Args:
            intention_id: Iptal edilecek intention ID.
            reason: Iptal nedeni.

        Returns:
            Guncellenmis intention veya None.
        """
        intention = self.intentions.get(intention_id)
        if intention is None:
            return None

        intention.status = PlanStatus.ABORTED
        intention.metadata["abort_reason"] = reason

        plan = self.plan_library.get(intention.plan_id)
        if plan is not None:
            plan.status = PlanStatus.ABORTED

        logger.info("Intention iptal edildi: %s", intention_id)
        return intention

    def get_active_intentions(self) -> list[Intention]:
        """Aktif (READY veya EXECUTING) intention'lari dondurur.

        Returns:
            Aktif intention listesi.
        """
        return [
            i for i in self.intentions.values()
            if i.status in (PlanStatus.READY, PlanStatus.EXECUTING)
        ]

    def get_intention_for_desire(
        self,
        desire_id: str,
    ) -> Intention | None:
        """Belirli bir hedef icin aktif intention'i dondurur.

        Args:
            desire_id: Hedef ID.

        Returns:
            Intention veya None.
        """
        for intention in self.intentions.values():
            if (
                intention.desire_id == desire_id
                and intention.status
                in (PlanStatus.READY, PlanStatus.EXECUTING)
            ):
                return intention
        return None

    def get_plan(self, plan_id: str) -> Plan | None:
        """Plan kutuphanesinden plan getirir."""
        return self.plan_library.get(plan_id)

    def get(self, intention_id: str) -> Intention | None:
        """Tek bir intention'i getirir."""
        return self.intentions.get(intention_id)

    def snapshot(self) -> dict[str, Any]:
        """Mevcut intention durumunun goruntusunu dondurur."""
        return {
            "total_intentions": len(self.intentions),
            "active": len(self.get_active_intentions()),
            "plan_library_size": len(self.plan_library),
            "intentions": {
                iid: {
                    "desire_id": i.desire_id,
                    "plan_id": i.plan_id,
                    "status": i.status.value,
                    "current_step": i.current_step,
                }
                for iid, i in self.intentions.items()
            },
        }
