"""ATLAS Varlık Kayıt Defteri modülü.

Varlık kaydı, kategorizasyon,
metadata yönetimi, yaşam döngüsü takibi,
sahiplik atama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AssetRegistry:
    """Varlık kayıt defteri.

    Fiziksel varlıkları kaydeder ve yönetir.

    Attributes:
        _assets: Varlık kayıtları.
        _owners: Sahiplik atamaları.
    """

    def __init__(self) -> None:
        """Kayıt defterini başlatır."""
        self._assets: dict[
            str, dict[str, Any]
        ] = {}
        self._owners: dict[
            str, str
        ] = {}
        self._counter = 0
        self._stats = {
            "assets_registered": 0,
            "assets_disposed": 0,
        }

        logger.info(
            "AssetRegistry baslatildi",
        )

    def register_asset(
        self,
        name: str,
        category: str = "equipment",
        purchase_cost: float = 0.0,
        serial_number: str = "",
    ) -> dict[str, Any]:
        """Varlık kaydeder.

        Args:
            name: Varlık adı.
            category: Kategori.
            purchase_cost: Satın alma maliyeti.
            serial_number: Seri numarası.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        aid = f"asset_{self._counter}"

        self._assets[aid] = {
            "asset_id": aid,
            "name": name,
            "category": category,
            "purchase_cost": purchase_cost,
            "serial_number": serial_number,
            "status": "active",
            "metadata": {},
            "created_at": time.time(),
        }

        self._stats[
            "assets_registered"
        ] += 1

        return {
            "asset_id": aid,
            "name": name,
            "category": category,
            "registered": True,
        }

    def categorize(
        self,
        asset_id: str,
        category: str,
        subcategory: str = "",
    ) -> dict[str, Any]:
        """Varlığı kategorize eder.

        Args:
            asset_id: Varlık kimliği.
            category: Kategori.
            subcategory: Alt kategori.

        Returns:
            Kategorizasyon bilgisi.
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return {
                "asset_id": asset_id,
                "found": False,
            }

        asset["category"] = category
        if subcategory:
            asset["subcategory"] = (
                subcategory
            )

        return {
            "asset_id": asset_id,
            "category": category,
            "subcategory": subcategory,
            "categorized": True,
        }

    def manage_metadata(
        self,
        asset_id: str,
        key: str,
        value: Any = None,
        action: str = "set",
    ) -> dict[str, Any]:
        """Metadata yönetimi yapar.

        Args:
            asset_id: Varlık kimliği.
            key: Anahtar.
            value: Değer.
            action: Aksiyon (set/delete).

        Returns:
            Yönetim bilgisi.
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return {
                "asset_id": asset_id,
                "found": False,
            }

        if action == "set":
            asset["metadata"][key] = value
        elif action == "delete":
            asset["metadata"].pop(
                key, None,
            )

        return {
            "asset_id": asset_id,
            "key": key,
            "action": action,
            "managed": True,
        }

    def track_lifecycle(
        self,
        asset_id: str,
        new_status: str = "active",
    ) -> dict[str, Any]:
        """Yaşam döngüsü takibi yapar.

        Args:
            asset_id: Varlık kimliği.
            new_status: Yeni durum.

        Returns:
            Takip bilgisi.
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return {
                "asset_id": asset_id,
                "found": False,
            }

        old_status = asset["status"]
        asset["status"] = new_status

        if new_status == "disposed":
            self._stats[
                "assets_disposed"
            ] += 1

        return {
            "asset_id": asset_id,
            "old_status": old_status,
            "new_status": new_status,
            "updated": True,
        }

    def assign_owner(
        self,
        asset_id: str,
        owner_id: str,
    ) -> dict[str, Any]:
        """Sahiplik atar.

        Args:
            asset_id: Varlık kimliği.
            owner_id: Sahip kimliği.

        Returns:
            Atama bilgisi.
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return {
                "asset_id": asset_id,
                "found": False,
            }

        self._owners[asset_id] = owner_id
        asset["owner_id"] = owner_id

        return {
            "asset_id": asset_id,
            "owner_id": owner_id,
            "assigned": True,
        }

    @property
    def asset_count(self) -> int:
        """Varlık sayısı."""
        return self._stats[
            "assets_registered"
        ]

    @property
    def disposed_count(self) -> int:
        """Elden çıkarılan sayısı."""
        return self._stats[
            "assets_disposed"
        ]
