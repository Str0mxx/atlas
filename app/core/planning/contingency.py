"""ATLAS Contingency Planner modulu.

Olasilik planlamasi: Plan B, C, D yonetimi,
tetikleyici kosullar ve otomatik plan degistirme.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.planning import (
    ContingencyActivation,
    ContingencyPlanDef,
    TriggerCondition,
    TriggerType,
)

logger = logging.getLogger(__name__)

# Karsilastirma operatorleri
_OPERATORS: dict[str, Any] = {
    "gt": lambda a, b: a > b,
    "lt": lambda a, b: a < b,
    "gte": lambda a, b: a >= b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
}


class ContingencyPlanner:
    """Olasilik planlayici.

    Plan B, C, D... yonetimi. Tetikleyici kosullari izler,
    kosullar saglandiginda otomatik plan degistirme yapar.

    Attributes:
        plans: Kayitli acil durum planlari (id -> ContingencyPlanDef).
        activations: Gecmis aktivasyon kayitlari.
        active_plan_id: Su an aktif plan ID.
        metrics: Izlenen metrikler (anahtar -> deger).
        failure_counts: Hata sayaclari (anahtar -> sayi).
    """

    def __init__(self) -> None:
        self.plans: dict[str, ContingencyPlanDef] = {}
        self.activations: list[ContingencyActivation] = []
        self.active_plan_id: str | None = None
        self.metrics: dict[str, float] = {}
        self.failure_counts: dict[str, int] = {}

    def register_plan(self, plan: ContingencyPlanDef) -> None:
        """Acil durum plani kayit eder.

        Args:
            plan: Kaydedilecek plan.
        """
        self.plans[plan.id] = plan
        logger.info(
            "Acil durum plani kaydedildi: %s (oncelik=%d)",
            plan.name,
            plan.priority,
        )

    def remove_plan(self, plan_id: str) -> bool:
        """Plani kaldirir.

        Args:
            plan_id: Kaldirilacak plan ID.

        Returns:
            Kaldirma basarili mi.
        """
        if plan_id not in self.plans:
            return False
        del self.plans[plan_id]
        if self.active_plan_id == plan_id:
            self.active_plan_id = None
        return True

    def update_metrics(self, metrics: dict[str, float]) -> None:
        """Metrikleri gunceller.

        Args:
            metrics: Guncellenecek metrikler.
        """
        self.metrics.update(metrics)

    def record_failure(self, key: str) -> int:
        """Hata sayacini arttirir.

        Args:
            key: Hata anahtari.

        Returns:
            Yeni hata sayisi.
        """
        self.failure_counts[key] = self.failure_counts.get(key, 0) + 1
        return self.failure_counts[key]

    def reset_failure(self, key: str) -> None:
        """Hata sayacini sifirlar.

        Args:
            key: Sifirlanacak anahtar.
        """
        self.failure_counts.pop(key, None)

    def _evaluate_trigger(self, trigger: TriggerCondition) -> bool:
        """Tetikleyici kosulu degerlendirir.

        Args:
            trigger: Degerlendirilecek tetikleyici.

        Returns:
            Tetikleyici aktive oldu mu.
        """
        if trigger.trigger_type == TriggerType.THRESHOLD:
            value = self.metrics.get(trigger.metric_key)
            if value is None:
                return False
            op_fn = _OPERATORS.get(trigger.operator)
            if op_fn is None:
                return False
            return op_fn(value, trigger.threshold)

        elif trigger.trigger_type == TriggerType.FAILURE_COUNT:
            count = self.failure_counts.get(trigger.metric_key, 0)
            op_fn = _OPERATORS.get(trigger.operator, _OPERATORS["gte"])
            return op_fn(count, trigger.threshold)

        elif trigger.trigger_type == TriggerType.TIMEOUT:
            # Timeout: metrik degerinin (epoch saniye) threshold'u asmasi
            value = self.metrics.get(trigger.metric_key)
            if value is None:
                return False
            elapsed = datetime.now(timezone.utc).timestamp() - value
            return elapsed > trigger.threshold

        elif trigger.trigger_type == TriggerType.CONDITION:
            # Genel kosul: metric_key'in degeri threshold'a esit mi
            value = self.metrics.get(trigger.metric_key)
            if value is None:
                return False
            op_fn = _OPERATORS.get(trigger.operator, _OPERATORS["eq"])
            return op_fn(value, trigger.threshold)

        elif trigger.trigger_type == TriggerType.EXTERNAL_EVENT:
            # Harici olay: metrik 1.0 ise tetiklenir
            value = self.metrics.get(trigger.metric_key, 0.0)
            return value >= 1.0

        return False

    async def evaluate(self) -> ContingencyActivation | None:
        """Tum planlari degerlendirir ve tetiklenen varsa aktive eder.

        Planlari oncelik sirasina gore kontrol eder.
        Ilk tetiklenen plan aktive edilir.

        Returns:
            Aktivasyon kaydi veya None (tetiklenen yoksa).
        """
        # Oncelige gore sirala (yuksek once)
        sorted_plans = sorted(
            (p for p in self.plans.values() if p.active),
            key=lambda p: p.priority,
            reverse=True,
        )

        for plan in sorted_plans:
            if self._evaluate_trigger(plan.trigger):
                activation = await self._activate_plan(plan)
                return activation

        return None

    async def _activate_plan(
        self, plan: ContingencyPlanDef
    ) -> ContingencyActivation:
        """Plani aktive eder.

        Args:
            plan: Aktive edilecek plan.

        Returns:
            Aktivasyon kaydi.
        """
        self.active_plan_id = plan.id

        activation = ContingencyActivation(
            plan_id=plan.id,
            plan_name=plan.name,
            trigger_reason=f"Trigger: {plan.trigger.description or plan.trigger.trigger_type.value}",
        )
        self.activations.append(activation)

        logger.info(
            "Acil durum plani aktive edildi: %s (sebep: %s)",
            plan.name,
            activation.trigger_reason,
        )
        return activation

    async def force_activate(self, plan_id: str, reason: str = "") -> ContingencyActivation | None:
        """Plani zorla aktive eder.

        Args:
            plan_id: Aktive edilecek plan ID.
            reason: Aktivasyon sebebi.

        Returns:
            Aktivasyon kaydi veya None.
        """
        plan = self.plans.get(plan_id)
        if plan is None:
            return None

        self.active_plan_id = plan_id
        activation = ContingencyActivation(
            plan_id=plan_id,
            plan_name=plan.name,
            trigger_reason=reason or "Manuel aktivasyon",
        )
        self.activations.append(activation)

        logger.info("Plan zorla aktive edildi: %s", plan.name)
        return activation

    async def resolve(self, plan_id: str | None = None) -> bool:
        """Aktif plani cozulmus olarak isaretler.

        Args:
            plan_id: Cozulen plan ID (None ise aktif plan).

        Returns:
            Basarili mi.
        """
        target_id = plan_id or self.active_plan_id
        if target_id is None:
            return False

        # Son aktivasyonu bul ve cozulmus isaretle
        for activation in reversed(self.activations):
            if activation.plan_id == target_id and not activation.resolved:
                activation.resolved = True
                elapsed = (
                    datetime.now(timezone.utc) - activation.activated_at
                ).total_seconds()
                activation.resolution_time = elapsed
                break

        if self.active_plan_id == target_id:
            self.active_plan_id = None

        logger.info("Plan cozuldu: %s", target_id)
        return True

    def get_active_plan(self) -> ContingencyPlanDef | None:
        """Aktif plani dondurur.

        Returns:
            Aktif plan veya None.
        """
        if self.active_plan_id is None:
            return None
        return self.plans.get(self.active_plan_id)

    def get_activation_history(self) -> list[ContingencyActivation]:
        """Aktivasyon gecmisini dondurur.

        Returns:
            Aktivasyon kayitlari.
        """
        return list(self.activations)

    def get_plans_by_priority(self) -> list[ContingencyPlanDef]:
        """Planlari oncelik sirasina gore dondurur.

        Returns:
            Sirali plan listesi.
        """
        return sorted(
            self.plans.values(),
            key=lambda p: p.priority,
            reverse=True,
        )
