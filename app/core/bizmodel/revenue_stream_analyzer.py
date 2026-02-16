"""
Gelir akışı analizi modülü.

Farklı gelir kaynaklarını analiz eder,
büyüme trendlerini takip eder ve
çeşitlendirme değerlendirmesi yapar.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RevenueStreamAnalyzer:
    """
    Gelir akışı analizci sınıfı.

    Gelir kaynaklarını analiz eder,
    fiyatlandırma değerlendirir ve
    büyüme trendlerini izler.
    """

    def __init__(self) -> None:
        """Analizciyi başlatır."""
        self._streams: list[dict] = []
        self._stats: dict = {
            "analyses_completed": 0
        }

    @property
    def analysis_count(self) -> int:
        """
        Tamamlanan analiz sayısı.

        Returns:
            Analiz sayısı.
        """
        return self._stats[
            "analyses_completed"
        ]

    def analyze_revenue(
        self,
        streams: (
            list[dict[str, Any]] | None
        ) = None,
    ) -> dict[str, Any]:
        """
        Gelir akışlarını analiz eder.

        Args:
            streams: Gelir akışı listesi.

        Returns:
            Analiz sonuçları.
        """
        try:
            if streams is None:
                streams = []
            total = sum(
                s.get("amount", 0)
                for s in streams
            )
            if streams:
                top_stream = max(
                    streams,
                    key=lambda s: s.get(
                        "amount", 0
                    ),
                )
            else:
                top_stream = "none"
            stream_count = len(streams)
            self._stats[
                "analyses_completed"
            ] += 1
            return {
                "total_revenue": round(
                    total, 2
                ),
                "stream_count": (
                    stream_count
                ),
                "top_stream": top_stream,
                "analyzed": True,
            }
        except Exception as e:
            logger.error(
                "Gelir analizi hatası:"
                " %s",
                e,
            )
            return {
                "analyzed": False,
                "error": str(e),
            }

    def breakdown_streams(
        self,
        streams: (
            list[dict[str, Any]] | None
        ) = None,
    ) -> dict[str, Any]:
        """
        Gelir akışlarını türe göre ayırır.

        Args:
            streams: Gelir akışı listesi.

        Returns:
            Tür bazlı dağılım.
        """
        try:
            if streams is None:
                streams = []
            breakdown: dict[str, int] = {}
            for s in streams:
                t = s.get(
                    "type", "unknown"
                )
                breakdown[t] = (
                    breakdown.get(t, 0) + 1
                )
            return {
                "breakdown": breakdown,
                "category_count": len(
                    breakdown
                ),
                "detailed": True,
            }
        except Exception as e:
            logger.error(
                "Dağılım hatası: %s", e
            )
            return {
                "detailed": False,
                "error": str(e),
            }

    def track_growth(
        self,
        current: float = 0.0,
        previous: float = 0.0,
    ) -> dict[str, Any]:
        """
        Büyüme oranını takip eder.

        Args:
            current: Mevcut gelir.
            previous: Önceki gelir.

        Returns:
            Büyüme analizi sonuçları.
        """
        try:
            growth_rate = round(
                (
                    (current - previous)
                    / max(previous, 1)
                )
                * 100,
                1,
            )
            if growth_rate > 5:
                trend = "growing"
            elif growth_rate < -5:
                trend = "declining"
            else:
                trend = "stable"
            return {
                "current": current,
                "previous": previous,
                "growth_rate": (
                    growth_rate
                ),
                "trend": trend,
                "tracked": True,
            }
        except Exception as e:
            logger.error(
                "Büyüme takip hatası:"
                " %s",
                e,
            )
            return {
                "tracked": False,
                "error": str(e),
            }

    def analyze_pricing(
        self,
        price: float = 0.0,
        cost: float = 0.0,
        competitors: (
            list[float] | None
        ) = None,
    ) -> dict[str, Any]:
        """
        Fiyatlandırma analizi yapar.

        Args:
            price: Ürün fiyatı.
            cost: Ürün maliyeti.
            competitors: Rakip fiyatları.

        Returns:
            Fiyatlandırma analizi.
        """
        try:
            if competitors is None:
                competitors = []
            margin = round(
                (
                    (price - cost)
                    / max(price, 1)
                )
                * 100,
                1,
            )
            if competitors:
                avg_competitor = round(
                    sum(competitors)
                    / max(
                        len(competitors),
                        1,
                    ),
                    2,
                )
            else:
                avg_competitor = 0
            if (
                avg_competitor > 0
                and price
                > avg_competitor * 1.2
            ):
                position = "premium"
            elif (
                avg_competitor > 0
                and price
                < avg_competitor * 0.8
            ):
                position = "budget"
            else:
                position = "competitive"
            return {
                "price": price,
                "cost": cost,
                "margin": margin,
                "avg_competitor": (
                    avg_competitor
                ),
                "position": position,
                "analyzed": True,
            }
        except Exception as e:
            logger.error(
                "Fiyat analizi hatası:"
                " %s",
                e,
            )
            return {
                "analyzed": False,
                "error": str(e),
            }

    def check_diversification(
        self,
        streams: (
            list[dict[str, Any]] | None
        ) = None,
    ) -> dict[str, Any]:
        """
        Çeşitlendirme değerlendirmesi.

        Args:
            streams: Gelir akışı listesi.

        Returns:
            Çeşitlendirme sonuçları.
        """
        try:
            if streams is None:
                streams = []
            types = set(
                s.get("type", "unknown")
                for s in streams
            )
            score = min(
                len(types) * 25, 100
            )
            if score >= 75:
                risk = "low"
            elif score >= 50:
                risk = "medium"
            else:
                risk = "high"
            return {
                "unique_types": len(
                    types
                ),
                "diversification_score": (
                    score
                ),
                "risk_level": risk,
                "assessed": True,
            }
        except Exception as e:
            logger.error(
                "Çeşitlendirme hatası:"
                " %s",
                e,
            )
            return {
                "assessed": False,
                "error": str(e),
            }
