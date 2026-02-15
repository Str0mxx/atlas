"""ATLAS EntityMem Orkestrator modulu.

Tam varlık yönetimi, çapraz kanal entegrasyon,
sorgu arayüzü, analitik, export/import.
"""

import logging
from typing import Any

from app.core.entitymem.context_provider import (
    EntityContextProvider,
)
from app.core.entitymem.entity_registry import (
    EntityRegistry,
)
from app.core.entitymem.interaction_logger import (
    InteractionLogger,
)
from app.core.entitymem.preference_learner import (
    EntityPreferenceLearner,
)
from app.core.entitymem.privacy_manager import (
    EntityPrivacyManager,
)
from app.core.entitymem.profile_builder import (
    ProfileBuilder,
)
from app.core.entitymem.relationship_mapper import (
    RelationshipMapper,
)
from app.core.entitymem.timeline_builder import (
    TimelineBuilder,
)

logger = logging.getLogger(__name__)


class EntityMemOrchestrator:
    """EntityMem orkestrator.

    Tüm varlık hafızası bileşenlerini koordine eder.

    Attributes:
        registry: Varlık kayıt defteri.
        profiles: Profil oluşturucu.
        interactions: Etkileşim kaydedici.
        relationships: İlişki haritacısı.
        timeline: Zaman çizelgesi.
        preferences: Tercih öğrenici.
        context: Bağlam sağlayıcı.
        privacy: Gizlilik yöneticisi.
    """

    def __init__(
        self,
        retention_days: int = 365,
        privacy_mode: str = "standard",
        max_interactions: int = 10000,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            retention_days: Saklama süresi.
            privacy_mode: Gizlilik modu.
            max_interactions: Maks etkileşim.
        """
        self.registry = EntityRegistry()
        self.profiles = ProfileBuilder()
        self.interactions = InteractionLogger(
            max_stored=max_interactions,
        )
        self.relationships = (
            RelationshipMapper()
        )
        self.timeline = TimelineBuilder()
        self.preferences = (
            EntityPreferenceLearner()
        )
        self.context = EntityContextProvider()
        self.privacy = EntityPrivacyManager(
            retention_days=retention_days,
            privacy_mode=privacy_mode,
        )

        self._stats = {
            "operations": 0,
        }

        logger.info(
            "EntityMemOrchestrator baslatildi",
        )

    def create_entity(
        self,
        name: str,
        entity_type: str = "person",
        properties: dict[str, Any] | None = None,
        profile_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Varlık oluşturur (tam pipeline).

        Args:
            name: Varlık adı.
            entity_type: Varlık tipi.
            properties: Özellikler.
            profile_data: Profil verileri.

        Returns:
            Oluşturma bilgisi.
        """
        # 1) Registry
        creation = self.registry.create_entity(
            name, entity_type, properties,
        )
        eid = creation["entity_id"]

        # 2) Profil
        pdata = profile_data or {}
        pdata["name"] = name
        self.profiles.build_profile(
            eid, pdata, source="creation",
        )

        # 3) Timeline
        self.timeline.add_event(
            eid, "created",
            f"Entity created: {name}",
        )

        self._stats["operations"] += 1

        return {
            "entity_id": eid,
            "name": name,
            "entity_type": entity_type,
            "created": True,
        }

    def record_interaction(
        self,
        entity_id: str,
        channel: str,
        content: str,
        context: dict[str, Any] | None = None,
        sentiment: float = 0.0,
    ) -> dict[str, Any]:
        """Etkileşim kaydeder.

        Args:
            entity_id: Varlık ID.
            channel: Kanal.
            content: İçerik.
            context: Bağlam.
            sentiment: Duygu puanı.

        Returns:
            Kayıt bilgisi.
        """
        # Varlık kontrolü
        entity = self.registry.get_entity(
            entity_id,
        )
        if entity.get("error"):
            return entity

        # Etkileşim logla
        log = self.interactions.log_interaction(
            entity_id, channel, content,
            context, sentiment,
        )

        # Timeline'a ekle
        self.timeline.add_event(
            entity_id, "interaction",
            f"{channel}: {content[:50]}",
        )

        self._stats["operations"] += 1

        return log

    def get_entity_context(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Varlık bağlamı getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Bağlam bilgisi.
        """
        entity = self.registry.get_entity(
            entity_id,
        )
        if entity.get("error"):
            return entity

        # Bileşenleri topla
        recent = self.interactions.get_recent(
            entity_id,
        )
        rels = (
            self.relationships.get_relationships(
                entity_id,
            )
        )
        profile = self.profiles.get_profile(
            entity_id,
        )

        ctx = self.context.get_context(
            entity_id,
            interactions=recent,
            relationships=rels,
            profile=profile,
        )

        self._stats["operations"] += 1

        return ctx

    def query_entity(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Varlık sorgular (tam bilgi).

        Args:
            entity_id: Varlık ID.

        Returns:
            Tam varlık bilgisi.
        """
        entity = self.registry.get_entity(
            entity_id,
        )
        if entity.get("error"):
            return entity

        profile = self.profiles.get_profile(
            entity_id,
        )
        int_count = (
            self.interactions
            .entity_interaction_count(
                entity_id,
            )
        )
        rels = (
            self.relationships.get_relationships(
                entity_id,
            )
        )
        prefs = (
            self.preferences
            .get_all_preferences(entity_id)
        )

        self._stats["operations"] += 1

        return {
            "entity": entity,
            "profile": profile,
            "interaction_count": int_count,
            "relationships": rels,
            "preferences": prefs,
        }

    def export_entity(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Varlık verisi export eder.

        Args:
            entity_id: Varlık ID.

        Returns:
            Export verisi.
        """
        entity = self.registry.get_entity(
            entity_id,
        )
        if entity.get("error"):
            return entity

        profile = self.profiles.get_profile(
            entity_id,
        )
        interactions = (
            self.interactions.get_interactions(
                entity_id,
            )
        )
        rels = (
            self.relationships.get_relationships(
                entity_id,
            )
        )
        timeline = self.timeline.get_timeline(
            entity_id,
        )
        prefs = (
            self.preferences
            .get_all_preferences(entity_id)
        )
        gdpr = self.privacy.get_gdpr_report(
            entity_id,
        )

        return {
            "entity": entity,
            "profile": profile,
            "interactions": interactions,
            "relationships": rels,
            "timeline": timeline,
            "preferences": prefs,
            "privacy": gdpr,
            "exported": True,
        }

    def import_entity(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Varlık verisi import eder.

        Args:
            data: Import verisi.

        Returns:
            Import bilgisi.
        """
        entity_data = data.get("entity", {})
        name = entity_data.get("name", "")
        etype = entity_data.get(
            "entity_type", "person",
        )
        props = entity_data.get(
            "properties", {},
        )

        creation = self.create_entity(
            name, etype, props,
        )
        eid = creation["entity_id"]

        # Profil
        profile_data = data.get("profile", {})
        if profile_data.get("fields"):
            self.profiles.build_profile(
                eid,
                profile_data["fields"],
                source="import",
            )

        return {
            "entity_id": eid,
            "imported": True,
            "name": name,
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "total_entities": (
                self.registry.entity_count
            ),
            "active_entities": (
                self.registry.active_count
            ),
            "total_profiles": (
                self.profiles.profile_count
            ),
            "total_interactions": (
                self.interactions
                .interaction_count
            ),
            "total_relationships": (
                self.relationships
                .relationship_count
            ),
            "timeline_events": (
                self.timeline.event_count
            ),
            "milestones": (
                self.timeline.milestone_count
            ),
            "preferences_learned": (
                self.preferences
                .preference_count
            ),
            "privacy_consents": (
                self.privacy.consent_count
            ),
            "operations": (
                self._stats["operations"]
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "total_entities": (
                self.registry.entity_count
            ),
            "total_interactions": (
                self.interactions
                .interaction_count
            ),
            "total_relationships": (
                self.relationships
                .relationship_count
            ),
            "operations": (
                self._stats["operations"]
            ),
        }

    @property
    def operations(self) -> int:
        """Operasyon sayısı."""
        return self._stats["operations"]
