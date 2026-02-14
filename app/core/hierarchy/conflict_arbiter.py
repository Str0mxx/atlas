"""ATLAS Catisma Hakemi modulu.

Kaynak catismalari, oncelik catismalari,
karar catismalari, kilitlenme tespiti ve cozum stratejileri.
"""

import logging
from typing import Any

from app.models.hierarchy import (
    ConflictRecord,
    ConflictType,
    ResolutionStrategy,
)

logger = logging.getLogger(__name__)


class ConflictArbiter:
    """Catisma hakem sistemi.

    Agent'lar arasi catismalari tespit eder,
    degerlendirir ve cozer.

    Attributes:
        _conflicts: Catisma kayitlari.
        _active: Aktif catismalar.
        _resource_locks: Kaynak kilitleri.
    """

    def __init__(self) -> None:
        """Catisma hakemini baslatir."""
        self._conflicts: list[ConflictRecord] = []
        self._active: dict[str, ConflictRecord] = {}
        self._resource_locks: dict[str, str] = {}  # resource -> agent

        logger.info("ConflictArbiter baslatildi")

    def report_conflict(
        self,
        conflict_type: ConflictType,
        agents: list[str],
        resource: str = "",
        description: str = "",
    ) -> ConflictRecord:
        """Catisma bildirir.

        Args:
            conflict_type: Catisma tipi.
            agents: Ilgili agent'lar.
            resource: Kaynak (opsiyonel).
            description: Aciklama.

        Returns:
            ConflictRecord nesnesi.
        """
        record = ConflictRecord(
            conflict_type=conflict_type,
            agents_involved=agents,
            resource=resource,
            description=description,
        )

        self._conflicts.append(record)
        self._active[record.conflict_id] = record

        logger.warning(
            "Catisma: tip=%s, agents=%s, kaynak=%s",
            conflict_type.value, agents, resource,
        )
        return record

    def resolve_by_priority(
        self,
        conflict_id: str,
        agent_priorities: dict[str, int],
    ) -> str:
        """Oncelik bazli cozer.

        Args:
            conflict_id: Catisma ID.
            agent_priorities: Agent oncelikleri.

        Returns:
            Kazanan agent ID.
        """
        record = self._active.get(conflict_id)
        if not record:
            return ""

        # En yuksek oncelikli agent kazanir
        winner = ""
        max_pri = -1
        for agent_id in record.agents_involved:
            pri = agent_priorities.get(agent_id, 0)
            if pri > max_pri:
                max_pri = pri
                winner = agent_id

        record.resolution = ResolutionStrategy.PRIORITY_BASED
        record.resolved = True
        record.winner = winner
        del self._active[conflict_id]

        return winner

    def resolve_by_authority(
        self,
        conflict_id: str,
        agent_authorities: dict[str, int],
    ) -> str:
        """Yetki bazli cozer.

        Args:
            conflict_id: Catisma ID.
            agent_authorities: Agent yetki seviyeleri.

        Returns:
            Kazanan agent ID.
        """
        record = self._active.get(conflict_id)
        if not record:
            return ""

        winner = ""
        max_auth = -1
        for agent_id in record.agents_involved:
            auth = agent_authorities.get(agent_id, 0)
            if auth > max_auth:
                max_auth = auth
                winner = agent_id

        record.resolution = ResolutionStrategy.AUTHORITY_BASED
        record.resolved = True
        record.winner = winner
        del self._active[conflict_id]

        return winner

    def resolve_by_consensus(
        self,
        conflict_id: str,
        votes: dict[str, str],
    ) -> str:
        """Konsensus ile cozer.

        Args:
            conflict_id: Catisma ID.
            votes: Agent oyları (voter -> choice).

        Returns:
            Kazanan secim.
        """
        record = self._active.get(conflict_id)
        if not record:
            return ""

        # Oy say
        vote_count: dict[str, int] = {}
        for choice in votes.values():
            vote_count[choice] = vote_count.get(choice, 0) + 1

        winner = max(vote_count, key=vote_count.get) if vote_count else ""

        record.resolution = ResolutionStrategy.CONSENSUS
        record.resolved = True
        record.winner = winner
        del self._active[conflict_id]

        return winner

    def escalate_conflict(self, conflict_id: str) -> bool:
        """Catismayi ust seviyeye eskalasyon eder.

        Args:
            conflict_id: Catisma ID.

        Returns:
            Basarili ise True.
        """
        record = self._active.get(conflict_id)
        if not record:
            return False

        record.resolution = ResolutionStrategy.ESCALATION
        record.resolved = True
        del self._active[conflict_id]

        logger.info("Catisma eskalasyon edildi: %s", conflict_id)
        return True

    def detect_deadlock(
        self,
        wait_graph: dict[str, list[str]],
    ) -> list[list[str]]:
        """Kilitlenme tespit eder (dongusel bekleme).

        Args:
            wait_graph: Bekleme grafi (agent -> bekledigi agent'lar).

        Returns:
            Dongu listesi.
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()

        for start in wait_graph:
            if start in visited:
                continue

            path: list[str] = []
            path_set: set[str] = set()

            self._dfs_cycle(
                start, wait_graph, visited, path, path_set, cycles,
            )

        return cycles

    def lock_resource(
        self, resource: str, agent_id: str,
    ) -> bool:
        """Kaynagi kilitler.

        Args:
            resource: Kaynak adi.
            agent_id: Kilitleyen agent.

        Returns:
            Basarili ise True.
        """
        if resource in self._resource_locks:
            if self._resource_locks[resource] != agent_id:
                return False

        self._resource_locks[resource] = agent_id
        return True

    def unlock_resource(
        self, resource: str, agent_id: str,
    ) -> bool:
        """Kaynak kilidini acar.

        Args:
            resource: Kaynak adi.
            agent_id: Kilidi acan agent.

        Returns:
            Basarili ise True.
        """
        if resource not in self._resource_locks:
            return False

        if self._resource_locks[resource] != agent_id:
            return False

        del self._resource_locks[resource]
        return True

    def get_resource_owner(self, resource: str) -> str:
        """Kaynak sahibini getirir.

        Args:
            resource: Kaynak adi.

        Returns:
            Agent ID veya bos string.
        """
        return self._resource_locks.get(resource, "")

    def get_conflict(self, conflict_id: str) -> ConflictRecord | None:
        """Catisma kaydini getirir.

        Args:
            conflict_id: Catisma ID.

        Returns:
            ConflictRecord veya None.
        """
        for c in self._conflicts:
            if c.conflict_id == conflict_id:
                return c
        return None

    def get_active_conflicts(self) -> list[ConflictRecord]:
        """Aktif catismalari getirir.

        Returns:
            ConflictRecord listesi.
        """
        return list(self._active.values())

    def _dfs_cycle(
        self,
        node: str,
        graph: dict[str, list[str]],
        visited: set[str],
        path: list[str],
        path_set: set[str],
        cycles: list[list[str]],
    ) -> None:
        """DFS ile dongu arar."""
        if node in path_set:
            # Dongu bulundu
            idx = path.index(node)
            cycles.append(path[idx:] + [node])
            return

        if node in visited:
            return

        path.append(node)
        path_set.add(node)

        for neighbor in graph.get(node, []):
            self._dfs_cycle(neighbor, graph, visited, path, path_set, cycles)

        path.pop()
        path_set.discard(node)
        visited.add(node)

    @property
    def total_conflicts(self) -> int:
        """Toplam catisma sayisi."""
        return len(self._conflicts)

    @property
    def active_conflicts(self) -> int:
        """Aktif catisma sayisi."""
        return len(self._active)

    @property
    def resolved_count(self) -> int:
        """Cozulmus catisma sayisi."""
        return sum(1 for c in self._conflicts if c.resolved)

    @property
    def locked_resources(self) -> int:
        """Kilitli kaynak sayisi."""
        return len(self._resource_locks)
