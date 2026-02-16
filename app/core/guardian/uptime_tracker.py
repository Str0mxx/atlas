"""ATLAS Çalışma Süresi Takipçisi modülü.

Çalışma süresi hesaplama, kesinti loglama,
SLA takibi, erişilebilirlik metrikleri,
tarihsel trendler.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class UptimeTracker:
    """Çalışma süresi takipçisi.

    Servis uptime metriklerini izler.

    Attributes:
        _services: Servis kayıtları.
        _downtimes: Kesinti kayıtları.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._services: dict[
            str, dict[str, Any]
        ] = {}
        self._downtimes: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "services_tracked": 0,
            "downtimes_logged": 0,
        }

        logger.info(
            "UptimeTracker baslatildi",
        )

    def track_service(
        self,
        service: str,
        start_time: float = 0.0,
        sla_target: float = 99.9,
    ) -> dict[str, Any]:
        """Servis takibi başlatır.

        Args:
            service: Servis adı.
            start_time: Başlangıç zamanı.
            sla_target: SLA hedefi (%).

        Returns:
            Takip bilgisi.
        """
        self._counter += 1
        sid = f"svc_{self._counter}"
        now = start_time or time.time()

        self._services[service] = {
            "service_id": sid,
            "service": service,
            "start_time": now,
            "sla_target": sla_target,
            "total_downtime_sec": 0.0,
            "status": "up",
        }
        self._stats[
            "services_tracked"
        ] += 1

        return {
            "service_id": sid,
            "service": service,
            "sla_target": sla_target,
            "tracked": True,
        }

    def calculate_uptime(
        self,
        service: str,
        period_hours: float = 24.0,
    ) -> dict[str, Any]:
        """Çalışma süresi hesaplar.

        Args:
            service: Servis adı.
            period_hours: Dönem (saat).

        Returns:
            Uptime bilgisi.
        """
        svc = self._services.get(service)
        if not svc:
            return {
                "service": service,
                "calculated": False,
            }

        total_sec = period_hours * 3600
        down_sec = svc[
            "total_downtime_sec"
        ]
        up_sec = max(
            total_sec - down_sec, 0,
        )
        uptime_pct = round(
            up_sec / total_sec * 100, 3,
        ) if total_sec > 0 else 100.0

        return {
            "service": service,
            "uptime_pct": uptime_pct,
            "up_seconds": round(up_sec, 1),
            "down_seconds": round(
                down_sec, 1,
            ),
            "period_hours": period_hours,
            "calculated": True,
        }

    def log_downtime(
        self,
        service: str,
        duration_sec: float = 0.0,
        reason: str = "",
    ) -> dict[str, Any]:
        """Kesinti kaydeder.

        Args:
            service: Servis adı.
            duration_sec: Süre (saniye).
            reason: Sebep.

        Returns:
            Kayıt bilgisi.
        """
        svc = self._services.get(service)
        if svc:
            svc[
                "total_downtime_sec"
            ] += duration_sec

        entry = {
            "service": service,
            "duration_sec": duration_sec,
            "reason": reason,
            "timestamp": time.time(),
        }
        self._downtimes.append(entry)
        self._stats[
            "downtimes_logged"
        ] += 1

        return {
            "service": service,
            "duration_sec": duration_sec,
            "reason": reason,
            "logged": True,
        }

    def check_sla(
        self,
        service: str,
        period_hours: float = 720.0,
    ) -> dict[str, Any]:
        """SLA kontrol eder.

        Args:
            service: Servis adı.
            period_hours: Dönem (saat).

        Returns:
            SLA bilgisi.
        """
        svc = self._services.get(service)
        if not svc:
            return {
                "service": service,
                "checked": False,
            }

        uptime = self.calculate_uptime(
            service, period_hours,
        )
        uptime_pct = uptime["uptime_pct"]
        target = svc["sla_target"]

        status = (
            "compliant"
            if uptime_pct >= target
            else "at_risk"
            if uptime_pct >= target - 0.5
            else "breached"
        )

        return {
            "service": service,
            "uptime_pct": uptime_pct,
            "sla_target": target,
            "status": status,
            "margin": round(
                uptime_pct - target, 3,
            ),
            "checked": True,
        }

    def get_availability_metrics(
        self,
        service: str,
    ) -> dict[str, Any]:
        """Erişilebilirlik metrikleri döndürür.

        Args:
            service: Servis adı.

        Returns:
            Metrik bilgisi.
        """
        svc = self._services.get(service)
        if not svc:
            return {
                "service": service,
                "found": False,
            }

        downtimes = [
            d for d in self._downtimes
            if d["service"] == service
        ]
        total_incidents = len(downtimes)
        total_down = sum(
            d["duration_sec"]
            for d in downtimes
        )
        avg_down = (
            round(
                total_down / total_incidents,
                1,
            )
            if total_incidents > 0
            else 0.0
        )

        return {
            "service": service,
            "total_incidents": (
                total_incidents
            ),
            "total_downtime_sec": round(
                total_down, 1,
            ),
            "avg_downtime_sec": avg_down,
            "status": svc["status"],
            "found": True,
        }

    def get_historical_trend(
        self,
        service: str,
        periods: int = 7,
        period_hours: float = 24.0,
    ) -> dict[str, Any]:
        """Tarihsel trend döndürür.

        Args:
            service: Servis adı.
            periods: Dönem sayısı.
            period_hours: Dönem uzunluğu.

        Returns:
            Trend bilgisi.
        """
        svc = self._services.get(service)
        if not svc:
            return {
                "service": service,
                "found": False,
            }

        uptime = self.calculate_uptime(
            service,
            period_hours * periods,
        )
        current_pct = uptime["uptime_pct"]

        trend = (
            "improving"
            if current_pct >= 99.9
            else "stable"
            if current_pct >= 99.0
            else "declining"
        )

        return {
            "service": service,
            "periods": periods,
            "period_hours": period_hours,
            "current_uptime": current_pct,
            "trend": trend,
            "found": True,
        }

    @property
    def service_count(self) -> int:
        """Servis sayısı."""
        return self._stats[
            "services_tracked"
        ]

    @property
    def downtime_count(self) -> int:
        """Kesinti sayısı."""
        return self._stats[
            "downtimes_logged"
        ]
