"""
Fiyat uyarı ayarlayıcı modülü.

Fiyat izleme, düşüş uyarıları, geçmiş
karşılaştırma, en iyi zaman, fırsat tespiti.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TravelPriceAlertSetter:
    """Seyahat fiyat uyarı ayarlayıcı.

    Attributes:
        _alerts: Uyarı kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Ayarlayıcıyı başlatır."""
        self._alerts: list[dict] = []
        self._stats: dict[str, int] = {
            "alerts_created": 0,
        }
        logger.info(
            "TravelPriceAlertSetter baslatildi"
        )

    @property
    def alert_count(self) -> int:
        """Uyarı sayısı."""
        return len(self._alerts)

    def set_price_monitor(
        self,
        item_type: str = "flight",
        route: str = "",
        target_price: float = 0.0,
        current_price: float = 0.0,
    ) -> dict[str, Any]:
        """Fiyat izleme ayarlar.

        Args:
            item_type: Öğe türü.
            route: Rota.
            target_price: Hedef fiyat.
            current_price: Mevcut fiyat.

        Returns:
            İzleme bilgisi.
        """
        try:
            aid = f"pa_{uuid4()!s:.8}"

            gap_pct = round(
                (current_price - target_price)
                / current_price
                * 100,
                1,
            ) if current_price > 0 else 0.0

            record = {
                "alert_id": aid,
                "item_type": item_type,
                "route": route,
                "target_price": target_price,
                "current_price": current_price,
                "active": True,
            }
            self._alerts.append(record)
            self._stats["alerts_created"] += 1

            return {
                "alert_id": aid,
                "item_type": item_type,
                "route": route,
                "target_price": target_price,
                "current_price": current_price,
                "gap_pct": gap_pct,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def check_drop_alerts(
        self,
        current_price: float = 0.0,
        previous_price: float = 0.0,
        threshold_pct: float = 10.0,
    ) -> dict[str, Any]:
        """Düşüş uyarılarını kontrol eder.

        Args:
            current_price: Mevcut fiyat.
            previous_price: Önceki fiyat.
            threshold_pct: Eşik yüzdesi.

        Returns:
            Uyarı bilgisi.
        """
        try:
            if previous_price > 0:
                drop_pct = round(
                    (previous_price - current_price)
                    / previous_price
                    * 100,
                    1,
                )
            else:
                drop_pct = 0.0

            alert_triggered = (
                drop_pct >= threshold_pct
            )

            if drop_pct >= 20:
                urgency = "high"
            elif drop_pct >= threshold_pct:
                urgency = "medium"
            else:
                urgency = "low"

            return {
                "current_price": current_price,
                "previous_price": previous_price,
                "drop_pct": drop_pct,
                "threshold_pct": threshold_pct,
                "alert_triggered": alert_triggered,
                "urgency": urgency,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def compare_historical(
        self,
        current_price: float = 0.0,
        historical_prices: list[float] | None = None,
    ) -> dict[str, Any]:
        """Geçmiş fiyatlarla karşılaştırır.

        Args:
            current_price: Mevcut fiyat.
            historical_prices: Geçmiş fiyatlar.

        Returns:
            Karşılaştırma sonucu.
        """
        try:
            prices = historical_prices or []
            if not prices:
                return {
                    "compared": True,
                    "assessment": "no_data",
                    "count": 0,
                }

            avg = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)

            vs_avg_pct = round(
                (current_price - avg)
                / avg
                * 100,
                1,
            ) if avg > 0 else 0.0

            if current_price <= min_price:
                assessment = "all_time_low"
            elif vs_avg_pct < -15:
                assessment = "great_deal"
            elif vs_avg_pct < -5:
                assessment = "good_price"
            elif vs_avg_pct <= 5:
                assessment = "average"
            elif vs_avg_pct <= 15:
                assessment = "above_average"
            else:
                assessment = "expensive"

            return {
                "current_price": current_price,
                "avg_price": round(avg, 2),
                "min_price": min_price,
                "max_price": max_price,
                "vs_avg_pct": vs_avg_pct,
                "assessment": assessment,
                "count": len(prices),
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def suggest_best_time(
        self,
        destination: str = "",
        months_ahead: int = 3,
    ) -> dict[str, Any]:
        """En iyi rezervasyon zamanını önerir.

        Args:
            destination: Hedef.
            months_ahead: Kaç ay önce.

        Returns:
            Zaman önerisi.
        """
        try:
            if months_ahead >= 3:
                booking_advice = "ideal"
                expected_savings_pct = 25.0
            elif months_ahead >= 2:
                booking_advice = "good"
                expected_savings_pct = 15.0
            elif months_ahead >= 1:
                booking_advice = "fair"
                expected_savings_pct = 5.0
            else:
                booking_advice = "late"
                expected_savings_pct = 0.0

            return {
                "destination": destination,
                "months_ahead": months_ahead,
                "booking_advice": booking_advice,
                "expected_savings_pct": (
                    expected_savings_pct
                ),
                "suggested": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "suggested": False,
                "error": str(e),
            }

    def detect_deals(
        self,
        prices: list[dict] | None = None,
        threshold_pct: float = 20.0,
    ) -> dict[str, Any]:
        """Fırsatları tespit eder.

        Args:
            prices: Fiyat listesi.
            threshold_pct: Fırsat eşiği (%).

        Returns:
            Fırsat bilgisi.
        """
        try:
            items = prices or []
            if not items:
                return {
                    "detected": True,
                    "deals": [],
                    "deal_count": 0,
                }

            all_prices = [
                p.get("price", 0)
                for p in items
            ]
            avg = (
                sum(all_prices) / len(all_prices)
                if all_prices
                else 0
            )

            deals = []
            for item in items:
                price = item.get("price", 0)
                if avg > 0:
                    discount = round(
                        (avg - price) / avg * 100,
                        1,
                    )
                    if discount >= threshold_pct:
                        deals.append({
                            **item,
                            "discount_pct": discount,
                        })

            return {
                "avg_price": round(avg, 2),
                "deals": deals,
                "deal_count": len(deals),
                "threshold_pct": threshold_pct,
                "detected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "detected": False,
                "error": str(e),
            }
