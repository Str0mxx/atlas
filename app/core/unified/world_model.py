"""ATLAS Dunya Modeli modulu.

Varlik takibi, iliski esleme, durum tahmini,
karsi-olgusal akil yurutme ve zihinsel
simulasyon.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.unified import EntityType, WorldEntity

logger = logging.getLogger(__name__)


class WorldModel:
    """Dunya modeli.

    Sistemin cevresini modelleyerek
    tahmin ve simulasyon yapar.

    Attributes:
        _entities: Dunya varliklari.
        _relationships: Iliski eslestirmeleri.
        _predictions: Tahminler.
        _simulations: Simulasyon kayitlari.
    """

    def __init__(self) -> None:
        """Dunya modelini baslatir."""
        self._entities: dict[str, WorldEntity] = {}
        self._relationships: list[dict[str, Any]] = []
        self._predictions: list[dict[str, Any]] = []
        self._simulations: list[dict[str, Any]] = []
        self._state_snapshots: list[dict[str, Any]] = []

        logger.info("WorldModel baslatildi")

    def add_entity(
        self,
        name: str,
        entity_type: EntityType = EntityType.SYSTEM,
        state: str = "active",
        properties: dict[str, Any] | None = None,
    ) -> WorldEntity:
        """Varlik ekler.

        Args:
            name: Varlik adi.
            entity_type: Varlik turu.
            state: Durum.
            properties: Ozellikler.

        Returns:
            WorldEntity nesnesi.
        """
        entity = WorldEntity(
            name=name,
            entity_type=entity_type,
            state=state,
            properties=properties or {},
        )
        self._entities[entity.entity_id] = entity

        return entity

    def update_entity(
        self,
        entity_id: str,
        state: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """Varlik gunceller.

        Args:
            entity_id: Varlik ID.
            state: Yeni durum.
            properties: Yeni ozellikler.

        Returns:
            Basarili ise True.
        """
        entity = self._entities.get(entity_id)
        if not entity:
            return False

        if state is not None:
            entity.state = state
        if properties:
            entity.properties.update(properties)
        entity.last_updated = datetime.now(timezone.utc)

        return True

    def remove_entity(self, entity_id: str) -> bool:
        """Varlik kaldirir.

        Args:
            entity_id: Varlik ID.

        Returns:
            Basarili ise True.
        """
        if entity_id in self._entities:
            # Iliskilerini de kaldir
            self._relationships = [
                r for r in self._relationships
                if r["source"] != entity_id and r["target"] != entity_id
            ]
            del self._entities[entity_id]
            return True
        return False

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        strength: float = 0.5,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Iliski ekler.

        Args:
            source_id: Kaynak varlik.
            target_id: Hedef varlik.
            relation_type: Iliski turu.
            strength: Guc (0-1).
            properties: Ozellikler.

        Returns:
            Iliski kaydi veya None.
        """
        if source_id not in self._entities or target_id not in self._entities:
            return None

        rel = {
            "source": source_id,
            "target": target_id,
            "type": relation_type,
            "strength": max(0.0, min(1.0, strength)),
            "properties": properties or {},
        }
        self._relationships.append(rel)

        # Varliklara iliski ekle
        src = self._entities[source_id]
        tgt = self._entities[target_id]
        if target_id not in src.relationships:
            src.relationships.append(target_id)
        if source_id not in tgt.relationships:
            tgt.relationships.append(source_id)

        return rel

    def get_relationships(
        self,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """Varlik iliskilerini getirir.

        Args:
            entity_id: Varlik ID.

        Returns:
            Iliski listesi.
        """
        return [
            r for r in self._relationships
            if r["source"] == entity_id or r["target"] == entity_id
        ]

    def predict_state(
        self,
        entity_id: str,
        time_steps: int = 1,
    ) -> dict[str, Any]:
        """Durum tahmini yapar.

        Args:
            entity_id: Varlik ID.
            time_steps: Ileri adim sayisi.

        Returns:
            Tahmin sonucu.
        """
        entity = self._entities.get(entity_id)
        if not entity:
            return {"success": False, "reason": "Varlik bulunamadi"}

        # Basit tahmin: mevcut durumu temel al
        related = self.get_relationships(entity_id)
        related_states = []
        for r in related:
            other_id = (
                r["target"] if r["source"] == entity_id
                else r["source"]
            )
            other = self._entities.get(other_id)
            if other:
                related_states.append(other.state)

        # Tahmin guven puani
        confidence = round(max(0.3, 1.0 - time_steps * 0.1), 3)

        prediction = {
            "entity_id": entity_id,
            "current_state": entity.state,
            "predicted_state": entity.state,  # stabilite varsayimi
            "time_steps": time_steps,
            "confidence": confidence,
            "related_states": related_states,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._predictions.append(prediction)

        return prediction

    def counterfactual(
        self,
        entity_id: str,
        hypothetical_state: str,
    ) -> dict[str, Any]:
        """Karsi-olgusal akil yurutme.

        Args:
            entity_id: Varlik ID.
            hypothetical_state: Varsayimsal durum.

        Returns:
            Karsi-olgusal analiz.
        """
        entity = self._entities.get(entity_id)
        if not entity:
            return {"success": False, "reason": "Varlik bulunamadi"}

        # Etkilenen varliklari bul
        affected = []
        for r in self.get_relationships(entity_id):
            other_id = (
                r["target"] if r["source"] == entity_id
                else r["source"]
            )
            other = self._entities.get(other_id)
            if other:
                affected.append({
                    "entity_id": other_id,
                    "name": other.name,
                    "current_state": other.state,
                    "relation_type": r["type"],
                    "impact": r["strength"],
                })

        return {
            "entity_id": entity_id,
            "actual_state": entity.state,
            "hypothetical_state": hypothetical_state,
            "affected_entities": affected,
            "total_impact": sum(a["impact"] for a in affected),
        }

    def simulate(
        self,
        scenario: str,
        changes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Zihinsel simulasyon yapar.

        Args:
            scenario: Senaryo adi.
            changes: Varlik ID -> yeni durum eslestirmesi.

        Returns:
            Simulasyon sonucu.
        """
        effective_changes = changes or {}
        effects: list[dict[str, Any]] = []

        for entity_id, new_state in effective_changes.items():
            cf = self.counterfactual(entity_id, new_state)
            if cf.get("success") is not False:
                effects.append(cf)

        simulation = {
            "scenario": scenario,
            "changes": effective_changes,
            "effects": effects,
            "total_entities_affected": sum(
                len(e.get("affected_entities", []))
                for e in effects
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._simulations.append(simulation)

        return simulation

    def take_snapshot(self) -> str:
        """Dunya durumu snapshot'i alir.

        Returns:
            Snapshot ID.
        """
        snap_id = f"world-{len(self._state_snapshots)}"
        self._state_snapshots.append({
            "snapshot_id": snap_id,
            "entities": {
                eid: {
                    "name": e.name,
                    "type": e.entity_type.value,
                    "state": e.state,
                    "properties": dict(e.properties),
                }
                for eid, e in self._entities.items()
            },
            "relationship_count": len(self._relationships),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return snap_id

    def get_entity(self, entity_id: str) -> WorldEntity | None:
        """Varlik getirir.

        Args:
            entity_id: Varlik ID.

        Returns:
            WorldEntity veya None.
        """
        return self._entities.get(entity_id)

    def find_by_type(
        self,
        entity_type: EntityType,
    ) -> list[WorldEntity]:
        """Ture gore varliklari getirir.

        Args:
            entity_type: Varlik turu.

        Returns:
            Varlik listesi.
        """
        return [
            e for e in self._entities.values()
            if e.entity_type == entity_type
        ]

    def find_by_state(self, state: str) -> list[WorldEntity]:
        """Duruma gore varliklari getirir.

        Args:
            state: Durum.

        Returns:
            Varlik listesi.
        """
        return [
            e for e in self._entities.values()
            if e.state == state
        ]

    @property
    def entity_count(self) -> int:
        """Varlik sayisi."""
        return len(self._entities)

    @property
    def relationship_count(self) -> int:
        """Iliski sayisi."""
        return len(self._relationships)

    @property
    def prediction_count(self) -> int:
        """Tahmin sayisi."""
        return len(self._predictions)

    @property
    def simulation_count(self) -> int:
        """Simulasyon sayisi."""
        return len(self._simulations)

    @property
    def snapshot_count(self) -> int:
        """Snapshot sayisi."""
        return len(self._state_snapshots)
