"""ATLAS Cevirmen modulu.

Metin cevirisi, baglam duyarli
ceviri, alan-ozel terimler, ceviri
bellegi ve kalite puanlama.
"""

import logging
from typing import Any

from app.models.localization import (
    LanguageCode,
    TranslationRecord,
)

logger = logging.getLogger(__name__)


class Translator:
    """Cevirmen.

    Metinleri diller arasi cevirir ve
    ceviri bellegi yonetir.

    Attributes:
        _memory: Ceviri bellegi.
        _domain_terms: Alan-ozel terimler.
        _cache: Ceviri onbellegi.
    """

    def __init__(
        self,
        cache_enabled: bool = True,
    ) -> None:
        """Cevirmeni baslatir.

        Args:
            cache_enabled: Onbellek aktif mi.
        """
        self._memory: list[TranslationRecord] = []
        self._domain_terms: dict[
            str, dict[str, dict[str, str]]
        ] = {}
        self._cache: dict[str, str] = {}
        self._cache_enabled = cache_enabled
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info("Translator baslatildi")

    def translate(
        self,
        text: str,
        source: LanguageCode,
        target: LanguageCode,
        domain: str = "general",
        context: str = "",
    ) -> TranslationRecord:
        """Metin cevirir.

        Args:
            text: Kaynak metin.
            source: Kaynak dil.
            target: Hedef dil.
            domain: Alan.
            context: Baglam.

        Returns:
            Ceviri kaydi.
        """
        # Ayni dil
        if source == target:
            return TranslationRecord(
                source_lang=source,
                target_lang=target,
                source_text=text,
                translated_text=text,
                quality_score=1.0,
                domain=domain,
            )

        # Onbellek kontrolu
        cache_key = f"{source.value}:{target.value}:{text}"
        if self._cache_enabled and cache_key in self._cache:
            self._cache_hits += 1
            return TranslationRecord(
                source_lang=source,
                target_lang=target,
                source_text=text,
                translated_text=self._cache[cache_key],
                quality_score=0.9,
                domain=domain,
            )
        self._cache_misses += 1

        # Ceviri bellegi kontrolu
        for mem in self._memory:
            if (
                mem.source_lang == source
                and mem.target_lang == target
                and mem.source_text == text
            ):
                if self._cache_enabled:
                    self._cache[cache_key] = (
                        mem.translated_text
                    )
                return mem

        # Alan-ozel terim kontrolu
        translated = self._apply_domain_terms(
            text, source, target, domain,
        )

        quality = 0.7 if translated != text else 0.5

        record = TranslationRecord(
            source_lang=source,
            target_lang=target,
            source_text=text,
            translated_text=translated,
            quality_score=quality,
            domain=domain,
        )
        self._memory.append(record)

        if self._cache_enabled:
            self._cache[cache_key] = translated

        return record

    def add_to_memory(
        self,
        source_text: str,
        translated_text: str,
        source: LanguageCode,
        target: LanguageCode,
        domain: str = "general",
        quality: float = 1.0,
    ) -> TranslationRecord:
        """Ceviri bellege ekler.

        Args:
            source_text: Kaynak metin.
            translated_text: Cevrilmis metin.
            source: Kaynak dil.
            target: Hedef dil.
            domain: Alan.
            quality: Kalite puani.

        Returns:
            Ceviri kaydi.
        """
        record = TranslationRecord(
            source_lang=source,
            target_lang=target,
            source_text=source_text,
            translated_text=translated_text,
            quality_score=quality,
            domain=domain,
        )
        self._memory.append(record)
        return record

    def add_domain_term(
        self,
        domain: str,
        term: str,
        translations: dict[str, str],
    ) -> None:
        """Alan-ozel terim ekler.

        Args:
            domain: Alan.
            term: Terim.
            translations: Dil -> ceviri eslesmesi.
        """
        if domain not in self._domain_terms:
            self._domain_terms[domain] = {}
        self._domain_terms[domain][term] = translations

    def get_memory_entries(
        self,
        source: LanguageCode | None = None,
        target: LanguageCode | None = None,
    ) -> list[TranslationRecord]:
        """Ceviri bellegi getirir.

        Args:
            source: Kaynak dil filtresi.
            target: Hedef dil filtresi.

        Returns:
            Ceviri kayitlari.
        """
        results = self._memory
        if source:
            results = [
                r for r in results
                if r.source_lang == source
            ]
        if target:
            results = [
                r for r in results
                if r.target_lang == target
            ]
        return results

    def clear_cache(self) -> int:
        """Onbellegi temizler.

        Returns:
            Temizlenen giris sayisi.
        """
        count = len(self._cache)
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        return count

    def _apply_domain_terms(
        self,
        text: str,
        source: LanguageCode,
        target: LanguageCode,
        domain: str,
    ) -> str:
        """Alan-ozel terimleri uygular.

        Args:
            text: Metin.
            source: Kaynak dil.
            target: Hedef dil.
            domain: Alan.

        Returns:
            Terimler uygulanmis metin.
        """
        terms = self._domain_terms.get(domain, {})
        result = text
        for term, translations in terms.items():
            target_term = translations.get(
                target.value, term,
            )
            if term in result:
                result = result.replace(term, target_term)
        return result

    @property
    def memory_count(self) -> int:
        """Bellek kayit sayisi."""
        return len(self._memory)

    @property
    def domain_count(self) -> int:
        """Alan sayisi."""
        return len(self._domain_terms)

    @property
    def cache_hit_rate(self) -> float:
        """Onbellek isabet orani."""
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return round(self._cache_hits / total, 3)
