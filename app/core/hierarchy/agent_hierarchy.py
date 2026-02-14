"""ATLAS Agent Hiyerarsisi modulu.

Parent-child iliskiler, kume tanimlari,
yetki seviyeleri, delegasyon kurallari ve raporlama zincirleri.
"""

import logging
from typing import Any

from app.models.hierarchy import (
    AgentNode,
    AuthorityLevel,
    AutonomyLevel,
)

logger = logging.getLogger(__name__)

# Yetki siralamasi
_AUTHORITY_ORDER: dict[AuthorityLevel, int] = {
    AuthorityLevel.MASTER: 4,
    AuthorityLevel.SUPERVISOR: 3,
    AuthorityLevel.LEAD: 2,
    AuthorityLevel.WORKER: 1,
    AuthorityLevel.OBSERVER: 0,
}


class AgentHierarchy:
    """Agent hiyerarsi sistemi.

    Parent-child iliskilerini yonetir, yetki
    seviyeleri ve delegasyon kurallarini uygular.

    Attributes:
        _agents: Agent dugum haritasi.
        _root_id: Kok agent ID.
        _max_depth: Maksimum derinlik.
    """

    def __init__(self, max_depth: int = 5) -> None:
        """Hiyerarsiyi baslatir.

        Args:
            max_depth: Maksimum hiyerarsi derinligi.
        """
        self._agents: dict[str, AgentNode] = {}
        self._root_id: str = ""
        self._max_depth = max_depth

        logger.info("AgentHierarchy baslatildi (max_depth=%d)", max_depth)

    def add_agent(
        self,
        name: str,
        authority: AuthorityLevel = AuthorityLevel.WORKER,
        autonomy: AutonomyLevel = AutonomyLevel.MEDIUM,
        parent_id: str = "",
        capabilities: list[str] | None = None,
    ) -> AgentNode:
        """Agent ekler.

        Args:
            name: Agent adi.
            authority: Yetki seviyesi.
            autonomy: Otonomi seviyesi.
            parent_id: Ust agent ID.
            capabilities: Yetenekler.

        Returns:
            AgentNode nesnesi.
        """
        node = AgentNode(
            name=name,
            authority=authority,
            autonomy=autonomy,
            parent_id=parent_id,
            capabilities=capabilities or [],
        )

        # Parent-child baglantisi
        if parent_id and parent_id in self._agents:
            depth = self._get_depth(parent_id)
            if depth >= self._max_depth:
                logger.warning(
                    "Maks derinlik asildi: %s (depth=%d)", name, depth,
                )
            else:
                self._agents[parent_id].children_ids.append(node.agent_id)

        # Ilk agent root olur
        if not self._root_id:
            self._root_id = node.agent_id

        self._agents[node.agent_id] = node
        logger.info("Agent eklendi: %s (authority=%s)", name, authority.value)
        return node

    def remove_agent(self, agent_id: str) -> bool:
        """Agent siler.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        if agent_id not in self._agents:
            return False

        node = self._agents[agent_id]

        # Cocuklari yetim birak veya parent'a bagla
        for child_id in node.children_ids:
            if child_id in self._agents:
                self._agents[child_id].parent_id = node.parent_id
                if node.parent_id and node.parent_id in self._agents:
                    self._agents[node.parent_id].children_ids.append(child_id)

        # Parent'tan cikar
        if node.parent_id and node.parent_id in self._agents:
            parent = self._agents[node.parent_id]
            if agent_id in parent.children_ids:
                parent.children_ids.remove(agent_id)

        del self._agents[agent_id]

        if agent_id == self._root_id:
            self._root_id = ""

        return True

    def get_agent(self, agent_id: str) -> AgentNode | None:
        """Agent getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            AgentNode veya None.
        """
        return self._agents.get(agent_id)

    def get_parent(self, agent_id: str) -> AgentNode | None:
        """Ust agent'i getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Parent AgentNode veya None.
        """
        node = self._agents.get(agent_id)
        if not node or not node.parent_id:
            return None
        return self._agents.get(node.parent_id)

    def get_children(self, agent_id: str) -> list[AgentNode]:
        """Alt agent'lari getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Cocuk agent listesi.
        """
        node = self._agents.get(agent_id)
        if not node:
            return []
        return [
            self._agents[cid]
            for cid in node.children_ids
            if cid in self._agents
        ]

    def get_ancestors(self, agent_id: str) -> list[AgentNode]:
        """Ata agent'lari getirir (asagidan yukari).

        Args:
            agent_id: Agent ID.

        Returns:
            Ata agent listesi.
        """
        ancestors: list[AgentNode] = []
        current = self._agents.get(agent_id)
        if not current:
            return ancestors

        visited: set[str] = {agent_id}
        while current and current.parent_id:
            if current.parent_id in visited:
                break
            visited.add(current.parent_id)
            parent = self._agents.get(current.parent_id)
            if parent:
                ancestors.append(parent)
                current = parent
            else:
                break

        return ancestors

    def get_descendants(self, agent_id: str) -> list[AgentNode]:
        """Tum alt agent'lari getirir (yukaridan asagi).

        Args:
            agent_id: Agent ID.

        Returns:
            Alt agent listesi.
        """
        descendants: list[AgentNode] = []
        node = self._agents.get(agent_id)
        if not node:
            return descendants

        queue = list(node.children_ids)
        visited: set[str] = set()
        while queue:
            cid = queue.pop(0)
            if cid in visited or cid not in self._agents:
                continue
            visited.add(cid)
            child = self._agents[cid]
            descendants.append(child)
            queue.extend(child.children_ids)

        return descendants

    def can_delegate(self, from_id: str, to_id: str) -> bool:
        """Delegasyon yapilabilir mi kontrol eder.

        Args:
            from_id: Delege eden agent.
            to_id: Delege edilen agent.

        Returns:
            Yetkilendirilmis ise True.
        """
        from_agent = self._agents.get(from_id)
        to_agent = self._agents.get(to_id)

        if not from_agent or not to_agent:
            return False

        # Ust seviye alta delege edebilir
        from_level = _AUTHORITY_ORDER.get(from_agent.authority, 0)
        to_level = _AUTHORITY_ORDER.get(to_agent.authority, 0)

        if from_level <= to_level:
            return False

        # Hedef aktif olmali
        if not to_agent.active:
            return False

        return True

    def get_reporting_chain(self, agent_id: str) -> list[str]:
        """Raporlama zincirini getirir (asagidan yukari).

        Args:
            agent_id: Agent ID.

        Returns:
            Agent ID listesi.
        """
        chain: list[str] = []
        current = self._agents.get(agent_id)
        visited: set[str] = set()

        while current and current.parent_id:
            if current.parent_id in visited:
                break
            visited.add(current.parent_id)
            chain.append(current.parent_id)
            current = self._agents.get(current.parent_id)

        return chain

    def find_by_capability(self, capability: str) -> list[AgentNode]:
        """Yetenegine gore agent bulur.

        Args:
            capability: Aranan yetenek.

        Returns:
            Agent listesi.
        """
        return [
            a for a in self._agents.values()
            if capability in a.capabilities and a.active
        ]

    def set_authority(
        self, agent_id: str, authority: AuthorityLevel
    ) -> bool:
        """Yetki seviyesini ayarlar.

        Args:
            agent_id: Agent ID.
            authority: Yeni yetki seviyesi.

        Returns:
            Basarili ise True.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.authority = authority
        return True

    def _get_depth(self, agent_id: str) -> int:
        """Agent derinligini hesaplar."""
        depth = 0
        current = self._agents.get(agent_id)
        visited: set[str] = set()
        while current and current.parent_id:
            if current.parent_id in visited:
                break
            visited.add(current.parent_id)
            depth += 1
            current = self._agents.get(current.parent_id)
        return depth

    @property
    def root(self) -> AgentNode | None:
        """Kok agent."""
        return self._agents.get(self._root_id)

    @property
    def agent_count(self) -> int:
        """Agent sayisi."""
        return len(self._agents)

    @property
    def active_count(self) -> int:
        """Aktif agent sayisi."""
        return sum(1 for a in self._agents.values() if a.active)

    @property
    def all_agents(self) -> list[AgentNode]:
        """Tum agent'lar."""
        return list(self._agents.values())
