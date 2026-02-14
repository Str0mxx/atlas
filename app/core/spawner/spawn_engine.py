"""ATLAS Olusturma Motoru modulu.

Sablondan, sifirdan, klonlama ve hibrit
agent olusturma islemleri.
"""

import logging
from typing import Any

from app.models.spawner import (
    AgentState,
    SpawnedAgent,
    SpawnMethod,
)

from app.core.spawner.agent_template import AgentTemplateManager

logger = logging.getLogger(__name__)


class SpawnEngine:
    """Agent olusturma motoru.

    Farkli yontemlerle yeni agent'lar olusturur.

    Attributes:
        _templates: Sablon yoneticisi.
        _spawn_history: Olusturma gecmisi.
        _total_spawned: Toplam olusturulan.
    """

    def __init__(self, templates: AgentTemplateManager) -> None:
        """Olusturma motorunu baslatir.

        Args:
            templates: Sablon yoneticisi.
        """
        self._templates = templates
        self._spawn_history: list[dict[str, Any]] = []
        self._total_spawned: int = 0

        logger.info("SpawnEngine baslatildi")

    def spawn_from_template(
        self,
        template_id: str,
        name: str = "",
        config_overrides: dict[str, Any] | None = None,
    ) -> SpawnedAgent | None:
        """Sablondan agent olusturur.

        Args:
            template_id: Sablon ID.
            name: Agent adi (bos ise sablondan).
            config_overrides: Konfigürasyon üzerine yazma.

        Returns:
            SpawnedAgent veya None.
        """
        tmpl = self._templates.get_template(template_id)
        if not tmpl:
            logger.warning("Sablon bulunamadi: %s", template_id)
            return None

        config = dict(tmpl.config)
        if config_overrides:
            config.update(config_overrides)

        agent = SpawnedAgent(
            name=name or tmpl.name,
            state=AgentState.INITIALIZING,
            spawn_method=SpawnMethod.TEMPLATE,
            template_id=template_id,
            capabilities=list(tmpl.capabilities),
            config=config,
            resources=dict(tmpl.resource_profile),
        )

        self._record_spawn(agent)
        logger.info(
            "Sablondan olusturuldu: %s (tmpl=%s)",
            agent.name, template_id,
        )
        return agent

    def spawn_from_scratch(
        self,
        name: str,
        capabilities: list[str] | None = None,
        config: dict[str, Any] | None = None,
        resources: dict[str, float] | None = None,
    ) -> SpawnedAgent:
        """Sifirdan agent olusturur.

        Args:
            name: Agent adi.
            capabilities: Yetenekler.
            config: Konfigürasyon.
            resources: Kaynaklar.

        Returns:
            SpawnedAgent nesnesi.
        """
        agent = SpawnedAgent(
            name=name,
            state=AgentState.INITIALIZING,
            spawn_method=SpawnMethod.SCRATCH,
            capabilities=capabilities or [],
            config=config or {},
            resources=resources or {},
        )

        self._record_spawn(agent)
        logger.info("Sifirdan olusturuldu: %s", name)
        return agent

    def clone_agent(
        self,
        source: SpawnedAgent,
        name: str = "",
    ) -> SpawnedAgent:
        """Mevcut agent'i klonlar.

        Args:
            source: Kaynak agent.
            name: Yeni agent adi.

        Returns:
            Klonlanmis SpawnedAgent.
        """
        agent = SpawnedAgent(
            name=name or f"{source.name}-clone",
            state=AgentState.INITIALIZING,
            spawn_method=SpawnMethod.CLONE,
            template_id=source.template_id,
            parent_agent_id=source.agent_id,
            capabilities=list(source.capabilities),
            config=dict(source.config),
            resources=dict(source.resources),
            metadata={"cloned_from": source.agent_id},
        )

        self._record_spawn(agent)
        logger.info(
            "Klonlandi: %s <- %s",
            agent.name, source.name,
        )
        return agent

    def spawn_hybrid(
        self,
        template_ids: list[str],
        name: str = "",
    ) -> SpawnedAgent | None:
        """Hibrit agent olusturur (birden fazla sablondan).

        Args:
            template_ids: Sablon ID'leri.
            name: Agent adi.

        Returns:
            SpawnedAgent veya None.
        """
        merged = self._templates.merge_templates(template_ids, name)
        if not merged:
            return None

        agent = SpawnedAgent(
            name=name or merged.name,
            state=AgentState.INITIALIZING,
            spawn_method=SpawnMethod.HYBRID,
            template_id=merged.template_id,
            capabilities=list(merged.capabilities),
            config=dict(merged.config),
            resources=dict(merged.resource_profile),
            metadata={"source_templates": template_ids},
        )

        self._record_spawn(agent)
        logger.info(
            "Hibrit olusturuldu: %s (templates=%s)",
            agent.name, template_ids,
        )
        return agent

    def batch_spawn(
        self,
        template_id: str,
        count: int,
        name_prefix: str = "",
    ) -> list[SpawnedAgent]:
        """Toplu agent olusturur.

        Args:
            template_id: Sablon ID.
            count: Adet.
            name_prefix: Isim on-eki.

        Returns:
            SpawnedAgent listesi.
        """
        agents: list[SpawnedAgent] = []
        prefix = name_prefix or template_id

        for i in range(count):
            agent = self.spawn_from_template(
                template_id=template_id,
                name=f"{prefix}-{i + 1}",
            )
            if agent:
                agents.append(agent)

        logger.info(
            "Toplu olusturma: %d/%d basarili (tmpl=%s)",
            len(agents), count, template_id,
        )
        return agents

    def get_spawn_history(
        self, limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Olusturma gecmisini getirir.

        Args:
            limit: Maks kayit.

        Returns:
            Gecmis listesi.
        """
        return self._spawn_history[-limit:]

    def _record_spawn(self, agent: SpawnedAgent) -> None:
        """Olusturma kaydeder."""
        self._total_spawned += 1
        self._spawn_history.append({
            "agent_id": agent.agent_id,
            "name": agent.name,
            "method": agent.spawn_method.value,
            "template_id": agent.template_id,
        })

    @property
    def total_spawned(self) -> int:
        """Toplam olusturulan agent sayisi."""
        return self._total_spawned
