"""ATLAS Stok Seviyesi Takipçisi modülü.

Miktar takibi, min/max seviyeler,
stok hareketleri, rezervasyon yönetimi,
çoklu lokasyon.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class StockLevelTracker:
    """Stok seviyesi takipçisi.

    Stok miktarlarını ve hareketlerini izler.

    Attributes:
        _items: Stok kayıtları.
        _movements: Hareket kayıtları.
        _reservations: Rezervasyonlar.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._items: dict[
            str, dict[str, Any]
        ] = {}
        self._movements: list[
            dict[str, Any]
        ] = []
        self._reservations: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "items_tracked": 0,
            "movements_logged": 0,
        }

        logger.info(
            "StockLevelTracker "
            "baslatildi",
        )

    def track_quantity(
        self,
        item_id: str,
        quantity: int,
        location: str = "main",
    ) -> dict[str, Any]:
        """Miktar takibi yapar.

        Args:
            item_id: Ürün kimliği.
            quantity: Miktar.
            location: Lokasyon.

        Returns:
            Takip bilgisi.
        """
        key = f"{item_id}_{location}"
        is_new = key not in self._items

        self._items[key] = {
            "item_id": item_id,
            "quantity": quantity,
            "location": location,
            "updated_at": time.time(),
        }

        if is_new:
            self._stats[
                "items_tracked"
            ] += 1

        return {
            "item_id": item_id,
            "quantity": quantity,
            "location": location,
            "tracked": True,
        }

    def set_levels(
        self,
        item_id: str,
        min_level: int = 0,
        max_level: int = 1000,
        location: str = "main",
    ) -> dict[str, Any]:
        """Min/max seviyeleri belirler.

        Args:
            item_id: Ürün kimliği.
            min_level: Minimum seviye.
            max_level: Maksimum seviye.
            location: Lokasyon.

        Returns:
            Seviye bilgisi.
        """
        key = f"{item_id}_{location}"
        item = self._items.get(key)
        if not item:
            return {
                "item_id": item_id,
                "found": False,
            }

        item["min_level"] = min_level
        item["max_level"] = max_level

        current = item.get("quantity", 0)
        if current <= min_level:
            alert = "below_minimum"
        elif current >= max_level:
            alert = "above_maximum"
        else:
            alert = "normal"

        return {
            "item_id": item_id,
            "min_level": min_level,
            "max_level": max_level,
            "current": current,
            "alert": alert,
            "set": True,
        }

    def log_movement(
        self,
        item_id: str,
        movement_type: str = "inbound",
        quantity: int = 0,
        location: str = "main",
    ) -> dict[str, Any]:
        """Stok hareketi kaydeder.

        Args:
            item_id: Ürün kimliği.
            movement_type: Hareket tipi.
            quantity: Miktar.
            location: Lokasyon.

        Returns:
            Hareket bilgisi.
        """
        key = f"{item_id}_{location}"
        item = self._items.get(key)

        if item:
            if movement_type == "inbound":
                item["quantity"] += quantity
            elif movement_type == "outbound":
                item["quantity"] = max(
                    0,
                    item["quantity"]
                    - quantity,
                )

        self._movements.append({
            "item_id": item_id,
            "type": movement_type,
            "quantity": quantity,
            "location": location,
            "timestamp": time.time(),
        })

        self._stats[
            "movements_logged"
        ] += 1

        return {
            "item_id": item_id,
            "movement_type": movement_type,
            "quantity": quantity,
            "new_quantity": (
                item["quantity"]
                if item
                else 0
            ),
            "logged": True,
        }

    def reserve_stock(
        self,
        item_id: str,
        quantity: int,
        requester: str = "",
        location: str = "main",
    ) -> dict[str, Any]:
        """Stok rezervasyonu yapar.

        Args:
            item_id: Ürün kimliği.
            quantity: Miktar.
            requester: Talep eden.
            location: Lokasyon.

        Returns:
            Rezervasyon bilgisi.
        """
        key = f"{item_id}_{location}"
        item = self._items.get(key)

        if not item:
            return {
                "item_id": item_id,
                "found": False,
            }

        available = item["quantity"]
        reserved = quantity <= available

        if reserved:
            if key not in self._reservations:
                self._reservations[key] = []
            self._reservations[key].append({
                "quantity": quantity,
                "requester": requester,
                "timestamp": time.time(),
            })

        return {
            "item_id": item_id,
            "requested": quantity,
            "available": available,
            "reserved": reserved,
        }

    def get_multi_location(
        self,
        item_id: str,
    ) -> dict[str, Any]:
        """Çoklu lokasyon stok sorgular.

        Args:
            item_id: Ürün kimliği.

        Returns:
            Lokasyon bilgisi.
        """
        locations = []
        total = 0

        for key, item in (
            self._items.items()
        ):
            if item["item_id"] == item_id:
                locations.append({
                    "location": item[
                        "location"
                    ],
                    "quantity": item[
                        "quantity"
                    ],
                })
                total += item["quantity"]

        return {
            "item_id": item_id,
            "locations": len(locations),
            "total_quantity": total,
            "details": locations,
            "retrieved": True,
        }

    @property
    def item_count(self) -> int:
        """Takip edilen ürün sayısı."""
        return self._stats[
            "items_tracked"
        ]

    @property
    def movement_count(self) -> int:
        """Hareket sayısı."""
        return self._stats[
            "movements_logged"
        ]
