"""ATLAS Coğrafi Uyarı Motoru modülü.

Konum tabanlı uyarılar, geofence olayları,
özel koşullar, çok kanallı bildirim,
uyarı bastırma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class GeoAlertEngine:
    """Coğrafi uyarı motoru.

    Konum tabanlı uyarı üretir ve yönetir.

    Attributes:
        _alerts: Uyarı kayıtları.
        _conditions: Koşul kayıtları.
        _suppressed: Bastırılan uyarılar.
    """

    def __init__(self) -> None:
        """Motoru başlatır."""
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._conditions: dict[
            str, dict[str, Any]
        ] = {}
        self._suppressed: set[str] = set()
        self._counter = 0
        self._stats = {
            "alerts_generated": 0,
            "alerts_suppressed": 0,
        }

        logger.info(
            "GeoAlertEngine baslatildi",
        )

    def create_location_alert(
        self,
        device_id: str,
        alert_type: str = "entry",
        zone_id: str = "",
        message: str = "",
    ) -> dict[str, Any]:
        """Konum tabanlı uyarı oluşturur.

        Args:
            device_id: Cihaz kimliği.
            alert_type: Uyarı tipi.
            zone_id: Zone kimliği.
            message: Mesaj.

        Returns:
            Uyarı bilgisi.
        """
        self._counter += 1
        aid = f"alert_{self._counter}"

        if aid in self._suppressed:
            self._stats[
                "alerts_suppressed"
            ] += 1
            return {
                "alert_id": aid,
                "suppressed": True,
                "generated": False,
            }

        alert = {
            "alert_id": aid,
            "device_id": device_id,
            "alert_type": alert_type,
            "zone_id": zone_id,
            "message": message,
            "created_at": time.time(),
        }

        self._alerts.append(alert)
        self._stats[
            "alerts_generated"
        ] += 1

        return {
            "alert_id": aid,
            "device_id": device_id,
            "alert_type": alert_type,
            "generated": True,
        }

    def handle_geofence_event(
        self,
        device_id: str,
        zone_id: str,
        event: str = "entry",
    ) -> dict[str, Any]:
        """Geofence olayını işler.

        Args:
            device_id: Cihaz kimliği.
            zone_id: Zone kimliği.
            event: Olay tipi.

        Returns:
            İşlem bilgisi.
        """
        alert = (
            self.create_location_alert(
                device_id=device_id,
                alert_type=event,
                zone_id=zone_id,
                message=(
                    f"Geofence {event}: "
                    f"{device_id} -> "
                    f"{zone_id}"
                ),
            )
        )

        return {
            "device_id": device_id,
            "zone_id": zone_id,
            "event": event,
            "alert_id": alert.get(
                "alert_id", "",
            ),
            "handled": True,
        }

    def define_condition(
        self,
        condition_id: str,
        condition_type: str = "",
        threshold: float = 0.0,
        action: str = "",
    ) -> dict[str, Any]:
        """Özel koşul tanımlar.

        Args:
            condition_id: Koşul kimliği.
            condition_type: Koşul tipi.
            threshold: Eşik değer.
            action: Aksiyon.

        Returns:
            Tanım bilgisi.
        """
        self._conditions[condition_id] = {
            "condition_id": condition_id,
            "type": condition_type,
            "threshold": threshold,
            "action": action,
            "created_at": time.time(),
        }

        return {
            "condition_id": condition_id,
            "condition_type": (
                condition_type
            ),
            "defined": True,
        }

    def notify_channels(
        self,
        alert_id: str,
        channels: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Çok kanallı bildirim gönderir.

        Args:
            alert_id: Uyarı kimliği.
            channels: Kanal listesi.

        Returns:
            Bildirim bilgisi.
        """
        channels = channels or [
            "telegram",
        ]

        alert = None
        for a in self._alerts:
            if a["alert_id"] == alert_id:
                alert = a
                break

        if not alert:
            return {
                "alert_id": alert_id,
                "found": False,
            }

        notified = []
        for ch in channels:
            notified.append({
                "channel": ch,
                "status": "sent",
            })

        return {
            "alert_id": alert_id,
            "channels_notified": len(
                notified,
            ),
            "channels": [
                n["channel"]
                for n in notified
            ],
            "notified": True,
        }

    def suppress_alert(
        self,
        alert_pattern: str,
        duration_sec: int = 3600,
    ) -> dict[str, Any]:
        """Uyarı bastırma kuralı ekler.

        Args:
            alert_pattern: Uyarı kalıbı.
            duration_sec: Bastırma süresi.

        Returns:
            Bastırma bilgisi.
        """
        self._suppressed.add(
            alert_pattern,
        )

        return {
            "pattern": alert_pattern,
            "duration_sec": duration_sec,
            "suppressed": True,
        }

    @property
    def alert_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "alerts_generated"
        ]

    @property
    def suppressed_count(self) -> int:
        """Bastırılan uyarı sayısı."""
        return self._stats[
            "alerts_suppressed"
        ]
