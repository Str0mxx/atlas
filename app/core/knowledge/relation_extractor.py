"""ATLAS Iliski Cikarma modulu.

Iliski tipleri, guc puanlama, zamansal iliskiler,
nedensel iliskiler ve cift yonlu iliskiler.
"""

import logging
import re
from typing import Any

from app.models.knowledge import KGEntity, KGRelation, RelationType

logger = logging.getLogger(__name__)

# Iliski kaliplari (turkce ve ingilizce)
_RELATION_PATTERNS: dict[RelationType, list[str]] = {
    RelationType.IS_A: ["bir", "turu", "cesidi", "is a", "is an", "type of", "kind of"],
    RelationType.HAS_A: ["sahip", "iceren", "barindiran", "has", "contains", "includes"],
    RelationType.PART_OF: ["parcasi", "bolusu", "bileseni", "part of", "belongs to", "member of"],
    RelationType.CAUSES: ["neden", "sebep", "yol acar", "causes", "leads to", "results in"],
    RelationType.DEPENDS_ON: ["bagimli", "gerektirir", "ihtiyac", "depends on", "requires", "needs"],
    RelationType.RELATED_TO: ["ilgili", "iliskili", "bagli", "related to", "associated", "connected"],
    RelationType.LOCATED_IN: ["bulunur", "konumlu", "yerlesik", "located in", "based in", "situated"],
    RelationType.WORKS_FOR: ["calisan", "calisir", "gorevli", "works for", "employed by"],
    RelationType.PRODUCES: ["uretir", "olusturur", "yapar", "produces", "creates", "generates"],
    RelationType.USES: ["kullanir", "kullanan", "yararlanan", "uses", "utilizes", "employs"],
}

# Cift yonlu iliski tipleri
_BIDIRECTIONAL_TYPES = {RelationType.RELATED_TO}


class RelationExtractor:
    """Iliski cikarma sistemi.

    Metinlerden varliklar arasi iliskileri cikarir,
    tiplendirir ve puanlar.

    Attributes:
        _relations: Cikarilmis iliskiler.
    """

    def __init__(self) -> None:
        """Iliski cikarma sistemini baslatir."""
        self._relations: list[KGRelation] = []

        logger.info("RelationExtractor baslatildi")

    def extract(self, text: str, entities: list[KGEntity]) -> list[KGRelation]:
        """Metinden iliskileri cikarir.

        Args:
            text: Giris metni.
            entities: Metindeki varliklar.

        Returns:
            Cikarilmis iliski listesi.
        """
        relations: list[KGRelation] = []

        if len(entities) < 2:
            return relations

        text_lower = text.lower()

        # Her varlik cifti icin iliski ara
        for i, src in enumerate(entities):
            for j, tgt in enumerate(entities):
                if i == j:
                    continue

                rel_type, strength = self._detect_relation(text_lower, src.name, tgt.name)
                if rel_type:
                    relation = KGRelation(
                        relation_type=rel_type,
                        source_id=src.id,
                        target_id=tgt.id,
                        strength=strength,
                        bidirectional=rel_type in _BIDIRECTIONAL_TYPES,
                        confidence=strength * 0.8,
                    )
                    relations.append(relation)
                    self._relations.append(relation)

        logger.info("Iliski cikarma: %d iliski bulundu", len(relations))
        return relations

    def _detect_relation(self, text: str, source_name: str, target_name: str) -> tuple[RelationType | None, float]:
        """Iki varlik arasi iliskiyi tespit eder.

        Args:
            text: Kucuk harfli metin.
            source_name: Kaynak varlik adi.
            target_name: Hedef varlik adi.

        Returns:
            (Iliski tipi, guc) ikilisi veya (None, 0).
        """
        src = source_name.lower()
        tgt = target_name.lower()

        src_idx = text.find(src)
        tgt_idx = text.find(tgt)

        if src_idx < 0 or tgt_idx < 0:
            return None, 0.0

        # Iki varlik arasindaki metin
        if src_idx < tgt_idx:
            between = text[src_idx + len(src):tgt_idx]
        else:
            between = text[tgt_idx + len(tgt):src_idx]

        # Kalip eslestirme
        best_type: RelationType | None = None
        best_score = 0.0

        for rel_type, patterns in _RELATION_PATTERNS.items():
            for pattern in patterns:
                if pattern in between:
                    # Yakinlik bazli puanlama
                    distance = abs(tgt_idx - src_idx)
                    score = max(0.3, 1.0 - distance / 200)
                    if score > best_score:
                        best_score = score
                        best_type = rel_type

        return best_type, best_score

    def score_relation_strength(self, relation: KGRelation, context: dict[str, Any] | None = None) -> float:
        """Iliski gucunu puanlar.

        Args:
            relation: Iliski nesnesi.
            context: Ek baglam bilgisi.

        Returns:
            Guc puani (0-1).
        """
        base = relation.strength

        # Baglam bazli bonus
        if context:
            if context.get("frequency", 0) > 3:
                base = min(1.0, base + 0.1)
            if context.get("explicit", False):
                base = min(1.0, base + 0.2)
            if context.get("verified", False):
                base = min(1.0, base + 0.15)

        return max(0.0, min(1.0, base))

    def create_temporal_relation(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationType,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> KGRelation:
        """Zamansal iliski olusturur.

        Args:
            source_id: Kaynak varlik ID.
            target_id: Hedef varlik ID.
            rel_type: Iliski tipi.
            start_time: Baslangic zamani (ISO format).
            end_time: Bitis zamani (ISO format).

        Returns:
            KGRelation nesnesi.
        """
        from datetime import datetime, timezone

        relation = KGRelation(
            relation_type=rel_type,
            source_id=source_id,
            target_id=target_id,
            temporal=True,
            start_time=datetime.fromisoformat(start_time) if start_time else None,
            end_time=datetime.fromisoformat(end_time) if end_time else None,
        )
        self._relations.append(relation)
        return relation

    def create_causal_relation(
        self,
        cause_id: str,
        effect_id: str,
        strength: float = 0.5,
    ) -> KGRelation:
        """Nedensel iliski olusturur.

        Args:
            cause_id: Neden varlik ID.
            effect_id: Sonuc varlik ID.
            strength: Iliski gucu.

        Returns:
            KGRelation nesnesi.
        """
        relation = KGRelation(
            relation_type=RelationType.CAUSES,
            source_id=cause_id,
            target_id=effect_id,
            strength=max(0.0, min(1.0, strength)),
            attributes={"causal": True},
        )
        self._relations.append(relation)
        return relation

    def create_bidirectional_relation(
        self,
        entity_a_id: str,
        entity_b_id: str,
        rel_type: RelationType = RelationType.RELATED_TO,
        strength: float = 0.5,
    ) -> KGRelation:
        """Cift yonlu iliski olusturur.

        Args:
            entity_a_id: Birinci varlik ID.
            entity_b_id: Ikinci varlik ID.
            rel_type: Iliski tipi.
            strength: Iliski gucu.

        Returns:
            KGRelation nesnesi.
        """
        relation = KGRelation(
            relation_type=rel_type,
            source_id=entity_a_id,
            target_id=entity_b_id,
            bidirectional=True,
            strength=max(0.0, min(1.0, strength)),
        )
        self._relations.append(relation)
        return relation

    @property
    def relations(self) -> list[KGRelation]:
        """Tum iliskiler."""
        return list(self._relations)

    @property
    def relation_count(self) -> int:
        """Toplam iliski sayisi."""
        return len(self._relations)
