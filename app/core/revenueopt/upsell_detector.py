"""ATLAS Upsell Tespitçisi modülü.

Fırsat tespiti, ürün önerileri,
zamanlama optimizasyonu, eğilim
puanlama, dönüşüm takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class UpsellDetector:
    """Upsell tespitçisi.

    Upsell fırsatlarını tespit eder.

    Attributes:
        _opportunities: Fırsat kayıtları.
        _conversions: Dönüşüm kayıtları.
    """

    def __init__(self) -> None:
        """Tespitçiyi başlatır."""
        self._opportunities: list[
            dict[str, Any]
        ] = []
        self._conversions: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "opportunities_found": 0,
            "conversions_tracked": 0,
        }

        logger.info(
            "UpsellDetector baslatildi",
        )

    def detect_opportunity(
        self,
        customer_id: str,
        current_product: str = "",
        purchase_history: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Fırsat tespiti yapar.

        Args:
            customer_id: Müşteri kimliği.
            current_product: Güncel ürün.
            purchase_history: Satın alma
                geçmişi.

        Returns:
            Tespit bilgisi.
        """
        purchase_history = (
            purchase_history or []
        )
        self._counter += 1
        oid = f"opp_{self._counter}"

        upgrades = []
        if current_product:
            upgrades.append(
                f"{current_product}_pro",
            )
            upgrades.append(
                f"{current_product}_premium",
            )

        opp = {
            "opportunity_id": oid,
            "customer_id": customer_id,
            "current_product": (
                current_product
            ),
            "suggested_upgrades": upgrades,
            "timestamp": time.time(),
        }
        self._opportunities.append(opp)
        self._stats[
            "opportunities_found"
        ] += 1

        return {
            "opportunity_id": oid,
            "customer_id": customer_id,
            "upgrades": upgrades,
            "detected": True,
        }

    def recommend_products(
        self,
        customer_id: str,
        current_products: list[str]
        | None = None,
        catalog: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Ürün önerileri verir.

        Args:
            customer_id: Müşteri kimliği.
            current_products: Güncel ürünler.
            catalog: Ürün kataloğu.

        Returns:
            Öneri bilgisi.
        """
        current_products = (
            current_products or []
        )
        catalog = catalog or []

        recommendations = [
            p for p in catalog
            if p not in current_products
        ]

        return {
            "customer_id": customer_id,
            "recommendations": (
                recommendations[:5]
            ),
            "count": min(
                5, len(recommendations),
            ),
            "recommended": True,
        }

    def optimize_timing(
        self,
        customer_id: str,
        days_since_purchase: int = 0,
        engagement_score: float = 0.0,
    ) -> dict[str, Any]:
        """Zamanlama optimizasyonu yapar.

        Args:
            customer_id: Müşteri kimliği.
            days_since_purchase: Son satın
                almadan bu yana gün.
            engagement_score: Etkileşim
                puanı.

        Returns:
            Zamanlama bilgisi.
        """
        if (
            7 <= days_since_purchase <= 30
            and engagement_score >= 50
        ):
            timing = "optimal"
        elif days_since_purchase < 7:
            timing = "too_early"
        elif days_since_purchase > 90:
            timing = "late"
        else:
            timing = "acceptable"

        return {
            "customer_id": customer_id,
            "timing": timing,
            "days_since_purchase": (
                days_since_purchase
            ),
            "engagement_score": (
                engagement_score
            ),
            "optimized": True,
        }

    def score_propensity(
        self,
        customer_id: str,
        purchase_frequency: float = 0.0,
        avg_order_value: float = 0.0,
        engagement_score: float = 0.0,
    ) -> dict[str, Any]:
        """Eğilim puanlama yapar.

        Args:
            customer_id: Müşteri kimliği.
            purchase_frequency: Satın alma
                sıklığı.
            avg_order_value: Ortalama sipariş
                değeri.
            engagement_score: Etkileşim
                puanı.

        Returns:
            Puanlama bilgisi.
        """
        score = (
            purchase_frequency * 30
            + avg_order_value * 0.1
            + engagement_score * 0.4
        )
        score = min(100, max(0, score))

        if score >= 70:
            likelihood = "high"
        elif score >= 40:
            likelihood = "medium"
        else:
            likelihood = "low"

        return {
            "customer_id": customer_id,
            "propensity_score": round(
                score, 1,
            ),
            "likelihood": likelihood,
            "scored": True,
        }

    def track_conversion(
        self,
        opportunity_id: str,
        converted: bool = False,
        revenue: float = 0.0,
    ) -> dict[str, Any]:
        """Dönüşüm takibi yapar.

        Args:
            opportunity_id: Fırsat kimliği.
            converted: Dönüştü mü.
            revenue: Gelir.

        Returns:
            Takip bilgisi.
        """
        self._conversions.append({
            "opportunity_id": (
                opportunity_id
            ),
            "converted": converted,
            "revenue": revenue,
            "timestamp": time.time(),
        })

        if converted:
            self._stats[
                "conversions_tracked"
            ] += 1

        total = len(self._conversions)
        converted_count = sum(
            1 for c in self._conversions
            if c["converted"]
        )
        rate = (
            (converted_count / total) * 100
            if total > 0
            else 0.0
        )

        return {
            "opportunity_id": (
                opportunity_id
            ),
            "converted": converted,
            "conversion_rate": round(
                rate, 1,
            ),
            "tracked": True,
        }

    @property
    def opportunity_count(self) -> int:
        """Fırsat sayısı."""
        return self._stats[
            "opportunities_found"
        ]

    @property
    def conversion_count(self) -> int:
        """Dönüşüm sayısı."""
        return self._stats[
            "conversions_tracked"
        ]
