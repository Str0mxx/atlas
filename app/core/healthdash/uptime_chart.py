"""
Çalışma süresi grafiği modülü.

Uptime görselleştirme, downtime kaydı,
SLA takibi, geçmiş görünüm,
olay işaretleri.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class UptimeChart:
    """Çalışma süresi grafiği.

    Attributes:
        _services: Servis kayıtları.
        _incidents: Olay kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Grafiği başlatır."""
        self._services: list[dict] = []
        self._incidents: list[dict] = []
        self._stats: dict[str, int] = {
            "services_tracked": 0,
            "incidents_logged": 0,
        }
        logger.info(
            "UptimeChart baslatildi"
        )

    @property
    def service_count(self) -> int:
        """Servis sayısı."""
        return len(self._services)

    def track_service(
        self,
        name: str = "",
        sla_target: float = 99.9,
    ) -> dict[str, Any]:
        """Servis takibe alır.

        Args:
            name: Servis adı.
            sla_target: SLA hedefi (%).

        Returns:
            Takip bilgisi.
        """
        try:
            sid = f"sv_{uuid4()!s:.8}"

            record = {
                "service_id": sid,
                "name": name,
                "sla_target": sla_target,
                "total_minutes": 0,
                "uptime_minutes": 0,
                "downtime_minutes": 0,
                "status": "up",
            }
            self._services.append(record)
            self._stats[
                "services_tracked"
            ] += 1

            return {
                "service_id": sid,
                "name": name,
                "sla_target": sla_target,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def record_uptime(
        self,
        service_id: str = "",
        minutes: int = 60,
    ) -> dict[str, Any]:
        """Uptime kaydeder.

        Args:
            service_id: Servis ID.
            minutes: Dakika.

        Returns:
            Kayıt bilgisi.
        """
        try:
            service = None
            for s in self._services:
                if s["service_id"] == service_id:
                    service = s
                    break

            if not service:
                return {
                    "recorded": False,
                    "error": "service_not_found",
                }

            service["total_minutes"] += minutes
            service["uptime_minutes"] += minutes
            service["status"] = "up"

            uptime_pct = (
                service["uptime_minutes"]
                / service["total_minutes"]
                * 100.0
            ) if service["total_minutes"] > 0 else 100.0

            return {
                "service_id": service_id,
                "minutes": minutes,
                "uptime_percent": round(
                    uptime_pct, 3
                ),
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def log_downtime(
        self,
        service_id: str = "",
        minutes: int = 0,
        reason: str = "",
    ) -> dict[str, Any]:
        """Downtime kaydeder.

        Args:
            service_id: Servis ID.
            minutes: Dakika.
            reason: Sebep.

        Returns:
            Kayıt bilgisi.
        """
        try:
            service = None
            for s in self._services:
                if s["service_id"] == service_id:
                    service = s
                    break

            if not service:
                return {
                    "logged": False,
                    "error": "service_not_found",
                }

            service["total_minutes"] += minutes
            service[
                "downtime_minutes"
            ] += minutes
            service["status"] = "down"

            iid = f"inc_{uuid4()!s:.8}"
            incident = {
                "incident_id": iid,
                "service_id": service_id,
                "service_name": service["name"],
                "duration_minutes": minutes,
                "reason": reason,
                "type": "downtime",
            }
            self._incidents.append(incident)
            self._stats[
                "incidents_logged"
            ] += 1

            return {
                "service_id": service_id,
                "incident_id": iid,
                "duration_minutes": minutes,
                "reason": reason,
                "logged": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "logged": False,
                "error": str(e),
            }

    def get_sla_status(
        self,
        service_id: str = "",
    ) -> dict[str, Any]:
        """SLA durumu getirir.

        Args:
            service_id: Servis ID.

        Returns:
            SLA bilgisi.
        """
        try:
            service = None
            for s in self._services:
                if s["service_id"] == service_id:
                    service = s
                    break

            if not service:
                return {
                    "retrieved": False,
                    "error": "service_not_found",
                }

            total = service["total_minutes"]
            uptime_pct = (
                service["uptime_minutes"]
                / total * 100.0
            ) if total > 0 else 100.0

            target = service["sla_target"]
            met = uptime_pct >= target
            margin = uptime_pct - target

            allowed_downtime = (
                total * (100.0 - target) / 100.0
            ) if total > 0 else 0.0

            remaining_downtime = max(
                0.0,
                allowed_downtime
                - service["downtime_minutes"],
            )

            return {
                "service_id": service_id,
                "name": service["name"],
                "uptime_percent": round(
                    uptime_pct, 3
                ),
                "sla_target": target,
                "sla_met": met,
                "margin": round(margin, 3),
                "total_downtime_min": service[
                    "downtime_minutes"
                ],
                "remaining_budget_min": round(
                    remaining_downtime, 1
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_history(
        self,
        service_id: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Geçmiş görünümü getirir.

        Args:
            service_id: Servis ID.
            limit: Limit.

        Returns:
            Geçmiş bilgisi.
        """
        try:
            if service_id:
                filtered = [
                    i for i in self._incidents
                    if i["service_id"]
                    == service_id
                ]
            else:
                filtered = self._incidents

            recent = filtered[-limit:]
            total_downtime = sum(
                i["duration_minutes"]
                for i in recent
            )

            return {
                "incidents": recent,
                "incident_count": len(recent),
                "total_downtime_min": (
                    total_downtime
                ),
                "service_filter": service_id,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def add_incident_marker(
        self,
        service_id: str = "",
        marker_type: str = "incident",
        description: str = "",
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Olay işareti ekler.

        Args:
            service_id: Servis ID.
            marker_type: İşaret türü.
            description: Açıklama.
            severity: Ciddiyet.

        Returns:
            İşaret bilgisi.
        """
        try:
            mid = f"mk_{uuid4()!s:.8}"

            marker = {
                "marker_id": mid,
                "service_id": service_id,
                "type": marker_type,
                "description": description,
                "severity": severity,
            }
            self._incidents.append(marker)

            return {
                "marker_id": mid,
                "service_id": service_id,
                "type": marker_type,
                "severity": severity,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }
