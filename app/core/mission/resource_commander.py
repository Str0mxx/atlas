"""ATLAS Kaynak Komutani modulu.

Agent atama, arac tahsisi, butce takibi,
kaynak catismasi ve dinamik yeniden dagitim.
"""

import logging
from typing import Any

from app.models.mission import ResourceAssignment

logger = logging.getLogger(__name__)


class ResourceCommander:
    """Kaynak komutani.

    Gorev kaynaklarini yonetir, agent ve arac
    tahsisini yapar, catismalari cozer.

    Attributes:
        _assignments: Kaynak atamalari.
        _available_agents: Musait agent'lar.
        _available_tools: Musait araclar.
        _agent_missions: Agent -> gorev eslesmesi.
    """

    def __init__(self) -> None:
        """Kaynak komutanini baslatir."""
        self._assignments: dict[str, ResourceAssignment] = {}
        self._available_agents: set[str] = set()
        self._available_tools: set[str] = set()
        self._agent_missions: dict[str, str] = {}
        self._tool_missions: dict[str, str] = {}
        self._budgets: dict[str, float] = {}  # mission -> budget
        self._spent: dict[str, float] = {}  # mission -> spent

        logger.info("ResourceCommander baslatildi")

    def register_agent(self, agent_id: str) -> None:
        """Agent kaydeder.

        Args:
            agent_id: Agent ID.
        """
        self._available_agents.add(agent_id)

    def register_tool(self, tool_id: str) -> None:
        """Arac kaydeder.

        Args:
            tool_id: Arac ID.
        """
        self._available_tools.add(tool_id)

    def assign_agent(
        self,
        mission_id: str,
        agent_id: str,
    ) -> ResourceAssignment | None:
        """Agent atar.

        Args:
            mission_id: Gorev ID.
            agent_id: Agent ID.

        Returns:
            ResourceAssignment veya None.
        """
        if agent_id not in self._available_agents:
            return None

        # Zaten baska gorevde mi
        if agent_id in self._agent_missions:
            return None

        assignment = ResourceAssignment(
            mission_id=mission_id,
            resource_id=agent_id,
            resource_type="agent",
        )
        self._assignments[assignment.assignment_id] = assignment
        self._agent_missions[agent_id] = mission_id

        logger.info("Agent atandi: %s -> %s", agent_id, mission_id)
        return assignment

    def assign_tool(
        self,
        mission_id: str,
        tool_id: str,
    ) -> ResourceAssignment | None:
        """Arac atar.

        Args:
            mission_id: Gorev ID.
            tool_id: Arac ID.

        Returns:
            ResourceAssignment veya None.
        """
        if tool_id not in self._available_tools:
            return None

        if tool_id in self._tool_missions:
            return None

        assignment = ResourceAssignment(
            mission_id=mission_id,
            resource_id=tool_id,
            resource_type="tool",
        )
        self._assignments[assignment.assignment_id] = assignment
        self._tool_missions[tool_id] = mission_id

        logger.info("Arac atandi: %s -> %s", tool_id, mission_id)
        return assignment

    def release_agent(self, agent_id: str) -> bool:
        """Agent'i serbest birakir.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        if agent_id not in self._agent_missions:
            return False

        del self._agent_missions[agent_id]
        return True

    def release_tool(self, tool_id: str) -> bool:
        """Araci serbest birakir.

        Args:
            tool_id: Arac ID.

        Returns:
            Basarili ise True.
        """
        if tool_id not in self._tool_missions:
            return False

        del self._tool_missions[tool_id]
        return True

    def reallocate_agent(
        self,
        agent_id: str,
        new_mission_id: str,
    ) -> bool:
        """Agent'i baska goreve atar.

        Args:
            agent_id: Agent ID.
            new_mission_id: Yeni gorev ID.

        Returns:
            Basarili ise True.
        """
        if agent_id not in self._available_agents:
            return False

        # Once serbest birak
        self._agent_missions.pop(agent_id, None)
        self._agent_missions[agent_id] = new_mission_id
        return True

    def set_budget(self, mission_id: str, budget: float) -> None:
        """Gorev butcesini ayarlar.

        Args:
            mission_id: Gorev ID.
            budget: Butce.
        """
        self._budgets[mission_id] = budget
        self._spent.setdefault(mission_id, 0.0)

    def spend(self, mission_id: str, amount: float) -> bool:
        """Butceden harcar.

        Args:
            mission_id: Gorev ID.
            amount: Miktar.

        Returns:
            Basarili ise True.
        """
        if amount <= 0:
            return False

        budget = self._budgets.get(mission_id, 0)
        spent = self._spent.get(mission_id, 0)

        if budget > 0 and spent + amount > budget:
            return False

        self._spent[mission_id] = spent + amount
        return True

    def get_budget_status(self, mission_id: str) -> dict[str, float]:
        """Butce durumunu getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Butce bilgileri.
        """
        budget = self._budgets.get(mission_id, 0)
        spent = self._spent.get(mission_id, 0)
        return {
            "budget": budget,
            "spent": spent,
            "remaining": max(0, budget - spent),
        }

    def detect_conflicts(self) -> list[dict[str, Any]]:
        """Kaynak catismalarini tespit eder.

        Returns:
            Catisma listesi.
        """
        conflicts: list[dict[str, Any]] = []

        # Butce asimi
        for mission_id, budget in self._budgets.items():
            spent = self._spent.get(mission_id, 0)
            if budget > 0 and spent > budget:
                conflicts.append({
                    "type": "budget_exceeded",
                    "mission_id": mission_id,
                    "budget": budget,
                    "spent": spent,
                })

        return conflicts

    def get_mission_resources(
        self,
        mission_id: str,
    ) -> dict[str, list[str]]:
        """Gorev kaynaklarini getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Kaynak tipi -> ID listesi.
        """
        agents = [
            a for a, m in self._agent_missions.items()
            if m == mission_id
        ]
        tools = [
            t for t, m in self._tool_missions.items()
            if m == mission_id
        ]
        return {"agents": agents, "tools": tools}

    def get_free_agents(self) -> list[str]:
        """Serbest agent'lari getirir.

        Returns:
            Agent ID listesi.
        """
        return [
            a for a in self._available_agents
            if a not in self._agent_missions
        ]

    def get_free_tools(self) -> list[str]:
        """Serbest araclari getirir.

        Returns:
            Arac ID listesi.
        """
        return [
            t for t in self._available_tools
            if t not in self._tool_missions
        ]

    @property
    def total_agents(self) -> int:
        """Toplam agent sayisi."""
        return len(self._available_agents)

    @property
    def assigned_agent_count(self) -> int:
        """Atanmis agent sayisi."""
        return len(self._agent_missions)

    @property
    def total_assignments(self) -> int:
        """Toplam atama sayisi."""
        return len(self._assignments)
