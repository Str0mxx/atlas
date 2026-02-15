"""ATLAS Kaynak Sıralayıcı modülü.

Güvenilirlik puanlama, otorite değerlendirme,
güncellik ağırlığı, önyargı tespiti,
alan uzmanlığı.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SourceRanker:
    """Kaynak sıralayıcı.

    Kaynakları güvenilirlik ve kaliteye göre sıralar.

    Attributes:
        _rankings: Sıralama geçmişi.
        _domain_scores: Alan puanları.
    """

    def __init__(
        self,
        min_credibility: float = 0.3,
    ) -> None:
        """Sıralayıcıyı başlatır.

        Args:
            min_credibility: Minimum güvenilirlik.
        """
        self._rankings: list[
            dict[str, Any]
        ] = []
        self._domain_scores: dict[
            str, float
        ] = {
            "gov": 0.95,
            "edu": 0.9,
            "org": 0.75,
            "com": 0.6,
            "net": 0.5,
            "io": 0.5,
        }
        self._authority_list: dict[
            str, float
        ] = {}
        self._bias_patterns: list[
            dict[str, Any]
        ] = []
        self._min_credibility = min_credibility
        self._counter = 0
        self._stats = {
            "sources_ranked": 0,
            "biases_detected": 0,
            "filtered_out": 0,
        }

        logger.info(
            "SourceRanker baslatildi",
        )

    def rank(
        self,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Kaynakları sıralar.

        Args:
            sources: Kaynak listesi.

        Returns:
            Sıralı kaynak listesi.
        """
        self._counter += 1

        ranked = []
        for source in sources:
            score = self._calculate_score(
                source,
            )
            if score >= self._min_credibility:
                source_copy = dict(source)
                source_copy[
                    "credibility_score"
                ] = score
                source_copy[
                    "credibility_level"
                ] = self._score_to_level(score)
                ranked.append(source_copy)
                self._stats[
                    "sources_ranked"
                ] += 1
            else:
                self._stats["filtered_out"] += 1

        ranked.sort(
            key=lambda s: s[
                "credibility_score"
            ],
            reverse=True,
        )

        self._rankings.append({
            "ranking_id": (
                f"rank_{self._counter}"
            ),
            "input_count": len(sources),
            "output_count": len(ranked),
            "filtered": (
                len(sources) - len(ranked)
            ),
            "timestamp": time.time(),
        })

        return ranked

    def _calculate_score(
        self,
        source: dict[str, Any],
    ) -> float:
        """Güvenilirlik puanı hesaplar."""
        score = 0.5

        # Alan puanı
        url = source.get("url", "")
        for domain, dscore in (
            self._domain_scores.items()
        ):
            if f".{domain}" in url:
                score = dscore
                break

        # Otorite kontrolü
        authority = self._authority_list.get(
            url, None,
        )
        if authority is not None:
            score = (score + authority) / 2

        # Güncellik
        freshness = source.get(
            "freshness", 0.5,
        )
        score = score * 0.7 + freshness * 0.3

        # Önyargı cezası
        bias = self._detect_bias(source)
        if bias["has_bias"]:
            score *= 0.8
            self._stats["biases_detected"] += 1

        return round(
            min(max(score, 0.0), 1.0), 3,
        )

    def _score_to_level(
        self,
        score: float,
    ) -> str:
        """Puan seviyeye çevirir."""
        if score >= 0.9:
            return "authoritative"
        if score >= 0.7:
            return "high"
        if score >= 0.5:
            return "moderate"
        if score >= 0.3:
            return "low"
        return "unreliable"

    def assess_authority(
        self,
        url: str,
        author: str = "",
        citations: int = 0,
    ) -> dict[str, Any]:
        """Otorite değerlendirmesi yapar.

        Args:
            url: URL.
            author: Yazar.
            citations: Atıf sayısı.

        Returns:
            Değerlendirme bilgisi.
        """
        authority = 0.5

        # Alan puanı
        for domain, dscore in (
            self._domain_scores.items()
        ):
            if f".{domain}" in url:
                authority = dscore
                break

        # Atıf etkisi
        if citations > 100:
            authority += 0.2
        elif citations > 10:
            authority += 0.1

        # Yazar etkisi
        if author:
            authority += 0.05

        authority = round(
            min(authority, 1.0), 3,
        )
        self._authority_list[url] = authority

        return {
            "url": url,
            "authority_score": authority,
            "author": author,
            "citations": citations,
        }

    def _detect_bias(
        self,
        source: dict[str, Any],
    ) -> dict[str, Any]:
        """Önyargı tespit eder."""
        content = source.get("snippet", "")
        content_lower = content.lower()

        bias_words = [
            "always", "never", "obviously",
            "clearly", "everyone knows",
        ]
        has_bias = any(
            w in content_lower
            for w in bias_words
        )

        return {
            "has_bias": has_bias,
            "bias_type": (
                "language_bias" if has_bias
                else "none"
            ),
        }

    def add_bias_pattern(
        self,
        name: str,
        keywords: list[str],
        penalty: float = 0.2,
    ) -> dict[str, Any]:
        """Önyargı kalıbı ekler.

        Args:
            name: Kalıp adı.
            keywords: Anahtar kelimeler.
            penalty: Ceza puanı.

        Returns:
            Ekleme bilgisi.
        """
        pattern = {
            "name": name,
            "keywords": keywords,
            "penalty": penalty,
        }
        self._bias_patterns.append(pattern)
        return {"name": name, "added": True}

    def set_domain_score(
        self,
        domain: str,
        score: float,
    ) -> dict[str, Any]:
        """Alan puanı ayarlar.

        Args:
            domain: Alan adı.
            score: Puan.

        Returns:
            Ayarlama bilgisi.
        """
        self._domain_scores[domain] = round(
            min(max(score, 0.0), 1.0), 3,
        )
        return {
            "domain": domain,
            "score": self._domain_scores[domain],
            "set": True,
        }

    def assess_freshness(
        self,
        age_hours: float,
    ) -> dict[str, Any]:
        """Güncellik değerlendirmesi yapar.

        Args:
            age_hours: Yaş (saat).

        Returns:
            Değerlendirme bilgisi.
        """
        if age_hours <= 1:
            freshness = 1.0
        elif age_hours <= 24:
            freshness = 0.9
        elif age_hours <= 168:
            freshness = 0.7
        elif age_hours <= 720:
            freshness = 0.5
        elif age_hours <= 8760:
            freshness = 0.3
        else:
            freshness = 0.1

        return {
            "age_hours": age_hours,
            "freshness_score": freshness,
        }

    def get_rankings(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Sıralamaları getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Sıralama listesi.
        """
        return list(self._rankings[-limit:])

    @property
    def ranked_count(self) -> int:
        """Sıralanan kaynak sayısı."""
        return self._stats["sources_ranked"]

    @property
    def bias_count(self) -> int:
        """Tespit edilen önyargı sayısı."""
        return self._stats["biases_detected"]

    @property
    def filtered_count(self) -> int:
        """Filtrelenen kaynak sayısı."""
        return self._stats["filtered_out"]
