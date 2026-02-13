"""ATLAS Bilgi Birlestirme modulu.

Coklu kaynak entegrasyonu, catisma cozumu, guven
puanlama, kaynak takibi ve kalite degerlendirmesi.
"""

import logging
from typing import Any

from app.models.knowledge import (
    ConflictResolution,
    FusionResult,
    FusionStrategy,
    KGEntity,
    KGRelation,
    QualityLevel,
)

logger = logging.getLogger(__name__)


class KnowledgeFusion:
    """Bilgi birlestirme sistemi.

    Birden fazla kaynaktan gelen bilgileri birlestirir,
    catismalari cozer ve kaliteyi degerlendirir.

    Attributes:
        _source_trust: Kaynak guven puanlari.
        _fusion_history: Birlestirme gecmisi.
        _conflict_strategy: Catisma cozum stratejisi.
    """

    def __init__(
        self,
        strategy: FusionStrategy = FusionStrategy.TRUST_BASED,
        conflict_resolution: ConflictResolution = ConflictResolution.KEEP_TRUSTED,
    ) -> None:
        """Bilgi birlestirme sistemini baslatir.

        Args:
            strategy: Birlestirme stratejisi.
            conflict_resolution: Catisma cozum yontemi.
        """
        self._strategy = strategy
        self._conflict_resolution = conflict_resolution
        self._source_trust: dict[str, float] = {}
        self._fusion_history: list[FusionResult] = []

        logger.info(
            "KnowledgeFusion baslatildi (strategy=%s, conflict=%s)",
            strategy.value, conflict_resolution.value,
        )

    def set_source_trust(self, source: str, trust: float) -> None:
        """Kaynak guven puanini ayarlar.

        Args:
            source: Kaynak adi.
            trust: Guven puani (0-1).
        """
        self._source_trust[source] = max(0.0, min(1.0, trust))

    def merge_entities(
        self,
        entities_a: list[KGEntity],
        entities_b: list[KGEntity],
        source_a: str = "source_a",
        source_b: str = "source_b",
    ) -> tuple[list[KGEntity], int]:
        """Iki kaynagin varliklarini birlestirir.

        Args:
            entities_a: Birinci kaynak varliklari.
            entities_b: Ikinci kaynak varliklari.
            source_a: Birinci kaynak adi.
            source_b: Ikinci kaynak adi.

        Returns:
            (Birlestirilmis varliklar, catisma sayisi) ikilisi.
        """
        merged: dict[str, KGEntity] = {}
        conflicts = 0

        # Birinci kaynagi ekle
        for entity in entities_a:
            entity.source = source_a
            merged[entity.name.lower()] = entity

        # Ikinci kaynak ile birlestir
        for entity in entities_b:
            entity.source = source_b
            key = entity.name.lower()
            if key in merged:
                conflicts += 1
                resolved = self._resolve_entity_conflict(merged[key], entity, source_a, source_b)
                merged[key] = resolved
            else:
                merged[key] = entity

        return list(merged.values()), conflicts

    def merge_relations(
        self,
        relations_a: list[KGRelation],
        relations_b: list[KGRelation],
    ) -> tuple[list[KGRelation], int]:
        """Iki kaynagin iliskilerini birlestirir.

        Args:
            relations_a: Birinci kaynak iliskileri.
            relations_b: Ikinci kaynak iliskileri.

        Returns:
            (Birlestirilmis iliskiler, catisma sayisi) ikilisi.
        """
        merged: dict[str, KGRelation] = {}
        conflicts = 0

        for rel in relations_a:
            key = f"{rel.source_id}_{rel.relation_type.value}_{rel.target_id}"
            merged[key] = rel

        for rel in relations_b:
            key = f"{rel.source_id}_{rel.relation_type.value}_{rel.target_id}"
            if key in merged:
                conflicts += 1
                # Guc ortalamasini al
                existing = merged[key]
                existing.strength = (existing.strength + rel.strength) / 2
                existing.confidence = max(existing.confidence, rel.confidence)
            else:
                merged[key] = rel

        return list(merged.values()), conflicts

    def _resolve_entity_conflict(
        self,
        entity_a: KGEntity,
        entity_b: KGEntity,
        source_a: str,
        source_b: str,
    ) -> KGEntity:
        """Varlik catismasini cozer.

        Args:
            entity_a: Birinci varlik.
            entity_b: Ikinci varlik.
            source_a: Birinci kaynak.
            source_b: Ikinci kaynak.

        Returns:
            Cozulmus varlik.
        """
        if self._conflict_resolution == ConflictResolution.KEEP_FIRST:
            return entity_a

        elif self._conflict_resolution == ConflictResolution.KEEP_LATEST:
            return entity_b

        elif self._conflict_resolution == ConflictResolution.KEEP_TRUSTED:
            trust_a = self._source_trust.get(source_a, 0.5)
            trust_b = self._source_trust.get(source_b, 0.5)
            return entity_a if trust_a >= trust_b else entity_b

        elif self._conflict_resolution == ConflictResolution.MERGE:
            # Ozellikleri birlestir
            merged = entity_a.model_copy()
            for k, v in entity_b.attributes.items():
                if k not in merged.attributes:
                    merged.attributes[k] = v
            if entity_b.name not in merged.aliases:
                merged.aliases.append(entity_b.name)
            merged.confidence = max(entity_a.confidence, entity_b.confidence)
            return merged

        else:  # FLAG
            entity_a.attributes["_conflict"] = True
            entity_a.attributes["_conflict_source"] = source_b
            return entity_a

    def calculate_trust_score(self, source: str, history: list[dict[str, Any]] | None = None) -> float:
        """Kaynak guven puanini hesaplar.

        Args:
            source: Kaynak adi.
            history: Gecmis dogruluk kayitlari.

        Returns:
            Guven puani (0-1).
        """
        base = self._source_trust.get(source, 0.5)

        if history:
            correct = sum(1 for h in history if h.get("correct", False))
            accuracy = correct / len(history) if history else 0.5
            # Gecmis dogruluk ile agirlikli ortalama
            trust = base * 0.4 + accuracy * 0.6
        else:
            trust = base

        return max(0.0, min(1.0, trust))

    def assess_quality(self, entities: list[KGEntity], relations: list[KGRelation]) -> QualityLevel:
        """Kalite degerlendirmesi yapar.

        Args:
            entities: Varlik listesi.
            relations: Iliski listesi.

        Returns:
            QualityLevel enum degeri.
        """
        if not entities:
            return QualityLevel.UNVERIFIED

        # Ortalama guven
        avg_confidence = sum(e.confidence for e in entities) / len(entities)

        # Kaynak cesitliligi
        sources = {e.source for e in entities if e.source}
        diversity_bonus = min(0.2, len(sources) * 0.05)

        # Iliski zenginligi
        relation_bonus = min(0.1, len(relations) / max(len(entities), 1) * 0.05)

        score = avg_confidence + diversity_bonus + relation_bonus

        if score >= 0.8:
            return QualityLevel.VERIFIED
        elif score >= 0.65:
            return QualityLevel.HIGH
        elif score >= 0.45:
            return QualityLevel.MEDIUM
        elif score >= 0.25:
            return QualityLevel.LOW
        else:
            return QualityLevel.UNVERIFIED

    def fuse(
        self,
        entities_a: list[KGEntity],
        relations_a: list[KGRelation],
        entities_b: list[KGEntity],
        relations_b: list[KGRelation],
        source_a: str = "source_a",
        source_b: str = "source_b",
    ) -> FusionResult:
        """Tam birlestirme islemini yapar.

        Args:
            entities_a: Birinci kaynak varliklari.
            relations_a: Birinci kaynak iliskileri.
            entities_b: Ikinci kaynak varliklari.
            relations_b: Ikinci kaynak iliskileri.
            source_a: Birinci kaynak adi.
            source_b: Ikinci kaynak adi.

        Returns:
            FusionResult nesnesi.
        """
        merged_entities, e_conflicts = self.merge_entities(entities_a, entities_b, source_a, source_b)
        merged_relations, r_conflicts = self.merge_relations(relations_a, relations_b)
        quality = self.assess_quality(merged_entities, merged_relations)

        result = FusionResult(
            strategy=self._strategy,
            entities_merged=len(merged_entities),
            relations_merged=len(merged_relations),
            conflicts_found=e_conflicts + r_conflicts,
            conflicts_resolved=e_conflicts + r_conflicts,
            quality=quality,
            provenance=[source_a, source_b],
        )
        self._fusion_history.append(result)

        logger.info(
            "Birlestirme tamamlandi: %d varlik, %d iliski, %d catisma",
            len(merged_entities), len(merged_relations), e_conflicts + r_conflicts,
        )
        return result

    @property
    def fusion_history(self) -> list[FusionResult]:
        """Birlestirme gecmisi."""
        return list(self._fusion_history)

    @property
    def fusion_count(self) -> int:
        """Toplam birlestirme sayisi."""
        return len(self._fusion_history)
