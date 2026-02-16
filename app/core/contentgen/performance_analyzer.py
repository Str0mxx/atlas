"""ATLAS İçerik Performans Analizcisi modülü.

Etkileşim metrikleri, dönüşüm takibi,
karşılaştırma analizi, trend tespiti,
öneriler.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ContentPerformanceAnalyzer:
    """İçerik performans analizcisi.

    İçerik performansını analiz eder.

    Attributes:
        _metrics: Metrik kayıtları.
        _trends: Trend kayıtları.
    """

    def __init__(self) -> None:
        """Analizciyı başlatır."""
        self._metrics: dict[
            str, dict[str, Any]
        ] = {}
        self._trends: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "analyses_done": 0,
            "trends_detected": 0,
            "recommendations_made": 0,
        }

        logger.info(
            "ContentPerformanceAnalyzer "
            "baslatildi",
        )

    def track_engagement(
        self,
        content_id: str,
        views: int = 0,
        likes: int = 0,
        shares: int = 0,
        comments: int = 0,
    ) -> dict[str, Any]:
        """Etkileşim takip eder.

        Args:
            content_id: İçerik ID.
            views: Görüntülenme.
            likes: Beğeni.
            shares: Paylaşım.
            comments: Yorum.

        Returns:
            Etkileşim bilgisi.
        """
        total_engagement = (
            likes + shares + comments
        )
        engagement_rate = round(
            total_engagement
            / max(views, 1) * 100, 2,
        )

        metrics = {
            "content_id": content_id,
            "views": views,
            "likes": likes,
            "shares": shares,
            "comments": comments,
            "engagement_rate": engagement_rate,
            "timestamp": time.time(),
        }
        self._metrics[
            content_id
        ] = metrics

        level = (
            "excellent"
            if engagement_rate >= 5.0
            else "good"
            if engagement_rate >= 2.0
            else "average"
            if engagement_rate >= 1.0
            else "poor"
        )

        return {
            "content_id": content_id,
            "engagement_rate": engagement_rate,
            "total_engagement": (
                total_engagement
            ),
            "level": level,
            "tracked": True,
        }

    def track_conversion(
        self,
        content_id: str,
        impressions: int = 0,
        clicks: int = 0,
        conversions: int = 0,
        revenue: float = 0.0,
    ) -> dict[str, Any]:
        """Dönüşüm takip eder.

        Args:
            content_id: İçerik ID.
            impressions: Gösterimler.
            clicks: Tıklamalar.
            conversions: Dönüşümler.
            revenue: Gelir.

        Returns:
            Dönüşüm bilgisi.
        """
        ctr = round(
            clicks / max(impressions, 1)
            * 100, 2,
        )
        conv_rate = round(
            conversions
            / max(clicks, 1) * 100, 2,
        )
        cost_per_conv = round(
            revenue
            / max(conversions, 1), 2,
        )

        self._stats[
            "analyses_done"
        ] += 1

        return {
            "content_id": content_id,
            "ctr": ctr,
            "conversion_rate": conv_rate,
            "revenue": revenue,
            "cost_per_conversion": (
                cost_per_conv
            ),
            "tracked": True,
        }

    def compare_content(
        self,
        content_a_id: str,
        content_b_id: str,
    ) -> dict[str, Any]:
        """İçerik karşılaştırır.

        Args:
            content_a_id: İçerik A ID.
            content_b_id: İçerik B ID.

        Returns:
            Karşılaştırma bilgisi.
        """
        a = self._metrics.get(
            content_a_id, {},
        )
        b = self._metrics.get(
            content_b_id, {},
        )

        if not a or not b:
            return {
                "compared": False,
                "reason": "Missing metrics",
            }

        a_rate = a.get(
            "engagement_rate", 0,
        )
        b_rate = b.get(
            "engagement_rate", 0,
        )

        winner = (
            content_a_id
            if a_rate >= b_rate
            else content_b_id
        )

        return {
            "content_a": content_a_id,
            "content_b": content_b_id,
            "a_engagement": a_rate,
            "b_engagement": b_rate,
            "winner": winner,
            "margin": round(
                abs(a_rate - b_rate), 2,
            ),
            "compared": True,
        }

    def detect_trends(
        self,
        content_ids: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Trend tespit eder.

        Args:
            content_ids: İçerik IDleri.

        Returns:
            Trend bilgisi.
        """
        content_ids = content_ids or list(
            self._metrics.keys(),
        )

        rates = []
        for cid in content_ids:
            m = self._metrics.get(cid)
            if m:
                rates.append(
                    m.get(
                        "engagement_rate", 0,
                    ),
                )

        if len(rates) < 2:
            return {
                "trend": "insufficient_data",
                "data_points": len(rates),
            }

        avg = sum(rates) / len(rates)
        recent = rates[-1]

        trend = (
            "improving"
            if recent > avg
            else "declining"
            if recent < avg * 0.8
            else "stable"
        )

        self._stats[
            "trends_detected"
        ] += 1

        return {
            "trend": trend,
            "average_rate": round(avg, 2),
            "latest_rate": round(recent, 2),
            "data_points": len(rates),
        }

    def recommend(
        self,
        content_id: str,
    ) -> dict[str, Any]:
        """Öneri yapar.

        Args:
            content_id: İçerik ID.

        Returns:
            Öneri bilgisi.
        """
        metrics = self._metrics.get(
            content_id, {},
        )

        recommendations = []

        if not metrics:
            recommendations.append(
                "Start tracking metrics",
            )
        else:
            rate = metrics.get(
                "engagement_rate", 0,
            )
            views = metrics.get("views", 0)
            shares = metrics.get("shares", 0)

            if rate < 1.0:
                recommendations.append(
                    "Improve content quality",
                )
                recommendations.append(
                    "Add more engaging visuals",
                )
            if views < 100:
                recommendations.append(
                    "Increase distribution",
                )
            if shares == 0:
                recommendations.append(
                    "Add share-worthy content",
                )
            if rate >= 5.0:
                recommendations.append(
                    "Replicate this format",
                )

        if not recommendations:
            recommendations.append(
                "Content performing well",
            )

        self._stats[
            "recommendations_made"
        ] += 1

        return {
            "content_id": content_id,
            "recommendations": (
                recommendations
            ),
            "count": len(recommendations),
        }

    def get_metrics(
        self,
        content_id: str,
    ) -> dict[str, Any] | None:
        """Metrik döndürür."""
        return self._metrics.get(
            content_id,
        )

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "analyses_done"
        ]

    @property
    def recommendation_count(self) -> int:
        """Öneri sayısı."""
        return self._stats[
            "recommendations_made"
        ]
