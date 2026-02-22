"""Location Node - konum dugum modulu.

GPS konum takibi ve gecmis sorgulama islevleri.
"""

import logging
import time
from typing import Optional

from app.models.nodes_models import LocationData, NodesConfig

logger = logging.getLogger(__name__)


class LocationNode:
    """Konum dugumu yonetim sinifi."""

    def __init__(self, config: Optional[NodesConfig] = None) -> None:
        """LocationNode baslatici."""
        self.config = config or NodesConfig()
        self._locations: dict[str, list[LocationData]] = {}
        self._intervals: dict[str, int] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina yeni bir giris ekler."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details or {}})

    def get_history(self) -> list[dict]:
        return list(self._history)

    def get_stats(self) -> dict:
        total = sum(len(v) for v in self._locations.values())
        return {"tracked_nodes": len(self._locations), "total_points": total}

    def get_location(self, node_id: str) -> Optional[LocationData]:
        """Dugumun en son konum verisini dondurur."""
        locs = self._locations.get(node_id, [])
        if not locs:
            return None
        self._record_history("get_location", {"node_id": node_id})
        return locs[-1]

    def update_location(self, data: LocationData) -> None:
        """Konum verisini gunceller."""
        data.timestamp = data.timestamp or time.time()
        self._locations.setdefault(data.node_id, []).append(data)
        self._record_history("update_location", {"node_id": data.node_id})

    def get_location_history(self, node_id: str, limit: int = 10) -> list[LocationData]:
        """Dugumun konum gecmisini dondurur."""
        return self._locations.get(node_id, [])[-limit:]

    def set_update_interval(self, node_id: str, seconds: int) -> None:
        """Konum guncelleme sikligini ayarlar."""
        self._intervals[node_id] = max(1, seconds)
        self._record_history("set_update_interval", {"node_id": node_id, "seconds": seconds})

    def get_address(self, lat: float, lon: float) -> str:
        """Ters geocoding (stub)."""
        self._record_history("get_address", {"lat": lat, "lon": lon})
        return f"Address near ({lat:.4f}, {lon:.4f})"
