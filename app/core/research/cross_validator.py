"""ATLAS Çapraz Doğrulayıcı modülü.

Gerçek doğrulama, kaynak karşılaştırma,
çelişki tespiti, konsensüs bulma,
güven puanlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CrossValidator:
    """Çapraz doğrulayıcı.

    Bilgileri birden fazla kaynakla doğrular.

    Attributes:
        _validations: Doğrulama geçmişi.
        _contradictions: Çelişki kayıtları.
    """

    def __init__(
        self,
        min_sources: int = 2,
        consensus_threshold: float = 0.6,
    ) -> None:
        """Doğrulayıcıyı başlatır.

        Args:
            min_sources: Min kaynak sayısı.
            consensus_threshold: Konsensüs eşiği.
        """
        self._validations: list[
            dict[str, Any]
        ] = []
        self._contradictions: list[
            dict[str, Any]
        ] = []
        self._min_sources = min_sources
        self._consensus_threshold = (
            consensus_threshold
        )
        self._counter = 0
        self._stats = {
            "validations": 0,
            "verified": 0,
            "contradicted": 0,
            "uncertain": 0,
        }

        logger.info(
            "CrossValidator baslatildi",
        )

    def validate_fact(
        self,
        fact: str,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Gerçeği doğrular.

        Args:
            fact: Doğrulanacak gerçek.
            sources: Kaynak bilgileri.

        Returns:
            Doğrulama bilgisi.
        """
        self._counter += 1
        vid = f"val_{self._counter}"

        supporting = 0
        contradicting = 0
        neutral = 0

        for source in sources:
            stance = self._compare_source(
                fact, source,
            )
            if stance == "supports":
                supporting += 1
            elif stance == "contradicts":
                contradicting += 1
            else:
                neutral += 1

        total = len(sources)
        result = self._determine_result(
            supporting, contradicting, total,
        )
        confidence = self._calculate_confidence(
            supporting, contradicting, total,
        )

        validation = {
            "validation_id": vid,
            "fact": fact[:200],
            "result": result,
            "confidence": confidence,
            "supporting_sources": supporting,
            "contradicting_sources": (
                contradicting
            ),
            "neutral_sources": neutral,
            "total_sources": total,
            "timestamp": time.time(),
        }
        self._validations.append(validation)
        self._stats["validations"] += 1

        if result == "verified":
            self._stats["verified"] += 1
        elif result == "contradicted":
            self._stats["contradicted"] += 1
        else:
            self._stats["uncertain"] += 1

        return validation

    def _compare_source(
        self,
        fact: str,
        source: dict[str, Any],
    ) -> str:
        """Kaynağı karşılaştırır."""
        content = source.get(
            "content", source.get("snippet", ""),
        ).lower()
        fact_lower = fact.lower()
        fact_words = fact_lower.split()

        # Basit kelime eşleşme
        matching = sum(
            1 for w in fact_words
            if w in content
            and len(w) > 3
        )
        match_ratio = (
            matching / max(len(fact_words), 1)
        )

        if match_ratio > 0.5:
            return "supports"
        if source.get("contradicts"):
            return "contradicts"
        return "neutral"

    def _determine_result(
        self,
        supporting: int,
        contradicting: int,
        total: int,
    ) -> str:
        """Sonuç belirler."""
        if total == 0:
            return "unverifiable"
        if total < self._min_sources:
            return "uncertain"

        support_ratio = supporting / total
        contradict_ratio = contradicting / total

        if (
            support_ratio
            >= self._consensus_threshold
        ):
            return "verified"
        if (
            contradict_ratio
            >= self._consensus_threshold
        ):
            return "contradicted"
        if support_ratio > contradict_ratio:
            return "likely_true"
        return "uncertain"

    def _calculate_confidence(
        self,
        supporting: int,
        contradicting: int,
        total: int,
    ) -> float:
        """Güven puanı hesaplar."""
        if total == 0:
            return 0.0
        agreement = abs(
            supporting - contradicting,
        )
        confidence = agreement / total
        # Daha fazla kaynak = daha güvenilir
        source_factor = min(total / 5, 1.0)
        return round(
            confidence * source_factor, 3,
        )

    def compare_sources(
        self,
        sources: list[dict[str, Any]],
        topic: str = "",
    ) -> dict[str, Any]:
        """Kaynakları karşılaştırır.

        Args:
            sources: Kaynak listesi.
            topic: Konu.

        Returns:
            Karşılaştırma bilgisi.
        """
        agreements = 0
        disagreements = 0

        for i in range(len(sources)):
            for j in range(
                i + 1, len(sources),
            ):
                s1 = sources[i].get(
                    "content",
                    sources[i].get("snippet", ""),
                )
                s2 = sources[j].get(
                    "content",
                    sources[j].get("snippet", ""),
                )
                if self._texts_agree(s1, s2):
                    agreements += 1
                else:
                    disagreements += 1

        total = agreements + disagreements
        agreement_rate = (
            round(agreements / total * 100, 1)
            if total > 0 else 0.0
        )

        return {
            "topic": topic,
            "source_count": len(sources),
            "agreements": agreements,
            "disagreements": disagreements,
            "agreement_rate": agreement_rate,
        }

    def _texts_agree(
        self,
        text1: str,
        text2: str,
    ) -> bool:
        """İki metin uyuşuyor mu kontrol eder."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return False
        overlap = words1 & words2
        ratio = len(overlap) / min(
            len(words1), len(words2),
        )
        return ratio > 0.3

    def detect_contradictions(
        self,
        facts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Çelişkileri tespit eder.

        Args:
            facts: Gerçek listesi.

        Returns:
            Çelişki listesi.
        """
        contradictions = []
        for i in range(len(facts)):
            for j in range(
                i + 1, len(facts),
            ):
                f1 = facts[i].get("content", "")
                f2 = facts[j].get("content", "")
                if self._are_contradictory(
                    f1, f2,
                ):
                    contradiction = {
                        "fact_1": f1[:100],
                        "fact_2": f2[:100],
                        "type": "potential",
                    }
                    contradictions.append(
                        contradiction,
                    )
                    self._contradictions.append(
                        contradiction,
                    )

        return contradictions

    def _are_contradictory(
        self,
        text1: str,
        text2: str,
    ) -> bool:
        """İki metin çelişiyor mu kontrol eder."""
        negation_words = {
            "not", "never", "no", "neither",
            "none", "isn't", "doesn't",
            "won't", "can't",
        }
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        neg1 = words1 & negation_words
        neg2 = words2 & negation_words

        # Biri olumsuz biri olumlu
        common = words1 & words2
        if len(common) > 2 and (
            bool(neg1) != bool(neg2)
        ):
            return True
        return False

    def find_consensus(
        self,
        facts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Konsensüs bulur.

        Args:
            facts: Gerçek listesi.

        Returns:
            Konsensüs bilgisi.
        """
        if not facts:
            return {
                "consensus_found": False,
                "reason": "no_facts",
            }

        # En çok desteklenen gerçeği bul
        best_fact = max(
            facts,
            key=lambda f: f.get(
                "confidence", 0,
            ),
        )

        return {
            "consensus_found": True,
            "consensus_fact": best_fact.get(
                "content", "",
            ),
            "confidence": best_fact.get(
                "confidence", 0,
            ),
            "total_facts": len(facts),
        }

    def get_validations(
        self,
        result_filter: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Doğrulamaları getirir.

        Args:
            result_filter: Sonuç filtresi.
            limit: Maks kayıt.

        Returns:
            Doğrulama listesi.
        """
        results = self._validations
        if result_filter:
            results = [
                v for v in results
                if v["result"] == result_filter
            ]
        return list(results[-limit:])

    @property
    def validation_count(self) -> int:
        """Doğrulama sayısı."""
        return self._stats["validations"]

    @property
    def verified_count(self) -> int:
        """Doğrulanmış sayısı."""
        return self._stats["verified"]

    @property
    def contradiction_count(self) -> int:
        """Çelişki sayısı."""
        return self._stats["contradicted"]
