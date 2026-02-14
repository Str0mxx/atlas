"""ATLAS Agent Havuzu modulu.

Onceden olusturulmus agent havuzu, hizli atama,
havuz boyutlandirma, bosta yonetimi ve istatistikler.
"""

import logging
from typing import Any

from app.models.spawner import (
    AgentState,
    PoolStatus,
    PoolStrategy,
    SpawnedAgent,
)

logger = logging.getLogger(__name__)


class AgentPool:
    """Agent havuz yoneticisi.

    Onceden olusturulmus agent'lari havuzda tutar,
    hizli atama ve geri alma saglar.

    Attributes:
        _pool_id: Havuz ID.
        _strategy: Havuz stratejisi.
        _target_size: Hedef havuz boyutu.
        _idle: Bosta bekleyen agent'lar.
        _assigned: Atanmis agent'lar.
        _all_agents: Tum agent'lar.
    """

    def __init__(
        self,
        pool_id: str = "default",
        strategy: PoolStrategy = PoolStrategy.FIXED,
        target_size: int = 5,
    ) -> None:
        """Agent havuzunu baslatir.

        Args:
            pool_id: Havuz ID.
            strategy: Havuz stratejisi.
            target_size: Hedef boyut.
        """
        self._pool_id = pool_id
        self._strategy = strategy
        self._target_size = target_size
        self._idle: list[SpawnedAgent] = []
        self._assigned: dict[str, SpawnedAgent] = {}
        self._all_agents: dict[str, SpawnedAgent] = {}
        self._total_assignments: int = 0

        logger.info(
            "AgentPool baslatildi (id=%s, strategy=%s, size=%d)",
            pool_id, strategy.value, target_size,
        )

    def add_to_pool(self, agent: SpawnedAgent) -> bool:
        """Havuza agent ekler.

        Args:
            agent: Eklenecek agent.

        Returns:
            Basarili ise True.
        """
        if self._strategy == PoolStrategy.FIXED:
            if len(self._all_agents) >= self._target_size:
                return False

        self._all_agents[agent.agent_id] = agent
        self._idle.append(agent)
        return True

    def acquire(
        self,
        required_capabilities: list[str] | None = None,
    ) -> SpawnedAgent | None:
        """Havuzdan agent alir.

        Args:
            required_capabilities: Gereken yetenekler.

        Returns:
            SpawnedAgent veya None.
        """
        if not self._idle:
            return None

        target: SpawnedAgent | None = None

        if required_capabilities:
            for agent in self._idle:
                if all(
                    c in agent.capabilities
                    for c in required_capabilities
                ):
                    target = agent
                    break
        else:
            target = self._idle[0]

        if not target:
            return None

        self._idle.remove(target)
        self._assigned[target.agent_id] = target
        target.state = AgentState.ACTIVE
        self._total_assignments += 1

        logger.info("Havuzdan alindi: %s", target.name)
        return target

    def release(self, agent_id: str) -> bool:
        """Agent'i havuza geri birakir.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        agent = self._assigned.get(agent_id)
        if not agent:
            return False

        del self._assigned[agent_id]
        agent.state = AgentState.PAUSED
        agent.workload = 0.0
        self._idle.append(agent)

        logger.info("Havuza geri birakildi: %s", agent.name)
        return True

    def remove_from_pool(self, agent_id: str) -> bool:
        """Agent'i havuzdan cikarir.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        if agent_id not in self._all_agents:
            return False

        agent = self._all_agents[agent_id]

        # Idle'dan cikar
        if agent in self._idle:
            self._idle.remove(agent)

        # Assigned'dan cikar
        if agent_id in self._assigned:
            del self._assigned[agent_id]

        del self._all_agents[agent_id]
        return True

    def resize(self, new_size: int) -> None:
        """Havuz boyutunu degistirir.

        Args:
            new_size: Yeni hedef boyut.
        """
        self._target_size = new_size
        logger.info("Havuz boyutu: %d", new_size)

    def get_idle_agents(self) -> list[SpawnedAgent]:
        """Bosta bekleyen agent'lari getirir.

        Returns:
            SpawnedAgent listesi.
        """
        return list(self._idle)

    def get_assigned_agents(self) -> list[SpawnedAgent]:
        """Atanmis agent'lari getirir.

        Returns:
            SpawnedAgent listesi.
        """
        return list(self._assigned.values())

    def needs_scaling(self) -> dict[str, Any]:
        """Olcekleme gereksinimi kontrol eder.

        Returns:
            Olcekleme bilgisi.
        """
        current = len(self._all_agents)
        idle_count = len(self._idle)

        if self._strategy == PoolStrategy.FIXED:
            return {
                "needs_scale": current < self._target_size,
                "direction": "up" if current < self._target_size else "none",
                "deficit": max(0, self._target_size - current),
            }

        if self._strategy == PoolStrategy.ELASTIC:
            # Idle cok azsa buyut, cok fazlaysa kucult
            if idle_count == 0 and current > 0:
                return {
                    "needs_scale": True,
                    "direction": "up",
                    "deficit": max(1, self._target_size // 4),
                }
            if idle_count > self._target_size:
                return {
                    "needs_scale": True,
                    "direction": "down",
                    "surplus": idle_count - self._target_size,
                }

        return {"needs_scale": False, "direction": "none", "deficit": 0}

    def get_status(self) -> PoolStatus:
        """Havuz durumunu getirir.

        Returns:
            PoolStatus nesnesi.
        """
        return PoolStatus(
            pool_id=self._pool_id,
            strategy=self._strategy,
            total_agents=len(self._all_agents),
            active_agents=len(self._assigned),
            idle_agents=len(self._idle),
            assigned_agents=len(self._assigned),
            target_size=self._target_size,
        )

    @property
    def pool_id(self) -> str:
        """Havuz ID."""
        return self._pool_id

    @property
    def total_agents(self) -> int:
        """Toplam agent sayisi."""
        return len(self._all_agents)

    @property
    def idle_count(self) -> int:
        """Bosta bekleyen sayisi."""
        return len(self._idle)

    @property
    def assigned_count(self) -> int:
        """Atanmis sayisi."""
        return len(self._assigned)

    @property
    def total_assignments(self) -> int:
        """Toplam atama sayisi."""
        return self._total_assignments
