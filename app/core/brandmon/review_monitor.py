"""ATLAS Yorum İzleyici modülü.

Yorum takibi, puan toplama,
yanıt takibi, rakip karşılaştırma,
negatif uyarı.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ReviewMonitor:
    """Yorum izleyici.

    Yorum sitelerini izler ve analiz eder.

    Attributes:
        _reviews: Yorum kayıtları.
        _responses: Yanıt kayıtları.
    """

    def __init__(self) -> None:
        """İzleyiciyi başlatır."""
        self._reviews: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._responses: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "reviews_tracked": 0,
            "alerts_generated": 0,
        }

        logger.info(
            "ReviewMonitor baslatildi",
        )

    def track_review(
        self,
        brand: str,
        platform: str = "",
        rating: float = 0.0,
        content: str = "",
        author: str = "",
    ) -> dict[str, Any]:
        """Yorum takip eder.

        Args:
            brand: Marka.
            platform: Platform.
            rating: Puan.
            content: İçerik.
            author: Yazar.

        Returns:
            Takip bilgisi.
        """
        self._counter += 1
        rid = f"rev_{self._counter}"

        if brand not in self._reviews:
            self._reviews[brand] = []

        entry = {
            "review_id": rid,
            "brand": brand,
            "platform": platform,
            "rating": rating,
            "content": content,
            "author": author,
            "timestamp": time.time(),
        }
        self._reviews[brand].append(entry)
        self._stats[
            "reviews_tracked"
        ] += 1

        return {
            "review_id": rid,
            "brand": brand,
            "rating": rating,
            "tracked": True,
        }

    def aggregate_ratings(
        self,
        brand: str,
    ) -> dict[str, Any]:
        """Puanları toplar.

        Args:
            brand: Marka.

        Returns:
            Toplama bilgisi.
        """
        reviews = self._reviews.get(
            brand, [],
        )
        if not reviews:
            return {
                "brand": brand,
                "aggregated": False,
            }

        ratings = [
            r["rating"] for r in reviews
        ]
        avg = round(
            sum(ratings) / len(ratings), 1,
        )

        by_platform: dict[
            str, list[float]
        ] = {}
        for r in reviews:
            p = r["platform"]
            if p not in by_platform:
                by_platform[p] = []
            by_platform[p].append(
                r["rating"],
            )

        platform_avgs = {
            p: round(
                sum(vals) / len(vals), 1,
            )
            for p, vals in by_platform.items()
        }

        return {
            "brand": brand,
            "avg_rating": avg,
            "total_reviews": len(reviews),
            "by_platform": platform_avgs,
            "aggregated": True,
        }

    def track_response(
        self,
        review_id: str,
        response: str = "",
        response_time_hours: float = 0.0,
    ) -> dict[str, Any]:
        """Yanıt takip eder.

        Args:
            review_id: Yorum ID.
            response: Yanıt.
            response_time_hours: Yanıt süresi.

        Returns:
            Takip bilgisi.
        """
        self._responses[review_id] = {
            "review_id": review_id,
            "response": response,
            "response_time_hours": (
                response_time_hours
            ),
            "timestamp": time.time(),
        }

        return {
            "review_id": review_id,
            "response_time_hours": (
                response_time_hours
            ),
            "responded": True,
        }

    def compare_competitors(
        self,
        brands: list[str] | None = None,
    ) -> dict[str, Any]:
        """Rakip karşılaştırma yapar.

        Args:
            brands: Markalar.

        Returns:
            Karşılaştırma bilgisi.
        """
        brands = brands or []
        results = {}

        for brand in brands:
            reviews = self._reviews.get(
                brand, [],
            )
            if reviews:
                ratings = [
                    r["rating"]
                    for r in reviews
                ]
                results[brand] = {
                    "avg_rating": round(
                        sum(ratings)
                        / len(ratings), 1,
                    ),
                    "count": len(reviews),
                }
            else:
                results[brand] = {
                    "avg_rating": 0.0,
                    "count": 0,
                }

        ranked = sorted(
            results.items(),
            key=lambda x: x[1]["avg_rating"],
            reverse=True,
        )

        return {
            "comparison": results,
            "ranking": [
                r[0] for r in ranked
            ],
            "brands_compared": len(results),
        }

    def alert_on_negative(
        self,
        brand: str,
        threshold: float = 2.0,
    ) -> dict[str, Any]:
        """Negatif yorum uyarısı üretir.

        Args:
            brand: Marka.
            threshold: Eşik (altı uyarı).

        Returns:
            Uyarı bilgisi.
        """
        reviews = self._reviews.get(
            brand, [],
        )
        negative = [
            r for r in reviews
            if r["rating"] <= threshold
        ]

        if negative:
            self._stats[
                "alerts_generated"
            ] += len(negative)

        return {
            "brand": brand,
            "negative_count": len(negative),
            "threshold": threshold,
            "alert": len(negative) > 0,
        }

    @property
    def review_count(self) -> int:
        """Yorum sayısı."""
        return self._stats[
            "reviews_tracked"
        ]

    @property
    def alert_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "alerts_generated"
        ]
