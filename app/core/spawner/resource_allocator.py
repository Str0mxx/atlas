"""ATLAS Kaynak Tahsis Yoneticisi modulu.

Bellek, CPU, API kotasi ve depolama tahsisi,
limit yonetimi ve dinamik yeniden dagitim.
"""

import logging
from typing import Any

from app.models.spawner import (
    ResourceAllocation,
    ResourceType,
)

logger = logging.getLogger(__name__)

# Varsayilan kaynak limitleri
_DEFAULT_LIMITS: dict[ResourceType, float] = {
    ResourceType.MEMORY: 512.0,      # MB
    ResourceType.CPU: 1.0,           # cores
    ResourceType.API_QUOTA: 1000.0,  # requests/hour
    ResourceType.STORAGE: 1024.0,    # MB
}

# Toplam sistem kapasitesi
_SYSTEM_CAPACITY: dict[ResourceType, float] = {
    ResourceType.MEMORY: 16384.0,    # 16 GB
    ResourceType.CPU: 8.0,           # 8 cores
    ResourceType.API_QUOTA: 10000.0, # requests/hour
    ResourceType.STORAGE: 102400.0,  # 100 GB
}


class ResourceAllocator:
    """Kaynak tahsis yoneticisi.

    Agent'lara kaynak tahsis eder, kullanimi izler
    ve dinamik yeniden dagitim saglar.

    Attributes:
        _allocations: Kaynak tahsisleri.
        _system_capacity: Sistem kapasitesi.
        _default_limits: Varsayilan limitler.
    """

    def __init__(
        self,
        system_capacity: dict[ResourceType, float] | None = None,
        default_limits: dict[ResourceType, float] | None = None,
    ) -> None:
        """Kaynak yoneticisini baslatir.

        Args:
            system_capacity: Sistem kapasitesi.
            default_limits: Varsayilan limitler.
        """
        self._allocations: dict[str, dict[ResourceType, ResourceAllocation]] = {}
        self._system_capacity = system_capacity or dict(_SYSTEM_CAPACITY)
        self._default_limits = default_limits or dict(_DEFAULT_LIMITS)

        logger.info("ResourceAllocator baslatildi")

    def allocate(
        self,
        agent_id: str,
        resource_type: ResourceType,
        amount: float,
    ) -> ResourceAllocation | None:
        """Kaynak tahsis eder.

        Args:
            agent_id: Agent ID.
            resource_type: Kaynak tipi.
            amount: Miktar.

        Returns:
            ResourceAllocation veya None.
        """
        # Kapasite kontrolu
        total_allocated = self._total_allocated(resource_type)
        capacity = self._system_capacity.get(resource_type, 0)

        if total_allocated + amount > capacity:
            logger.warning(
                "Kapasite yetersiz: %s (talep=%.1f, bos=%.1f)",
                resource_type.value, amount, capacity - total_allocated,
            )
            return None

        # Limit kontrolu
        limit = self._default_limits.get(resource_type, amount)

        alloc = ResourceAllocation(
            agent_id=agent_id,
            resource_type=resource_type,
            allocated=amount,
            used=0.0,
            limit=limit,
        )

        if agent_id not in self._allocations:
            self._allocations[agent_id] = {}
        self._allocations[agent_id][resource_type] = alloc

        logger.info(
            "Kaynak tahsis: %s -> %s: %.1f",
            agent_id, resource_type.value, amount,
        )
        return alloc

    def deallocate(
        self,
        agent_id: str,
        resource_type: ResourceType | None = None,
    ) -> bool:
        """Kaynak serbest birakir.

        Args:
            agent_id: Agent ID.
            resource_type: Kaynak tipi (None ise tumu).

        Returns:
            Basarili ise True.
        """
        if agent_id not in self._allocations:
            return False

        if resource_type:
            if resource_type in self._allocations[agent_id]:
                del self._allocations[agent_id][resource_type]
                if not self._allocations[agent_id]:
                    del self._allocations[agent_id]
                return True
            return False

        del self._allocations[agent_id]
        return True

    def update_usage(
        self,
        agent_id: str,
        resource_type: ResourceType,
        used: float,
    ) -> bool:
        """Kullanim gunceller.

        Args:
            agent_id: Agent ID.
            resource_type: Kaynak tipi.
            used: Kullanilan miktar.

        Returns:
            Basarili ise True.
        """
        alloc = self._get_allocation(agent_id, resource_type)
        if not alloc:
            return False

        alloc.used = min(used, alloc.allocated)
        return True

    def reallocate(
        self,
        agent_id: str,
        resource_type: ResourceType,
        new_amount: float,
    ) -> bool:
        """Dinamik yeniden tahsis.

        Args:
            agent_id: Agent ID.
            resource_type: Kaynak tipi.
            new_amount: Yeni miktar.

        Returns:
            Basarili ise True.
        """
        alloc = self._get_allocation(agent_id, resource_type)
        if not alloc:
            return False

        # Kapasite kontrolu (mevcut tahsisi cikar)
        total = self._total_allocated(resource_type) - alloc.allocated
        capacity = self._system_capacity.get(resource_type, 0)

        if total + new_amount > capacity:
            return False

        alloc.allocated = new_amount
        logger.info(
            "Yeniden tahsis: %s -> %s: %.1f",
            agent_id, resource_type.value, new_amount,
        )
        return True

    def get_allocation(
        self, agent_id: str,
    ) -> dict[str, Any]:
        """Agent kaynak tahsisini getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Tahsis bilgisi.
        """
        if agent_id not in self._allocations:
            return {}

        result: dict[str, Any] = {}
        for rtype, alloc in self._allocations[agent_id].items():
            result[rtype.value] = {
                "allocated": alloc.allocated,
                "used": alloc.used,
                "limit": alloc.limit,
                "utilization": round(
                    alloc.used / alloc.allocated, 3,
                ) if alloc.allocated > 0 else 0.0,
            }
        return result

    def get_system_usage(self) -> dict[str, Any]:
        """Sistem kaynak kullanimini getirir.

        Returns:
            Sistem kullanim bilgisi.
        """
        usage: dict[str, Any] = {}
        for rtype in ResourceType:
            total = self._total_allocated(rtype)
            capacity = self._system_capacity.get(rtype, 0)
            usage[rtype.value] = {
                "allocated": total,
                "capacity": capacity,
                "available": capacity - total,
                "utilization": round(
                    total / capacity, 3,
                ) if capacity > 0 else 0.0,
            }
        return usage

    def get_overutilized_agents(
        self, threshold: float = 0.9,
    ) -> list[dict[str, Any]]:
        """Asiri kullanan agent'lari getirir.

        Args:
            threshold: Kullanim esigi (0-1).

        Returns:
            Agent bilgi listesi.
        """
        results: list[dict[str, Any]] = []
        for agent_id, allocs in self._allocations.items():
            for rtype, alloc in allocs.items():
                if alloc.allocated > 0:
                    util = alloc.used / alloc.allocated
                    if util >= threshold:
                        results.append({
                            "agent_id": agent_id,
                            "resource": rtype.value,
                            "utilization": round(util, 3),
                            "allocated": alloc.allocated,
                            "used": alloc.used,
                        })
        return results

    def _get_allocation(
        self,
        agent_id: str,
        resource_type: ResourceType,
    ) -> ResourceAllocation | None:
        """Tahsisi getirir."""
        if agent_id not in self._allocations:
            return None
        return self._allocations[agent_id].get(resource_type)

    def _total_allocated(self, resource_type: ResourceType) -> float:
        """Toplam tahsis edilmis miktari hesaplar."""
        total = 0.0
        for allocs in self._allocations.values():
            if resource_type in allocs:
                total += allocs[resource_type].allocated
        return total

    @property
    def total_agents(self) -> int:
        """Kaynak tahsisli agent sayisi."""
        return len(self._allocations)
