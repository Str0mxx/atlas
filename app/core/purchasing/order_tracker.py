"""ATLAS Sipariş Takipçisi modülü.

Sipariş durumu, sevkiyat takibi,
teslimat tahmini, sorun tespiti,
geçmiş yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class OrderTracker:
    """Sipariş takipçisi.

    Siparişleri takip eder.

    Attributes:
        _orders: Sipariş kayıtları.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._orders: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "orders_tracked": 0,
            "issues_detected": 0,
            "deliveries_completed": 0,
        }

        logger.info(
            "OrderTracker baslatildi",
        )

    def create_order(
        self,
        item: str,
        supplier: str,
        quantity: int = 1,
        unit_price: float = 0.0,
    ) -> dict[str, Any]:
        """Sipariş oluşturur.

        Args:
            item: Ürün.
            supplier: Tedarikçi.
            quantity: Miktar.
            unit_price: Birim fiyat.

        Returns:
            Sipariş bilgisi.
        """
        self._counter += 1
        oid = f"ord_{self._counter}"

        order = {
            "order_id": oid,
            "item": item,
            "supplier": supplier,
            "quantity": quantity,
            "unit_price": unit_price,
            "total": round(
                quantity * unit_price, 2,
            ),
            "status": "pending",
            "shipment": None,
            "issues": [],
            "timestamp": time.time(),
        }
        self._orders[oid] = order
        self._stats[
            "orders_tracked"
        ] += 1

        return {
            "order_id": oid,
            "item": item,
            "total": order["total"],
            "status": "pending",
            "created": True,
        }

    def update_status(
        self,
        order_id: str,
        status: str,
    ) -> dict[str, Any]:
        """Durum günceller.

        Args:
            order_id: Sipariş ID.
            status: Durum.

        Returns:
            Güncelleme bilgisi.
        """
        if order_id not in self._orders:
            return {
                "order_id": order_id,
                "updated": False,
            }

        self._orders[order_id][
            "status"
        ] = status

        if status == "delivered":
            self._stats[
                "deliveries_completed"
            ] += 1

        return {
            "order_id": order_id,
            "status": status,
            "updated": True,
        }

    def track_shipment(
        self,
        order_id: str,
        carrier: str = "",
        tracking_number: str = "",
        estimated_days: int = 0,
    ) -> dict[str, Any]:
        """Sevkiyat takip eder.

        Args:
            order_id: Sipariş ID.
            carrier: Taşıyıcı.
            tracking_number: Takip no.
            estimated_days: Tahmini gün.

        Returns:
            Sevkiyat bilgisi.
        """
        if order_id not in self._orders:
            return {
                "order_id": order_id,
                "tracked": False,
            }

        shipment = {
            "carrier": carrier,
            "tracking_number": (
                tracking_number
            ),
            "estimated_days": estimated_days,
            "timestamp": time.time(),
        }
        self._orders[order_id][
            "shipment"
        ] = shipment
        self._orders[order_id][
            "status"
        ] = "shipped"

        return {
            "order_id": order_id,
            "carrier": carrier,
            "tracking_number": (
                tracking_number
            ),
            "estimated_days": estimated_days,
            "tracked": True,
        }

    def predict_delivery(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        """Teslimat tahmin eder.

        Args:
            order_id: Sipariş ID.

        Returns:
            Tahmin bilgisi.
        """
        if order_id not in self._orders:
            return {
                "order_id": order_id,
                "predicted": False,
            }

        order = self._orders[order_id]
        shipment = order.get("shipment")

        if not shipment:
            return {
                "order_id": order_id,
                "predicted": False,
                "reason": "No shipment info",
            }

        est_days = shipment.get(
            "estimated_days", 7,
        )
        confidence = (
            "high" if est_days <= 3
            else "medium" if est_days <= 7
            else "low"
        )

        return {
            "order_id": order_id,
            "estimated_days": est_days,
            "confidence": confidence,
            "status": order["status"],
            "predicted": True,
        }

    def detect_issues(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        """Sorun tespit eder.

        Args:
            order_id: Sipariş ID.

        Returns:
            Sorun bilgisi.
        """
        if order_id not in self._orders:
            return {
                "order_id": order_id,
                "checked": False,
            }

        order = self._orders[order_id]
        issues = []

        if order["status"] == "pending":
            age = (
                time.time()
                - order["timestamp"]
            )
            if age > 86400:
                issues.append(
                    "Order pending > 24h",
                )

        if (
            order["status"] == "shipped"
            and order.get("shipment")
        ):
            est = order["shipment"].get(
                "estimated_days", 0,
            )
            if est > 14:
                issues.append(
                    "Long delivery estimate",
                )

        if issues:
            order["issues"].extend(issues)
            self._stats[
                "issues_detected"
            ] += len(issues)

        return {
            "order_id": order_id,
            "issues": issues,
            "issue_count": len(issues),
            "checked": True,
        }

    def get_history(
        self,
        supplier: str = "",
        status: str = "",
    ) -> list[dict[str, Any]]:
        """Geçmiş döndürür."""
        orders = list(
            self._orders.values(),
        )
        if supplier:
            orders = [
                o for o in orders
                if o["supplier"] == supplier
            ]
        if status:
            orders = [
                o for o in orders
                if o["status"] == status
            ]
        return [
            {
                "order_id": o["order_id"],
                "item": o["item"],
                "status": o["status"],
                "total": o["total"],
            }
            for o in orders
        ]

    def get_order(
        self,
        order_id: str,
    ) -> dict[str, Any] | None:
        """Sipariş döndürür."""
        return self._orders.get(order_id)

    @property
    def order_count(self) -> int:
        """Sipariş sayısı."""
        return self._stats[
            "orders_tracked"
        ]

    @property
    def delivery_count(self) -> int:
        """Teslimat sayısı."""
        return self._stats[
            "deliveries_completed"
        ]
