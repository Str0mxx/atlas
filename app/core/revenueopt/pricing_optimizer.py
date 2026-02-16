"""ATLAS Fiyat Optimizasyonu modülü.

Dinamik fiyatlandırma, esneklik analizi,
rakip fiyatlandırma, paket optimizasyonu,
marj koruma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PricingOptimizer:
    """Fiyat optimizasyonu.

    Fiyatlandırma stratejilerini optimize
    eder.

    Attributes:
        _products: Ürün fiyat kayıtları.
        _competitors: Rakip fiyatları.
    """

    def __init__(self) -> None:
        """Optimizatörü başlatır."""
        self._products: dict[
            str, dict[str, Any]
        ] = {}
        self._competitors: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._bundles: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "prices_optimized": 0,
            "bundles_created": 0,
        }

        logger.info(
            "PricingOptimizer baslatildi",
        )

    def dynamic_pricing(
        self,
        product_id: str,
        base_price: float = 0.0,
        demand_factor: float = 1.0,
        supply_factor: float = 1.0,
    ) -> dict[str, Any]:
        """Dinamik fiyatlandırma yapar.

        Args:
            product_id: Ürün kimliği.
            base_price: Taban fiyat.
            demand_factor: Talep faktörü.
            supply_factor: Arz faktörü.

        Returns:
            Fiyat bilgisi.
        """
        adjusted = (
            base_price
            * demand_factor
            / supply_factor
        )

        self._products[product_id] = {
            "product_id": product_id,
            "base_price": base_price,
            "adjusted_price": round(
                adjusted, 2,
            ),
            "demand_factor": demand_factor,
            "supply_factor": supply_factor,
            "timestamp": time.time(),
        }

        self._stats[
            "prices_optimized"
        ] += 1

        return {
            "product_id": product_id,
            "base_price": base_price,
            "adjusted_price": round(
                adjusted, 2,
            ),
            "change_pct": round(
                (
                    (adjusted - base_price)
                    / base_price
                )
                * 100
                if base_price > 0
                else 0,
                1,
            ),
            "optimized": True,
        }

    def analyze_elasticity(
        self,
        product_id: str,
        price_changes: list[
            dict[str, float]
        ]
        | None = None,
    ) -> dict[str, Any]:
        """Esneklik analizi yapar.

        Args:
            product_id: Ürün kimliği.
            price_changes: Fiyat-talep
                değişimleri.

        Returns:
            Esneklik bilgisi.
        """
        price_changes = (
            price_changes or []
        )

        if len(price_changes) < 2:
            return {
                "product_id": product_id,
                "elasticity": 0.0,
                "type": "unknown",
                "analyzed": True,
            }

        p1 = price_changes[0]
        p2 = price_changes[-1]

        pct_demand = (
            (
                p2.get("demand", 0)
                - p1.get("demand", 0)
            )
            / p1.get("demand", 1)
            if p1.get("demand", 0) > 0
            else 0
        )
        pct_price = (
            (
                p2.get("price", 0)
                - p1.get("price", 0)
            )
            / p1.get("price", 1)
            if p1.get("price", 0) > 0
            else 0
        )

        elasticity = (
            abs(pct_demand / pct_price)
            if pct_price != 0
            else 0.0
        )

        if elasticity > 1:
            etype = "elastic"
        elif elasticity < 1:
            etype = "inelastic"
        else:
            etype = "unit_elastic"

        return {
            "product_id": product_id,
            "elasticity": round(
                elasticity, 3,
            ),
            "type": etype,
            "analyzed": True,
        }

    def compare_competitors(
        self,
        product_id: str,
        our_price: float = 0.0,
        competitor_prices: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Rakip fiyatları karşılaştırır.

        Args:
            product_id: Ürün kimliği.
            our_price: Bizim fiyatımız.
            competitor_prices: Rakip fiyatları.

        Returns:
            Karşılaştırma bilgisi.
        """
        competitor_prices = (
            competitor_prices or []
        )

        if not competitor_prices:
            return {
                "product_id": product_id,
                "position": "unknown",
                "compared": True,
            }

        avg_comp = (
            sum(competitor_prices)
            / len(competitor_prices)
        )
        min_comp = min(competitor_prices)
        max_comp = max(competitor_prices)

        if our_price < avg_comp * 0.9:
            position = "below_market"
        elif our_price > avg_comp * 1.1:
            position = "above_market"
        else:
            position = "at_market"

        self._competitors[product_id] = (
            [
                {"price": p}
                for p in competitor_prices
            ]
        )

        return {
            "product_id": product_id,
            "our_price": our_price,
            "avg_competitor": round(
                avg_comp, 2,
            ),
            "min_competitor": min_comp,
            "max_competitor": max_comp,
            "position": position,
            "compared": True,
        }

    def optimize_bundle(
        self,
        bundle_name: str,
        products: list[dict[str, Any]]
        | None = None,
        discount_pct: float = 10.0,
    ) -> dict[str, Any]:
        """Paket optimizasyonu yapar.

        Args:
            bundle_name: Paket adı.
            products: Ürünler.
            discount_pct: İndirim yüzdesi.

        Returns:
            Paket bilgisi.
        """
        products = products or []

        individual_total = sum(
            p.get("price", 0)
            for p in products
        )
        bundle_price = (
            individual_total
            * (1 - discount_pct / 100)
        )

        self._bundles[bundle_name] = {
            "name": bundle_name,
            "products": products,
            "individual_total": round(
                individual_total, 2,
            ),
            "bundle_price": round(
                bundle_price, 2,
            ),
            "discount_pct": discount_pct,
        }

        self._stats[
            "bundles_created"
        ] += 1

        return {
            "bundle_name": bundle_name,
            "product_count": len(products),
            "individual_total": round(
                individual_total, 2,
            ),
            "bundle_price": round(
                bundle_price, 2,
            ),
            "savings": round(
                individual_total
                - bundle_price,
                2,
            ),
            "optimized": True,
        }

    def protect_margin(
        self,
        product_id: str,
        cost: float = 0.0,
        current_price: float = 0.0,
        min_margin_pct: float = 20.0,
    ) -> dict[str, Any]:
        """Marj koruma yapar.

        Args:
            product_id: Ürün kimliği.
            cost: Maliyet.
            current_price: Güncel fiyat.
            min_margin_pct: Minimum marj.

        Returns:
            Koruma bilgisi.
        """
        margin = (
            (
                (current_price - cost)
                / current_price
            )
            * 100
            if current_price > 0
            else 0.0
        )

        protected = margin >= min_margin_pct
        min_price = (
            cost / (1 - min_margin_pct / 100)
            if min_margin_pct < 100
            else cost
        )

        return {
            "product_id": product_id,
            "current_margin": round(
                margin, 1,
            ),
            "min_margin": min_margin_pct,
            "protected": protected,
            "min_price": round(
                min_price, 2,
            ),
            "checked": True,
        }

    @property
    def optimized_count(self) -> int:
        """Optimize sayısı."""
        return self._stats[
            "prices_optimized"
        ]

    @property
    def bundle_count(self) -> int:
        """Paket sayısı."""
        return self._stats[
            "bundles_created"
        ]
