"""
Voice Command Parser - Sesli komut ayrıştırma ve entity çıkarma modülü.

Bu modül sesli komutları parse eder, intent'leri belirler ve entity'leri
çıkarır.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VoiceCommandParser:
    """Sesli komut ayrıştırma ve entity çıkarma sınıfı."""

    def __init__(self) -> None:
        """VoiceCommandParser başlatıcı."""
        self._commands: list[dict] = []
        self._intents: dict[str, dict] = {}
        self._entities: dict[str, list] = {}
        self._stats = {"commands_parsed": 0, "entities_extracted": 0}
        self._supported_langs = ["tr", "en", "de", "fr"]
        logger.info("VoiceCommandParser başlatıldı")

    @property
    def parse_count(self) -> int:
        """Parse edilen komut sayısını döndürür."""
        return self._stats["commands_parsed"]

    @property
    def entity_count(self) -> int:
        """Çıkarılan entity sayısını döndürür."""
        return self._stats["entities_extracted"]

    def parse_command(
        self,
        raw_text: str,
        language: str = "en"
    ) -> dict[str, Any]:
        """
        Ham sesli komutu parse eder.

        Args:
            raw_text: Ham komut metni
            language: Dil kodu

        Returns:
            Parse sonucu (tokenler, intent, güven skoru)
        """
        tokens = raw_text.lower().split()

        # Intent belirleme (basit keyword tabanlı)
        intent = "general"
        if any(kw in tokens for kw in ["turn", "set"]):
            intent = "control"
        elif any(kw in tokens for kw in ["what", "how"]):
            intent = "query"
        elif any(kw in tokens for kw in ["when", "every"]):
            intent = "automation"

        self._stats["commands_parsed"] += 1

        logger.info(
            f"Komut parse edildi: '{raw_text}' -> intent: {intent} "
            f"({language})"
        )

        return {
            "raw_text": raw_text,
            "language": language,
            "tokens": tokens,
            "intent": intent,
            "confidence": 0.85,
            "parsed": True
        }

    def extract_entities(self, raw_text: str) -> dict[str, Any]:
        """
        Metinden entity'leri çıkarır.

        Args:
            raw_text: Ham metin

        Returns:
            Çıkarılan entity'ler
        """
        tokens = raw_text.split()
        entities = []

        # Sayıları tespit et
        for token in tokens:
            if token.isdigit():
                entities.append({"type": "number", "value": token})

        # Bilinen keyword'leri entity olarak işaretle
        known_keywords = [
            "light", "temperature", "alarm", "music", "volume"
        ]
        for token in tokens:
            if token.lower() in known_keywords:
                entities.append({"type": "device", "value": token})

        count = len(entities)
        self._stats["entities_extracted"] += count

        logger.debug(f"{count} entity çıkarıldı: {raw_text}")

        return {
            "raw_text": raw_text,
            "entities": entities,
            "count": count,
            "extracted": True
        }

    def map_intent(
        self,
        raw_text: str,
        available_intents: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Metni mevcut intent'lere eşleştirir.

        Args:
            raw_text: Ham metin
            available_intents: Mevcut intent listesi

        Returns:
            Eşleştirilen intent ve skorlar
        """
        if available_intents is None:
            available_intents = ["control", "query", "automation"]

        tokens = set(raw_text.lower().split())
        scores = {}

        # Basit keyword overlap hesaplama
        intent_keywords = {
            "control": {"turn", "set", "switch", "change"},
            "query": {"what", "how", "when", "where", "who"},
            "automation": {"every", "schedule", "when", "if"}
        }

        best_intent = "general"
        best_score = 0.0

        for intent in available_intents:
            if intent in intent_keywords:
                overlap = len(tokens & intent_keywords[intent])
                score = overlap / len(intent_keywords[intent])
                scores[intent] = score

                if score > best_score:
                    best_score = score
                    best_intent = intent

        logger.debug(
            f"Intent eşleştirildi: {best_intent} (skor: {best_score:.2f})"
        )

        return {
            "raw_text": raw_text,
            "matched_intent": best_intent,
            "score": best_score,
            "all_scores": scores,
            "mapped": True
        }

    def resolve_ambiguity(
        self,
        raw_text: str,
        candidates: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Belirsiz intent'leri çözümler.

        Args:
            raw_text: Ham metin
            candidates: Aday intent'ler

        Returns:
            Çözümlenen intent
        """
        if candidates is None:
            candidates = []

        resolved_intent = "unknown"
        if len(candidates) == 1:
            resolved_intent = candidates[0]
        elif len(candidates) > 1:
            resolved_intent = candidates[0]  # İlkini seç

        logger.debug(
            f"Belirsizlik çözüldü: {resolved_intent} "
            f"({len(candidates)} aday)"
        )

        return {
            "raw_text": raw_text,
            "resolved_intent": resolved_intent,
            "candidates_count": len(candidates),
            "resolved": True
        }

    def detect_language(self, raw_text: str) -> dict[str, Any]:
        """
        Metinden dil tespiti yapar.

        Args:
            raw_text: Ham metin

        Returns:
            Tespit edilen dil
        """
        detected = "en"  # Default

        # Türkçe karakterler
        if any(c in raw_text for c in "ğışöüçĞİŞÖÜÇ"):
            detected = "tr"
        # Almanca karakterler
        elif any(c in raw_text for c in "äöüßÄÖÜ"):
            detected = "de"

        supported = detected in self._supported_langs

        logger.debug(
            f"Dil tespit edildi: {detected} (destekleniyor: {supported})"
        )

        return {
            "raw_text": raw_text,
            "detected_language": detected,
            "supported": supported,
            "detected": True
        }
