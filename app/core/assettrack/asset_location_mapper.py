"""ATLAS Varlık Konum Haritacısı modülü.

Konum takibi, transfer kaydı,
zone eşleme, konum arama,
görselleştirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AssetLocationMapper:
    """Varlık konum haritacısı.

    Varlık konumlarını takip ve haritalandırır.

    Attributes:
        _locations: Konum kayıtları.
        _transfers: Transfer kayıtları.
        _zones: Zone tanımları.
    """

    def __init__(self) -> None:
        """Haritacıyı başlatır."""
        self._locations: dict[
            str, dict[str, Any]
        ] = {}
        self._transfers: list[
            dict[str, Any]
        ] = []
        self._zones: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "locations_tracked": 0,
            "transfers_logged": 0,
        }

        logger.info(
            "AssetLocationMapper "
            "baslatildi",
        )

    def track_location(
        self,
        asset_id: str,
        location: str,
        building: str = "",
        floor: str = "",
        room: str = "",
    ) -> dict[str, Any]:
        """Varlık konumunu takip eder.

        Args:
            asset_id: Varlık kimliği.
            location: Konum adı.
            building: Bina.
            floor: Kat.
            room: Oda.

        Returns:
            Takip bilgisi.
        """
        is_new = (
            asset_id
            not in self._locations
        )

        self._locations[asset_id] = {
            "asset_id": asset_id,
            "location": location,
            "building": building,
            "floor": floor,
            "room": room,
            "updated_at": time.time(),
        }

        if is_new:
            self._stats[
                "locations_tracked"
            ] += 1

        return {
            "asset_id": asset_id,
            "location": location,
            "tracked": True,
        }

    def log_transfer(
        self,
        asset_id: str,
        from_location: str,
        to_location: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Transfer kaydeder.

        Args:
            asset_id: Varlık kimliği.
            from_location: Kaynak konum.
            to_location: Hedef konum.
            reason: Sebep.

        Returns:
            Transfer bilgisi.
        """
        self._transfers.append({
            "asset_id": asset_id,
            "from": from_location,
            "to": to_location,
            "reason": reason,
            "timestamp": time.time(),
        })

        if asset_id in self._locations:
            self._locations[asset_id][
                "location"
            ] = to_location

        self._stats[
            "transfers_logged"
        ] += 1

        return {
            "asset_id": asset_id,
            "from": from_location,
            "to": to_location,
            "transferred": True,
        }

    def map_zone(
        self,
        zone_name: str,
        description: str = "",
        capacity: int = 0,
    ) -> dict[str, Any]:
        """Zone tanımlar.

        Args:
            zone_name: Zone adı.
            description: Açıklama.
            capacity: Kapasite.

        Returns:
            Tanım bilgisi.
        """
        self._zones[zone_name] = {
            "name": zone_name,
            "description": description,
            "capacity": capacity,
            "created_at": time.time(),
        }

        return {
            "zone_name": zone_name,
            "capacity": capacity,
            "mapped": True,
        }

    def search_by_location(
        self,
        location: str,
    ) -> dict[str, Any]:
        """Konuma göre arar.

        Args:
            location: Konum adı.

        Returns:
            Arama bilgisi.
        """
        found = [
            {
                "asset_id": loc[
                    "asset_id"
                ],
                "location": loc[
                    "location"
                ],
            }
            for loc in (
                self._locations.values()
            )
            if loc["location"] == location
        ]

        return {
            "location": location,
            "assets_found": len(found),
            "assets": found,
            "searched": True,
        }

    def get_visualization(
        self,
    ) -> dict[str, Any]:
        """Konum görselleştirmesi döndürür.

        Returns:
            Görselleştirme bilgisi.
        """
        location_summary: dict[
            str, int
        ] = {}
        for loc in (
            self._locations.values()
        ):
            name = loc["location"]
            location_summary[name] = (
                location_summary.get(
                    name, 0,
                )
                + 1
            )

        return {
            "total_assets": len(
                self._locations,
            ),
            "locations": len(
                location_summary,
            ),
            "distribution": (
                location_summary
            ),
            "zones": len(self._zones),
            "generated": True,
        }

    @property
    def location_count(self) -> int:
        """Takip edilen konum sayısı."""
        return self._stats[
            "locations_tracked"
        ]

    @property
    def transfer_count(self) -> int:
        """Transfer sayısı."""
        return self._stats[
            "transfers_logged"
        ]
