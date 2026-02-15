"""ATLAS Kendine Atayici modulu.

Gorev kendine atama, yetenek esleme,
yuk dengeleme, oncelik yonetimi, delegasyon kararlari.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SelfAssigner:
    """Kendine atayici.

    Gorevleri yeteneklere gore atar.

    Attributes:
        _assignments: Atama kayitlari.
        _agents: Ajan yetenekleri.
    """

    def __init__(self) -> None:
        """Kendine atayiciyi baslatir."""
        self._assignments: dict[
            str, dict[str, Any]
        ] = {}
        self._agents: dict[
            str, dict[str, Any]
        ] = {}
        self._workload: dict[str, int] = {}
        self._stats = {
            "assigned": 0,
            "delegated": 0,
        }

        logger.info(
            "SelfAssigner baslatildi",
        )

    def register_agent(
        self,
        agent_id: str,
        capabilities: list[str],
        max_concurrent: int = 5,
    ) -> dict[str, Any]:
        """Ajan kaydeder.

        Args:
            agent_id: Ajan ID.
            capabilities: Yetenekler.
            max_concurrent: Maks esanli gorev.

        Returns:
            Kayit bilgisi.
        """
        self._agents[agent_id] = {
            "agent_id": agent_id,
            "capabilities": capabilities,
            "max_concurrent": max_concurrent,
            "available": True,
        }
        self._workload[agent_id] = 0

        return {
            "agent_id": agent_id,
            "registered": True,
            "capabilities": len(capabilities),
        }

    def assign_task(
        self,
        task_id: str,
        required_capabilities: (
            list[str] | None
        ) = None,
        priority: str = "medium",
        strategy: str = "capability_match",
    ) -> dict[str, Any]:
        """Gorev atar.

        Args:
            task_id: Gorev ID.
            required_capabilities: Gerekli yetenekler.
            priority: Oncelik.
            strategy: Atama stratejisi.

        Returns:
            Atama bilgisi.
        """
        if not self._agents:
            return {
                "task_id": task_id,
                "assigned": False,
                "reason": "no_agents",
            }

        required = required_capabilities or []

        # Strateji secimi
        if strategy == "capability_match":
            agent_id = (
                self._match_capability(
                    required,
                )
            )
        elif strategy == "load_balance":
            agent_id = self._balance_load()
        elif strategy == "priority_first":
            agent_id = (
                self._priority_assign(
                    priority,
                )
            )
        else:
            agent_id = self._balance_load()

        if not agent_id:
            return {
                "task_id": task_id,
                "assigned": False,
                "reason": "no_suitable_agent",
            }

        assignment = {
            "task_id": task_id,
            "agent_id": agent_id,
            "strategy": strategy,
            "priority": priority,
            "status": "assigned",
            "assigned_at": time.time(),
        }

        self._assignments[task_id] = assignment
        self._workload[agent_id] = (
            self._workload.get(agent_id, 0) + 1
        )
        self._stats["assigned"] += 1

        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "assigned": True,
            "strategy": strategy,
        }

    def _match_capability(
        self,
        required: list[str],
    ) -> str | None:
        """Yetenek eslestirmesi yapar.

        Args:
            required: Gerekli yetenekler.

        Returns:
            Uygun ajan ID veya None.
        """
        best_agent = None
        best_score = -1

        for aid, agent in self._agents.items():
            if not agent["available"]:
                continue
            if (
                self._workload.get(aid, 0)
                >= agent["max_concurrent"]
            ):
                continue

            caps = set(agent["capabilities"])
            req = set(required)

            if not req:
                score = 1
            else:
                overlap = caps & req
                score = (
                    len(overlap) / len(req)
                )

            if score > best_score:
                best_score = score
                best_agent = aid

        return best_agent

    def _balance_load(self) -> str | None:
        """Yuk dengeleme yapar.

        Returns:
            En az yuklu ajan ID veya None.
        """
        available = [
            (aid, self._workload.get(aid, 0))
            for aid, a in self._agents.items()
            if a["available"]
            and self._workload.get(aid, 0)
            < a["max_concurrent"]
        ]

        if not available:
            return None

        # En az yuklu ajan
        available.sort(key=lambda x: x[1])
        return available[0][0]

    def _priority_assign(
        self,
        priority: str,
    ) -> str | None:
        """Oncelik bazli atama yapar.

        Args:
            priority: Oncelik seviyesi.

        Returns:
            Ajan ID veya None.
        """
        # Kritik gorevler icin en az yuklu ajan
        return self._balance_load()

    def delegate_task(
        self,
        task_id: str,
        from_agent: str,
        to_agent: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Gorevi devreder.

        Args:
            task_id: Gorev ID.
            from_agent: Kaynak ajan.
            to_agent: Hedef ajan.
            reason: Neden.

        Returns:
            Devir bilgisi.
        """
        if to_agent not in self._agents:
            return {
                "error": "target_not_found",
            }

        assignment = self._assignments.get(
            task_id,
        )
        if assignment:
            old_agent = assignment["agent_id"]
            if old_agent in self._workload:
                self._workload[old_agent] = max(
                    0,
                    self._workload[old_agent] - 1,
                )
            assignment["agent_id"] = to_agent
            assignment["delegated_from"] = (
                from_agent
            )
            assignment["delegation_reason"] = (
                reason
            )
        else:
            self._assignments[task_id] = {
                "task_id": task_id,
                "agent_id": to_agent,
                "delegated_from": from_agent,
                "delegation_reason": reason,
                "status": "assigned",
                "assigned_at": time.time(),
            }

        self._workload[to_agent] = (
            self._workload.get(to_agent, 0) + 1
        )
        self._stats["delegated"] += 1

        return {
            "task_id": task_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "delegated": True,
        }

    def complete_task(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        """Gorevi tamamlar.

        Args:
            task_id: Gorev ID.

        Returns:
            Tamamlama bilgisi.
        """
        assignment = self._assignments.get(
            task_id,
        )
        if not assignment:
            return {
                "error": "assignment_not_found",
            }

        assignment["status"] = "completed"
        assignment["completed_at"] = time.time()

        agent_id = assignment["agent_id"]
        if agent_id in self._workload:
            self._workload[agent_id] = max(
                0,
                self._workload[agent_id] - 1,
            )

        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "completed": True,
        }

    def get_assignment(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        """Atama bilgisi getirir.

        Args:
            task_id: Gorev ID.

        Returns:
            Atama bilgisi.
        """
        a = self._assignments.get(task_id)
        if not a:
            return {
                "error": "assignment_not_found",
            }
        return dict(a)

    def get_agent_workload(
        self,
        agent_id: str,
    ) -> dict[str, Any]:
        """Ajan is yukunu getirir.

        Args:
            agent_id: Ajan ID.

        Returns:
            Yuk bilgisi.
        """
        if agent_id not in self._agents:
            return {
                "error": "agent_not_found",
            }

        current = self._workload.get(
            agent_id, 0,
        )
        max_c = self._agents[agent_id][
            "max_concurrent"
        ]

        return {
            "agent_id": agent_id,
            "current_tasks": current,
            "max_concurrent": max_c,
            "utilization": round(
                current / max(max_c, 1) * 100,
                1,
            ),
        }

    @property
    def assignment_count(self) -> int:
        """Atama sayisi."""
        return self._stats["assigned"]

    @property
    def delegation_count(self) -> int:
        """Delegasyon sayisi."""
        return self._stats["delegated"]
