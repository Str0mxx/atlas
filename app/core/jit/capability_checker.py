"""ATLAS Yetenek Kontrolu modulu.

Mevcut yetenekleri kontrol etme, benzer yetenek bulma,
efor tahmini, bagimlilik analizi ve fizibilite degerlendirmesi.
"""

import logging
from typing import Any

from app.models.jit import (
    CapabilityInfo,
    CapabilityStatus,
    EffortLevel,
    FeasibilityLevel,
)

logger = logging.getLogger(__name__)

# Bilinen yetenek kategorileri
_BUILTIN_CAPABILITIES: dict[str, list[str]] = {
    "server": ["monitor", "ssh", "deploy", "restart", "health"],
    "security": ["scan", "audit", "firewall", "ssl", "auth"],
    "research": ["web_search", "scrape", "analyze", "compare"],
    "marketing": ["google_ads", "campaign", "keywords", "budget"],
    "communication": ["email", "telegram", "notification", "sms"],
    "coding": ["analyze", "generate", "test", "refactor", "debug"],
    "creative": ["content", "copy", "brand", "design"],
    "analysis": ["financial", "market", "competitor", "feasibility"],
    "data": ["database", "csv", "excel", "pdf", "json"],
    "integration": ["api", "webhook", "oauth", "rest", "graphql"],
}


