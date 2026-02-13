"""ATLAS Dunya Modelleyici modulu.

Mevcut durumun anlik goruntusu, varlik iliskileri,
kaynak durumlari, kisitlama modelleme ve varsayim takibi.
"""

import logging
from typing import Any

from app.models.simulation import (
    Assumption,
    Constraint,
    EntityState,
    ResourceState,
    ResourceType,
    WorldSnapshot,
)

logger = logging.getLogger(__name__)


class WorldModeler:
    """Dunya modelleyici sistemi.

    Sistemin mevcut durumunu modelleyerek
    simulasyon icin temel olusturur.

    Attributes:
        _entities: Varlik kayitlari.
        _resources: Kaynak durumlari.
        _constraints: Kisitlamalar.
        _assumptions: Varsayimlar.
        _relationships: Varlik iliskileri.
        _snapshots: Gecmis goruntuler.
    """

    def __init__(self) -> None:
        """Dunya modelleyiciyi baslatir."""
        self._entities: dict[str, EntityState] = {}
        self._resources: dict[ResourceType, ResourceState] = {}
        self._constraints: list[Constraint] = []
        self._assumptions: list[Assumption] = []
        self._relationships: dict[str, list[str]] = {}
        self._snapshots: list[WorldSnapshot] = []

        logger.info("WorldModeler baslatildi")

    def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        properties: dict[str, Any] | None = None,
        status: str = "active",
    ) -> EntityState:
        """Varlik ekler.

        Args:
            entity_id: Varlik ID.
            entity_type: Varlik tipi.
            properties: Ozellikler.
            status: Durum.

        Returns:
            EntityState nesnesi.
        """
        entity = EntityState(
            entity_id=entity_id,
            entity_type=entity_type,
            properties=properties or {},
            status=status,
        )
        self._entities[entity_id] = entity
        return entity

    def get_entity(self, entity_id: str) -> EntityState | None:
        """Varlik getirir.

        Args:
            entity_id: Varlik ID.

        Returns:
            EntityState veya None.
        """
        return self._entities.get(entity_id)

    def update_entity(
        self, entity_id: str, properties: dict[str, Any]
    ) -> EntityState | None:
        """Varlik gunceller.

        Args:
            entity_id: Varlik ID.
            properties: Guncellenecek ozellikler.

        Returns:
            Guncellenmis EntityState veya None.
        """
        entity = self._entities.get(entity_id)
        if not entity:
            return None
        entity.properties.update(properties)
        return entity

    def remove_entity(self, entity_id: str) -> bool:
        """Varlik siler.

        Args:
            entity_id: Varlik ID.

        Returns:
            Basarili ise True.
        """
        if entity_id in self._entities:
            del self._entities[entity_id]
            self._relationships.pop(entity_id, None)
            for targets in self._relationships.values():
                if entity_id in targets:
                    targets.remove(entity_id)
            return True
        return False

    def add_relationship(self, source_id: str, target_id: str) -> None:
        """Iliski ekler.

        Args:
            source_id: Kaynak varlik ID.
            target_id: Hedef varlik ID.
        """
        targets = self._relationships.setdefault(source_id, [])
        if target_id not in targets:
            targets.append(target_id)

    def get_relationships(self, entity_id: str) -> list[str]:
        """Iliskileri getirir.

        Args:
            entity_id: Varlik ID.

        Returns:
            Iliskili varlik ID'leri.
        """
        return list(self._relationships.get(entity_id, []))

    def set_resource(
        self,
        resource_type: ResourceType,
        current_usage: float,
        capacity: float = 100.0,
        unit: str = "",
    ) -> ResourceState:
        """Kaynak durumu belirler.

        Args:
            resource_type: Kaynak tipi.
            current_usage: Mevcut kullanim (0-1).
            capacity: Kapasite.
            unit: Birim.

        Returns:
            ResourceState nesnesi.
        """
        available = capacity * (1.0 - current_usage)
        resource = ResourceState(
            resource_type=resource_type,
            current_usage=min(max(current_usage, 0.0), 1.0),
            capacity=capacity,
            available=max(available, 0.0),
            unit=unit,
        )
        self._resources[resource_type] = resource
        return resource

    def get_resource(self, resource_type: ResourceType) -> ResourceState | None:
        """Kaynak durumu getirir.

        Args:
            resource_type: Kaynak tipi.

        Returns:
            ResourceState veya None.
        """
        return self._resources.get(resource_type)

    def add_constraint(
        self,
        name: str,
        description: str = "",
        constraint_type: str = "hard",
        expression: str = "",
    ) -> Constraint:
        """Kisitlama ekler.

        Args:
            name: Kisitlama adi.
            description: Aciklama.
            constraint_type: Tip (hard/soft).
            expression: Ifade.

        Returns:
            Constraint nesnesi.
        """
        constraint = Constraint(
            name=name,
            description=description,
            constraint_type=constraint_type,
            expression=expression,
        )
        self._constraints.append(constraint)
        return constraint

    def check_constraints(self) -> list[Constraint]:
        """Karsilanmayan kisitlamalari getirir.

        Returns:
            Karsilanmayan Constraint listesi.
        """
        return [c for c in self._constraints if not c.is_satisfied]

    def add_assumption(
        self,
        description: str,
        confidence: float = 0.5,
        source: str = "",
    ) -> Assumption:
        """Varsayim ekler.

        Args:
            description: Aciklama.
            confidence: Guven puani.
            source: Kaynak.

        Returns:
            Assumption nesnesi.
        """
        assumption = Assumption(
            description=description,
            confidence=min(max(confidence, 0.0), 1.0),
            source=source,
        )
        self._assumptions.append(assumption)
        return assumption

    def validate_assumption(self, assumption_id: str, is_valid: bool) -> bool:
        """Varsayimi dogrular.

        Args:
            assumption_id: Varsayim ID.
            is_valid: Gecerli mi.

        Returns:
            Bulundu ise True.
        """
        for a in self._assumptions:
            if a.assumption_id == assumption_id:
                a.is_validated = True
                if not is_valid:
                    a.confidence = 0.0
                return True
        return False

    def get_unvalidated_assumptions(self) -> list[Assumption]:
        """Dogrulanmamis varsayimlari getirir.

        Returns:
            Assumption listesi.
        """
        return [a for a in self._assumptions if not a.is_validated]

    def take_snapshot(self, metadata: dict[str, Any] | None = None) -> WorldSnapshot:
        """Anlik goruntu alir.

        Args:
            metadata: Ek metadata.

        Returns:
            WorldSnapshot nesnesi.
        """
        snapshot = WorldSnapshot(
            entities=list(self._entities.values()),
            resources=list(self._resources.values()),
            constraints=list(self._constraints),
            assumptions=list(self._assumptions),
            relationships={k: list(v) for k, v in self._relationships.items()},
            metadata=metadata or {},
        )
        self._snapshots.append(snapshot)
        return snapshot

    def get_latest_snapshot(self) -> WorldSnapshot | None:
        """Son goruntuyu getirir.

        Returns:
            WorldSnapshot veya None.
        """
        return self._snapshots[-1] if self._snapshots else None

    def get_entities_by_type(self, entity_type: str) -> list[EntityState]:
        """Tipe gore varliklari getirir.

        Args:
            entity_type: Varlik tipi.

        Returns:
            EntityState listesi.
        """
        return [e for e in self._entities.values() if e.entity_type == entity_type]

    @property
    def entity_count(self) -> int:
        """Varlik sayisi."""
        return len(self._entities)

    @property
    def snapshot_count(self) -> int:
        """Goruntu sayisi."""
        return len(self._snapshots)

    @property
    def constraint_count(self) -> int:
        """Kisitlama sayisi."""
        return len(self._constraints)
