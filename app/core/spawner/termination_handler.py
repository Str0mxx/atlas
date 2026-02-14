"""ATLAS Sonlandirma Isleyici modulu.

Nazik sonlandirma, zorla sonlandirma, durum koruma,
temizlik rutinleri ve olum bildirimleri.
"""

import logging
from typing import Any

from app.models.spawner import (
    AgentState,
    SpawnedAgent,
    TerminationRecord,
    TerminationType,
)

logger = logging.getLogger(__name__)


class TerminationHandler:
    """Sonlandirma isleyicisi.

    Agent'lari guvenli sekilde sonlandirir,
    durumlarini korur ve temizlik yapar.

    Attributes:
        _records: Sonlandirma kayitlari.
        _preserved_states: Korunan durumlar.
        _callbacks: Bildirim callback'leri.
    """

    def __init__(self) -> None:
        """Sonlandirma isleyicisini baslatir."""
        self._records: list[TerminationRecord] = []
        self._preserved_states: dict[str, dict[str, Any]] = {}
        self._callbacks: list[Any] = []

        logger.info("TerminationHandler baslatildi")

    def graceful_terminate(
        self,
        agent: SpawnedAgent,
        reason: str = "",
        preserve_state: bool = True,
    ) -> TerminationRecord:
        """Nazik sonlandirma.

        Args:
            agent: Sonlandirilacak agent.
            reason: Sonlandirma nedeni.
            preserve_state: Durumu koru.

        Returns:
            TerminationRecord nesnesi.
        """
        # Durumu koru
        state_preserved = False
        if preserve_state:
            state_preserved = self._preserve_state(agent)

        # Temizlik
        cleanup_done = self._cleanup(agent)

        # Durumu guncelle
        agent.state = AgentState.TERMINATED

        record = TerminationRecord(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            termination_type=TerminationType.GRACEFUL,
            reason=reason or "Nazik sonlandirma",
            state_preserved=state_preserved,
            cleanup_done=cleanup_done,
        )
        self._records.append(record)

        self._notify(record)
        logger.info("Nazik sonlandirma: %s (%s)", agent.name, reason)
        return record

    def force_terminate(
        self,
        agent: SpawnedAgent,
        reason: str = "",
    ) -> TerminationRecord:
        """Zorla sonlandirma.

        Args:
            agent: Sonlandirilacak agent.
            reason: Sonlandirma nedeni.

        Returns:
            TerminationRecord nesnesi.
        """
        agent.state = AgentState.TERMINATED

        record = TerminationRecord(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            termination_type=TerminationType.FORCE,
            reason=reason or "Zorla sonlandirma",
            state_preserved=False,
            cleanup_done=False,
        )
        self._records.append(record)

        self._notify(record)
        logger.warning("Zorla sonlandirma: %s (%s)", agent.name, reason)
        return record

    def timeout_terminate(
        self,
        agent: SpawnedAgent,
        timeout_seconds: int = 0,
    ) -> TerminationRecord:
        """Zaman asimi sonlandirma.

        Args:
            agent: Sonlandirilacak agent.
            timeout_seconds: Zaman asimi suresi.

        Returns:
            TerminationRecord nesnesi.
        """
        state_preserved = self._preserve_state(agent)
        agent.state = AgentState.TERMINATED

        record = TerminationRecord(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            termination_type=TerminationType.TIMEOUT,
            reason=f"Zaman asimi ({timeout_seconds}s)",
            state_preserved=state_preserved,
            cleanup_done=True,
        )
        self._records.append(record)

        self._notify(record)
        return record

    def idle_terminate(
        self,
        agent: SpawnedAgent,
        idle_seconds: int = 0,
    ) -> TerminationRecord:
        """Bosta kalma sonlandirma.

        Args:
            agent: Sonlandirilacak agent.
            idle_seconds: Bosta kalma suresi.

        Returns:
            TerminationRecord nesnesi.
        """
        state_preserved = self._preserve_state(agent)
        cleanup_done = self._cleanup(agent)
        agent.state = AgentState.TERMINATED

        record = TerminationRecord(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            termination_type=TerminationType.IDLE,
            reason=f"Bosta kalma ({idle_seconds}s)",
            state_preserved=state_preserved,
            cleanup_done=cleanup_done,
        )
        self._records.append(record)

        self._notify(record)
        return record

    def error_terminate(
        self,
        agent: SpawnedAgent,
        error: str = "",
    ) -> TerminationRecord:
        """Hata sonlandirma.

        Args:
            agent: Sonlandirilacak agent.
            error: Hata mesaji.

        Returns:
            TerminationRecord nesnesi.
        """
        state_preserved = self._preserve_state(agent)
        agent.state = AgentState.TERMINATED

        record = TerminationRecord(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            termination_type=TerminationType.ERROR,
            reason=f"Hata: {error}",
            state_preserved=state_preserved,
            cleanup_done=False,
        )
        self._records.append(record)

        self._notify(record)
        logger.error("Hata sonlandirma: %s (%s)", agent.name, error)
        return record

    def get_preserved_state(
        self, agent_id: str,
    ) -> dict[str, Any]:
        """Korunan durumu getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Durum sozlugu.
        """
        return dict(self._preserved_states.get(agent_id, {}))

    def get_records(
        self,
        termination_type: TerminationType | None = None,
    ) -> list[TerminationRecord]:
        """Sonlandirma kayitlarini getirir.

        Args:
            termination_type: Tip filtresi.

        Returns:
            TerminationRecord listesi.
        """
        if termination_type:
            return [
                r for r in self._records
                if r.termination_type == termination_type
            ]
        return list(self._records)

    def register_callback(self, callback: Any) -> None:
        """Bildirim callback'i kaydeder.

        Args:
            callback: Callback fonksiyonu.
        """
        self._callbacks.append(callback)

    def _preserve_state(self, agent: SpawnedAgent) -> bool:
        """Agent durumunu korur."""
        self._preserved_states[agent.agent_id] = {
            "name": agent.name,
            "state": agent.state.value,
            "capabilities": list(agent.capabilities),
            "config": dict(agent.config),
            "resources": dict(agent.resources),
            "metadata": dict(agent.metadata),
            "workload": agent.workload,
            "error_count": agent.error_count,
        }
        return True

    def _cleanup(self, agent: SpawnedAgent) -> bool:
        """Temizlik yapar."""
        agent.workload = 0.0
        agent.resources = {}
        return True

    def _notify(self, record: TerminationRecord) -> None:
        """Bildirim gonderir."""
        for cb in self._callbacks:
            try:
                cb(record)
            except Exception as e:
                logger.error("Bildirim hatasi: %s", e)

    @property
    def total_terminated(self) -> int:
        """Toplam sonlandirma sayisi."""
        return len(self._records)

    @property
    def preserved_count(self) -> int:
        """Korunan durum sayisi."""
        return len(self._preserved_states)
