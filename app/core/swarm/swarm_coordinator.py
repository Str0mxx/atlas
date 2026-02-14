"""ATLAS Suru Koordinatoru modulu.

Suru olusturma, hedef dagitimi, kolektif karar alma,
ortaya cikan davranis yonetimi ve suru dagitma.
"""

import logging
from typing import Any

from app.models.swarm import SwarmInfo, SwarmState

logger = logging.getLogger(__name__)


class SwarmCoordinator:
    """Suru koordinatoru.

    Suruleri olusturur, yonetir, hedef dagitir
    ve yasam dongusunu kontrol eder.

    Attributes:
        _swarms: Aktif surular.
        _agent_swarm: Agent -> suru eslesmesi.
        _min_size: Varsayilan min boyut.
        _max_size: Varsayilan maks boyut.
    """

    def __init__(
        self,
        min_size: int = 2,
        max_size: int = 20,
    ) -> None:
        """Koordinatoru baslatir.

        Args:
            min_size: Varsayilan min suru boyutu.
            max_size: Varsayilan maks suru boyutu.
        """
        self._swarms: dict[str, SwarmInfo] = {}
        self._agent_swarm: dict[str, str] = {}
        self._min_size = min_size
        self._max_size = max_size

        logger.info(
            "SwarmCoordinator baslatildi (min=%d, max=%d)",
            min_size, max_size,
        )

    def create_swarm(
        self,
        name: str,
        goal: str = "",
        min_size: int = 0,
        max_size: int = 0,
    ) -> SwarmInfo:
        """Yeni suru olusturur.

        Args:
            name: Suru adi.
            goal: Hedef.
            min_size: Min boyut (0 ise varsayilan).
            max_size: Maks boyut (0 ise varsayilan).

        Returns:
            SwarmInfo nesnesi.
        """
        swarm = SwarmInfo(
            name=name,
            goal=goal,
            state=SwarmState.FORMING,
            min_size=min_size or self._min_size,
            max_size=max_size or self._max_size,
        )
        self._swarms[swarm.swarm_id] = swarm
        logger.info("Suru olusturuldu: %s (%s)", name, swarm.swarm_id)
        return swarm

    def join_swarm(self, swarm_id: str, agent_id: str) -> bool:
        """Suruye katilim.

        Args:
            swarm_id: Suru ID.
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return False

        if swarm.state == SwarmState.DISSOLVED:
            return False

        if len(swarm.members) >= swarm.max_size:
            return False

        if agent_id in swarm.members:
            return False

        # Baska surude ise cikar
        if agent_id in self._agent_swarm:
            self.leave_swarm(self._agent_swarm[agent_id], agent_id)

        swarm.members.append(agent_id)
        self._agent_swarm[agent_id] = swarm_id

        # Ilk uye lider olur
        if not swarm.leader_id:
            swarm.leader_id = agent_id

        # Min boyuta ulasilinca aktif ol
        if len(swarm.members) >= swarm.min_size and swarm.state == SwarmState.FORMING:
            swarm.state = SwarmState.ACTIVE

        return True

    def leave_swarm(self, swarm_id: str, agent_id: str) -> bool:
        """Surudan ayrilma.

        Args:
            swarm_id: Suru ID.
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        swarm = self._swarms.get(swarm_id)
        if not swarm or agent_id not in swarm.members:
            return False

        swarm.members.remove(agent_id)
        self._agent_swarm.pop(agent_id, None)

        # Lider ayrilirsa yeni lider sec
        if swarm.leader_id == agent_id:
            swarm.leader_id = swarm.members[0] if swarm.members else ""

        # Min boyutun altina duserse forming'e dondur
        if len(swarm.members) < swarm.min_size and swarm.state == SwarmState.ACTIVE:
            swarm.state = SwarmState.FORMING

        return True

    def set_goal(self, swarm_id: str, goal: str) -> bool:
        """Hedef belirler.

        Args:
            swarm_id: Suru ID.
            goal: Hedef.

        Returns:
            Basarili ise True.
        """
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return False

        swarm.goal = goal
        if swarm.state == SwarmState.ACTIVE:
            swarm.state = SwarmState.WORKING

        return True

    def dissolve_swarm(self, swarm_id: str) -> bool:
        """Suruyu dagitir.

        Args:
            swarm_id: Suru ID.

        Returns:
            Basarili ise True.
        """
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return False

        for agent_id in list(swarm.members):
            self._agent_swarm.pop(agent_id, None)

        swarm.members.clear()
        swarm.leader_id = ""
        swarm.state = SwarmState.DISSOLVED

        logger.info("Suru dagitildi: %s", swarm.name)
        return True

    def get_swarm(self, swarm_id: str) -> SwarmInfo | None:
        """Suru bilgisini getirir.

        Args:
            swarm_id: Suru ID.

        Returns:
            SwarmInfo veya None.
        """
        return self._swarms.get(swarm_id)

    def get_agent_swarm(self, agent_id: str) -> SwarmInfo | None:
        """Agent'in surusunu getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            SwarmInfo veya None.
        """
        swarm_id = self._agent_swarm.get(agent_id)
        if swarm_id:
            return self._swarms.get(swarm_id)
        return None

    def elect_leader(self, swarm_id: str, agent_id: str) -> bool:
        """Lider secer.

        Args:
            swarm_id: Suru ID.
            agent_id: Yeni lider.

        Returns:
            Basarili ise True.
        """
        swarm = self._swarms.get(swarm_id)
        if not swarm or agent_id not in swarm.members:
            return False

        swarm.leader_id = agent_id
        return True

    def list_swarms(
        self, state: SwarmState | None = None,
    ) -> list[SwarmInfo]:
        """Suruleri listeler.

        Args:
            state: Durum filtresi.

        Returns:
            SwarmInfo listesi.
        """
        swarms = list(self._swarms.values())
        if state is not None:
            swarms = [s for s in swarms if s.state == state]
        return swarms

    def distribute_goal(
        self,
        swarm_id: str,
        sub_goals: list[str],
    ) -> dict[str, str]:
        """Hedefi alt hedeflere dagitir.

        Args:
            swarm_id: Suru ID.
            sub_goals: Alt hedefler.

        Returns:
            Agent -> alt hedef eslesmesi.
        """
        swarm = self._swarms.get(swarm_id)
        if not swarm or not swarm.members:
            return {}

        assignments: dict[str, str] = {}
        for i, goal in enumerate(sub_goals):
            agent_idx = i % len(swarm.members)
            agent_id = swarm.members[agent_idx]
            assignments[agent_id] = goal

        return assignments

    @property
    def swarm_count(self) -> int:
        """Toplam suru sayisi."""
        return len(self._swarms)

    @property
    def active_swarm_count(self) -> int:
        """Aktif suru sayisi."""
        return sum(
            1 for s in self._swarms.values()
            if s.state in (SwarmState.ACTIVE, SwarmState.WORKING)
        )

    @property
    def total_members(self) -> int:
        """Toplam uye sayisi."""
        return len(self._agent_swarm)
