"""ATLAS Suru Hata Toleransi modulu.

Agent hata tespiti, gorev yeniden atama,
durum kurtarma, yedeklilik ve kendini iyilestirme.
"""

import logging
from typing import Any

from app.models.swarm import FaultAction, FaultEvent

logger = logging.getLogger(__name__)


class SwarmFaultTolerance:
    """Suru hata tolerans sistemi.

    Agent hatalarini tespit eder, gorevleri yeniden atar,
    durumları kurtarir ve kendini iyilestirir.

    Attributes:
        _events: Hata olaylari.
        _agent_health: Agent saglik durumu.
        _agent_tasks: Agent gorevleri.
        _redundancy: Yedeklilik eslesmesi.
        _max_retries: Maks yeniden deneme.
    """

    def __init__(self, max_retries: int = 3) -> None:
        """Hata tolerans sistemini baslatir.

        Args:
            max_retries: Maks yeniden deneme.
        """
        self._events: list[FaultEvent] = []
        self._agent_health: dict[str, bool] = {}
        self._agent_tasks: dict[str, list[str]] = {}
        self._redundancy: dict[str, str] = {}  # agent -> backup
        self._retry_counts: dict[str, int] = {}  # task -> retry count
        self._max_retries = max_retries

        logger.info("SwarmFaultTolerance baslatildi (max_retries=%d)", max_retries)

    def register_agent(
        self,
        agent_id: str,
        tasks: list[str] | None = None,
    ) -> None:
        """Agent'i kaydeder.

        Args:
            agent_id: Agent ID.
            tasks: Mevcut gorevler.
        """
        self._agent_health[agent_id] = True
        self._agent_tasks[agent_id] = tasks or []

    def report_failure(
        self,
        agent_id: str,
        task_id: str = "",
        fault_type: str = "unknown",
    ) -> FaultEvent:
        """Hata bildirir.

        Args:
            agent_id: Agent ID.
            task_id: Gorev ID.
            fault_type: Hata tipi.

        Returns:
            FaultEvent nesnesi.
        """
        self._agent_health[agent_id] = False

        # Aksiyon belirle
        action = self._determine_action(agent_id, task_id, fault_type)

        event = FaultEvent(
            agent_id=agent_id,
            task_id=task_id,
            fault_type=fault_type,
            action_taken=action,
        )
        self._events.append(event)

        logger.warning(
            "Hata: agent=%s, task=%s, type=%s, action=%s",
            agent_id, task_id, fault_type, action.value,
        )
        return event

    def reassign_task(
        self,
        task_id: str,
        failed_agent: str,
        available_agents: list[str],
    ) -> str:
        """Gorevi yeniden atar.

        Args:
            task_id: Gorev ID.
            failed_agent: Basarisiz agent.
            available_agents: Musait agent'lar.

        Returns:
            Atanan agent ID.
        """
        # Basarisiz agent'tan cikar
        if failed_agent in self._agent_tasks:
            tasks = self._agent_tasks[failed_agent]
            if task_id in tasks:
                tasks.remove(task_id)

        # Yedek agent var mi
        backup = self._redundancy.get(failed_agent)
        if backup and backup in available_agents and self._agent_health.get(backup, False):
            self._agent_tasks.setdefault(backup, []).append(task_id)
            return backup

        # Saglikli ve musait agent'lari filtrele
        healthy = [
            a for a in available_agents
            if a != failed_agent and self._agent_health.get(a, False)
        ]

        if not healthy:
            return ""

        # En az gorevli agent'a ata
        target = min(healthy, key=lambda a: len(self._agent_tasks.get(a, [])))
        self._agent_tasks.setdefault(target, []).append(task_id)

        # Hata olayini guncelle
        for event in reversed(self._events):
            if event.task_id == task_id and event.agent_id == failed_agent:
                event.reassigned_to = target
                event.resolved = True
                break

        return target

    def retry_task(
        self,
        agent_id: str,
        task_id: str,
    ) -> bool:
        """Gorevi yeniden dener.

        Args:
            agent_id: Agent ID.
            task_id: Gorev ID.

        Returns:
            Yeniden deneme basarili ise True.
        """
        key = f"{agent_id}:{task_id}"
        retries = self._retry_counts.get(key, 0)

        if retries >= self._max_retries:
            return False

        self._retry_counts[key] = retries + 1
        # Agent'i tekrar saglikli isaretle
        self._agent_health[agent_id] = True
        return True

    def set_backup(self, agent_id: str, backup_id: str) -> None:
        """Yedek agent atar.

        Args:
            agent_id: Asil agent.
            backup_id: Yedek agent.
        """
        self._redundancy[agent_id] = backup_id

    def get_backup(self, agent_id: str) -> str:
        """Yedek agent'i getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Yedek agent ID.
        """
        return self._redundancy.get(agent_id, "")

    def heal_agent(self, agent_id: str) -> bool:
        """Agent'i iyilestirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        if agent_id not in self._agent_health:
            return False

        self._agent_health[agent_id] = True
        logger.info("Agent iyilestirildi: %s", agent_id)
        return True

    def get_healthy_agents(self) -> list[str]:
        """Saglikli agent'lari getirir.

        Returns:
            Agent ID listesi.
        """
        return [a for a, h in self._agent_health.items() if h]

    def get_failed_agents(self) -> list[str]:
        """Basarisiz agent'lari getirir.

        Returns:
            Agent ID listesi.
        """
        return [a for a, h in self._agent_health.items() if not h]

    def get_events(
        self,
        agent_id: str | None = None,
        resolved: bool | None = None,
    ) -> list[FaultEvent]:
        """Hata olaylarini getirir.

        Args:
            agent_id: Agent filtresi.
            resolved: Cozulme filtresi.

        Returns:
            FaultEvent listesi.
        """
        events = list(self._events)
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        if resolved is not None:
            events = [e for e in events if e.resolved == resolved]
        return events

    def get_redundancy_coverage(self) -> float:
        """Yedeklilik kapsamini hesaplar.

        Returns:
            Kapsam orani (0-1).
        """
        if not self._agent_health:
            return 0.0
        covered = sum(1 for a in self._agent_health if a in self._redundancy)
        return round(covered / len(self._agent_health), 3)

    def _determine_action(
        self,
        agent_id: str,
        task_id: str,
        fault_type: str,
    ) -> FaultAction:
        """Hata aksiyonu belirler."""
        key = f"{agent_id}:{task_id}"
        retries = self._retry_counts.get(key, 0)

        if fault_type == "critical":
            return FaultAction.ESCALATE

        if retries < self._max_retries:
            return FaultAction.RETRY

        if self._redundancy.get(agent_id):
            return FaultAction.REASSIGN

        return FaultAction.ESCALATE

    @property
    def total_events(self) -> int:
        """Toplam hata olayi sayisi."""
        return len(self._events)

    @property
    def unresolved_count(self) -> int:
        """Cozulmemis hata sayisi."""
        return sum(1 for e in self._events if not e.resolved)

    @property
    def healthy_ratio(self) -> float:
        """Saglikli agent orani."""
        if not self._agent_health:
            return 0.0
        healthy = sum(1 for h in self._agent_health.values() if h)
        return round(healthy / len(self._agent_health), 3)
