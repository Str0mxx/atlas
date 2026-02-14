"""ATLAS Yasam Dongusu Yoneticisi modulu.

Agent durumlari, durum gecisleri, saglik izleme,
otomatik yeniden baslatma ve nazik kapatma.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.spawner import (
    AgentState,
    SpawnedAgent,
)

logger = logging.getLogger(__name__)

# Gecerli durum gecisleri
_VALID_TRANSITIONS: dict[AgentState, list[AgentState]] = {
    AgentState.INITIALIZING: [AgentState.ACTIVE, AgentState.ERROR, AgentState.TERMINATED],
    AgentState.ACTIVE: [AgentState.PAUSED, AgentState.ERROR, AgentState.TERMINATING],
    AgentState.PAUSED: [AgentState.ACTIVE, AgentState.TERMINATING],
    AgentState.ERROR: [AgentState.ACTIVE, AgentState.TERMINATING, AgentState.TERMINATED],
    AgentState.TERMINATING: [AgentState.TERMINATED],
    AgentState.TERMINATED: [],
}


class LifecycleManager:
    """Yasam dongusu yoneticisi.

    Agent durumlarini yonetir, gecisleri kontrol eder,
    saglik izler ve otomatik kurtarma saglar.

    Attributes:
        _agents: Yonetilen agent'lar.
        _state_history: Durum gecmisi.
        _max_restarts: Maks yeniden baslatma.
        _health_threshold: Saglik esigi (saniye).
    """

    def __init__(
        self,
        max_restarts: int = 3,
        health_threshold: int = 60,
    ) -> None:
        """Yasam dongusu yoneticisini baslatir.

        Args:
            max_restarts: Maks yeniden baslatma sayisi.
            health_threshold: Saglik kontrol esigi (saniye).
        """
        self._agents: dict[str, SpawnedAgent] = {}
        self._state_history: list[dict[str, Any]] = []
        self._max_restarts = max_restarts
        self._health_threshold = health_threshold

        logger.info(
            "LifecycleManager baslatildi (max_restarts=%d, threshold=%ds)",
            max_restarts, health_threshold,
        )

    def register(self, agent: SpawnedAgent) -> None:
        """Agent'i kaydeder.

        Args:
            agent: Kaydedilecek agent.
        """
        self._agents[agent.agent_id] = agent
        logger.info("Agent kaydedildi: %s (%s)", agent.name, agent.agent_id)

    def activate(self, agent_id: str) -> bool:
        """Agent'i aktif eder.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        return self._transition(agent_id, AgentState.ACTIVE)

    def pause(self, agent_id: str) -> bool:
        """Agent'i duraklatir.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        return self._transition(agent_id, AgentState.PAUSED)

    def resume(self, agent_id: str) -> bool:
        """Agent'i devam ettirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        return self._transition(agent_id, AgentState.ACTIVE)

    def mark_error(self, agent_id: str) -> bool:
        """Agent'i hata durumuna alir.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        result = self._transition(agent_id, AgentState.ERROR)
        if result:
            agent.error_count += 1
        return result

    def begin_termination(self, agent_id: str) -> bool:
        """Sonlandirma baslatir.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        return self._transition(agent_id, AgentState.TERMINATING)

    def complete_termination(self, agent_id: str) -> bool:
        """Sonlandirmayi tamamlar.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        return self._transition(agent_id, AgentState.TERMINATED)

    def auto_restart(self, agent_id: str) -> bool:
        """Otomatik yeniden baslatir.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        if agent.state != AgentState.ERROR:
            return False

        if agent.restart_count >= self._max_restarts:
            logger.warning(
                "Maks restart asildi: %s (%d/%d)",
                agent.name, agent.restart_count, self._max_restarts,
            )
            return False

        agent.restart_count += 1
        result = self._transition(agent_id, AgentState.ACTIVE)
        if result:
            logger.info(
                "Otomatik restart: %s (deneme %d/%d)",
                agent.name, agent.restart_count, self._max_restarts,
            )
        return result

    def heartbeat(self, agent_id: str) -> bool:
        """Kalp atisi kaydeder.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        agent.last_heartbeat = datetime.now(timezone.utc)
        return True

    def check_health(self, agent_id: str) -> dict[str, Any]:
        """Saglik kontrol eder.

        Args:
            agent_id: Agent ID.

        Returns:
            Saglik bilgisi.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return {"healthy": False, "reason": "Agent bulunamadi"}

        now = datetime.now(timezone.utc)
        elapsed = (now - agent.last_heartbeat).total_seconds()
        stale = elapsed > self._health_threshold

        healthy = (
            agent.state == AgentState.ACTIVE
            and not stale
            and agent.error_count < self._max_restarts
        )

        return {
            "agent_id": agent_id,
            "healthy": healthy,
            "state": agent.state.value,
            "last_heartbeat_seconds": round(elapsed, 1),
            "stale": stale,
            "error_count": agent.error_count,
            "restart_count": agent.restart_count,
        }

    def get_unhealthy_agents(self) -> list[str]:
        """Sagliksiz agent'lari getirir.

        Returns:
            Agent ID listesi.
        """
        unhealthy: list[str] = []
        for agent_id in self._agents:
            health = self.check_health(agent_id)
            if not health["healthy"] and self._agents[agent_id].state != AgentState.TERMINATED:
                unhealthy.append(agent_id)
        return unhealthy

    def get_agent(self, agent_id: str) -> SpawnedAgent | None:
        """Agent'i getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            SpawnedAgent veya None.
        """
        return self._agents.get(agent_id)

    def get_agents_by_state(
        self, state: AgentState,
    ) -> list[SpawnedAgent]:
        """Duruma gore agent'lari getirir.

        Args:
            state: Agent durumu.

        Returns:
            SpawnedAgent listesi.
        """
        return [a for a in self._agents.values() if a.state == state]

    def get_state_history(
        self, agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Durum gecmisini getirir.

        Args:
            agent_id: Agent filtresi.

        Returns:
            Gecmis listesi.
        """
        if agent_id:
            return [h for h in self._state_history if h["agent_id"] == agent_id]
        return list(self._state_history)

    def _transition(
        self, agent_id: str, new_state: AgentState,
    ) -> bool:
        """Durum gecisi yapar.

        Args:
            agent_id: Agent ID.
            new_state: Yeni durum.

        Returns:
            Basarili ise True.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        valid = _VALID_TRANSITIONS.get(agent.state, [])
        if new_state not in valid:
            logger.warning(
                "Gecersiz gecis: %s %s -> %s",
                agent.name, agent.state.value, new_state.value,
            )
            return False

        old_state = agent.state
        agent.state = new_state

        self._state_history.append({
            "agent_id": agent_id,
            "from_state": old_state.value,
            "to_state": new_state.value,
        })

        return True

    def unregister(self, agent_id: str) -> bool:
        """Agent kaydini siler.

        Args:
            agent_id: Agent ID.

        Returns:
            Basarili ise True.
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    @property
    def managed_count(self) -> int:
        """Yonetilen agent sayisi."""
        return len(self._agents)

    @property
    def active_count(self) -> int:
        """Aktif agent sayisi."""
        return sum(
            1 for a in self._agents.values()
            if a.state == AgentState.ACTIVE
        )
