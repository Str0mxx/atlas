"""ATLAS Coğrafi Konum Orkestratörü.

Tam geolocation yönetim pipeline,
Track → Detect → Alert → Optimize,
çoklu varlık takibi, analitik.
"""

import logging
from typing import Any

from app.core.geolocation.eta_calculator import (
    ETACalculator,
)
from app.core.geolocation.fleet_tracker import (
    FleetTracker,
)
from app.core.geolocation.geo_alert_engine import (
    GeoAlertEngine,
)
from app.core.geolocation.geofence_manager import (
    GeofenceManager,
)
from app.core.geolocation.location_history import (
    LocationHistory,
)
from app.core.geolocation.location_tracker import (
    LocationTracker,
)
from app.core.geolocation.proximity_trigger import (
    ProximityTrigger,
)
from app.core.geolocation.route_optimizer import (
    RouteOptimizer,
)

logger = logging.getLogger(__name__)


class GeolocationOrchestrator:
    """Coğrafi konum orkestratörü.

    Tüm geolocation bileşenlerini koordine eder.

    Attributes:
        geofence: Geofence yöneticisi.
        tracker: Konum takipçisi.
        proximity: Yakınlık tetikleyici.
        routes: Rota optimizer.
        eta: ETA hesaplayıcı.
        history: Konum geçmişi.
        alerts: Uyarı motoru.
        fleet: Filo takipçisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.geofence = GeofenceManager()
        self.tracker = LocationTracker()
        self.proximity = (
            ProximityTrigger()
        )
        self.routes = RouteOptimizer()
        self.eta = ETACalculator()
        self.history = LocationHistory()
        self.alerts = GeoAlertEngine()
        self.fleet = FleetTracker()
        self._stats = {
            "pipelines_run": 0,
            "assets_tracked": 0,
        }

        logger.info(
            "GeolocationOrchestrator "
            "baslatildi",
        )

    def track_and_detect(
        self,
        device_id: str,
        lat: float,
        lon: float,
        zone_id: str = "",
        prev_lat: float = 0.0,
        prev_lon: float = 0.0,
    ) -> dict[str, Any]:
        """Track → Detect → Alert pipeline.

        Args:
            device_id: Cihaz kimliği.
            lat: Enlem.
            lon: Boylam.
            zone_id: Zone kimliği.
            prev_lat: Önceki enlem.
            prev_lon: Önceki boylam.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Track
        track = self.tracker.track_realtime(
            device_id=device_id,
            lat=lat,
            lon=lon,
        )

        # 2. Store history
        self.history.store_location(
            device_id=device_id,
            lat=lat,
            lon=lon,
        )

        # 3. Detect geofence event
        event = "none"
        if zone_id:
            detection = (
                self.geofence.detect_entry_exit(
                    zone_id=zone_id,
                    prev_lat=prev_lat,
                    prev_lon=prev_lon,
                    curr_lat=lat,
                    curr_lon=lon,
                )
            )
            event = detection.get(
                "event", "none",
            )

            # 4. Alert if needed
            if event in (
                "entry",
                "exit",
            ):
                self.alerts.handle_geofence_event(
                    device_id=device_id,
                    zone_id=zone_id,
                    event=event,
                )

        self._stats[
            "pipelines_run"
        ] += 1

        return {
            "device_id": device_id,
            "tracked": True,
            "event": event,
            "pipeline_complete": True,
        }

    def multi_asset_track(
        self,
        assets: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Çoklu varlık takibi yapar.

        Args:
            assets: Varlık listesi.

        Returns:
            Takip bilgisi.
        """
        tracked = 0
        for asset in assets:
            self.tracker.track_realtime(
                device_id=asset.get(
                    "device_id", "",
                ),
                lat=asset.get("lat", 0.0),
                lon=asset.get("lon", 0.0),
            )
            tracked += 1

        self._stats[
            "assets_tracked"
        ] += tracked

        return {
            "assets_submitted": len(
                assets,
            ),
            "assets_tracked": tracked,
            "tracked": True,
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
                self._stats[
                    "pipelines_run"
                ]
            ),
            "assets_tracked": (
                self._stats[
                    "assets_tracked"
                ]
            ),
            "zones_created": (
                self.geofence.zone_count
            ),
            "location_updates": (
                self.tracker.update_count
            ),
            "triggers_fired": (
                self.proximity.trigger_count
            ),
            "routes_optimized": (
                self.routes.route_count
            ),
            "eta_estimates": (
                self.eta.estimate_count
            ),
            "history_records": (
                self.history.record_count
            ),
            "alerts_generated": (
                self.alerts.alert_count
            ),
            "vehicles_tracked": (
                self.fleet.vehicle_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def asset_count(self) -> int:
        """Takip edilen varlık sayısı."""
        return self._stats[
            "assets_tracked"
        ]
