"""ATLAS Satın Alma Orkestratör modülü.

Tam satın alma pipeline,
Find → Compare → Decide → Order → Track → Verify,
otonom operasyon, analitik.
"""

import logging
import time
from typing import Any

from app.core.purchasing.budget_checker import (
    PurchaseBudgetChecker,
)
from app.core.purchasing.order_tracker import (
    OrderTracker,
)
from app.core.purchasing.price_comparator import (
    PriceComparator,
)
from app.core.purchasing.purchase_decision_engine import (
    PurchaseDecisionEngine,
)
from app.core.purchasing.quality_verifier import (
    QualityVerifier,
)
from app.core.purchasing.reorder_predictor import (
    ReorderPredictor,
)
from app.core.purchasing.supplier_finder import (
    SupplierFinder,
)
from app.core.purchasing.vendor_manager import (
    VendorManager,
)

logger = logging.getLogger(__name__)


class PurchasingOrchestrator:
    """Satın alma orkestratör.

    Tüm satın alma bileşenlerini
    koordine eder.

    Attributes:
        prices: Fiyat karşılaştırıcı.
        suppliers: Tedarikçi bulucu.
        decisions: Karar motoru.
        orders: Sipariş takipçisi.
        quality: Kalite doğrulayıcı.
        budget: Bütçe kontrolcüsü.
        reorder: Sipariş tahmincisi.
        vendors: Satıcı yöneticisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.prices = PriceComparator()
        self.suppliers = SupplierFinder()
        self.decisions = (
            PurchaseDecisionEngine()
        )
        self.orders = OrderTracker()
        self.quality = QualityVerifier()
        self.budget = PurchaseBudgetChecker()
        self.reorder = ReorderPredictor()
        self.vendors = VendorManager()
        self._stats = {
            "pipelines_run": 0,
            "purchases_made": 0,
        }

        logger.info(
            "PurchasingOrchestrator "
            "baslatildi",
        )

    def run_purchase_pipeline(
        self,
        item: str,
        quantity: int = 1,
        budget_category: str = "general",
        max_price: float = 0.0,
    ) -> dict[str, Any]:
        """Find → Compare → Decide → Order.

        Args:
            item: Ürün.
            quantity: Miktar.
            budget_category: Bütçe kategorisi.
            max_price: Maks fiyat.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Compare prices
        comparison = (
            self.prices.compare_prices(item)
        )

        # 2. Budget check
        price = (
            comparison.get(
                "cheapest_price", max_price,
            )
            if comparison.get("compared")
            else max_price
        )
        total_cost = price * quantity

        budget_check = (
            self.budget.check_budget(
                budget_category, total_cost,
            )
        )

        # 3. Decision
        approval = (
            self.decisions.route_approval(
                total_cost,
            )
        )

        # 4. Create order
        supplier = (
            comparison.get(
                "cheapest", "unknown",
            )
            if comparison.get("compared")
            else "unknown"
        )

        order = self.orders.create_order(
            item=item,
            supplier=supplier,
            quantity=quantity,
            unit_price=price,
        )

        self._stats["pipelines_run"] += 1
        self._stats["purchases_made"] += 1

        return {
            "order_id": order["order_id"],
            "item": item,
            "supplier": supplier,
            "total_cost": round(
                total_cost, 2,
            ),
            "budget_status": (
                budget_check.get(
                    "status", "no_budget",
                )
            ),
            "approval_level": approval[
                "approval_level"
            ],
            "pipeline_complete": True,
        }

    def autonomous_purchase(
        self,
        item: str,
        quantity: int = 1,
        auto_limit: float = 100.0,
    ) -> dict[str, Any]:
        """Otonom satın alma yapar.

        Args:
            item: Ürün.
            quantity: Miktar.
            auto_limit: Otomatik limit.

        Returns:
            Satın alma bilgisi.
        """
        # Fiyat kontrolü
        best_deal = (
            self.prices.find_best_deal(item)
        )
        price = (
            best_deal["price"]
            if best_deal.get("found")
            else auto_limit
        )
        total = price * quantity

        # Otonom karar
        if total <= auto_limit:
            order = self.orders.create_order(
                item=item,
                supplier=best_deal.get(
                    "supplier", "auto",
                ),
                quantity=quantity,
                unit_price=price,
            )
            self._stats[
                "purchases_made"
            ] += 1

            return {
                "order_id": order[
                    "order_id"
                ],
                "item": item,
                "total": round(total, 2),
                "auto_approved": True,
                "purchased": True,
            }

        return {
            "item": item,
            "total": round(total, 2),
            "auto_approved": False,
            "purchased": False,
            "reason": (
                f"Exceeds auto limit "
                f"${auto_limit}"
            ),
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": (
                self._stats["pipelines_run"]
            ),
            "purchases_made": (
                self._stats["purchases_made"]
            ),
            "price_comparisons": (
                self.prices.comparison_count
            ),
            "suppliers": (
                self.suppliers.supplier_count
            ),
            "decisions": (
                self.decisions.decision_count
            ),
            "orders": (
                self.orders.order_count
            ),
            "inspections": (
                self.quality.inspection_count
            ),
            "budget_checks": (
                self.budget.check_count
            ),
            "predictions": (
                self.reorder.prediction_count
            ),
            "vendors": (
                self.vendors.vendor_count
            ),
        }

    @property
    def purchase_count(self) -> int:
        """Satın alma sayısı."""
        return self._stats[
            "purchases_made"
        ]

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]
