"""ATLAS Varlik Cikarma modulu.

Adlandirilmis varlik tanima, varlik tipleri, varlik
baglama, ortak referans cozumleme ve ozellik cikarma.
"""

import logging
import re
from typing import Any

from app.models.knowledge import EntityType, KGEntity

logger = logging.getLogger(__name__)

# Varlik tip kaliplari
_ENTITY_PATTERNS: dict[EntityType, list[str]] = {
    EntityType.PERSON: ["bay", "bayan", "dr", "prof", "mr", "mrs", "ms"],
    EntityType.ORGANIZATION: ["sirket", "firma", "kurum", "ltd", "a.s.", "inc", "corp", "org", "company"],
    EntityType.LOCATION: ["sehir", "ulke", "bolge", "il", "ilce", "city", "country", "region"],
    EntityType.TECHNOLOGY: ["api", "sdk", "framework", "library", "database", "server", "cloud"],
    EntityType.PRODUCT: ["urun", "paket", "servis", "product", "service", "app"],
    EntityType.EVENT: ["toplanti", "konferans", "etkinlik", "meeting", "event", "conference"],
    EntityType.METRIC: ["kpi", "metrik", "oran", "yuzde", "rate", "score", "metric"],
}


class EntityExtractor:
    """Varlik cikarma sistemi.

    Metinlerden varliklari cikarir, tiplendirir,
    baglar ve ozelliklerini belirler.

    Attributes:
        _entities: Cikarilmis varliklar.
        _aliases: Takma ad -> ana varlik eslesmesi.
    """

    def __init__(self) -> None:
        """Varlik cikarma sistemini baslatir."""
        self._entities: dict[str, KGEntity] = {}
        self._aliases: dict[str, str] = {}

        logger.info("EntityExtractor baslatildi")

    def extract(self, text: str) -> list[KGEntity]:
        """Metinden varliklari cikarir.

        Args:
            text: Giris metni.

        Returns:
            Cikarilmis varlik listesi.
        """
        entities: list[KGEntity] = []

        # Buyuk harfli kelime gruplari (adlandirilmis varliklar)
        named_pattern = r"\b([A-Z][a-zA-ZçğıöşüÇĞİÖŞÜ]+(?:\s+[A-Z][a-zA-ZçğıöşüÇĞİÖŞÜ]+)*)\b"
        matches = re.findall(named_pattern, text)

        for match in matches:
            if len(match) < 2:
                continue
            entity_type = self._classify_entity(match, text)
            entity = KGEntity(
                name=match,
                entity_type=entity_type,
                confidence=0.7 if entity_type != EntityType.CONCEPT else 0.5,
                source="text_extraction",
            )
            entities.append(entity)
            self._entities[entity.id] = entity

        # Tirnak icindeki ifadeler
        quoted = re.findall(r'"([^"]+)"', text) + re.findall(r"'([^']+)'", text)
        for q in quoted:
            if q not in [e.name for e in entities]:
                entity = KGEntity(
                    name=q,
                    entity_type=EntityType.CONCEPT,
                    confidence=0.6,
                    source="quoted_extraction",
                )
                entities.append(entity)
                self._entities[entity.id] = entity

        logger.info("Varlik cikarma: %d varlik bulundu", len(entities))
        return entities

    def _classify_entity(self, name: str, context: str) -> EntityType:
        """Varligin tipini belirler.

        Args:
            name: Varlik adi.
            context: Baglam metni.

        Returns:
            EntityType enum degeri.
        """
        name_lower = name.lower()
        context_lower = context.lower()

        for entity_type, patterns in _ENTITY_PATTERNS.items():
            for pattern in patterns:
                # Adin kendisinde veya yakin baglamda ara
                if pattern in name_lower:
                    return entity_type
                # Varliktan once/sonra gelen kelime
                idx = context_lower.find(name_lower)
                if idx >= 0:
                    window_start = max(0, idx - 30)
                    window_end = min(len(context_lower), idx + len(name_lower) + 30)
                    window = context_lower[window_start:window_end]
                    if pattern in window:
                        return entity_type

        return EntityType.CONCEPT

    def link_entity(self, entity_id: str, canonical_id: str) -> bool:
        """Varligi kanonikal varlika baglar.

        Args:
            entity_id: Baglanacak varlik ID.
            canonical_id: Hedef kanonikal varlik ID.

        Returns:
            Basarili mi.
        """
        if entity_id not in self._entities or canonical_id not in self._entities:
            return False

        entity = self._entities[entity_id]
        canonical = self._entities[canonical_id]

        # Alias olarak ekle
        if entity.name not in canonical.aliases:
            canonical.aliases.append(entity.name)
        self._aliases[entity.name.lower()] = canonical_id

        logger.info("Varlik baglandi: %s -> %s", entity.name, canonical.name)
        return True

    def resolve_coreference(self, text: str, entities: list[KGEntity]) -> dict[str, str]:
        """Ortak referanslari cozer.

        'o', 'bu', 'onlar' gibi zamirleri varliklarla eslestirir.

        Args:
            text: Giris metni.
            entities: Mevcut varlik listesi.

        Returns:
            Zamir -> varlik adi eslesmesi.
        """
        resolutions: dict[str, str] = {}
        pronouns = ["o", "bu", "su", "onlar", "bunlar", "it", "this", "they", "he", "she"]

        if not entities:
            return resolutions

        # En son bahsedilen varligi referans olarak kullan
        last_entity = entities[-1].name

        text_lower = text.lower()
        for pronoun in pronouns:
            pattern = rf"\b{re.escape(pronoun)}\b"
            if re.search(pattern, text_lower):
                resolutions[pronoun] = last_entity

        return resolutions

    def extract_attributes(self, text: str, entity_name: str) -> dict[str, Any]:
        """Varlik ozelliklerini cikarir.

        Args:
            text: Kaynak metin.
            entity_name: Varlik adi.

        Returns:
            Ozellik adi -> deger eslesmesi.
        """
        attributes: dict[str, Any] = {}
        text_lower = text.lower()
        name_lower = entity_name.lower()

        if name_lower not in text_lower:
            return attributes

        # Sayisal deger cikarma
        numbers = re.findall(rf"{re.escape(name_lower)}\s+(\d+(?:\.\d+)?)", text_lower)
        if numbers:
            attributes["numeric_value"] = float(numbers[0])

        # "X olan Y" kalip cikarma
        pattern = rf"(\w+)\s+olan\s+{re.escape(name_lower)}"
        adj_matches = re.findall(pattern, text_lower)
        if adj_matches:
            attributes["adjective"] = adj_matches[0]

        # "X'in Y'si" kalip cikarma
        possession = rf"{re.escape(name_lower)}[''']?(?:n[ıiuü]n|in|un|ün)\s+(\w+)"
        poss_matches = re.findall(possession, text_lower)
        if poss_matches:
            attributes["possession"] = poss_matches[0]

        return attributes

    def get_entity(self, entity_id: str) -> KGEntity | None:
        """Varlik getirir.

        Args:
            entity_id: Varlik ID.

        Returns:
            KGEntity veya None.
        """
        return self._entities.get(entity_id)

    def find_by_name(self, name: str) -> KGEntity | None:
        """Ada gore varlik arar.

        Args:
            name: Varlik adi.

        Returns:
            KGEntity veya None.
        """
        name_lower = name.lower()
        # Alias kontrolu
        if name_lower in self._aliases:
            return self._entities.get(self._aliases[name_lower])
        # Dogrudan arama
        for entity in self._entities.values():
            if entity.name.lower() == name_lower:
                return entity
        return None

    @property
    def entity_count(self) -> int:
        """Toplam varlik sayisi."""
        return len(self._entities)

    @property
    def entities(self) -> list[KGEntity]:
        """Tum varliklar."""
        return list(self._entities.values())
