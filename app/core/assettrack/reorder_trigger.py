"""ATLAS Yeniden Sipariş Tetikleyici modülü.

Yeniden sipariş noktası hesaplama,
otomatik sipariş, tedarikçi seçimi,
tedarik süresi yönetimi, sipariş takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class InventoryReorderTrigger:
    """Yeniden sipariş tetikleyici.

    Stok yeniden sipariş süreçlerini yönetir.

    Attributes:
        _reorder_points: Sipariş noktaları.
        _orders: Sipariş kayıtları.
        _suppliers: Tedarikçi kayıtları.
    """

    def __init__(self) -> None:
        """Tetikleyiciyi başlatır."""
        self._reorder_points: dict[
            str, dict[str, Any]
        ] = {}
        self._orders: list[
            dict[str, Any]
        ] = []
        self._suppliers: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "orders_triggered": 0,
            "points_calculated": 0,
        }

        logger.info(
            "InventoryReorderTrigger "
            "baslatildi",
        )

    def calculate_reorder_point(
        self,
        item_id: str,
        daily_usage: float = 1.0,
        lead_time_days: int = 7,
        safety_stock: int = 10,
    ) -> dict[str, Any]:
        """Yeniden sipariş noktası hesaplar.

        Args:
            item_id: Ürün kimliği.
            daily_usage: Günlük kullanım.
            lead_time_days: Tedarik süresi.
            safety_stock: Güvenlik stoğu.

        Returns:
            Hesaplama bilgisi.
        """
        reorder_point = int(
            daily_usage * lead_time_days
            + safety_stock
        )

        self._reorder_points[item_id] = {
            "item_id": item_id,
            "reorder_point": reorder_point,
            "daily_usage": daily_usage,
            "lead_time_days": (
                lead_time_days
            ),
            "safety_stock": safety_stock,
        }

        self._stats[
            "points_calculated"
        ] += 1

        return {
            "item_id": item_id,
            "reorder_point": reorder_point,
            "daily_usage": daily_usage,
            "lead_time_days": (
                lead_time_days
            ),
            "safety_stock": safety_stock,
            "calculated": True,
        }

    def check_and_order(
        self,
        item_id: str,
        current_stock: int,
    ) -> dict[str, Any]:
        """Kontrol edip sipariş verir.

        Args:
            item_id: Ürün kimliği.
            current_stock: Mevcut stok.

        Returns:
            Sipariş bilgisi.
        """
        rp = self._reorder_points.get(
            item_id,
        )
        if not rp:
            return {
                "item_id": item_id,
                "found": False,
            }

        needs_order = (
            current_stock
            <= rp["reorder_point"]
        )

        order_qty = 0
        if needs_order:
            order_qty = int(
                rp["daily_usage"]
                * rp["lead_time_days"]
                * 2
            )
            self._trigger_order(
                item_id, order_qty,
            )

        return {
            "item_id": item_id,
            "current_stock": current_stock,
            "reorder_point": rp[
                "reorder_point"
            ],
            "needs_order": needs_order,
            "order_quantity": order_qty,
            "checked": True,
        }

    def select_supplier(
        self,
        item_id: str,
        suppliers: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Tedarikçi seçer.

        Args:
            item_id: Ürün kimliği.
            suppliers: Tedarikçi listesi.

        Returns:
            Seçim bilgisi.
        """
        suppliers = suppliers or []

        if not suppliers:
            return {
                "item_id": item_id,
                "selected": False,
                "reason": "no_suppliers",
            }

        best = min(
            suppliers,
            key=lambda s: s.get(
                "price", float("inf"),
            ),
        )

        return {
            "item_id": item_id,
            "supplier_id": best.get(
                "supplier_id", "",
            ),
            "price": best.get("price", 0),
            "selected": True,
        }

    def set_lead_time(
        self,
        item_id: str,
        lead_time_days: int,
    ) -> dict[str, Any]:
        """Tedarik süresini ayarlar.

        Args:
            item_id: Ürün kimliği.
            lead_time_days: Tedarik süresi.

        Returns:
            Ayar bilgisi.
        """
        rp = self._reorder_points.get(
            item_id,
        )
        if not rp:
            return {
                "item_id": item_id,
                "found": False,
            }

        rp["lead_time_days"] = (
            lead_time_days
        )
        rp["reorder_point"] = int(
            rp["daily_usage"]
            * lead_time_days
            + rp["safety_stock"]
        )

        return {
            "item_id": item_id,
            "lead_time_days": (
                lead_time_days
            ),
            "new_reorder_point": rp[
                "reorder_point"
            ],
            "updated": True,
        }

    def get_order_status(
        self,
        item_id: str = "",
    ) -> dict[str, Any]:
        """Sipariş durumunu sorgular.

        Args:
            item_id: Ürün kimliği (boşsa tümü).

        Returns:
            Durum bilgisi.
        """
        if item_id:
            orders = [
                o
                for o in self._orders
                if o["item_id"] == item_id
            ]
        else:
            orders = self._orders

        return {
            "total_orders": len(orders),
            "orders": orders,
            "retrieved": True,
        }

    def _trigger_order(
        self,
        item_id: str,
        quantity: int,
    ) -> None:
        """Sipariş tetikler.

        Args:
            item_id: Ürün kimliği.
            quantity: Miktar.
        """
        self._counter += 1
        self._orders.append({
            "order_id": (
                f"ord_{self._counter}"
            ),
            "item_id": item_id,
            "quantity": quantity,
            "status": "pending",
            "created_at": time.time(),
        })
        self._stats[
            "orders_triggered"
        ] += 1

    @property
    def order_count(self) -> int:
        """Sipariş sayısı."""
        return self._stats[
            "orders_triggered"
        ]

    @property
    def point_count(self) -> int:
        """Hesaplanan nokta sayısı."""
        return self._stats[
            "points_calculated"
        ]
