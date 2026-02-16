"""ATLAS Marka Sağlık Puanı modülü.

Genel sağlık puanı, bileşen puanları,
trend takibi, kıyaslama,
iyileştirme önerileri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BrandHealthScore:
    """Marka sağlık puanı.

    Markanın genel sağlığını puanlar.

    Attributes:
        _scores: Puan kayıtları.
        _components: Bileşen kayıtları.
    """

    def __init__(self) -> None:
        """Puanlayıcıyı başlatır."""
        self._scores: dict[
            str, dict[str, Any]
        ] = {}
        self._history: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._benchmarks: dict[
            str, float
        ] = {}
        self._stats = {
            "scores_calculated": 0,
            "improvements_suggested": 0,
        }

        logger.info(
            "BrandHealthScore baslatildi",
        )

    def calculate_health(
        self,
        brand: str,
        sentiment_score: float = 50.0,
        review_score: float = 50.0,
        mention_volume: float = 50.0,
        crisis_score: float = 100.0,
    ) -> dict[str, Any]:
        """Genel sağlık puanı hesaplar.

        Args:
            brand: Marka.
            sentiment_score: Duygu puanı.
            review_score: Yorum puanı.
            mention_volume: Bahsedilme hacmi.
            crisis_score: Kriz puanı (yüksek=iyi).

        Returns:
            Sağlık bilgisi.
        """
        overall = round(
            sentiment_score * 0.3
            + review_score * 0.3
            + mention_volume * 0.15
            + crisis_score * 0.25,
            1,
        )

        grade = (
            "excellent" if overall >= 85
            else "good" if overall >= 70
            else "fair" if overall >= 50
            else "poor" if overall >= 30
            else "critical"
        )

        self._scores[brand] = {
            "brand": brand,
            "overall": overall,
            "grade": grade,
            "components": {
                "sentiment": sentiment_score,
                "reviews": review_score,
                "mentions": mention_volume,
                "crisis": crisis_score,
            },
            "timestamp": time.time(),
        }

        if brand not in self._history:
            self._history[brand] = []
        self._history[brand].append({
            "score": overall,
            "grade": grade,
            "timestamp": time.time(),
        })

        self._stats[
            "scores_calculated"
        ] += 1

        return {
            "brand": brand,
            "overall": overall,
            "grade": grade,
            "calculated": True,
        }

    def get_component_scores(
        self,
        brand: str,
    ) -> dict[str, Any]:
        """Bileşen puanlarını döndürür.

        Args:
            brand: Marka.

        Returns:
            Bileşen bilgisi.
        """
        record = self._scores.get(brand)
        if not record:
            return {
                "brand": brand,
                "found": False,
            }

        return {
            "brand": brand,
            "components": record[
                "components"
            ],
            "overall": record["overall"],
            "found": True,
        }

    def track_trend(
        self,
        brand: str,
    ) -> dict[str, Any]:
        """Trend takibi yapar.

        Args:
            brand: Marka.

        Returns:
            Trend bilgisi.
        """
        history = self._history.get(
            brand, [],
        )
        if len(history) < 2:
            return {
                "brand": brand,
                "tracked": False,
            }

        scores = [
            h["score"] for h in history
        ]
        latest = scores[-1]
        previous = scores[-2]
        change = round(
            latest - previous, 1,
        )
        direction = (
            "improving" if change > 0
            else "declining" if change < 0
            else "stable"
        )

        return {
            "brand": brand,
            "latest": latest,
            "previous": previous,
            "change": change,
            "direction": direction,
            "data_points": len(scores),
            "tracked": True,
        }

    def compare_benchmark(
        self,
        brand: str,
        industry_avg: float = 60.0,
    ) -> dict[str, Any]:
        """Kıyaslama karşılaştırması yapar.

        Args:
            brand: Marka.
            industry_avg: Sektör ortalaması.

        Returns:
            Karşılaştırma bilgisi.
        """
        record = self._scores.get(brand)
        if not record:
            return {
                "brand": brand,
                "compared": False,
            }

        overall = record["overall"]
        diff = round(
            overall - industry_avg, 1,
        )
        position = (
            "above_average"
            if diff > 5
            else "below_average"
            if diff < -5
            else "average"
        )

        return {
            "brand": brand,
            "score": overall,
            "industry_avg": industry_avg,
            "diff": diff,
            "position": position,
            "compared": True,
        }

    def suggest_improvements(
        self,
        brand: str,
    ) -> dict[str, Any]:
        """İyileştirme önerileri sunar.

        Args:
            brand: Marka.

        Returns:
            Öneri bilgisi.
        """
        record = self._scores.get(brand)
        if not record:
            return {
                "brand": brand,
                "suggested": False,
            }

        components = record["components"]
        suggestions = []

        for comp, val in sorted(
            components.items(),
            key=lambda x: x[1],
        ):
            if val < 60:
                suggestions.append({
                    "component": comp,
                    "current_score": val,
                    "priority": (
                        "high" if val < 40
                        else "medium"
                    ),
                })

        self._stats[
            "improvements_suggested"
        ] += len(suggestions)

        return {
            "brand": brand,
            "suggestions": suggestions,
            "suggestion_count": len(
                suggestions,
            ),
            "suggested": True,
        }

    @property
    def score_count(self) -> int:
        """Puan sayısı."""
        return self._stats[
            "scores_calculated"
        ]
