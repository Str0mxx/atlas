"""ATLAS Niyet Analiz modulu.

Komut siniflandirma, varlik cikarma, baglam anlama,
belirsizlik cozumleme ve coklu tur diyalog islemleri.
"""

import logging
import re
from typing import Any

from app.models.nlp_engine import (
    ConfidenceLevel,
    DialogueTurn,
    Entity,
    EntityType,
    Intent,
    IntentCategory,
)

logger = logging.getLogger(__name__)

# Niyet anahtar kelime haritasi
_INTENT_KEYWORDS: dict[IntentCategory, list[str]] = {
    IntentCategory.CREATE: ["olustur", "yarat", "ekle", "yaz", "kur", "create", "add", "build", "generate", "make"],
    IntentCategory.MODIFY: ["degistir", "guncelle", "duzenle", "modify", "update", "edit", "change", "fix"],
    IntentCategory.DELETE: ["sil", "kaldir", "temizle", "delete", "remove", "drop", "clean"],
    IntentCategory.QUERY: ["goster", "listele", "bul", "ara", "sorgula", "show", "list", "find", "search", "get"],
    IntentCategory.EXECUTE: ["calistir", "baslat", "yurut", "run", "start", "execute", "launch", "deploy"],
    IntentCategory.CONFIGURE: ["ayarla", "yapilandir", "configure", "setup", "set", "enable", "disable"],
    IntentCategory.ANALYZE: ["analiz", "incele", "kontrol", "analyze", "inspect", "check", "review", "audit"],
    IntentCategory.EXPLAIN: ["acikla", "anlat", "nedir", "nasil", "explain", "describe", "what", "how", "why"],
    IntentCategory.DEBUG: ["hata", "debug", "sorun", "problem", "fix", "troubleshoot", "diagnose"],
}

# Varlik kaliplari
_ENTITY_PATTERNS: dict[EntityType, list[str]] = {
    EntityType.AGENT: ["agent", "ajan"],
    EntityType.TOOL: ["tool", "arac"],
    EntityType.MODEL: ["model", "sema"],
    EntityType.API: ["api", "endpoint"],
    EntityType.DATABASE: ["veritabani", "database", "db", "tablo", "table"],
    EntityType.FILE: ["dosya", "file", "modul", "module"],
    EntityType.SERVICE: ["servis", "service", "sunucu", "server"],
    EntityType.CONFIG: ["ayar", "config", "yapilandirma", "setting"],
    EntityType.METRIC: ["metrik", "kpi", "olcum", "metric"],
}


