"""ATLAS Bilgi Çıkarıcı modülü.

Anahtar gerçek çıkarma, varlık tanıma,
ilişki haritalama, alıntı çıkarma,
veri çıkarma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class InformationExtractor:
    """Bilgi çıkarıcı.

    Kaynaklardan yapılandırılmış bilgi çıkarır.

    Attributes:
        _extractions: Çıkarma geçmişi.
        _entities: Tespit edilen varlıklar.
    """

    def __init__(self) -> None:
        """Çıkarıcıyı başlatır."""
        self._extractions: list[
            dict[str, Any]
        ] = []
        self._entities: list[
            dict[str, Any]
        ] = []
        self._relationships: list[
            dict[str, Any]
        ] = []
        self._quotes: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "extractions": 0,
            "facts_extracted": 0,
            "entities_found": 0,
            "relationships_mapped": 0,
            "quotes_found": 0,
        }

        logger.info(
            "InformationExtractor baslatildi",
        )

    def extract_facts(
        self,
        content: str,
        source_id: str = "",
    ) -> dict[str, Any]:
        """Anahtar gerçekleri çıkarır.

        Args:
            content: İçerik metni.
            source_id: Kaynak ID.

        Returns:
            Çıkarma bilgisi.
        """
        self._counter += 1
        eid = f"ext_{self._counter}"

        # Cümleleri ayır ve gerçek çıkar
        sentences = [
            s.strip() for s in content.split(".")
            if s.strip() and len(s.strip()) > 10
        ]

        facts = []
        for i, sentence in enumerate(
            sentences[:10],
        ):
            fact = {
                "fact_id": f"{eid}_f{i}",
                "content": sentence.strip(),
                "source_id": source_id,
                "confidence": round(
                    0.8 - (i * 0.05), 2,
                ),
                "type": "statement",
            }
            facts.append(fact)
            self._stats["facts_extracted"] += 1

        result = {
            "extraction_id": eid,
            "source_id": source_id,
            "facts": facts,
            "fact_count": len(facts),
            "timestamp": time.time(),
        }
        self._extractions.append(result)
        self._stats["extractions"] += 1

        return result

    def recognize_entities(
        self,
        content: str,
    ) -> dict[str, Any]:
        """Varlık tanıma yapar.

        Args:
            content: İçerik metni.

        Returns:
            Varlık bilgisi.
        """
        entities = []
        words = content.split()

        # Büyük harfle başlayan kelimeleri
        # potansiyel varlık olarak al
        for i, word in enumerate(words):
            clean = word.strip(".,;:!?\"'()")
            if (
                clean
                and clean[0].isupper()
                and len(clean) > 1
                and i > 0
            ):
                entity = {
                    "text": clean,
                    "type": "named_entity",
                    "position": i,
                }
                entities.append(entity)
                self._entities.append(entity)
                self._stats[
                    "entities_found"
                ] += 1

        return {
            "entities": entities,
            "entity_count": len(entities),
        }

    def map_relationships(
        self,
        entities: list[dict[str, Any]],
        context: str = "",
    ) -> dict[str, Any]:
        """İlişki haritalama yapar.

        Args:
            entities: Varlık listesi.
            context: Bağlam.

        Returns:
            İlişki bilgisi.
        """
        relationships = []
        for i in range(len(entities)):
            for j in range(
                i + 1, len(entities),
            ):
                rel = {
                    "source": entities[i].get(
                        "text", "",
                    ),
                    "target": entities[j].get(
                        "text", "",
                    ),
                    "type": "co_occurrence",
                    "context": context[:100],
                }
                relationships.append(rel)
                self._relationships.append(rel)
                self._stats[
                    "relationships_mapped"
                ] += 1

        return {
            "relationships": relationships,
            "count": len(relationships),
        }

    def extract_quotes(
        self,
        content: str,
        source_id: str = "",
    ) -> dict[str, Any]:
        """Alıntı çıkarır.

        Args:
            content: İçerik metni.
            source_id: Kaynak ID.

        Returns:
            Alıntı bilgisi.
        """
        quotes = []
        in_quote = False
        current = ""

        for char in content:
            if char == '"':
                if in_quote and current:
                    quote = {
                        "text": current,
                        "source_id": source_id,
                    }
                    quotes.append(quote)
                    self._quotes.append(quote)
                    self._stats[
                        "quotes_found"
                    ] += 1
                    current = ""
                in_quote = not in_quote
            elif in_quote:
                current += char

        return {
            "quotes": quotes,
            "quote_count": len(quotes),
            "source_id": source_id,
        }

    def extract_data(
        self,
        content: str,
        data_type: str = "numbers",
    ) -> dict[str, Any]:
        """Veri çıkarır.

        Args:
            content: İçerik metni.
            data_type: Veri tipi.

        Returns:
            Veri bilgisi.
        """
        data_points = []

        if data_type == "numbers":
            words = content.split()
            for word in words:
                clean = word.strip(
                    ".,;:!?\"'()$%",
                )
                try:
                    val = float(clean)
                    data_points.append({
                        "value": val,
                        "type": "number",
                        "raw": word,
                    })
                except ValueError:
                    continue

        return {
            "data_points": data_points,
            "count": len(data_points),
            "data_type": data_type,
        }

    def get_all_facts(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Tüm gerçekleri getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Gerçek listesi.
        """
        all_facts = []
        for ext in self._extractions:
            all_facts.extend(
                ext.get("facts", []),
            )
        return all_facts[-limit:]

    def get_entities(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Varlıkları getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Varlık listesi.
        """
        return list(self._entities[-limit:])

    @property
    def extraction_count(self) -> int:
        """Çıkarma sayısı."""
        return self._stats["extractions"]

    @property
    def fact_count(self) -> int:
        """Gerçek sayısı."""
        return self._stats["facts_extracted"]

    @property
    def entity_count(self) -> int:
        """Varlık sayısı."""
        return self._stats["entities_found"]

    @property
    def relationship_count(self) -> int:
        """İlişki sayısı."""
        return self._stats[
            "relationships_mapped"
        ]
