"""ATLAS HTN Planner modulu.

Hierarchical Task Network planlama: compound gorevleri
primitive gorevlere ayirir, metot secimi yapar ve
on kosullari kontrol eder.
"""

import logging
from typing import Any

from app.models.planning import (
    HTNMethod,
    HTNMethodStatus,
    HTNPlan,
    HTNTask,
    HTNTaskType,
)

logger = logging.getLogger(__name__)


class HTNPlanner:
    """Hierarchical Task Network planlayici.

    Compound gorevleri metotlar araciligiyla primitive gorevlere
    ayirir. Metot secimi, on kosul kontrolu ve plan olusturma.

    Attributes:
        tasks: Kayitli gorevler (ad -> HTNTask).
        methods: Kayitli metotlar (gorev_adi -> [HTNMethod]).
        world_state: Dunya durumu (anahtar -> deger).
        max_decomposition_depth: Maksimum ayristirma derinligi.
    """

    def __init__(
        self,
        max_decomposition_depth: int = 20,
    ) -> None:
        self.tasks: dict[str, HTNTask] = {}
        self.methods: dict[str, list[HTNMethod]] = {}
        self.world_state: dict[str, Any] = {}
        self.max_decomposition_depth = max_decomposition_depth

    def register_task(self, task: HTNTask) -> None:
        """Gorev kayit eder.

        Args:
            task: Kaydedilecek HTNTask.
        """
        self.tasks[task.name] = task
        logger.debug("HTN gorev kaydedildi: %s (tip=%s)", task.name, task.task_type.value)

    def register_method(self, method: HTNMethod) -> None:
        """Decomposition metodu kayit eder.

        Args:
            method: Kaydedilecek HTNMethod.
        """
        if method.task_name not in self.methods:
            self.methods[method.task_name] = []
        self.methods[method.task_name].append(method)
        # Tercih sirasina gore sirala
        self.methods[method.task_name].sort(
            key=lambda m: m.preference, reverse=True
        )
        logger.debug("HTN metot kaydedildi: %s -> %s", method.name, method.task_name)

    def set_world_state(self, state: dict[str, Any]) -> None:
        """Dunya durumunu ayarlar.

        Args:
            state: Yeni dunya durumu.
        """
        self.world_state = dict(state)

    def update_world_state(self, updates: dict[str, Any]) -> None:
        """Dunya durumunu gunceller.

        Args:
            updates: Guncellenecek anahtar-deger ciftleri.
        """
        self.world_state.update(updates)

    def check_preconditions(
        self, preconditions: dict[str, Any]
    ) -> bool:
        """On kosullarin karsilanip karsilanmadigini kontrol eder.

        Args:
            preconditions: Kontrol edilecek kosullar (anahtar -> beklenen deger).

        Returns:
            Tum kosullar karsilandi mi.
        """
        for key, expected in preconditions.items():
            actual = self.world_state.get(key)
            if actual != expected:
                return False
        return True

    def _apply_effects(self, effects: dict[str, Any]) -> None:
        """Gorev etkilerini dunya durumuna uygular.

        Args:
            effects: Uygulanacak etkiler.
        """
        self.world_state.update(effects)

    async def plan(self, task_name: str) -> HTNPlan:
        """Belirtilen gorev icin plan olusturur.

        Args:
            task_name: Planlanacak gorev adi.

        Returns:
            HTNPlan (primitive gorev listesi veya bos/infeasible).
        """
        logger.info("HTN planlama baslatiliyor: %s", task_name)

        ordered_tasks: list[HTNTask] = []
        method_chain: list[str] = []
        feasible = await self._decompose(
            task_name, ordered_tasks, method_chain, depth=0
        )

        total_duration = sum(t.duration_estimate for t in ordered_tasks)

        plan = HTNPlan(
            task_name=task_name,
            ordered_tasks=ordered_tasks,
            total_duration=total_duration,
            method_chain=method_chain,
            feasible=feasible,
        )

        logger.info(
            "HTN plan tamamlandi: %s (%d gorev, feasible=%s)",
            task_name,
            len(ordered_tasks),
            feasible,
        )
        return plan

    async def _decompose(
        self,
        task_name: str,
        ordered_tasks: list[HTNTask],
        method_chain: list[str],
        depth: int,
    ) -> bool:
        """Gorevi recursive olarak ayristirir.

        Args:
            task_name: Ayristirilacak gorev adi.
            ordered_tasks: Sonuc listesi (mutate edilir).
            method_chain: Kullanilan metot zinciri (mutate edilir).
            depth: Mevcut derinlik.

        Returns:
            Ayristirma basarili mi.
        """
        if depth > self.max_decomposition_depth:
            logger.warning("Maksimum ayristirma derinligi asildi: %s", task_name)
            return False

        task = self.tasks.get(task_name)
        if task is None:
            logger.warning("Gorev bulunamadi: %s", task_name)
            return False

        # Primitive gorev: on kosul kontrolu ve ekleme
        if task.task_type == HTNTaskType.PRIMITIVE:
            if not self.check_preconditions(task.preconditions):
                logger.debug("On kosullar karsilanmadi: %s", task_name)
                return False
            ordered_tasks.append(task)
            self._apply_effects(task.effects)
            return True

        # Compound gorev: metot ile ayristir
        methods = self.methods.get(task_name, [])
        if not methods:
            logger.warning("Metot bulunamadi: %s", task_name)
            return False

        for method in methods:
            if not self.check_preconditions(method.preconditions):
                continue

            # Dunya durumunu kaydet (backtracking icin)
            saved_state = dict(self.world_state)
            saved_len = len(ordered_tasks)
            saved_chain_len = len(method_chain)

            method_chain.append(method.name)
            method.status = HTNMethodStatus.EXECUTING

            success = True
            for subtask_name in method.subtasks:
                if not await self._decompose(
                    subtask_name, ordered_tasks, method_chain, depth + 1
                ):
                    success = False
                    break

            if success:
                method.status = HTNMethodStatus.COMPLETED
                return True

            # Backtrack: durumu geri yukle
            method.status = HTNMethodStatus.FAILED
            self.world_state = saved_state
            del ordered_tasks[saved_len:]
            del method_chain[saved_chain_len:]

        return False

    async def validate_plan(self, plan: HTNPlan) -> list[str]:
        """Plani dogrular.

        Args:
            plan: Dogrulanacak plan.

        Returns:
            Hata mesajlari listesi (bos = gecerli).
        """
        errors: list[str] = []

        if not plan.ordered_tasks:
            errors.append("Plan bos: hicbir gorev yok")
            return errors

        # Her gorev icin on kosul kontrolu (simulasyon)
        sim_state = dict(self.world_state)
        for i, task in enumerate(plan.ordered_tasks):
            for key, expected in task.preconditions.items():
                if sim_state.get(key) != expected:
                    errors.append(
                        f"Adim {i} ({task.name}): on kosul karsilanmadi "
                        f"({key}={sim_state.get(key)}, beklenen={expected})"
                    )
            sim_state.update(task.effects)

        return errors

    def get_applicable_methods(self, task_name: str) -> list[HTNMethod]:
        """Belirtilen gorev icin uygulanabilir metotlari dondurur.

        Args:
            task_name: Gorev adi.

        Returns:
            Uygulanabilir metot listesi.
        """
        methods = self.methods.get(task_name, [])
        return [
            m for m in methods
            if self.check_preconditions(m.preconditions)
        ]