class IntentParser:
    """Niyet analiz sistemi.

    Dogal dil girislerini analiz ederek niyet, varlik ve
    parametreleri cikarir. Belirsizlikleri tespit eder ve
    coklu tur diyalog ile cozumler.

    Attributes:
        _history: Diyalog gecmisi.
        _context: Mevcut baglam.
        _clarification_threshold: Belirsizlik esigi (0.0-1.0).
    """

    def __init__(self, clarification_threshold: float = 0.4) -> None:
        """Niyet analiz sistemini baslatir.

        Args:
            clarification_threshold: Belirsizlik esigi. Bu deger altindaki
                guven niyetin belirsiz oldugunu gosterir.
        """
        self._history: list[DialogueTurn] = []
        self._context: dict[str, Any] = {}
        self._clarification_threshold = max(0.0, min(1.0, clarification_threshold))

        logger.info(
            "IntentParser baslatildi (clarification_threshold=%.2f)",
            self._clarification_threshold,
        )

    def parse(self, text: str) -> Intent:
        """Dogal dil girisini analiz eder.

        Metni niyet kategorisine siniflandirir, varliklari
        cikarir ve guven derecesini hesaplar.

        Args:
            text: Analiz edilecek metin.

        Returns:
            Analiz edilmis Intent nesnesi.
        """
        text_lower = text.lower().strip()

        category, action, cat_confidence = self._classify_command(text_lower)
        entities = self._extract_entities(text_lower)
        context_refs = self._understand_context(text_lower)
        ambiguities = self._detect_ambiguities(text_lower, category, cat_confidence)

        # Varlik guveni ile birlesik guven hesapla
        entity_confidence = (
            sum(e.confidence for e in entities) / len(entities) if entities else 0.5
        )
        confidence = cat_confidence * 0.7 + entity_confidence * 0.3
        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.7:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence >= 0.4:
            confidence_level = ConfidenceLevel.MEDIUM
        elif ambiguities:
            confidence_level = ConfidenceLevel.AMBIGUOUS
        else:
            confidence_level = ConfidenceLevel.LOW

        resolved = len(ambiguities) == 0

        intent = Intent(
            raw_input=text,
            category=category,
            action=action,
            entities=entities,
            confidence=confidence,
            confidence_level=confidence_level,
            context_references=context_refs,
            ambiguities=ambiguities,
            resolved=resolved,
        )

        # Diyalog gecmisine ekle
        turn = DialogueTurn(role="user", content=text, intent=intent)
        self._history.append(turn)

        logger.info(
            "Niyet analiz edildi: kategori=%s, guven=%.2f, varlik=%d, belirsizlik=%d",
            category.value, confidence, len(entities), len(ambiguities),
        )
        return intent

    def _classify_command(self, text: str) -> tuple[IntentCategory, str, float]:
        """Komutu siniflandirir.

        Args:
            text: Kucuk harfli metin.

        Returns:
            (Kategori, eylem, guven) uclusu.
        """
        scores: dict[IntentCategory, float] = {}

        for category, keywords in _INTENT_KEYWORDS.items():
            score = 0.0
            matched_keyword = ""
            for kw in keywords:
                if kw in text:
                    # Tam kelime eslesmesine bonus
                    word_pattern = rf"\b{re.escape(kw)}\b"
                    if re.search(word_pattern, text):
                        score += 1.0
                    else:
                        score += 0.5
                    if not matched_keyword or len(kw) > len(matched_keyword):
                        matched_keyword = kw
            if score > 0:
                scores[category] = score

        if not scores:
            return IntentCategory.UNKNOWN, "", 0.2

        best_category = max(scores, key=scores.get)  # type: ignore[arg-type]
        best_score = scores[best_category]

        # Normalize et
        total = sum(scores.values())
        confidence = best_score / total if total > 0 else 0.0

        # Tek bir kategori varsa yuksek guven
        if len(scores) == 1:
            confidence = min(1.0, confidence + 0.3)

        # Eylemi bul
        action = ""
        for kw in _INTENT_KEYWORDS[best_category]:
            if kw in text:
                action = kw
                break

        return best_category, action, min(1.0, confidence)

    def _extract_entities(self, text: str) -> list[Entity]:
        """Metinden varliklari cikarir.

        Args:
            text: Kucuk harfli metin.

        Returns:
            Cikarilmis varlik listesi.
        """
        entities: list[Entity] = []
        words = text.split()

        for entity_type, patterns in _ENTITY_PATTERNS.items():
            for pattern in patterns:
                for i, word in enumerate(words):
                    if pattern in word:
                        # Sonraki kelimeyi varlik degeri olarak al
                        value = words[i + 1] if i + 1 < len(words) else ""
                        start = text.find(pattern)
                        entity = Entity(
                            name=pattern,
                            entity_type=entity_type,
                            value=value,
                            confidence=0.8 if pattern == word else 0.6,
                            span=(start, start + len(pattern)),
                        )
                        entities.append(entity)
                        break  # Her tip icin ilk eslemeyi al

        return entities

    def _understand_context(self, text: str) -> list[str]:
        """Baglam referanslarini cikarir.

        'o', 'bu', 'onceki', 'son' gibi referanslari tespit eder.

        Args:
            text: Kucuk harfli metin.

        Returns:
            Baglam referanslari listesi.
        """
        context_words = ["bu", "su", "o", "onceki", "son", "ayni", "this", "that", "previous", "last", "same", "it"]
        refs: list[str] = []
        for word in context_words:
            pattern = rf"\b{re.escape(word)}\b"
            if re.search(pattern, text):
                refs.append(word)
        return refs

    def _detect_ambiguities(self, text: str, category: IntentCategory, confidence: float) -> list[str]:
        """Belirsizlikleri tespit eder.

        Args:
            text: Kucuk harfli metin.
            category: Tespit edilen kategori.
            confidence: Guven derecesi.

        Returns:
            Belirsizlik listesi.
        """
        ambiguities: list[str] = []

        if confidence < self._clarification_threshold:
            ambiguities.append("Niyet belirsiz, daha fazla bilgi gerekiyor")

        if category == IntentCategory.UNKNOWN:
            ambiguities.append("Komut kategorisi tespit edilemedi")

        # Cok kisa metin
        if len(text.split()) < 2:
            ambiguities.append("Cok kisa giris, daha fazla detay gerekiyor")

        return ambiguities

    def resolve_ambiguity(self, intent_id: str, clarification: str) -> Intent | None:
        """Belirsizligi cozer.

        Onceki belirsiz niyeti yeni bilgi ile yeniden analiz eder.

        Args:
            intent_id: Orijinal niyet ID.
            clarification: Aciklama metni.

        Returns:
            Guncellenmis Intent nesnesi veya None.
        """
        # Orijinal niyeti bul
        original = None
        for turn in self._history:
            if turn.intent and turn.intent.id == intent_id:
                original = turn.intent
                break

        if not original:
            return None

        # Birlesik metin ile yeniden analiz et
        combined_text = f"{original.raw_input} {clarification}"
        new_intent = self.parse(combined_text)
        new_intent.ambiguities = []
        new_intent.resolved = True

        logger.info("Belirsizlik cozuldu: %s -> %s", intent_id[:8], new_intent.category.value)
        return new_intent

    def add_context(self, key: str, value: Any) -> None:
        """Baglam bilgisi ekler.

        Args:
            key: Baglam anahtari.
            value: Baglam degeri.
        """
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Baglam bilgisi getirir.

        Args:
            key: Baglam anahtari.
            default: Varsayilan deger.

        Returns:
            Baglam degeri.
        """
        return self._context.get(key, default)

    @property
    def history_count(self) -> int:
        """Diyalog gecmisi sayisi."""
        return len(self._history)

    @property
    def history(self) -> list[DialogueTurn]:
        """Diyalog gecmisi."""
        return list(self._history)
