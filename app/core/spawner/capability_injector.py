"""ATLAS Yetenek Enjeksiyon modulu.

Calisma zamaninda yetenek ekleme, cikarma,
yukseltme, bagimlilik yonetimi ve hot-swap.
"""

import logging
from typing import Any

from app.models.spawner import (
    CapabilityAction,
    CapabilityChange,
    SpawnedAgent,
)

logger = logging.getLogger(__name__)

# Yetenek bagimliliklari
_CAPABILITY_DEPS: dict[str, list[str]] = {
    "deploy": ["build", "test"],
    "test": ["code_analyze"],
    "debug": ["code_analyze", "log"],
    "code_generate": ["code_analyze"],
    "summarize": ["analyze"],
    "alert": ["observe"],
    "coordinate": ["delegate", "plan"],
    "optimize": ["analyze", "report"],
}

# Yetenek versiyonlari
_CAPABILITY_VERSIONS: dict[str, str] = {
    "execute": "1.0",
    "analyze": "1.0",
    "report": "1.0",
    "search": "1.0",
    "observe": "1.0",
    "log": "1.0",
    "alert": "1.0",
    "delegate": "1.0",
    "plan": "1.0",
    "coordinate": "1.0",
    "code_analyze": "1.0",
    "code_generate": "1.0",
    "test": "1.0",
    "debug": "1.0",
    "deploy": "1.0",
    "build": "1.0",
    "scan": "1.0",
    "detect": "1.0",
    "block": "1.0",
    "summarize": "1.0",
    "optimize": "1.0",
}


