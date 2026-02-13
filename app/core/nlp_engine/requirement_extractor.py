"""ATLAS Gereksinim Cikarma modulu.

Fonksiyonel gereksinimler, fonksiyonel olmayan gereksinimler,
kisitlama tespiti, varsayim belirleme ve kabul kriterleri.
"""

import logging
import re
from typing import Any

from app.models.nlp_engine import (
    Requirement,
    RequirementPriority,
    RequirementSet,
    RequirementType,
)

logger = logging.getLogger(__name__)

# Oncelik anahtar kelimeleri
_PRIORITY_KEYWORDS: dict[RequirementPriority, list[str]] = {
    RequirementPriority.MUST: ["mutlaka", "zorunlu", "sart", "gerekli", "must", "required", "essential", "critical"],
    RequirementPriority.SHOULD: ["olmali", "gerekir", "should", "recommended", "important"],
    RequirementPriority.COULD: ["olabilir", "iyi olur", "could", "nice to have", "optional", "ideally"],
    RequirementPriority.WONT: ["degil", "olmayacak", "wont", "excluded", "out of scope"],
}

# Fonksiyonel olmayan gereksinim isaretleri
_NFR_MARKERS: dict[str, str] = {
    "performans": "performance",
    "hiz": "performance",
    "gecikme": "performance",
    "guvenlik": "security",
    "sifreleme": "security",
    "yetkilendirme": "security",
    "olceklenebilir": "scalability",
    "yuklenme": "scalability",
    "erisilebilir": "availability",
    "uptime": "availability",
    "bakim": "maintainability",
    "test": "testability",
    "performance": "performance",
    "latency": "performance",
    "security": "security",
    "encryption": "security",
    "scalab": "scalability",
    "availab": "availability",
    "maintain": "maintainability",
}

# Kisitlama isaretleri
_CONSTRAINT_MARKERS = [
    "en fazla", "en az", "maksimum", "minimum", "sinir",
    "limit", "kisit", "olmamali", "yasak", "izin verilmez",
    "at most", "at least", "maximum", "minimum", "must not",
    "cannot", "forbidden", "restricted", "constraint",
]


