"""ATLAS Suru Yuk Dengeleyici modulu.

Is calma, dinamik yeniden dagitim, darbogazo tespiti,
adillik zorlama ve verimlilik optimizasyonu.
"""

import logging
from typing import Any

from app.models.swarm import BalanceStrategy

logger = logging.getLogger(__name__)


class SwarmLoadBalancer:
    """Suru yuk dengeleyici.

    Suru uyeleri arasinda is yukunu dengeler,
    darbogazlari tespit eder ve adillik saglar.

    Attributes:
        _agent_loads: Agent is yukleri.
        _agent_capacities: Agent kapasiteleri.
        _task_assignments: Gorev atamalari.
        _strategy: Dengeleme stratejisi.
    """

    def __init__(
        self,
        strategy: BalanceStrategy = BalanceStrategy.LEAST_LOADED,
    ) -> None:
        """Yuk dengeleyiciyi baslatir.

        Args:
            strategy: Dengeleme stratejisi.
        """
        self._agent_loads: dict[str, float] = {}
        self._agent_capacities: dict[str, float] = {}
        self._task_assignments: dict[str, list[str]] = {}
        self._strategy = strategy
        self._steal_history: list[dict[str, Any]] = []

        logger.info("SwarmLoadBalancer baslatildi (%s)", strategy.value)

    def register_agent(
        self,
        agent_id: str,
        capacity: float = 1.0,
    ) -> None:
        """Agent'i kaydeder.

        Args:
            agent_id: Agent ID.
            capacity: Kapasite.
        """
        self._agent_loads[agent_id] = 0.0
        self._agent_capacities[agent_id] = capacity
        self._task_assignments[agent_id] = []

    def unregister_agent(self, agent_id: str) -> list[str]:
        """Agent'i cikarir, gorevlerini dondurur.

        Args:
            agent_id: Agent ID.

        Returns:
            Atanmis gorev listesi.
        """
        tasks = list(self._task_assignments.get(agent_id, []))
        self._agent_loads.pop(agent_id, None)
        self._agent_capacities.pop(agent_id, None)
        self._task_assignments.pop(agent_id, None)
        return tasks

    def assign_task(
        self,
        task_id: str,
        preferred_agent: str = "",
    ) -> str:
        """Gorev atar.

        Args:
            task_id: Gorev ID.
            preferred_agent: Tercih edilen agent.

        Returns:
            Atanan agent ID.
        """
        if not self._agent_loads:
            return ""

        if preferred_agent and preferred_agent in self._agent_loads:
            target = preferred_agent
        elif self._strategy == BalanceStrategy.LEAST_LOADED:
            target = self._find_least_loaded()
        elif self._strategy == BalanceStrategy.ROUND_ROBIN:
            target = self._find_round_robin()
        else:
            target = self._find_least_loaded()

        self._task_assignments[target].append(task_id)
        self._update_load(target)
        return target

    def complete_task(self, agent_id: str, task_id: str) -> bool:
        """Gorevi tamamlar.

        Args:
            agent_id: Agent ID.
            task_id: Gorev ID.

        Returns:
            Basarili ise True.
        """
        tasks = self._task_assignments.get(agent_id, [])
        if task_id not in tasks:
            return False

        tasks.remove(task_id)
        self._update_load(agent_id)
        return True

    def steal_work(
        self,
        idle_agent: str,
    ) -> dict[str, Any]:
        """Is calma (work stealing).

        Args:
            idle_agent: Bosta olan agent.

        Returns:
            Calma sonucu.
        """
        if idle_agent not in self._agent_loads:
            return {"success": False, "reason": "Agent bulunamadi"}

        # En yuklu agent'i bul
        busiest = self._find_most_loaded()
        if not busiest or busiest == idle_agent:
            return {"success": False, "reason": "Calacak is yok"}

        tasks = self._task_assignments.get(busiest, [])
        if len(tasks) <= 1:
            return {"success": False, "reason": "Yeterli is yok"}

        # Son gorevi cal
        stolen_task = tasks.pop()
        self._task_assignments[idle_agent].append(stolen_task)
        self._update_load(busiest)
        self._update_load(idle_agent)

        result = {
            "success": True,
            "task_id": stolen_task,
            "from_agent": busiest,
            "to_agent": idle_agent,
        }
        self._steal_history.append(result)
        return result

    def detect_bottlenecks(
        self, threshold: float = 0.8,
    ) -> list[dict[str, Any]]:
        """Darbogazlari tespit eder.

        Args:
            threshold: Yuk esigi.

        Returns:
            Darbogazo listesi.
        """
        bottlenecks: list[dict[str, Any]] = []
        for agent_id, load in self._agent_loads.items():
            if load >= threshold:
                bottlenecks.append({
                    "agent_id": agent_id,
                    "load": round(load, 3),
                    "task_count": len(self._task_assignments.get(agent_id, [])),
                    "capacity": self._agent_capacities.get(agent_id, 1.0),
                })
        return bottlenecks

    def rebalance(self) -> list[dict[str, Any]]:
        """Yuk dengeleme yapar.

        Returns:
            Transfer listesi.
        """
        transfers: list[dict[str, Any]] = []

        if len(self._agent_loads) < 2:
            return transfers

        avg_load = self.avg_load
        overloaded = [
            (aid, load)
            for aid, load in self._agent_loads.items()
            if load > avg_load + 0.2
        ]
        underloaded = [
            (aid, load)
            for aid, load in self._agent_loads.items()
            if load < avg_load - 0.2
        ]

        for over_id, _ in overloaded:
            for under_id, _ in underloaded:
                tasks = self._task_assignments.get(over_id, [])
                if len(tasks) > 1:
                    task = tasks.pop()
                    self._task_assignments[under_id].append(task)
                    self._update_load(over_id)
                    self._update_load(under_id)
                    transfers.append({
                        "task_id": task,
                        "from": over_id,
                        "to": under_id,
                    })
                    break

        return transfers

    def get_load_distribution(self) -> dict[str, float]:
        """Yuk dagitimini getirir.

        Returns:
            Agent -> yuk eslesmesi.
        """
        return dict(self._agent_loads)

    def get_fairness_index(self) -> float:
        """Jain adillik indeksini hesaplar.

        Returns:
            Adillik indeksi (0-1, 1 = tam adil).
        """
        loads = list(self._agent_loads.values())
        if not loads:
            return 1.0

        n = len(loads)
        sum_loads = sum(loads)
        sum_sq = sum(x * x for x in loads)

        if sum_sq == 0:
            return 1.0

        return round((sum_loads ** 2) / (n * sum_sq), 3)

    def _find_least_loaded(self) -> str:
        """En az yuklu agent'i bulur."""
        return min(self._agent_loads, key=self._agent_loads.get)

    def _find_most_loaded(self) -> str:
        """En yuklu agent'i bulur."""
        if not self._agent_loads:
            return ""
        return max(self._agent_loads, key=self._agent_loads.get)

    def _find_round_robin(self) -> str:
        """Round-robin ile agent secer."""
        # En az gorev atanmis agent
        return min(
            self._task_assignments,
            key=lambda a: len(self._task_assignments[a]),
        )

    def _update_load(self, agent_id: str) -> None:
        """Yuk gunceller."""
        capacity = self._agent_capacities.get(agent_id, 1.0)
        task_count = len(self._task_assignments.get(agent_id, []))
        self._agent_loads[agent_id] = min(
            1.0, task_count / max(1.0, capacity * 5),
        )

    @property
    def agent_count(self) -> int:
        """Agent sayisi."""
        return len(self._agent_loads)

    @property
    def avg_load(self) -> float:
        """Ortalama yuk."""
        if not self._agent_loads:
            return 0.0
        return sum(self._agent_loads.values()) / len(self._agent_loads)

    @property
    def total_tasks(self) -> int:
        """Toplam gorev sayisi."""
        return sum(len(t) for t in self._task_assignments.values())
