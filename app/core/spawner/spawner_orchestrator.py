"""ATLAS Spawner Orkestratoru modulu.

Tam yasam dongusu yonetimi, otomatik olcekleme,
yuk bazli olusturma ve hiyerarsi entegrasyonu.
"""

import logging
from typing import Any

from app.models.spawner import (
    AgentState,
    PoolStrategy,
    ResourceType,
    SpawnedAgent,
    SpawnerSnapshot,
    TerminationType,
)

from app.core.spawner.agent_pool import AgentPool
from app.core.spawner.agent_registry import AgentRegistry
from app.core.spawner.agent_template import AgentTemplateManager
from app.core.spawner.capability_injector import CapabilityInjector
from app.core.spawner.lifecycle_manager import LifecycleManager
from app.core.spawner.resource_allocator import ResourceAllocator
from app.core.spawner.spawn_engine import SpawnEngine
from app.core.spawner.termination_handler import TerminationHandler

logger = logging.getLogger(__name__)


class SpawnerOrchestrator:
    """Spawner orkestratoru.

    Tum alt sistemleri koordine eder, tam yasam
    dongusu yonetimi ve otomatik olcekleme saglar.

    Attributes:
        _templates: Sablon yoneticisi.
        _engine: Olusturma motoru.
        _lifecycle: Yasam dongusu yoneticisi.
        _resources: Kaynak tahsisi.
        _capabilities: Yetenek enjeksiyonu.
        _pool: Agent havuzu.
        _termination: Sonlandirma isleyicisi.
        _registry: Agent kayit defteri.
        _max_agents: Maks agent sayisi.
        _auto_scale: Otomatik olcekleme.
    """

    def __init__(
        self,
        max_agents: int = 50,
        pool_size: int = 5,
        auto_scale: bool = True,
        idle_timeout: int = 300,
        spawn_timeout: int = 30,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            max_agents: Maks agent sayisi.
            pool_size: Havuz boyutu.
            auto_scale: Otomatik olcekleme.
            idle_timeout: Bosta kalma zamani (sn).
            spawn_timeout: Olusturma zaman asimi (sn).
        """
        self._templates = AgentTemplateManager()
        self._engine = SpawnEngine(self._templates)
        self._lifecycle = LifecycleManager(max_restarts=3, health_threshold=60)
        self._resources = ResourceAllocator()
        self._capabilities = CapabilityInjector()
        self._pool = AgentPool(
            pool_id="main",
            strategy=PoolStrategy.ELASTIC if auto_scale else PoolStrategy.FIXED,
            target_size=pool_size,
        )
        self._termination = TerminationHandler()
        self._registry = AgentRegistry()

        self._max_agents = max_agents
        self._auto_scale = auto_scale
        self._idle_timeout = idle_timeout
        self._spawn_timeout = spawn_timeout

        logger.info(
            "SpawnerOrchestrator baslatildi "
            "(max=%d, pool=%d, auto_scale=%s)",
            max_agents, pool_size, auto_scale,
        )

    def spawn_agent(
        self,
        template_id: str = "",
        name: str = "",
        capabilities: list[str] | None = None,
        config: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        resources: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Agent olusturur (tam pipeline).

        Args:
            template_id: Sablon ID (bos ise sifirdan).
            name: Agent adi.
            capabilities: Yetenekler.
            config: Konfigürasyon.
            tags: Etiketler.
            resources: Kaynak profili.

        Returns:
            Olusturma sonucu.
        """
        # Limit kontrolu
        if self._registry.count >= self._max_agents:
            return {"success": False, "reason": "Maks agent limitine ulasildi"}

        # Agent olustur
        agent: SpawnedAgent | None = None
        if template_id:
            agent = self._engine.spawn_from_template(
                template_id=template_id,
                name=name,
                config_overrides=config,
            )
        else:
            agent = self._engine.spawn_from_scratch(
                name=name or "Agent",
                capabilities=capabilities,
                config=config,
                resources=resources or {},
            )

        if not agent:
            return {"success": False, "reason": "Agent olusturulamadi"}

        # Ek yetenekler
        if capabilities and template_id:
            for cap in capabilities:
                if cap not in agent.capabilities:
                    agent.capabilities.append(cap)

        # Kaydet
        self._lifecycle.register(agent)
        self._capabilities.register(agent)
        self._registry.register(agent, tags=tags)

        # Kaynak tahsis
        res = resources or agent.resources
        for rtype_str, amount in res.items():
            try:
                rtype = ResourceType(rtype_str)
                self._resources.allocate(agent.agent_id, rtype, amount)
            except (ValueError, KeyError):
                pass

        # Aktif et
        self._lifecycle.activate(agent.agent_id)

        logger.info("Agent spawn: %s (%s)", agent.name, agent.agent_id)
        return {
            "success": True,
            "agent_id": agent.agent_id,
            "name": agent.name,
            "state": agent.state.value,
        }

    def spawn_from_pool(
        self,
        required_capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        """Havuzdan agent alir.

        Args:
            required_capabilities: Gereken yetenekler.

        Returns:
            Atama sonucu.
        """
        agent = self._pool.acquire(required_capabilities)
        if not agent:
            return {"success": False, "reason": "Havuzda uygun agent yok"}

        return {
            "success": True,
            "agent_id": agent.agent_id,
            "name": agent.name,
            "from_pool": True,
        }

    def terminate_agent(
        self,
        agent_id: str,
        force: bool = False,
        reason: str = "",
    ) -> dict[str, Any]:
        """Agent'i sonlandirir.

        Args:
            agent_id: Agent ID.
            force: Zorla sonlandir.
            reason: Neden.

        Returns:
            Sonlandirma sonucu.
        """
        agent = self._registry.get(agent_id)
        if not agent:
            return {"success": False, "reason": "Agent bulunamadi"}

        # Sonlandir
        if force:
            record = self._termination.force_terminate(agent, reason)
        else:
            record = self._termination.graceful_terminate(
                agent, reason, preserve_state=True,
            )

        # Kaynaklari serbest birak
        self._resources.deallocate(agent_id)

        # Lifecycle guncelle
        self._lifecycle.unregister(agent_id)

        # Registry'den cikar
        self._registry.unregister(agent_id)

        # Havuzdan cikar
        self._pool.remove_from_pool(agent_id)

        return {
            "success": True,
            "record_id": record.record_id,
            "type": record.termination_type.value,
            "state_preserved": record.state_preserved,
        }

    def clone_agent(
        self,
        source_agent_id: str,
        name: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Agent'i klonlar.

        Args:
            source_agent_id: Kaynak agent ID.
            name: Yeni agent adi.
            tags: Etiketler.

        Returns:
            Klonlama sonucu.
        """
        source = self._registry.get(source_agent_id)
        if not source:
            return {"success": False, "reason": "Kaynak agent bulunamadi"}

        if self._registry.count >= self._max_agents:
            return {"success": False, "reason": "Maks agent limitine ulasildi"}

        agent = self._engine.clone_agent(source, name)

        # Kaydet
        self._lifecycle.register(agent)
        self._capabilities.register(agent)
        self._registry.register(agent, tags=tags)
        self._lifecycle.activate(agent.agent_id)

        return {
            "success": True,
            "agent_id": agent.agent_id,
            "name": agent.name,
            "cloned_from": source_agent_id,
        }

    def add_capability(
        self,
        agent_id: str,
        capability: str,
    ) -> dict[str, Any]:
        """Agent'a yetenek ekler.

        Args:
            agent_id: Agent ID.
            capability: Yetenek adi.

        Returns:
            Ekleme sonucu.
        """
        change = self._capabilities.add_capability(agent_id, capability)
        if not change:
            return {"success": False, "reason": "Yetenek eklenemedi"}

        # Indeksi guncelle
        agent = self._registry.get(agent_id)
        if agent:
            self._registry.update_capability_index(agent)

        return {
            "success": True,
            "change_id": change.change_id,
            "capability": capability,
        }

    def remove_capability(
        self,
        agent_id: str,
        capability: str,
    ) -> dict[str, Any]:
        """Agent'tan yetenek cikarir.

        Args:
            agent_id: Agent ID.
            capability: Yetenek adi.

        Returns:
            Cikarma sonucu.
        """
        change = self._capabilities.remove_capability(agent_id, capability)
        if not change:
            return {"success": False, "reason": "Yetenek cikarilamadi"}

        agent = self._registry.get(agent_id)
        if agent:
            self._registry.update_capability_index(agent)

        return {
            "success": True,
            "change_id": change.change_id,
            "capability": capability,
        }

    def auto_scale_check(self) -> list[dict[str, Any]]:
        """Otomatik olcekleme kontrol eder.

        Returns:
            Olcekleme aksiyonlari.
        """
        if not self._auto_scale:
            return []

        actions: list[dict[str, Any]] = []

        # Havuz durumu
        scaling = self._pool.needs_scaling()
        if scaling.get("needs_scale"):
            actions.append({
                "type": "pool_scale",
                "direction": scaling["direction"],
                "amount": scaling.get("deficit", scaling.get("surplus", 0)),
            })

        # Sagliksiz agent'lar
        unhealthy = self._lifecycle.get_unhealthy_agents()
        for agent_id in unhealthy:
            agent = self._lifecycle.get_agent(agent_id)
            if agent and agent.state == AgentState.ERROR:
                restarted = self._lifecycle.auto_restart(agent_id)
                actions.append({
                    "type": "auto_restart",
                    "agent_id": agent_id,
                    "success": restarted,
                })

        return actions

    def get_snapshot(self) -> SpawnerSnapshot:
        """Anlik goruntuyu getirir.

        Returns:
            SpawnerSnapshot nesnesi.
        """
        stats = self._registry.get_statistics()
        state_dist = stats.get("state_distribution", {})

        active = state_dist.get("active", 0)
        paused = state_dist.get("paused", 0)
        error = state_dist.get("error", 0)
        total = stats.get("total_agents", 0)

        # Saglik puani
        health = 1.0
        if total > 0:
            error_ratio = error / total
            health -= error_ratio * 0.5
        if self._termination.total_terminated > 0:
            health -= 0.05 * min(
                self._termination.total_terminated, 5,
            )

        return SpawnerSnapshot(
            total_agents=total,
            active_agents=active,
            paused_agents=paused,
            error_agents=error,
            pool_size=self._pool.total_agents,
            total_spawned=self._engine.total_spawned,
            total_terminated=self._termination.total_terminated,
            avg_workload=stats.get("avg_workload", 0.0),
            health_score=max(0.0, min(1.0, health)),
        )

    def find_agents(
        self,
        capability: str | None = None,
        state: AgentState | None = None,
        tag: str | None = None,
    ) -> list[SpawnedAgent]:
        """Agent'lari arar.

        Args:
            capability: Yetenek filtresi.
            state: Durum filtresi.
            tag: Etiket filtresi.

        Returns:
            SpawnedAgent listesi.
        """
        return self._registry.search(
            state=state,
            capability=capability,
            tag=tag,
        )

    def fill_pool(self, template_id: str = "worker") -> int:
        """Havuzu doldurur.

        Args:
            template_id: Sablon ID.

        Returns:
            Eklenen agent sayisi.
        """
        status = self._pool.get_status()
        deficit = status.target_size - status.total_agents
        added = 0

        for i in range(deficit):
            agent = self._engine.spawn_from_template(
                template_id=template_id,
                name=f"pool-{template_id}-{status.total_agents + i + 1}",
            )
            if agent:
                agent.state = AgentState.PAUSED
                if self._pool.add_to_pool(agent):
                    self._registry.register(agent, tags=["pool"])
                    added += 1

        logger.info("Havuz dolduruldu: %d agent eklendi", added)
        return added

    # Alt sistem erisimi
    @property
    def templates(self) -> AgentTemplateManager:
        """Sablon yoneticisi."""
        return self._templates

    @property
    def engine(self) -> SpawnEngine:
        """Olusturma motoru."""
        return self._engine

    @property
    def lifecycle(self) -> LifecycleManager:
        """Yasam dongusu yoneticisi."""
        return self._lifecycle

    @property
    def resources(self) -> ResourceAllocator:
        """Kaynak tahsisi."""
        return self._resources

    @property
    def capabilities(self) -> CapabilityInjector:
        """Yetenek enjeksiyonu."""
        return self._capabilities

    @property
    def pool(self) -> AgentPool:
        """Agent havuzu."""
        return self._pool

    @property
    def termination(self) -> TerminationHandler:
        """Sonlandirma isleyicisi."""
        return self._termination

    @property
    def registry(self) -> AgentRegistry:
        """Agent kayit defteri."""
        return self._registry