class CapabilityInjector:
    """Yetenek enjeksiyon sistemi.

    Agent'lara calisma zamaninda yetenek ekler,
    cikarir, yukseltir ve hot-swap yapar.

    Attributes:
        _agents: Yonetilen agent'lar.
        _changes: Degisiklik gecmisi.
        _deps: Yetenek bagimliliklari.
        _versions: Yetenek versiyonlari.
    """

    def __init__(self) -> None:
        """Yetenek enjektorunu baslatir."""
        self._agents: dict[str, SpawnedAgent] = {}
        self._changes: list[CapabilityChange] = []
        self._deps: dict[str, list[str]] = dict(_CAPABILITY_DEPS)
        self._versions: dict[str, str] = dict(_CAPABILITY_VERSIONS)

        logger.info("CapabilityInjector baslatildi")

    def register(self, agent: SpawnedAgent) -> None:
        """Agent'i kaydeder.

        Args:
            agent: Kaydedilecek agent.
        """
        self._agents[agent.agent_id] = agent

    def add_capability(
        self,
        agent_id: str,
        capability: str,
        auto_resolve_deps: bool = True,
    ) -> CapabilityChange | None:
        """Yetenek ekler.

        Args:
            agent_id: Agent ID.
            capability: Yetenek adi.
            auto_resolve_deps: Bagimliliklari otomatik coz.

        Returns:
            CapabilityChange veya None.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return None

        if capability in agent.capabilities:
            return None

        # Bagimlilik kontrolu
        if auto_resolve_deps:
            deps = self._deps.get(capability, [])
            for dep in deps:
                if dep not in agent.capabilities:
                    self.add_capability(agent_id, dep, auto_resolve_deps=True)

        agent.capabilities.append(capability)

        change = CapabilityChange(
            agent_id=agent_id,
            action=CapabilityAction.ADD,
            capability=capability,
            new_version=self._versions.get(capability, "1.0"),
            success=True,
        )
        self._changes.append(change)

        logger.info("Yetenek eklendi: %s -> %s", agent_id, capability)
        return change

    def remove_capability(
        self,
        agent_id: str,
        capability: str,
        force: bool = False,
    ) -> CapabilityChange | None:
        """Yetenek cikarir.

        Args:
            agent_id: Agent ID.
            capability: Yetenek adi.
            force: Bagimli yetenekleri de cikar.

        Returns:
            CapabilityChange veya None.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return None

        if capability not in agent.capabilities:
            return None

        # Baska yetenekler bu yetenegine bagimli mi kontrol et
        if not force:
            dependents = self._get_dependents(capability, agent.capabilities)
            if dependents:
                logger.warning(
                    "Bagimli yetenekler var: %s -> %s",
                    capability, dependents,
                )
                return None

        agent.capabilities.remove(capability)

        change = CapabilityChange(
            agent_id=agent_id,
            action=CapabilityAction.REMOVE,
            capability=capability,
            old_version=self._versions.get(capability, "1.0"),
            success=True,
        )
        self._changes.append(change)

        logger.info("Yetenek cikarildi: %s -> %s", agent_id, capability)
        return change

    def upgrade_capability(
        self,
        agent_id: str,
        capability: str,
        new_version: str,
    ) -> CapabilityChange | None:
        """Yetenegini yukseltir.

        Args:
            agent_id: Agent ID.
            capability: Yetenek adi.
            new_version: Yeni versiyon.

        Returns:
            CapabilityChange veya None.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return None

        if capability not in agent.capabilities:
            return None

        old_version = self._versions.get(capability, "1.0")

        change = CapabilityChange(
            agent_id=agent_id,
            action=CapabilityAction.UPGRADE,
            capability=capability,
            old_version=old_version,
            new_version=new_version,
            success=True,
        )
        self._changes.append(change)

        # Global versiyonu guncelle
        self._versions[capability] = new_version

        logger.info(
            "Yetenek yukseltildi: %s %s -> %s",
            capability, old_version, new_version,
        )
        return change

    def hot_swap(
        self,
        agent_id: str,
        old_capability: str,
        new_capability: str,
    ) -> CapabilityChange | None:
        """Yetenek hot-swap yapar.

        Args:
            agent_id: Agent ID.
            old_capability: Eski yetenek.
            new_capability: Yeni yetenek.

        Returns:
            CapabilityChange veya None.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return None

        if old_capability not in agent.capabilities:
            return None

        # Eski yetenegi cikar, yenisini ekle
        idx = agent.capabilities.index(old_capability)
        agent.capabilities[idx] = new_capability

        change = CapabilityChange(
            agent_id=agent_id,
            action=CapabilityAction.SWAP,
            capability=f"{old_capability}->{new_capability}",
            old_version=self._versions.get(old_capability, "1.0"),
            new_version=self._versions.get(new_capability, "1.0"),
            success=True,
        )
        self._changes.append(change)

        logger.info(
            "Hot-swap: %s: %s -> %s",
            agent_id, old_capability, new_capability,
        )
        return change

    def check_dependencies(
        self, capability: str,
    ) -> list[str]:
        """Yetenek bagimliliklerini getirir.

        Args:
            capability: Yetenek adi.

        Returns:
            Bagimlilik listesi.
        """
        return list(self._deps.get(capability, []))

    def get_agent_capabilities(
        self, agent_id: str,
    ) -> list[str]:
        """Agent yeteneklerini getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Yetenek listesi.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return []
        return list(agent.capabilities)

    def get_change_history(
        self,
        agent_id: str | None = None,
    ) -> list[CapabilityChange]:
        """Degisiklik gecmisini getirir.

        Args:
            agent_id: Agent filtresi.

        Returns:
            CapabilityChange listesi.
        """
        if agent_id:
            return [c for c in self._changes if c.agent_id == agent_id]
        return list(self._changes)

    def _get_dependents(
        self,
        capability: str,
        current_caps: list[str],
    ) -> list[str]:
        """Bu yetenegine bagimli yetenekleri bulur."""
        dependents: list[str] = []
        for cap in current_caps:
            deps = self._deps.get(cap, [])
            if capability in deps:
                dependents.append(cap)
        return dependents

    @property
    def total_changes(self) -> int:
        """Toplam degisiklik sayisi."""
        return len(self._changes)
