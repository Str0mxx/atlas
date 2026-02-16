"""
Otel karşılaştırıcı modülü.

Otel arama, fiyat takibi, yorum birleştirme,
tesis filtreleme, konum puanlama.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class HotelComparator:
    """Otel karşılaştırıcı.

    Attributes:
        _hotels: Otel kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Karşılaştırıcıyı başlatır."""
        self._hotels: list[dict] = []
        self._stats: dict[str, int] = {
            "searches_performed": 0,
        }
        logger.info(
            "HotelComparator baslatildi"
        )

    @property
    def hotel_count(self) -> int:
        """Otel sayısı."""
        return len(self._hotels)

    def search_hotels(
        self,
        city: str = "",
        nights: int = 1,
        guests: int = 1,
        max_price: float = 0.0,
    ) -> dict[str, Any]:
        """Otel arar.

        Args:
            city: Şehir.
            nights: Gece sayısı.
            guests: Misafir sayısı.
            max_price: Maksimum fiyat.

        Returns:
            Arama sonuçları.
        """
        try:
            results = [
                {
                    "name": "Grand Hotel",
                    "price_per_night": 150.0,
                    "rating": 4.5,
                    "stars": 5,
                },
                {
                    "name": "City Inn",
                    "price_per_night": 80.0,
                    "rating": 3.8,
                    "stars": 3,
                },
                {
                    "name": "Budget Stay",
                    "price_per_night": 45.0,
                    "rating": 3.2,
                    "stars": 2,
                },
            ]

            if max_price > 0:
                results = [
                    r for r in results
                    if r["price_per_night"]
                    <= max_price
                ]

            for r in results:
                r["total_price"] = (
                    r["price_per_night"] * nights
                )

            self._stats[
                "searches_performed"
            ] += 1

            return {
                "city": city,
                "nights": nights,
                "results": results,
                "result_count": len(results),
                "searched": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "searched": False,
                "error": str(e),
            }

    def track_price(
        self,
        hotel_name: str = "",
        current_price: float = 0.0,
        previous_price: float = 0.0,
    ) -> dict[str, Any]:
        """Fiyat takibi yapar.

        Args:
            hotel_name: Otel adı.
            current_price: Mevcut fiyat.
            previous_price: Önceki fiyat.

        Returns:
            Fiyat değişimi.
        """
        try:
            if previous_price > 0:
                change_pct = round(
                    (current_price - previous_price)
                    / previous_price
                    * 100,
                    1,
                )
            else:
                change_pct = 0.0

            if change_pct < -10:
                trend = "significant_drop"
            elif change_pct < 0:
                trend = "slight_drop"
            elif change_pct == 0:
                trend = "stable"
            elif change_pct <= 10:
                trend = "slight_increase"
            else:
                trend = "significant_increase"

            return {
                "hotel_name": hotel_name,
                "current_price": current_price,
                "previous_price": previous_price,
                "change_pct": change_pct,
                "trend": trend,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def aggregate_reviews(
        self,
        reviews: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Yorumları birleştirir.

        Args:
            reviews: Yorum listesi.

        Returns:
            Yorum özeti.
        """
        try:
            items = reviews or []
            if not items:
                return {
                    "aggregated": True,
                    "avg_rating": 0.0,
                    "count": 0,
                }

            ratings = [
                r.get("rating", 0)
                for r in items
            ]
            avg = round(
                sum(ratings) / len(ratings), 1
            )

            positive = sum(
                1 for r in ratings if r >= 4
            )
            negative = sum(
                1 for r in ratings if r <= 2
            )
            neutral = len(ratings) - positive - negative

            if avg >= 4.5:
                sentiment = "excellent"
            elif avg >= 3.5:
                sentiment = "good"
            elif avg >= 2.5:
                sentiment = "mixed"
            else:
                sentiment = "poor"

            return {
                "avg_rating": avg,
                "count": len(items),
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "sentiment": sentiment,
                "aggregated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "aggregated": False,
                "error": str(e),
            }

    def filter_amenities(
        self,
        required: list[str] | None = None,
        hotel_amenities: list[str] | None = None,
    ) -> dict[str, Any]:
        """Tesislere göre filtreler.

        Args:
            required: İstenen tesisler.
            hotel_amenities: Otelin tesisleri.

        Returns:
            Filtreleme sonucu.
        """
        try:
            req = set(required or [])
            avail = set(hotel_amenities or [])

            matched = req & avail
            missing = req - avail

            match_pct = (
                round(
                    len(matched) / len(req) * 100,
                    1,
                )
                if req
                else 100.0
            )

            return {
                "required": list(req),
                "matched": list(matched),
                "missing": list(missing),
                "match_pct": match_pct,
                "meets_criteria": len(
                    missing
                ) == 0,
                "filtered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "filtered": False,
                "error": str(e),
            }

    def score_location(
        self,
        distance_center_km: float = 0.0,
        distance_airport_km: float = 0.0,
        nearby_restaurants: int = 0,
        public_transport: bool = False,
    ) -> dict[str, Any]:
        """Konum puanlar.

        Args:
            distance_center_km: Merkeze mesafe.
            distance_airport_km: Havaalanına mesafe.
            nearby_restaurants: Yakın restoran.
            public_transport: Toplu taşıma.

        Returns:
            Konum puanı.
        """
        try:
            center_score = max(
                0, 30 - distance_center_km * 3
            )
            airport_score = max(
                0, 20 - distance_airport_km * 0.5
            )
            restaurant_score = min(
                nearby_restaurants * 5, 25
            )
            transport_score = (
                25 if public_transport else 0
            )

            total = round(
                center_score
                + airport_score
                + restaurant_score
                + transport_score,
                1,
            )
            total = min(total, 100.0)

            if total >= 80:
                grade = "excellent"
            elif total >= 60:
                grade = "good"
            elif total >= 40:
                grade = "average"
            else:
                grade = "poor"

            return {
                "location_score": total,
                "grade": grade,
                "center_score": round(
                    center_score, 1
                ),
                "airport_score": round(
                    airport_score, 1
                ),
                "scored": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scored": False,
                "error": str(e),
            }
