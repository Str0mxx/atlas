"""ATLAS Karlılık Hesaplayıcı modülü.

Marj analizi, ürün karlılığı,
müşteri karlılığı, proje karlılığı,
trend takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProfitabilityCalculator:
    """Karlılık hesaplayıcı.

    Farklı boyutlarda karlılık hesaplar.

    Attributes:
        _products: Ürün karlılıkları.
        _customers: Müşteri karlılıkları.
        _projects: Proje karlılıkları.
    """

    def __init__(self) -> None:
        """Hesaplayıcıyı başlatır."""
        self._products: dict[
            str, dict[str, Any]
        ] = {}
        self._customers: dict[
            str, dict[str, Any]
        ] = {}
        self._projects: dict[
            str, dict[str, Any]
        ] = {}
        self._margins: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "calculations": 0,
            "products_tracked": 0,
            "customers_tracked": 0,
            "projects_tracked": 0,
        }

        logger.info(
            "ProfitabilityCalculator "
            "baslatildi",
        )

    def calculate_margin(
        self,
        revenue: float,
        cost: float,
        label: str = "",
    ) -> dict[str, Any]:
        """Marj hesaplar.

        Args:
            revenue: Gelir.
            cost: Maliyet.
            label: Etiket.

        Returns:
            Marj bilgisi.
        """
        profit = revenue - cost
        margin = (
            round(profit / revenue * 100, 2)
            if revenue > 0 else 0.0
        )

        record = {
            "label": label,
            "revenue": revenue,
            "cost": cost,
            "profit": round(profit, 2),
            "margin_percent": margin,
            "timestamp": time.time(),
        }
        self._margins.append(record)
        self._stats["calculations"] += 1

        return {
            "revenue": revenue,
            "cost": cost,
            "profit": round(profit, 2),
            "margin_percent": margin,
            "profitable": profit > 0,
        }

    def track_product(
        self,
        product_id: str,
        revenue: float,
        cost: float,
        units: int = 1,
    ) -> dict[str, Any]:
        """Ürün karlılığı takip eder.

        Args:
            product_id: Ürün ID.
            revenue: Gelir.
            cost: Maliyet.
            units: Birim sayısı.

        Returns:
            Takip bilgisi.
        """
        if product_id not in self._products:
            self._products[product_id] = {
                "total_revenue": 0.0,
                "total_cost": 0.0,
                "total_units": 0,
                "records": [],
            }
            self._stats[
                "products_tracked"
            ] += 1

        prod = self._products[product_id]
        prod["total_revenue"] += revenue
        prod["total_cost"] += cost
        prod["total_units"] += units
        prod["records"].append({
            "revenue": revenue,
            "cost": cost,
            "units": units,
            "timestamp": time.time(),
        })

        profit = (
            prod["total_revenue"]
            - prod["total_cost"]
        )
        margin = (
            round(
                profit
                / prod["total_revenue"]
                * 100, 2,
            )
            if prod["total_revenue"] > 0
            else 0.0
        )

        return {
            "product_id": product_id,
            "total_profit": round(profit, 2),
            "margin_percent": margin,
            "total_units": prod["total_units"],
            "tracked": True,
        }

    def track_customer(
        self,
        customer_id: str,
        revenue: float,
        cost: float,
    ) -> dict[str, Any]:
        """Müşteri karlılığı takip eder.

        Args:
            customer_id: Müşteri ID.
            revenue: Gelir.
            cost: Maliyet.

        Returns:
            Takip bilgisi.
        """
        if customer_id not in (
            self._customers
        ):
            self._customers[customer_id] = {
                "total_revenue": 0.0,
                "total_cost": 0.0,
                "transactions": 0,
            }
            self._stats[
                "customers_tracked"
            ] += 1

        cust = self._customers[customer_id]
        cust["total_revenue"] += revenue
        cust["total_cost"] += cost
        cust["transactions"] += 1

        profit = (
            cust["total_revenue"]
            - cust["total_cost"]
        )

        return {
            "customer_id": customer_id,
            "total_profit": round(profit, 2),
            "transactions": cust[
                "transactions"
            ],
            "tracked": True,
        }

    def track_project(
        self,
        project_id: str,
        revenue: float,
        cost: float,
        status: str = "active",
    ) -> dict[str, Any]:
        """Proje karlılığı takip eder.

        Args:
            project_id: Proje ID.
            revenue: Gelir.
            cost: Maliyet.
            status: Durum.

        Returns:
            Takip bilgisi.
        """
        if project_id not in self._projects:
            self._projects[project_id] = {
                "total_revenue": 0.0,
                "total_cost": 0.0,
                "status": status,
            }
            self._stats[
                "projects_tracked"
            ] += 1

        proj = self._projects[project_id]
        proj["total_revenue"] += revenue
        proj["total_cost"] += cost
        proj["status"] = status

        profit = (
            proj["total_revenue"]
            - proj["total_cost"]
        )
        margin = (
            round(
                profit
                / proj["total_revenue"]
                * 100, 2,
            )
            if proj["total_revenue"] > 0
            else 0.0
        )

        return {
            "project_id": project_id,
            "total_profit": round(profit, 2),
            "margin_percent": margin,
            "status": status,
            "tracked": True,
        }

    def get_product_ranking(
        self,
    ) -> dict[str, Any]:
        """Ürün karlılık sıralaması."""
        rankings = []
        for pid, prod in (
            self._products.items()
        ):
            profit = (
                prod["total_revenue"]
                - prod["total_cost"]
            )
            margin = (
                round(
                    profit
                    / prod["total_revenue"]
                    * 100, 2,
                )
                if prod["total_revenue"] > 0
                else 0.0
            )
            rankings.append({
                "product_id": pid,
                "profit": round(profit, 2),
                "margin": margin,
                "units": prod["total_units"],
            })

        rankings.sort(
            key=lambda x: x["profit"],
            reverse=True,
        )

        return {
            "rankings": rankings,
            "count": len(rankings),
        }

    def get_customer_ranking(
        self,
    ) -> dict[str, Any]:
        """Müşteri karlılık sıralaması."""
        rankings = []
        for cid, cust in (
            self._customers.items()
        ):
            profit = (
                cust["total_revenue"]
                - cust["total_cost"]
            )
            rankings.append({
                "customer_id": cid,
                "profit": round(profit, 2),
                "revenue": round(
                    cust["total_revenue"], 2,
                ),
                "transactions": cust[
                    "transactions"
                ],
            })

        rankings.sort(
            key=lambda x: x["profit"],
            reverse=True,
        )

        return {
            "rankings": rankings,
            "count": len(rankings),
        }

    def get_trend(
        self,
    ) -> dict[str, Any]:
        """Karlılık trendini döndürür."""
        if len(self._margins) < 2:
            return {
                "trend": "insufficient_data",
                "avg_margin": 0.0,
            }

        margins = [
            m["margin_percent"]
            for m in self._margins
        ]
        avg = sum(margins) / len(margins)

        mid = len(margins) // 2
        first = (
            sum(margins[:mid]) / mid
            if mid > 0 else 0
        )
        second = (
            sum(margins[mid:])
            / len(margins[mid:])
        )

        trend = (
            "improving" if second > first + 2
            else "declining"
            if second < first - 2
            else "stable"
        )

        return {
            "trend": trend,
            "avg_margin": round(avg, 2),
            "recent_margin": round(
                second, 2,
            ),
            "count": len(margins),
        }

    @property
    def product_count(self) -> int:
        """Ürün sayısı."""
        return self._stats[
            "products_tracked"
        ]

    @property
    def customer_count(self) -> int:
        """Müşteri sayısı."""
        return self._stats[
            "customers_tracked"
        ]

    @property
    def project_count(self) -> int:
        """Proje sayısı."""
        return self._stats[
            "projects_tracked"
        ]
