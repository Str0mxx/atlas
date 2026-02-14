"""ATLAS Dis Servis Kaydi modulu.

Servis kesfi, saglik izleme, failover,
yuk dengeleme ve circuit breaker.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.integration import ServiceStatus

logger = logging.getLogger(__name__)


class ExternalServiceRegistry:
    """Dis servis kaydi.

    Dis servisleri kaydeder, sagliklarini
    izler ve erisimi yonetir.

    Attributes:
        _services: Kayitli servisler.
        _health_history: Saglik gecmisi.
        _circuit_breakers: Circuit breaker durumlari.
        _failover_map: Failover eslemeleri.
    """

    def __init__(self) -> None:
        """Dis servis kaydini baslatir."""
        self._services: dict[str, dict[str, Any]] = {}
        self._health_history: list[dict[str, Any]] = []
        self._circuit_breakers: dict[str, dict[str, Any]] = {}
        self._failover_map: dict[str, str] = {}

        logger.info("ExternalServiceRegistry baslatildi")

    def register_service(
        self,
        name: str,
        url: str,
        description: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Servis kaydeder.

        Args:
            name: Servis adi.
            url: Servis URL.
            description: Aciklama.
            tags: Etiketler.

        Returns:
            Servis bilgisi.
        """
        service = {
            "name": name,
            "url": url,
            "description": description,
            "tags": tags or [],
            "status": ServiceStatus.UNKNOWN.value,
            "last_check": None,
            "check_count": 0,
            "failure_count": 0,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        self._services[name] = service

        # Circuit breaker baslat
        self._circuit_breakers[name] = {
            "state": "closed",
            "failures": 0,
            "threshold": 5,
            "last_failure": None,
            "recovery_timeout": 60,
        }

        logger.info("Servis kaydedildi: %s (%s)", name, url)
        return service

    def check_health(
        self,
        name: str,
        is_healthy: bool = True,
        latency_ms: float = 0.0,
    ) -> dict[str, Any]:
        """Servis sagligini kontrol eder.

        Args:
            name: Servis adi.
            is_healthy: Saglikli mi.
            latency_ms: Gecikme (ms).

        Returns:
            Saglik sonucu.
        """
        service = self._services.get(name)
        if not service:
            return {"error": "Servis bulunamadi"}

        if is_healthy:
            service["status"] = ServiceStatus.ACTIVE.value
            self._reset_circuit_breaker(name)
        else:
            service["failure_count"] += 1
            self._record_failure(name)

            cb = self._circuit_breakers.get(name, {})
            if cb.get("failures", 0) >= cb.get("threshold", 5):
                service["status"] = ServiceStatus.DOWN.value
            else:
                service["status"] = ServiceStatus.DEGRADED.value

        service["check_count"] += 1
        service["last_check"] = datetime.now(timezone.utc).isoformat()

        health = {
            "service": name,
            "healthy": is_healthy,
            "status": service["status"],
            "latency_ms": latency_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._health_history.append(health)

        return health

    def discover_services(
        self,
        tag: str = "",
        status: str = "",
    ) -> list[dict[str, Any]]:
        """Servisleri kesfeder.

        Args:
            tag: Etiket filtresi.
            status: Durum filtresi.

        Returns:
            Servis listesi.
        """
        services = list(self._services.values())

        if tag:
            services = [
                s for s in services
                if tag in s.get("tags", [])
            ]

        if status:
            services = [
                s for s in services
                if s.get("status") == status
            ]

        return services

    def set_failover(
        self,
        primary: str,
        fallback: str,
    ) -> bool:
        """Failover eslemesi ayarlar.

        Args:
            primary: Birincil servis.
            fallback: Yedek servis.

        Returns:
            Basarili ise True.
        """
        if primary not in self._services:
            return False
        if fallback not in self._services:
            return False

        self._failover_map[primary] = fallback
        logger.info("Failover: %s -> %s", primary, fallback)
        return True

    def get_active_service(
        self,
        name: str,
    ) -> str:
        """Aktif servisi getirir (failover dahil).

        Args:
            name: Servis adi.

        Returns:
            Aktif servis adi.
        """
        service = self._services.get(name)
        if not service:
            return name

        if service["status"] == ServiceStatus.DOWN.value:
            fallback = self._failover_map.get(name)
            if fallback:
                fb_service = self._services.get(fallback)
                if fb_service and fb_service["status"] != ServiceStatus.DOWN.value:
                    logger.info(
                        "Failover aktif: %s -> %s", name, fallback,
                    )
                    return fallback

        return name

    def get_circuit_breaker_state(
        self,
        name: str,
    ) -> str:
        """Circuit breaker durumunu getirir.

        Args:
            name: Servis adi.

        Returns:
            Durum: closed/open/half_open.
        """
        cb = self._circuit_breakers.get(name)
        if not cb:
            return "unknown"
        return cb["state"]

    def set_circuit_breaker_threshold(
        self,
        name: str,
        threshold: int,
    ) -> bool:
        """Circuit breaker esigini ayarlar.

        Args:
            name: Servis adi.
            threshold: Hata esigi.

        Returns:
            Basarili ise True.
        """
        cb = self._circuit_breakers.get(name)
        if not cb:
            return False
        cb["threshold"] = max(1, threshold)
        return True

    def unregister_service(self, name: str) -> bool:
        """Servis kaydini siler.

        Args:
            name: Servis adi.

        Returns:
            Basarili ise True.
        """
        if name in self._services:
            del self._services[name]
            self._circuit_breakers.pop(name, None)
            self._failover_map.pop(name, None)
            return True
        return False

    def get_service(self, name: str) -> dict[str, Any] | None:
        """Servis bilgisi getirir.

        Args:
            name: Servis adi.

        Returns:
            Servis bilgisi veya None.
        """
        return self._services.get(name)

    def _record_failure(self, name: str) -> None:
        """Hata kaydeder.

        Args:
            name: Servis adi.
        """
        cb = self._circuit_breakers.get(name)
        if not cb:
            return

        cb["failures"] += 1
        cb["last_failure"] = datetime.now(timezone.utc).isoformat()

        if cb["failures"] >= cb["threshold"]:
            cb["state"] = "open"
            logger.warning(
                "Circuit breaker acildi: %s (%d hata)",
                name, cb["failures"],
            )

    def _reset_circuit_breaker(self, name: str) -> None:
        """Circuit breaker sifirlar.

        Args:
            name: Servis adi.
        """
        cb = self._circuit_breakers.get(name)
        if not cb:
            return

        if cb["state"] == "open":
            cb["state"] = "half_open"
        elif cb["state"] == "half_open":
            cb["state"] = "closed"
            cb["failures"] = 0

    @property
    def service_count(self) -> int:
        """Servis sayisi."""
        return len(self._services)

    @property
    def active_count(self) -> int:
        """Aktif servis sayisi."""
        return sum(
            1 for s in self._services.values()
            if s["status"] == ServiceStatus.ACTIVE.value
        )

    @property
    def health_check_count(self) -> int:
        """Saglik kontrolu sayisi."""
        return len(self._health_history)
