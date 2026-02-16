"""ATLAS Yeniden Sipariş Tahmincisi modülü.

Tüketim analizi, tedarik süresi hesaplama,
yeniden sipariş noktası, güvenlik stoku,
otomatik sipariş.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ReorderPredictor:
    """Yeniden sipariş tahmincisi.

    Stok yenileme ihtiyacını tahmin eder.

    Attributes:
        _items: Ürün kayıtları.
        _consumption: Tüketim kayıtları.
    """

    def __init__(self) -> None:
        """Tahminciyı başlatır."""
        self._items: dict[
            str, dict[str, Any]
        ] = {}
        self._consumption: dict[
            str, list[float]
        ] = {}
        self._auto_orders: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "predictions_made": 0,
            "auto_orders_created": 0,
        }

        logger.info(
            "ReorderPredictor baslatildi",
        )

    def track_item(
        self,
        item: str,
        current_stock: int = 0,
        lead_time_days: int = 7,
        min_order_qty: int = 1,
    ) -> dict[str, Any]:
        """Ürün takip eder.

        Args:
            item: Ürün.
            current_stock: Mevcut stok.
            lead_time_days: Tedarik süresi.
            min_order_qty: Min sipariş.

        Returns:
            Takip bilgisi.
        """
        self._counter += 1
        iid = f"item_{self._counter}"

        self._items[item] = {
            "item_id": iid,
            "item": item,
            "current_stock": current_stock,
            "lead_time_days": lead_time_days,
            "min_order_qty": min_order_qty,
            "timestamp": time.time(),
        }

        return {
            "item_id": iid,
            "item": item,
            "current_stock": current_stock,
            "tracked": True,
        }

    def record_consumption(
        self,
        item: str,
        daily_usage: float,
    ) -> dict[str, Any]:
        """Tüketim kaydeder.

        Args:
            item: Ürün.
            daily_usage: Günlük kullanım.

        Returns:
            Kayıt bilgisi.
        """
        if item not in self._consumption:
            self._consumption[item] = []
        self._consumption[item].append(
            daily_usage,
        )

        return {
            "item": item,
            "daily_usage": daily_usage,
            "data_points": len(
                self._consumption[item],
            ),
            "recorded": True,
        }

    def analyze_consumption(
        self,
        item: str,
    ) -> dict[str, Any]:
        """Tüketim analizi yapar.

        Args:
            item: Ürün.

        Returns:
            Analiz bilgisi.
        """
        usage = self._consumption.get(
            item, [],
        )

        if not usage:
            return {
                "item": item,
                "analyzed": False,
            }

        avg_daily = round(
            sum(usage) / len(usage), 2,
        )
        max_daily = max(usage)
        min_daily = min(usage)

        trend = (
            "increasing"
            if len(usage) >= 2
            and usage[-1] > avg_daily * 1.1
            else "decreasing"
            if len(usage) >= 2
            and usage[-1] < avg_daily * 0.9
            else "stable"
        )

        return {
            "item": item,
            "avg_daily": avg_daily,
            "max_daily": max_daily,
            "min_daily": min_daily,
            "trend": trend,
            "data_points": len(usage),
            "analyzed": True,
        }

    def calculate_lead_time(
        self,
        item: str,
        supplier_lead_days: int = 0,
        buffer_days: int = 2,
    ) -> dict[str, Any]:
        """Tedarik süresi hesaplar.

        Args:
            item: Ürün.
            supplier_lead_days: Tedarik günü.
            buffer_days: Tampon günü.

        Returns:
            Süre bilgisi.
        """
        item_data = self._items.get(item)
        base_lead = (
            supplier_lead_days
            or (
                item_data["lead_time_days"]
                if item_data else 7
            )
        )

        total_lead = base_lead + buffer_days

        return {
            "item": item,
            "base_lead_days": base_lead,
            "buffer_days": buffer_days,
            "total_lead_days": total_lead,
        }

    def calculate_reorder_point(
        self,
        item: str,
    ) -> dict[str, Any]:
        """Yeniden sipariş noktası hesaplar.

        Args:
            item: Ürün.

        Returns:
            Nokta bilgisi.
        """
        analysis = self.analyze_consumption(
            item,
        )
        if not analysis.get("analyzed"):
            return {
                "item": item,
                "calculated": False,
            }

        avg_daily = analysis["avg_daily"]
        item_data = self._items.get(item, {})
        lead_time = item_data.get(
            "lead_time_days", 7,
        )

        # ROP = avg_daily * lead_time
        rop = round(
            avg_daily * lead_time, 0,
        )

        # Safety stock
        max_daily = analysis["max_daily"]
        safety = round(
            (max_daily - avg_daily)
            * lead_time, 0,
        )

        total_rop = int(rop + safety)

        self._stats[
            "predictions_made"
        ] += 1

        return {
            "item": item,
            "reorder_point": total_rop,
            "base_rop": int(rop),
            "safety_stock": int(safety),
            "avg_daily": avg_daily,
            "lead_time": lead_time,
            "calculated": True,
        }

    def calculate_safety_stock(
        self,
        item: str,
        service_level: float = 0.95,
    ) -> dict[str, Any]:
        """Güvenlik stoku hesaplar.

        Args:
            item: Ürün.
            service_level: Hizmet seviyesi.

        Returns:
            Stok bilgisi.
        """
        usage = self._consumption.get(
            item, [],
        )

        if not usage:
            return {
                "item": item,
                "calculated": False,
            }

        avg = sum(usage) / len(usage)
        max_usage = max(usage)
        item_data = self._items.get(item, {})
        lead_time = item_data.get(
            "lead_time_days", 7,
        )

        # Basit güvenlik stoku
        z_factor = (
            1.65 if service_level >= 0.95
            else 1.28 if service_level >= 0.90
            else 1.0
        )
        variability = max_usage - avg
        safety = round(
            z_factor * variability
            * lead_time ** 0.5, 0,
        )

        return {
            "item": item,
            "safety_stock": int(safety),
            "service_level": service_level,
            "z_factor": z_factor,
            "calculated": True,
        }

    def auto_reorder(
        self,
        item: str,
    ) -> dict[str, Any]:
        """Otomatik sipariş oluşturur.

        Args:
            item: Ürün.

        Returns:
            Sipariş bilgisi.
        """
        item_data = self._items.get(item)

        if not item_data:
            return {
                "item": item,
                "ordered": False,
                "reason": "Item not tracked",
            }

        rop_result = (
            self.calculate_reorder_point(item)
        )
        if not rop_result.get("calculated"):
            return {
                "item": item,
                "ordered": False,
                "reason": "Cannot calculate ROP",
            }

        stock = item_data["current_stock"]
        rop = rop_result["reorder_point"]

        if stock > rop:
            return {
                "item": item,
                "ordered": False,
                "reason": "Stock sufficient",
                "current_stock": stock,
                "reorder_point": rop,
            }

        qty = max(
            item_data["min_order_qty"],
            rop - stock + rop_result.get(
                "safety_stock", 0,
            ),
        )

        order = {
            "item": item,
            "quantity": int(qty),
            "reorder_point": rop,
            "current_stock": stock,
            "timestamp": time.time(),
        }
        self._auto_orders.append(order)
        self._stats[
            "auto_orders_created"
        ] += 1

        return {
            "item": item,
            "quantity": int(qty),
            "reorder_point": rop,
            "ordered": True,
        }

    @property
    def prediction_count(self) -> int:
        """Tahmin sayısı."""
        return self._stats[
            "predictions_made"
        ]

    @property
    def auto_order_count(self) -> int:
        """Otomatik sipariş sayısı."""
        return self._stats[
            "auto_orders_created"
        ]