class RequirementExtractor:
    """Gereksinim cikarma sistemi.

    Dogal dil metinlerinden fonksiyonel ve fonksiyonel olmayan
    gereksinimleri, kisitlamalari, varsayimlari ve kabul
    kriterlerini cikarir.

    Attributes:
        _requirement_sets: Gereksinim setleri (id -> RequirementSet).
    """

    def __init__(self) -> None:
        """Gereksinim cikarma sistemini baslatir."""
        self._requirement_sets: dict[str, RequirementSet] = {}

        logger.info("RequirementExtractor baslatildi")

    def extract(self, text: str, title: str = "") -> RequirementSet:
        """Metinden gereksinimleri cikarir.

        Metni cumlelere boler ve her cumlenin gereksinim tipini,
        onceligi ve kabul kriterlerini belirler.

        Args:
            text: Analiz edilecek metin.
            title: Gereksinim seti basligi.

        Returns:
            RequirementSet nesnesi.
        """
        sentences = self._split_sentences(text)
        requirements: list[Requirement] = []
        assumptions: list[str] = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            req_type = self._classify_requirement(sentence)
            priority = self._detect_priority(sentence)
            constraints = self._detect_constraints(sentence)
            acceptance = self._generate_acceptance_criteria(sentence, req_type)

            # Varsayim tespiti
            if self._is_assumption(sentence):
                assumptions.append(sentence)
                continue

            req = Requirement(
                description=sentence,
                requirement_type=req_type,
                priority=priority,
                source_text=sentence,
                acceptance_criteria=acceptance,
                constraints=constraints,
            )
            requirements.append(req)

        req_set = RequirementSet(
            title=title or text[:50],
            requirements=requirements,
            assumptions=assumptions,
        )
        self._requirement_sets[req_set.id] = req_set

        func_count = sum(1 for r in requirements if r.requirement_type == RequirementType.FUNCTIONAL)
        nfr_count = sum(1 for r in requirements if r.requirement_type == RequirementType.NON_FUNCTIONAL)
        logger.info(
            "Gereksinimler cikarildi: %d fonksiyonel, %d non-fonksiyonel, %d kisit, %d varsayim",
            func_count, nfr_count,
            sum(1 for r in requirements if r.requirement_type == RequirementType.CONSTRAINT),
            len(assumptions),
        )
        return req_set

    def extract_functional(self, text: str) -> list[Requirement]:
        """Sadece fonksiyonel gereksinimleri cikarir.

        Args:
            text: Analiz edilecek metin.

        Returns:
            Fonksiyonel gereksinimler listesi.
        """
        req_set = self.extract(text)
        return [r for r in req_set.requirements if r.requirement_type == RequirementType.FUNCTIONAL]

    def extract_non_functional(self, text: str) -> list[Requirement]:
        """Sadece fonksiyonel olmayan gereksinimleri cikarir.

        Args:
            text: Analiz edilecek metin.

        Returns:
            Fonksiyonel olmayan gereksinimler listesi.
        """
        req_set = self.extract(text)
        return [r for r in req_set.requirements if r.requirement_type == RequirementType.NON_FUNCTIONAL]

    def _split_sentences(self, text: str) -> list[str]:
        """Metni cumlelere boler.

        Args:
            text: Giris metni.

        Returns:
            Cumle listesi.
        """
        # Nokta, noktali virgul, yeni satir ile bol
        parts = re.split(r"[.\n;]+", text)
        # Virgul ile de bol (eger yeterince uzunsa)
        result: list[str] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            comma_parts = [p.strip() for p in part.split(",") if p.strip()]
            if len(comma_parts) > 1 and all(len(p.split()) >= 3 for p in comma_parts):
                result.extend(comma_parts)
            else:
                result.append(part)
        return result

    def _classify_requirement(self, sentence: str) -> RequirementType:
        """Gereksinim tipini siniflandirir.

        Args:
            sentence: Cumle.

        Returns:
            Gereksinim tipi.
        """
        lower = sentence.lower()

        # Kisitlama kontrolu
        for marker in _CONSTRAINT_MARKERS:
            if marker in lower:
                return RequirementType.CONSTRAINT

        # NFR kontrolu
        for marker in _NFR_MARKERS:
            if marker in lower:
                return RequirementType.NON_FUNCTIONAL

        # Varsayim kontrolu
        if self._is_assumption(sentence):
            return RequirementType.ASSUMPTION

        return RequirementType.FUNCTIONAL

    def _detect_priority(self, sentence: str) -> RequirementPriority:
        """Onceligi tespit eder.

        Args:
            sentence: Cumle.

        Returns:
            Oncelik seviyesi.
        """
        lower = sentence.lower()

        for priority, keywords in _PRIORITY_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    return priority

        return RequirementPriority.SHOULD

    def _detect_constraints(self, sentence: str) -> list[str]:
        """Kisitlamalari tespit eder.

        Args:
            sentence: Cumle.

        Returns:
            Kisitlamalar listesi.
        """
        constraints: list[str] = []
        lower = sentence.lower()

        for marker in _CONSTRAINT_MARKERS:
            if marker in lower:
                constraints.append(sentence)
                break

        # Sayisal kisitlamalar
        numbers = re.findall(r"\d+\s*(?:ms|saniye|mb|gb|kb|saat|dakika|gun|second|minute|hour|day)", lower)
        for num in numbers:
            constraints.append(f"Sayisal kisit: {num}")

        return constraints

    def _generate_acceptance_criteria(self, sentence: str, req_type: RequirementType) -> list[str]:
        """Kabul kriterleri olusturur.

        Args:
            sentence: Cumle.
            req_type: Gereksinim tipi.

        Returns:
            Kabul kriterleri listesi.
        """
        criteria: list[str] = []

        if req_type == RequirementType.FUNCTIONAL:
            criteria.append(f"'{sentence[:40]}...' fonksiyonu calisir durumda")
            criteria.append("Birim testler gecmeli")

        elif req_type == RequirementType.NON_FUNCTIONAL:
            criteria.append(f"'{sentence[:40]}...' gereksimi karsilaniyor")
            # Performans ise olcum kriteri ekle
            lower = sentence.lower()
            for marker, category in _NFR_MARKERS.items():
                if marker in lower:
                    criteria.append(f"{category} metrikleri kabul edilebilir duzeyde")
                    break

        elif req_type == RequirementType.CONSTRAINT:
            criteria.append(f"Kisit ihlal edilmiyor: {sentence[:50]}")

        return criteria

    def _is_assumption(self, sentence: str) -> bool:
        """Cumlenin varsayim olup olmadigini kontrol eder.

        Args:
            sentence: Cumle.

        Returns:
            Varsayim mi.
        """
        assumption_markers = [
            "varsayilir", "kabul edilir", "farz edelim", "assuming",
            "assumed", "presume", "given that", "varsayim",
        ]
        lower = sentence.lower()
        return any(m in lower for m in assumption_markers)

    def get_requirement_set(self, set_id: str) -> RequirementSet | None:
        """Gereksinim setini getirir.

        Args:
            set_id: Set ID.

        Returns:
            RequirementSet nesnesi veya None.
        """
        return self._requirement_sets.get(set_id)

    @property
    def set_count(self) -> int:
        """Toplam gereksinim seti sayisi."""
        return len(self._requirement_sets)
