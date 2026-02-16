"""ATLAS Fiyat İzleyici.

Fiyat izleme, değişiklik tespiti,
tarihsel trendler, karşılaştırma, uyarılar.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PriceWatcher:
    """Fiyat izleyici.

    Rakip fiyatlarını izler, değişiklikleri
    tespit eder ve trendleri analiz eder.

    Attributes:
        _prices: Fiyat kayıtları.
        _alerts: Uyarılar.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """İzleyiciyi başlatır."""
        self._prices: dict[
            str, list[dict]
        ] = {}
        self._alerts: list[dict] = []
        self._stats = {
            "prices_monitored": 0,
            "alerts_generated": 0,
        }
        logger.info(
            "PriceWatcher baslatildi",
        )

    @property
    def monitor_count(self) -> int:
        """İzlenen fiyat sayısı."""
        return self._stats[
            "prices_monitored"
        ]

    @property
    def alert_count(self) -> int:
        """Oluşturulan uyarı sayısı."""
        return self._stats[
            "alerts_generated"
        ]

    def monitor_price(
        self,
        competitor_id: str,
        product: str,
        price: float,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Fiyat izler.

        Args:
            competitor_id: Rakip kimliği.
            product: Ürün adı.
            price: Fiyat.
            currency: Para birimi.

        Returns:
            İzleme bilgisi.
        """
        key = (
            f"{competitor_id}_{product}"
        )
        if key not in self._prices:
            self._prices[key] = []

        self._prices[key].append(
            {
                "price": price,
                "currency": currency,
            },
        )
        self._stats[
            "prices_monitored"
        ] += 1

        return {
            "competitor_id": competitor_id,
            "product": product,
            "price": price,
            "currency": currency,
            "monitored": True,
        }

    def detect_change(
        self,
        competitor_id: str,
        product: str,
        old_price: float,
        new_price: float,
    ) -> dict[str, Any]:
        """Fiyat değişikliği tespit eder.

        Args:
            competitor_id: Rakip kimliği.
            product: Ürün adı.
            old_price: Eski fiyat.
            new_price: Yeni fiyat.

        Returns:
            Değişiklik bilgisi.
        """
        if old_price <= 0:
            change_pct = 0.0
        else:
            change_pct = round(
                (new_price - old_price)
                / old_price
                * 100,
                1,
            )

        if new_price > old_price:
            direction = "increase"
        elif new_price < old_price:
            direction = "decrease"
        else:
            direction = "stable"

        significant = (
            abs(change_pct) >= 5.0
        )

        if significant:
            self._stats[
                "alerts_generated"
            ] += 1

        return {
            "competitor_id": competitor_id,
            "product": product,
            "old_price": old_price,
            "new_price": new_price,
            "change_pct": change_pct,
            "direction": direction,
            "significant": significant,
            "detected": True,
        }

    def analyze_trend(
        self,
        competitor_id: str,
        product: str,
        price_history: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Tarihsel trend analizi yapar.

        Args:
            competitor_id: Rakip kimliği.
            product: Ürün adı.
            price_history: Fiyat geçmişi.

        Returns:
            Trend bilgisi.
        """
        if price_history is None:
            price_history = []

        if len(price_history) < 2:
            return {
                "competitor_id": (
                    competitor_id
                ),
                "product": product,
                "trend": "insufficient_data",
                "analyzed": False,
            }

        avg = round(
            sum(price_history)
            / len(price_history),
            2,
        )
        first_half = price_history[
            : len(price_history) // 2
        ]
        second_half = price_history[
            len(price_history) // 2 :
        ]

        avg_first = sum(first_half) / len(
            first_half,
        )
        avg_second = sum(
            second_half,
        ) / len(second_half)

        if avg_second > avg_first * 1.05:
            trend = "increasing"
        elif (
            avg_second < avg_first * 0.95
        ):
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "competitor_id": competitor_id,
            "product": product,
            "trend": trend,
            "average": avg,
            "min_price": min(price_history),
            "max_price": max(price_history),
            "data_points": len(
                price_history,
            ),
            "analyzed": True,
        }

    def compare_prices(
        self,
        our_price: float,
        competitor_prices: dict[
            str, float
        ]
        | None = None,
    ) -> dict[str, Any]:
        """Fiyat karşılaştırması yapar.

        Args:
            our_price: Bizim fiyat.
            competitor_prices: Rakip fiyatları.

        Returns:
            Karşılaştırma bilgisi.
        """
        if competitor_prices is None:
            competitor_prices = {}

        comparisons = {}
        for comp, price in (
            competitor_prices.items()
        ):
            diff = round(
                our_price - price, 2,
            )
            diff_pct = round(
                diff
                / max(price, 0.01)
                * 100,
                1,
            )
            comparisons[comp] = {
                "their_price": price,
                "difference": diff,
                "difference_pct": diff_pct,
                "position": (
                    "cheaper"
                    if diff < 0
                    else (
                        "expensive"
                        if diff > 0
                        else "equal"
                    )
                ),
            }

        cheaper_count = sum(
            1
            for c in comparisons.values()
            if c["position"] == "cheaper"
        )

        return {
            "our_price": our_price,
            "comparisons": comparisons,
            "cheaper_than": cheaper_count,
            "total_compared": len(
                comparisons,
            ),
            "compared": True,
        }

    def generate_alert(
        self,
        competitor_id: str,
        product: str,
        alert_type: str = "price_change",
        severity: str = "medium",
        message: str = "",
    ) -> dict[str, Any]:
        """Uyarı oluşturur.

        Args:
            competitor_id: Rakip kimliği.
            product: Ürün adı.
            alert_type: Uyarı tipi.
            severity: Ciddiyet.
            message: Mesaj.

        Returns:
            Uyarı bilgisi.
        """
        aid = f"pa_{str(uuid4())[:6]}"
        alert = {
            "alert_id": aid,
            "competitor_id": competitor_id,
            "product": product,
            "type": alert_type,
            "severity": severity,
            "message": message,
        }
        self._alerts.append(alert)
        self._stats[
            "alerts_generated"
        ] += 1

        return {
            "alert_id": aid,
            "competitor_id": competitor_id,
            "severity": severity,
            "generated": True,
        }
