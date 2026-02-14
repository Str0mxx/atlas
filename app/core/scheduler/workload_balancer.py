"""ATLAS Is Yuku Dengeleyici modulu.

Kapasite planlama, yuk dagitimi,
yogun donem yonetimi, tukenmislik
onleme ve adil dagilim.
"""

import logging
from typing import Any

from app.models.scheduler import WorkloadStatus

logger = logging.getLogger(__name__)


class WorkloadBalancer:
    """Is yuku dengeleyici.

    Is yukunu agentlar arasinda dengeler
    ve asiri yuklenmeyi onler.

    Attributes:
        _agents: Agent kapasiteleri.
        _assignments: Atamalar.
    """

    def __init__(
        self,
        overload_threshold: float = 0.85,
        burnout_threshold: float = 0.95,
    ) -> None:
        """Is yuku dengeleyiciyi baslatir.

        Args:
            overload_threshold: Asiri yuk esigi.
            burnout_threshold: Tukenmislik esigi.
        """
        self._agents: dict[str, dict[str, Any]] = {}
        self._assignments: list[dict[str, Any]] = []
        self._overload_threshold = overload_threshold
        self._burnout_threshold = burnout_threshold

        logger.info("WorkloadBalancer baslatildi")

    def register_agent(
        self,
        agent_id: str,
        capacity: float = 1.0,
    ) -> dict[str, Any]:
        """Agent kaydeder.

        Args:
            agent_id: Agent ID.
            capacity: Kapasite (0.0-1.0 arasi).

        Returns:
            Agent bilgisi.
        """
        agent = {
            "agent_id": agent_id,
            "capacity": max(0.1, capacity),
            "current_load": 0.0,
            "tasks_assigned": 0,
        }
        self._agents[agent_id] = agent
        return agent

    def assign_task(
        self,
        task_id: str,
        load: float = 0.1,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Gorev atar.

        Args:
            task_id: Gorev ID.
            load: Yuk miktari.
            agent_id: Belirli agent (opsiyonel).

        Returns:
            Atama bilgisi.
        """
        target = agent_id

        if not target:
            # En uygun agenti bul
            target = self._find_best_agent(load)

        if not target or target not in self._agents:
            return {
                "task_id": task_id,
                "assigned": False,
                "reason": "no_available_agent",
            }

        agent = self._agents[target]
        agent["current_load"] += load
        agent["tasks_assigned"] += 1

        assignment = {
            "task_id": task_id,
            "agent_id": target,
            "load": load,
            "assigned": True,
        }
        self._assignments.append(assignment)
        return assignment

    def release_task(
        self,
        task_id: str,
    ) -> bool:
        """Gorevi serbest birakir.

        Args:
            task_id: Gorev ID.

        Returns:
            Basarili ise True.
        """
        for assignment in self._assignments:
            if (
                assignment["task_id"] == task_id
                and assignment["assigned"]
            ):
                agent = self._agents.get(
                    assignment["agent_id"],
                )
                if agent:
                    agent["current_load"] = max(
                        0.0,
                        agent["current_load"]
                        - assignment["load"],
                    )
                    agent["tasks_assigned"] = max(
                        0, agent["tasks_assigned"] - 1,
                    )
                assignment["assigned"] = False
                return True
        return False

    def get_status(
        self,
        agent_id: str,
    ) -> WorkloadStatus:
        """Agent is yuku durumunu getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Is yuku durumu.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return WorkloadStatus.IDLE

        ratio = agent["current_load"] / agent["capacity"]

        if ratio >= self._burnout_threshold:
            return WorkloadStatus.OVERLOADED
        if ratio >= self._overload_threshold:
            return WorkloadStatus.HEAVY
        if ratio >= 0.5:
            return WorkloadStatus.NORMAL
        if ratio > 0.0:
            return WorkloadStatus.LIGHT
        return WorkloadStatus.IDLE

    def get_load_distribution(self) -> dict[str, float]:
        """Yuk dagilimini getirir.

        Returns:
            Agent -> yuk orani eslesmesi.
        """
        dist: dict[str, float] = {}
        for aid, agent in self._agents.items():
            dist[aid] = round(
                agent["current_load"] / agent["capacity"],
                3,
            )
        return dist

    def detect_overloaded(self) -> list[str]:
        """Asiri yuklu agentlari tespit eder.

        Returns:
            Asiri yuklu agent ID listesi.
        """
        overloaded: list[str] = []
        for aid, agent in self._agents.items():
            ratio = agent["current_load"] / agent["capacity"]
            if ratio >= self._overload_threshold:
                overloaded.append(aid)
        return overloaded

    def rebalance(self) -> dict[str, Any]:
        """Is yukunu yeniden dengeler.

        Returns:
            Dengeleme sonucu.
        """
        if not self._agents:
            return {"rebalanced": False, "moves": 0}

        total_load = sum(
            a["current_load"] for a in self._agents.values()
        )
        total_capacity = sum(
            a["capacity"] for a in self._agents.values()
        )
        target_ratio = total_load / total_capacity

        moves = 0
        for agent in self._agents.values():
            target_load = agent["capacity"] * target_ratio
            agent["current_load"] = round(target_load, 3)
            moves += 1

        return {"rebalanced": True, "moves": moves}

    def _find_best_agent(
        self,
        load: float,
    ) -> str | None:
        """En uygun agenti bulur.

        Args:
            load: Yuk miktari.

        Returns:
            Agent ID veya None.
        """
        best_id: str | None = None
        best_ratio = float("inf")

        for aid, agent in self._agents.items():
            ratio = agent["current_load"] / agent["capacity"]
            available = agent["capacity"] - agent["current_load"]
            if available >= load and ratio < best_ratio:
                best_ratio = ratio
                best_id = aid

        return best_id

    @property
    def agent_count(self) -> int:
        """Agent sayisi."""
        return len(self._agents)

    @property
    def assignment_count(self) -> int:
        """Atama sayisi."""
        return sum(
            1 for a in self._assignments if a["assigned"]
        )
