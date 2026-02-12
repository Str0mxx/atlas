"""ATLAS Resource Planner modulu.

Kaynak planlamasi: kaynak tahsisi, catisma cozumu
ve optimizasyon (lineer programlama benzeri greedy).
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.planning import (
    AllocationStatus,
    OptimizationResult,
    Resource,
    ResourceAllocation,
    ResourceConflict,
    ResourceType,
)

logger = logging.getLogger(__name__)


class ResourcePlanner:
    """Kaynak planlayici.

    Kaynak tahsisi, catisma tespiti, catisma cozumu
    ve kaynak kullanim optimizasyonu.

    Attributes:
        resources: Kayitli kaynaklar (id -> Resource).
        allocations: Aktif tahsisler (id -> ResourceAllocation).
        task_requirements: Gorev kaynak gereksinimleri (gorev_id -> {kaynak_id: miktar}).
    """

    def __init__(self) -> None:
        self.resources: dict[str, Resource] = {}
        self.allocations: dict[str, ResourceAllocation] = {}
        self.task_requirements: dict[str, dict[str, float]] = {}

    def register_resource(self, resource: Resource) -> None:
        """Kaynak kayit eder.

        Args:
            resource: Kaydedilecek kaynak.
        """
        self.resources[resource.id] = resource
        logger.debug(
            "Kaynak kaydedildi: %s (tip=%s, kapasite=%.1f)",
            resource.name,
            resource.resource_type.value,
            resource.capacity,
        )

    def set_task_requirements(
        self, task_id: str, requirements: dict[str, float]
    ) -> None:
        """Gorev kaynak gereksinimlerini ayarlar.

        Args:
            task_id: Gorev ID.
            requirements: Kaynak gereksinimleri (kaynak_id -> miktar).
        """
        self.task_requirements[task_id] = dict(requirements)

    async def allocate(
        self, task_id: str, resource_id: str, amount: float
    ) -> ResourceAllocation | ResourceConflict:
        """Kaynak tahsis eder.

        Args:
            task_id: Gorev ID.
            resource_id: Kaynak ID.
            amount: Tahsis miktari.

        Returns:
            ResourceAllocation (basarili) veya ResourceConflict (yetersiz).

        Raises:
            ValueError: Kaynak bulunamazsa.
        """
        resource = self.resources.get(resource_id)
        if resource is None:
            raise ValueError(f"Kaynak bulunamadi: {resource_id}")

        if amount > resource.available:
            conflict = ResourceConflict(
                resource_id=resource_id,
                resource_name=resource.name,
                requested=amount,
                available=resource.available,
                competing_tasks=self._get_competing_tasks(resource_id),
                resolution=self._suggest_resolution(resource, amount),
            )
            logger.warning(
                "Kaynak catismasi: %s (istenen=%.1f, mevcut=%.1f)",
                resource.name,
                amount,
                resource.available,
            )
            return conflict

        # Tahsis yap
        allocation = ResourceAllocation(
            resource_id=resource_id,
            task_id=task_id,
            amount=amount,
            status=AllocationStatus.ALLOCATED,
        )
        self.allocations[allocation.id] = allocation
        resource.available -= amount

        logger.info(
            "Kaynak tahsis edildi: %s -> gorev %s (miktar=%.1f)",
            resource.name,
            task_id,
            amount,
        )
        return allocation

    async def release(self, allocation_id: str) -> bool:
        """Tahsisi serbest birakir.

        Args:
            allocation_id: Serbest birakilacak tahsis ID.

        Returns:
            Basarili mi.
        """
        allocation = self.allocations.get(allocation_id)
        if allocation is None:
            return False

        if allocation.status == AllocationStatus.RELEASED:
            return False

        resource = self.resources.get(allocation.resource_id)
        if resource is not None:
            resource.available = min(
                resource.capacity,
                resource.available + allocation.amount,
            )

        allocation.status = AllocationStatus.RELEASED
        allocation.released_at = datetime.now(timezone.utc)

        logger.info("Kaynak serbest birakildi: tahsis %s", allocation_id)
        return True

    async def release_task_allocations(self, task_id: str) -> int:
        """Goreve ait tum tahsisleri serbest birakir.

        Args:
            task_id: Gorev ID.

        Returns:
            Serbest birakilan tahsis sayisi.
        """
        released = 0
        for alloc in list(self.allocations.values()):
            if alloc.task_id == task_id and alloc.status == AllocationStatus.ALLOCATED:
                await self.release(alloc.id)
                released += 1
        return released

    def detect_conflicts(self) -> list[ResourceConflict]:
        """Tum kaynak catismalarini tespit eder.

        Returns:
            Catisma listesi.
        """
        conflicts: list[ResourceConflict] = []

        for task_id, requirements in self.task_requirements.items():
            for resource_id, needed in requirements.items():
                resource = self.resources.get(resource_id)
                if resource is None:
                    continue
                if needed > resource.available:
                    conflicts.append(ResourceConflict(
                        resource_id=resource_id,
                        resource_name=resource.name,
                        requested=needed,
                        available=resource.available,
                        competing_tasks=self._get_competing_tasks(resource_id),
                        resolution=self._suggest_resolution(resource, needed),
                    ))

        return conflicts

    async def optimize(
        self,
        task_priorities: dict[str, float] | None = None,
    ) -> OptimizationResult:
        """Kaynak tahsisini optimize eder.

        Greedy algoritma: yuksek oncelikli gorevlere once tahsis eder.
        Her gorev icin en dusuk maliyetli kaynaklari secer.

        Args:
            task_priorities: Gorev oncelikleri (gorev_id -> oncelik, yuksek=once).

        Returns:
            OptimizationResult.
        """
        priorities = task_priorities or {}
        allocations: list[ResourceAllocation] = []
        conflicts: list[ResourceConflict] = []
        total_cost = 0.0

        # Kaynak durumunu simule et
        available: dict[str, float] = {
            rid: r.available for rid, r in self.resources.items()
        }

        # Gorevleri oncelik sirasina gore isle
        sorted_tasks = sorted(
            self.task_requirements.items(),
            key=lambda item: priorities.get(item[0], 0.0),
            reverse=True,
        )

        for task_id, requirements in sorted_tasks:
            task_ok = True
            task_allocs: list[ResourceAllocation] = []

            for resource_id, needed in requirements.items():
                resource = self.resources.get(resource_id)
                if resource is None:
                    task_ok = False
                    continue

                if needed <= available.get(resource_id, 0.0):
                    alloc = ResourceAllocation(
                        resource_id=resource_id,
                        task_id=task_id,
                        amount=needed,
                        status=AllocationStatus.ALLOCATED,
                    )
                    task_allocs.append(alloc)
                    available[resource_id] -= needed
                    total_cost += needed * resource.cost_per_unit
                else:
                    task_ok = False
                    conflicts.append(ResourceConflict(
                        resource_id=resource_id,
                        resource_name=resource.name,
                        requested=needed,
                        available=available.get(resource_id, 0.0),
                        competing_tasks=[task_id],
                    ))

            if task_ok:
                allocations.extend(task_allocs)
            else:
                # Geri al
                for alloc in task_allocs:
                    available[alloc.resource_id] = (
                        available.get(alloc.resource_id, 0.0) + alloc.amount
                    )
                    total_cost -= alloc.amount * (
                        self.resources[alloc.resource_id].cost_per_unit
                    )

        # Kullanim oranlari
        utilization: dict[str, float] = {}
        for rid, resource in self.resources.items():
            if resource.capacity > 0:
                used = resource.capacity - available.get(rid, resource.available)
                utilization[rid] = used / resource.capacity
            else:
                utilization[rid] = 0.0

        feasible = len(conflicts) == 0

        logger.info(
            "Kaynak optimizasyonu: %d tahsis, maliyet=%.2f, catisma=%d",
            len(allocations),
            total_cost,
            len(conflicts),
        )

        return OptimizationResult(
            allocations=allocations,
            total_cost=total_cost,
            utilization=utilization,
            conflicts=conflicts,
            feasible=feasible,
        )

    def get_utilization(self) -> dict[str, float]:
        """Kaynak kullanim oranlarini dondurur.

        Returns:
            Kullanim oranlari (kaynak_id -> oran).
        """
        utilization: dict[str, float] = {}
        for rid, resource in self.resources.items():
            if resource.capacity > 0:
                used = resource.capacity - resource.available
                utilization[rid] = used / resource.capacity
            else:
                utilization[rid] = 0.0
        return utilization

    def _get_competing_tasks(self, resource_id: str) -> list[str]:
        """Kaynagi kullanan gorevleri bulur.

        Args:
            resource_id: Kaynak ID.

        Returns:
            Gorev ID listesi.
        """
        tasks: list[str] = []
        for alloc in self.allocations.values():
            if (
                alloc.resource_id == resource_id
                and alloc.status == AllocationStatus.ALLOCATED
            ):
                tasks.append(alloc.task_id)
        return tasks

    def _suggest_resolution(self, resource: Resource, needed: float) -> str:
        """Catisma cozum onerisi uretir.

        Args:
            resource: Catisan kaynak.
            needed: Gereken miktar.

        Returns:
            Cozum onerisi metni.
        """
        deficit = needed - resource.available
        if deficit <= 0:
            return "Kaynak yeterli"

        suggestions: list[str] = []

        # Dusuk oncelikli tahsisleri serbest birak
        low_priority_allocs = [
            a for a in self.allocations.values()
            if a.resource_id == resource.id
            and a.status == AllocationStatus.ALLOCATED
        ]
        if low_priority_allocs:
            total_reclaimable = sum(a.amount for a in low_priority_allocs)
            if total_reclaimable >= deficit:
                suggestions.append(
                    f"Mevcut tahsislerden {deficit:.1f} birim serbest birakilabilir"
                )

        # Kapasite artirimi
        suggestions.append(
            f"Kaynak kapasitesi {resource.capacity:.1f} -> "
            f"{resource.capacity + deficit:.1f} arttirilabilir"
        )

        return "; ".join(suggestions) if suggestions else "Manuel mudahale gerekli"
