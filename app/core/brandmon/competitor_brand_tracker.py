"""ATLAS Rakip Marka Takipçisi modülü.

Rakip izleme, ses payı,
duygu karşılaştırma, kampanya tespiti,
konumlandırma analizi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CompetitorBrandTracker:
    """Rakip marka takipçisi.

    Rakip markaları izler ve karşılaştırır.

    Attributes:
        _competitors: Rakip kayıtları.
        _campaigns: Kampanya kayıtları.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._competitors: dict[
            str, dict[str, Any]
        ] = {}
        self._mentions: dict[
            str, int
        ] = {}
        self._campaigns: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "competitors_tracked": 0,
            "campaigns_detected": 0,
        }

        logger.info(
            "CompetitorBrandTracker "
            "baslatildi",
        )

    def monitor_competitor(
        self,
        competitor: str,
        industry: str = "",
        mentions: int = 0,
        sentiment_score: float = 0.5,
    ) -> dict[str, Any]:
        """Rakip izler.

        Args:
            competitor: Rakip.
            industry: Sektör.
            mentions: Bahsedilme.
            sentiment_score: Duygu puanı.

        Returns:
            İzleme bilgisi.
        """
        self._competitors[competitor] = {
            "name": competitor,
            "industry": industry,
            "mentions": mentions,
            "sentiment_score": sentiment_score,
            "timestamp": time.time(),
        }
        self._mentions[competitor] = mentions
        self._stats[
            "competitors_tracked"
        ] += 1

        return {
            "competitor": competitor,
            "mentions": mentions,
            "monitored": True,
        }

    def calculate_share_of_voice(
        self,
        brand: str,
        brand_mentions: int = 0,
    ) -> dict[str, Any]:
        """Ses payı hesaplar.

        Args:
            brand: Marka.
            brand_mentions: Marka bahsedilme.

        Returns:
            Ses payı bilgisi.
        """
        total = brand_mentions + sum(
            self._mentions.values(),
        )
        if total == 0:
            return {
                "brand": brand,
                "sov": 0.0,
                "calculated": False,
            }

        sov = round(
            brand_mentions / total * 100, 1,
        )

        competitor_sov = {}
        for comp, cnt in (
            self._mentions.items()
        ):
            competitor_sov[comp] = round(
                cnt / total * 100, 1,
            )

        return {
            "brand": brand,
            "sov": sov,
            "competitor_sov": competitor_sov,
            "total_mentions": total,
            "calculated": True,
        }

    def compare_sentiment(
        self,
        brand: str,
        brand_score: float = 0.5,
    ) -> dict[str, Any]:
        """Duygu karşılaştırma yapar.

        Args:
            brand: Marka.
            brand_score: Marka puanı.

        Returns:
            Karşılaştırma bilgisi.
        """
        comparison = {}
        for comp, data in (
            self._competitors.items()
        ):
            comp_score = data[
                "sentiment_score"
            ]
            diff = round(
                brand_score - comp_score, 2,
            )
            comparison[comp] = {
                "score": comp_score,
                "diff": diff,
                "position": (
                    "ahead" if diff > 0.05
                    else "behind"
                    if diff < -0.05
                    else "equal"
                ),
            }

        return {
            "brand": brand,
            "brand_score": brand_score,
            "comparison": comparison,
            "compared": len(comparison) > 0,
        }

    def detect_campaign(
        self,
        competitor: str,
        mention_spike: int = 0,
        normal_rate: int = 10,
        content_theme: str = "",
    ) -> dict[str, Any]:
        """Kampanya tespit eder.

        Args:
            competitor: Rakip.
            mention_spike: Bahsedilme artışı.
            normal_rate: Normal oran.
            content_theme: İçerik teması.

        Returns:
            Tespit bilgisi.
        """
        is_campaign = (
            mention_spike > normal_rate * 3
        )

        if is_campaign:
            self._counter += 1
            self._campaigns.append({
                "campaign_id": (
                    f"cmp_{self._counter}"
                ),
                "competitor": competitor,
                "spike": mention_spike,
                "theme": content_theme,
                "timestamp": time.time(),
            })
            self._stats[
                "campaigns_detected"
            ] += 1

        return {
            "competitor": competitor,
            "mention_spike": mention_spike,
            "is_campaign": is_campaign,
            "theme": content_theme,
        }

    def analyze_positioning(
        self,
        brand: str,
        brand_score: float = 50.0,
    ) -> dict[str, Any]:
        """Konumlandırma analizi yapar.

        Args:
            brand: Marka.
            brand_score: Marka puanı.

        Returns:
            Analiz bilgisi.
        """
        if not self._competitors:
            return {
                "brand": brand,
                "analyzed": False,
            }

        comp_scores = [
            d["sentiment_score"] * 100
            for d in self._competitors.values()
        ]
        avg_comp = (
            sum(comp_scores)
            / len(comp_scores)
        )
        max_comp = max(comp_scores)

        position = (
            "leader"
            if brand_score > max_comp
            else "challenger"
            if brand_score > avg_comp
            else "follower"
        )

        return {
            "brand": brand,
            "brand_score": brand_score,
            "avg_competitor": round(
                avg_comp, 1,
            ),
            "position": position,
            "analyzed": True,
        }

    @property
    def competitor_count(self) -> int:
        """Rakip sayısı."""
        return len(self._competitors)

    @property
    def campaign_count(self) -> int:
        """Kampanya sayısı."""
        return self._stats[
            "campaigns_detected"
        ]
