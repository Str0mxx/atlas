"""ATLAS Yetki Devri Motoru modulu.

Gorev ayrıstirma, yetenek esleme, is yuku
dagitimi, oncelik mirasi ve son tarih yayilimi.
"""

import logging
from typing import Any

from app.models.hierarchy import (
    AgentNode,
    DelegationRecord,
    DelegationStatus,
)

logger = logging.getLogger(__name__)


class DelegationEngine:
    """Yetki devri motoru.

    Gorevleri alt agent'lara devreder,
    yetenek esler ve is yukunu dagitir.

    Attributes:
        _delegations: Delegasyon kayitlari.
        _active: Aktif delegasyonlar.
    """

    def __init__(self) -> None:
        """Yetki devri motorunu baslatir."""
        self._delegations: list[DelegationRecord] = []
        self._active: dict[str, DelegationRecord] = {}

        logger.info("DelegationEngine baslatildi")

    def delegate(
        self,
        task_id: str,
        from_agent: str,
        to_agent: str,
        priority: int = 5,
        deadline_minutes: int = 0,
    ) -> DelegationRecord:
        """Gorev devreder.

        Args:
            task_id: Gorev ID.
            from_agent: Delege eden agent.
            to_agent: Delege edilen agent.
            priority: Oncelik (1-10).
            deadline_minutes: Son tarih (dakika).

        Returns:
            DelegationRecord nesnesi.
        """
        record = DelegationRecord(
            task_id=task_id,
            from_agent=from_agent,
            to_agent=to_agent,
            priority=min(max(priority, 1), 10),
            deadline_minutes=deadline_minutes,
            status=DelegationStatus.PENDING,
        )

        self._delegations.append(record)
        self._active[record.delegation_id] = record

        logger.info(
            "Gorev devredildi: %s -> %s (task=%s, pri=%d)",
            from_agent, to_agent, task_id, priority,
        )
        return record

    def accept(self, delegation_id: str) -> bool:
        """Delegasyonu kabul eder.

        Args:
            delegation_id: Delegasyon ID.

        Returns:
            Basarili ise True.
        """
        record = self._active.get(delegation_id)
        if not record or record.status != DelegationStatus.PENDING:
            return False

        record.status = DelegationStatus.ACCEPTED
        return True

    def start(self, delegation_id: str) -> bool:
        """Delegasyonu baslatir.

        Args:
            delegation_id: Delegasyon ID.

        Returns:
            Basarili ise True.
        """
        record = self._active.get(delegation_id)
        if not record or record.status not in (
            DelegationStatus.PENDING, DelegationStatus.ACCEPTED,
        ):
            return False

        record.status = DelegationStatus.IN_PROGRESS
        return True

    def complete(self, delegation_id: str, result: str = "") -> bool:
        """Delegasyonu tamamlar.

        Args:
            delegation_id: Delegasyon ID.
            result: Sonuc bilgisi.

        Returns:
            Basarili ise True.
        """
        record = self._active.get(delegation_id)
        if not record:
            return False

        record.status = DelegationStatus.COMPLETED
        record.result = result
        del self._active[delegation_id]
        return True

    def fail(self, delegation_id: str, reason: str = "") -> bool:
        """Delegasyonu basarisiz olarak isareler.

        Args:
            delegation_id: Delegasyon ID.
            reason: Basarisizlik nedeni.

        Returns:
            Basarili ise True.
        """
        record = self._active.get(delegation_id)
        if not record:
            return False

        record.status = DelegationStatus.FAILED
        record.result = reason
        del self._active[delegation_id]
        return True

    def escalate(self, delegation_id: str) -> bool:
        """Delegasyonu ust seviyeye eskalasyon eder.

        Args:
            delegation_id: Delegasyon ID.

        Returns:
            Basarili ise True.
        """
        record = self._active.get(delegation_id)
        if not record:
            return False

        record.status = DelegationStatus.ESCALATED
        del self._active[delegation_id]
        return True

    def decompose_task(
        self,
        task_description: str,
        subtask_count: int = 3,
    ) -> list[dict[str, Any]]:
        """Gorevi alt gorevlere ayirir.

        Args:
            task_description: Gorev aciklamasi.
            subtask_count: Alt gorev sayisi.

        Returns:
            Alt gorev listesi.
        """
        subtasks: list[dict[str, Any]] = []
        words = task_description.split()
        chunk_size = max(1, len(words) // subtask_count)

        for i in range(subtask_count):
            start = i * chunk_size
            end = start + chunk_size if i < subtask_count - 1 else len(words)
            chunk = " ".join(words[start:end]) if start < len(words) else ""

            subtasks.append({
                "subtask_id": f"sub_{i + 1}",
                "description": chunk or f"Alt gorev {i + 1}",
                "priority": 5,
                "order": i + 1,
            })

        return subtasks

    def match_capability(
        self,
        required: list[str],
        agents: list[AgentNode],
    ) -> list[AgentNode]:
        """Yetenek eslestirmesi yapar.

        Args:
            required: Gereken yetenekler.
            agents: Aday agent'lar.

        Returns:
            Eslesen agent'lar (skor sirasinda).
        """
        if not required:
            return [a for a in agents if a.active]

        scored: list[tuple[AgentNode, float]] = []
        for agent in agents:
            if not agent.active:
                continue
            matches = sum(1 for r in required if r in agent.capabilities)
            score = matches / len(required) if required else 0.0
            if score > 0:
                scored.append((agent, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [a for a, _ in scored]

    def distribute_workload(
        self,
        tasks: list[dict[str, Any]],
        agents: list[AgentNode],
    ) -> list[dict[str, str]]:
        """Is yukunu dagitir (round-robin + workload).

        Args:
            tasks: Gorev listesi.
            agents: Uygun agent'lar.

        Returns:
            Atama listesi (task_id -> agent_id).
        """
        if not agents or not tasks:
            return []

        # Aktif ve en az yuklulere once
        available = sorted(
            [a for a in agents if a.active],
            key=lambda a: a.workload,
        )

        if not available:
            return []

        assignments: list[dict[str, str]] = []
        for i, task in enumerate(tasks):
            agent = available[i % len(available)]
            assignments.append({
                "task_id": task.get("subtask_id", str(i)),
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
            })

        return assignments

    def propagate_priority(
        self,
        delegation_id: str,
        new_priority: int,
    ) -> bool:
        """Onceligi delegasyona yayar.

        Args:
            delegation_id: Delegasyon ID.
            new_priority: Yeni oncelik.

        Returns:
            Basarili ise True.
        """
        record = self._active.get(delegation_id)
        if not record:
            return False

        record.priority = min(max(new_priority, 1), 10)
        return True

    def get_delegation(self, delegation_id: str) -> DelegationRecord | None:
        """Delegasyon kaydini getirir.

        Args:
            delegation_id: Delegasyon ID.

        Returns:
            DelegationRecord veya None.
        """
        for d in self._delegations:
            if d.delegation_id == delegation_id:
                return d
        return None

    def get_agent_delegations(
        self, agent_id: str, active_only: bool = False,
    ) -> list[DelegationRecord]:
        """Agent'in delegasyonlarini getirir.

        Args:
            agent_id: Agent ID.
            active_only: Sadece aktifler.

        Returns:
            DelegationRecord listesi.
        """
        results: list[DelegationRecord] = []
        source = self._active.values() if active_only else self._delegations

        for d in source:
            if d.to_agent == agent_id or d.from_agent == agent_id:
                results.append(d)

        return results

    @property
    def total_delegations(self) -> int:
        """Toplam delegasyon sayisi."""
        return len(self._delegations)

    @property
    def active_delegations(self) -> int:
        """Aktif delegasyon sayisi."""
        return len(self._active)

    @property
    def completion_rate(self) -> float:
        """Tamamlanma orani."""
        if not self._delegations:
            return 0.0
        completed = sum(
            1 for d in self._delegations
            if d.status == DelegationStatus.COMPLETED
        )
        return completed / len(self._delegations)