class CapabilityChecker:
    """Yetenek kontrol sistemi.

    Mevcut yetenekleri kontrol eder, benzer yetenekleri bulur,
    uygulama eforunu tahmin eder ve fizibilite degerlendirir.

    Attributes:
        _capabilities: Kayitli yetenekler.
        _custom_capabilities: Ozel eklenen yetenekler.
    """

    def __init__(self) -> None:
        """Yetenek kontrol sistemini baslatir."""
        self._capabilities: dict[str, CapabilityInfo] = {}
        self._custom_capabilities: dict[str, CapabilityInfo] = {}

        logger.info("CapabilityChecker baslatildi")

    def check_exists(self, capability_name: str) -> bool:
        """Yetenegin mevcut olup olmadigini kontrol eder.

        Args:
            capability_name: Yetenek adi.

        Returns:
            Mevcut mu.
        """
        name_lower = capability_name.lower()

        # Kayitli yeteneklerde ara
        if name_lower in self._capabilities:
            return True

        # Ozel yeteneklerde ara
        if name_lower in self._custom_capabilities:
            return True

        # Yerlesik yeteneklerde ara
        for category, keywords in _BUILTIN_CAPABILITIES.items():
            if name_lower == category or name_lower in keywords:
                return True

        return False

    def find_similar(self, query: str, top_k: int = 5) -> list[CapabilityInfo]:
        """Benzer yetenekleri bulur.

        Args:
            query: Arama sorgusu.
            top_k: Maksimum sonuc sayisi.

        Returns:
            Benzerlik puanina gore sirali yetenek listesi.
        """
        results: list[CapabilityInfo] = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Kayitli + ozel yeteneklerde ara
        all_caps = {**self._capabilities, **self._custom_capabilities}
        for name, cap in all_caps.items():
            score = self._calculate_similarity(query_lower, query_words, name, cap)
            if score > 0.0:
                cap_copy = cap.model_copy()
                cap_copy.similarity_score = score
                results.append(cap_copy)

        # Yerlesik yeteneklerden olustur
        for category, keywords in _BUILTIN_CAPABILITIES.items():
            for keyword in keywords:
                full_name = f"{category}_{keyword}"
                score = self._calculate_similarity(query_lower, query_words, full_name, None)
                if score > 0.0:
                    results.append(CapabilityInfo(
                        name=full_name,
                        description=f"{category} - {keyword}",
                        similarity_score=score,
                        status=CapabilityStatus.AVAILABLE,
                    ))

        results.sort(key=lambda c: c.similarity_score, reverse=True)
        return results[:top_k]

    def _calculate_similarity(
        self,
        query: str,
        query_words: set[str],
        name: str,
        cap: CapabilityInfo | None,
    ) -> float:
        """Benzerlik puanini hesaplar."""
        score = 0.0
        name_lower = name.lower()
        name_words = set(name_lower.replace("_", " ").split())

        # Tam eslesme
        if query == name_lower:
            return 1.0

        # Kelime kesisimi
        overlap = query_words & name_words
        if overlap:
            score = len(overlap) / max(len(query_words), len(name_words))

        # Alt string kontrolu
        if query in name_lower or name_lower in query:
            score = max(score, 0.6)

        # Aciklama eslesme
        if cap and cap.description:
            desc_lower = cap.description.lower()
            if query in desc_lower:
                score = max(score, 0.5)
            desc_words = set(desc_lower.split())
            desc_overlap = query_words & desc_words
            if desc_overlap:
                score = max(score, len(desc_overlap) * 0.2)

        return min(1.0, score)

    def estimate_effort(self, requirement: str) -> EffortLevel:
        """Uygulama eforunu tahmin eder.

        Args:
            requirement: Gereksinim aciklamasi.

        Returns:
            EffortLevel enum degeri.
        """
        req_lower = requirement.lower()

        # Karmasiklik gostergeleri
        complex_indicators = ["oauth", "real-time", "streaming", "machine learning", "database migration"]
        hard_indicators = ["webhook", "graphql", "websocket", "batch", "pipeline"]
        moderate_indicators = ["api", "rest", "crud", "report", "export"]
        easy_indicators = ["query", "fetch", "format", "convert", "parse"]

        score = 0
        for ind in complex_indicators:
            if ind in req_lower:
                score += 4
        for ind in hard_indicators:
            if ind in req_lower:
                score += 3
        for ind in moderate_indicators:
            if ind in req_lower:
                score += 2
        for ind in easy_indicators:
            if ind in req_lower:
                score += 1

        # Kelime sayisina gore ek puan
        word_count = len(req_lower.split())
        if word_count > 30:
            score += 2
        elif word_count > 15:
            score += 1

        if score >= 8:
            return EffortLevel.COMPLEX
        elif score >= 6:
            return EffortLevel.HARD
        elif score >= 3:
            return EffortLevel.MODERATE
        elif score >= 1:
            return EffortLevel.EASY
        else:
            return EffortLevel.TRIVIAL

    def analyze_dependencies(self, capability_name: str) -> list[str]:
        """Bagimlilik analizi yapar.

        Args:
            capability_name: Yetenek adi.

        Returns:
            Bagimlilik listesi.
        """
        deps: list[str] = []
        name_lower = capability_name.lower()

        # Yaygin bagimliliklari tespit et
        dep_map: dict[str, list[str]] = {
            "api": ["httpx", "authentication"],
            "database": ["sqlalchemy", "connection_pool"],
            "email": ["gmail_api", "smtp"],
            "webhook": ["fastapi", "hmac_verification"],
            "oauth": ["token_storage", "refresh_handler"],
            "telegram": ["telegram_bot", "async_handler"],
            "scrape": ["playwright", "html_parser"],
            "ml": ["numpy", "model_storage"],
        }

        for key, key_deps in dep_map.items():
            if key in name_lower:
                deps.extend(key_deps)

        # Kayitli yetenegin bagimliliklari
        cap = self._capabilities.get(name_lower) or self._custom_capabilities.get(name_lower)
        if cap:
            deps.extend(cap.dependencies)

        return list(set(deps))

    def assess_feasibility(self, requirement: str, available_resources: dict[str, Any] | None = None) -> FeasibilityLevel:
        """Fizibilite degerlendirmesi yapar.

        Args:
            requirement: Gereksinim aciklamasi.
            available_resources: Mevcut kaynaklar.

        Returns:
            FeasibilityLevel enum degeri.
        """
        effort = self.estimate_effort(requirement)
        score = 1.0

        # Efor bazli azaltma
        effort_penalty = {
            EffortLevel.TRIVIAL: 0.0,
            EffortLevel.EASY: 0.05,
            EffortLevel.MODERATE: 0.15,
            EffortLevel.HARD: 0.3,
            EffortLevel.COMPLEX: 0.5,
        }
        score -= effort_penalty.get(effort, 0.2)

        # Kaynak kontrolu
        if available_resources:
            if not available_resources.get("api_keys_available", True):
                score -= 0.2
            if not available_resources.get("network_access", True):
                score -= 0.3
            if available_resources.get("time_limit_seconds", 0) > 0:
                if available_resources["time_limit_seconds"] < 30:
                    score -= 0.2

        if score >= 0.7:
            return FeasibilityLevel.HIGH
        elif score >= 0.5:
            return FeasibilityLevel.MEDIUM
        elif score >= 0.3:
            return FeasibilityLevel.LOW
        else:
            return FeasibilityLevel.INFEASIBLE

    def register_capability(self, capability: CapabilityInfo) -> None:
        """Yetenek kaydeder.

        Args:
            capability: Yetenek bilgisi.
        """
        self._custom_capabilities[capability.name.lower()] = capability
        logger.info("Yetenek kaydedildi: %s", capability.name)

    def get_capability(self, name: str) -> CapabilityInfo | None:
        """Yetenek bilgisi getirir."""
        name_lower = name.lower()
        return self._capabilities.get(name_lower) or self._custom_capabilities.get(name_lower)

    @property
    def capability_count(self) -> int:
        """Toplam yetenek sayisi."""
        return len(self._capabilities) + len(self._custom_capabilities)

    @property
    def all_capabilities(self) -> list[CapabilityInfo]:
        """Tum yetenekler."""
        return list(self._capabilities.values()) + list(self._custom_capabilities.values())
