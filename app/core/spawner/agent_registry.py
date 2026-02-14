"""ATLAS Agent Kayit Defteri modulu.

Tum aktif agent'lar, metadata, yetenek indeksi,
arama, filtreleme ve istatistikler.
"""

import logging
from typing import Any

from app.models.spawner import (
    AgentState,
    SpawnedAgent,
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Agent kayit defteri.

    Tum agent'lari merkezi olarak kaydeder,
    indeksler ve sorgulama imkani saglar.

    Attributes:
        _agents: Kayitli agent'lar.
        _capability_index: Yetenek indeksi.
        _tags: Agent etiketleri.
    """

    def __init__(self) -> None:
        """Kayit defterini baslatir."""
        self._agents: dict[str, SpawnedAgent] = {}
        self._capability_index: dict[str, set[str]] = {}
        self._tags: dict[str, set[str]] = {}  # agent_id -> tags

        logger.info("AgentRegistry baslatildi")

    def register(
        self,
        agent: SpawnedAgent,
        tags: list[str] | None = None,
    ) -> None:
        """Agent'i kaydeder.

        Args:
            agent: Kaydedilecek agent.
            tags: Etiketler.
        """
        self._agents[agent.agent_id] = agent

        # Yetenek indeksini guncelle
        for cap in agent.capabilities:
            if cap not in self._capability_index:
                self._capability_index[cap] = set()
            self._capability_index[cap].add(agent.agent_id)

        # Etiketler
        if tags:
            self._tags[agent.agent_id] = set(tags)

        logger.info("Agent kaydedildi: %s (%s)", agent.name, agent.agent_id)

    def unregister(self, agent_id: str) -> bool:
        """Agent kaydini siler.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        # Yetenek indeksinden cikar
        for cap in agent.capabilities:
            if cap in self._capability_index:
                self._capability_index[cap].discard(agent_id)

        # Etiketlerden cikar
        self._tags.pop(agent_id, None)

        del self._agents[agent_id]
        return True

    def get(self, agent_id: str) -> SpawnedAgent | None:
        """Agent'i getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            SpawnedAgent veya None.
        """
        return self._agents.get(agent_id)

    def find_by_capability(
        self, capability: str,
    ) -> list[SpawnedAgent]:
        """Yetenege gore agent'lari bulur.

        Args:
            capability: Yetenek adi.

        Returns:
            SpawnedAgent listesi.
        """
        agent_ids = self._capability_index.get(capability, set())
        return [
            self._agents[aid]
            for aid in agent_ids
            if aid in self._agents
        ]

    def find_by_state(
        self, state: AgentState,
    ) -> list[SpawnedAgent]:
        """Duruma gore agent'lari bulur.

        Args:
            state: Agent durumu.

        Returns:
            SpawnedAgent listesi.
        """
        return [a for a in self._agents.values() if a.state == state]

    def find_by_tag(self, tag: str) -> list[SpawnedAgent]:
        """Etikete gore agent'lari bulur.

        Args:
            tag: Etiket.

        Returns:
            SpawnedAgent listesi.
        """
        results: list[SpawnedAgent] = []
        for agent_id, tags in self._tags.items():
            if tag in tags and agent_id in self._agents:
                results.append(self._agents[agent_id])
        return results

    def find_by_name(self, name_pattern: str) -> list[SpawnedAgent]:
        """Isme gore agent'lari bulur.

        Args:
            name_pattern: Isim kalıbi (icerir).

        Returns:
            SpawnedAgent listesi.
        """
        pattern = name_pattern.lower()
        return [
            a for a in self._agents.values()
            if pattern in a.name.lower()
        ]

    def search(
        self,
        state: AgentState | None = None,
        capability: str | None = None,
        tag: str | None = None,
        min_workload: float | None = None,
        max_workload: float | None = None,
    ) -> list[SpawnedAgent]:
        """Gelismis arama.

        Args:
            state: Durum filtresi.
            capability: Yetenek filtresi.
            tag: Etiket filtresi.
            min_workload: Min is yuku.
            max_workload: Maks is yuku.

        Returns:
            SpawnedAgent listesi.
        """
        results = list(self._agents.values())

        if state is not None:
            results = [a for a in results if a.state == state]

        if capability:
            cap_agents = self._capability_index.get(capability, set())
            results = [a for a in results if a.agent_id in cap_agents]

        if tag:
            tag_agents = {
                aid for aid, tags in self._tags.items()
                if tag in tags
            }
            results = [a for a in results if a.agent_id in tag_agents]

        if min_workload is not None:
            results = [a for a in results if a.workload >= min_workload]

        if max_workload is not None:
            results = [a for a in results if a.workload <= max_workload]

        return results

    def add_tag(self, agent_id: str, tag: str) -> bool:
        """Etiket ekler.

        Args:
            agent_id: Agent ID.
            tag: Etiket.

        Returns:
            Basarili ise True.
        """
        if agent_id not in self._agents:
            return False

        if agent_id not in self._tags:
            self._tags[agent_id] = set()
        self._tags[agent_id].add(tag)
        return True

    def remove_tag(self, agent_id: str, tag: str) -> bool:
        """Etiket siler.

        Args:
            agent_id: Agent ID.
            tag: Etiket.

        Returns:
            Basarili ise True.
        """
        if agent_id not in self._tags:
            return False

        self._tags[agent_id].discard(tag)
        return True

    def update_capability_index(self, agent: SpawnedAgent) -> None:
        """Yetenek indeksini gunceller.

        Args:
            agent: Guncellenen agent.
        """
        # Eski indeksleri temizle
        for cap_agents in self._capability_index.values():
            cap_agents.discard(agent.agent_id)

        # Yeni indeksleri ekle
        for cap in agent.capabilities:
            if cap not in self._capability_index:
                self._capability_index[cap] = set()
            self._capability_index[cap].add(agent.agent_id)

    def get_statistics(self) -> dict[str, Any]:
        """Istatistikleri getirir.

        Returns:
            Istatistik sozlugu.
        """
        agents = list(self._agents.values())
        state_counts: dict[str, int] = {}
        for a in agents:
            state_counts[a.state.value] = state_counts.get(a.state.value, 0) + 1

        avg_workload = 0.0
        active = [a for a in agents if a.state == AgentState.ACTIVE]
        if active:
            avg_workload = sum(a.workload for a in active) / len(active)

        return {
            "total_agents": len(agents),
            "state_distribution": state_counts,
            "unique_capabilities": len(self._capability_index),
            "avg_workload": round(avg_workload, 3),
            "total_tags": sum(len(t) for t in self._tags.values()),
        }

    def list_all(self) -> list[SpawnedAgent]:
        """Tum agent'lari listeler.

        Returns:
            SpawnedAgent listesi.
        """
        return list(self._agents.values())

    @property
    def count(self) -> int:
        """Toplam agent sayisi."""
        return len(self._agents)

    @property
    def active_count(self) -> int:
        """Aktif agent sayisi."""
        return sum(
            1 for a in self._agents.values()
            if a.state == AgentState.ACTIVE
        )

    @property
    def capability_count(self) -> int:
        """Benzersiz yetenek sayisi."""
        return len(self._capability_index)
