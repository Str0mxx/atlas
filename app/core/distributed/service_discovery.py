"""ATLAS Servis Kesfi modulu.

Servis kaydi, saglik kontrolu,
yuk dengeleme, DNS entegrasyonu
ve servis mesh.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """Servis kesfi yoneticisi.

    Servisleri bulur ve yonetir.

    Attributes:
        _services: Kayitli servisler.
        _health_checks: Saglik kontrolleri.
    """

    def __init__(
        self,
        health_interval: int = 30,
    ) -> None:
        """Servis kesfini baslatir.

        Args:
            health_interval: Saglik kontrol suresi (sn).
        """
        self._services: dict[
            str, dict[str, Any]
        ] = {}
        self._health_checks: dict[
            str, dict[str, Any]
        ] = {}
        self._lb_counters: dict[str, int] = {}
        self._health_interval = health_interval

        logger.info(
            "ServiceDiscovery baslatildi",
        )

    def register(
        self,
        service_id: str,
        name: str,
        host: str = "localhost",
        port: int = 8000,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Servis kaydeder.

        Args:
            service_id: Servis ID.
            name: Servis adi.
            host: Ana bilgisayar.
            port: Port.
            tags: Etiketler.
            metadata: Ust veri.

        Returns:
            Kayit bilgisi.
        """
        service = {
            "service_id": service_id,
            "name": name,
            "host": host,
            "port": port,
            "tags": tags or [],
            "metadata": metadata or {},
            "status": "healthy",
            "registered_at": time.time(),
            "last_health_check": time.time(),
        }
        self._services[service_id] = service
        return {
            "service_id": service_id,
            "name": name,
            "status": "registered",
        }

    def deregister(
        self,
        service_id: str,
    ) -> bool:
        """Servis kaydini siler.

        Args:
            service_id: Servis ID.

        Returns:
            Basarili mi.
        """
        if service_id in self._services:
            del self._services[service_id]
            self._health_checks.pop(
                service_id, None,
            )
            return True
        return False

    def discover(
        self,
        name: str | None = None,
        tags: list[str] | None = None,
        healthy_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Servis kesfeder.

        Args:
            name: Servis adi filtresi.
            tags: Etiket filtresi.
            healthy_only: Sadece sagliklilari.

        Returns:
            Servis listesi.
        """
        result = list(self._services.values())

        if name:
            result = [
                s for s in result
                if s["name"] == name
            ]

        if tags:
            result = [
                s for s in result
                if all(
                    t in s["tags"] for t in tags
                )
            ]

        if healthy_only:
            result = [
                s for s in result
                if s["status"] == "healthy"
            ]

        return [
            {
                "service_id": s["service_id"],
                "name": s["name"],
                "host": s["host"],
                "port": s["port"],
                "status": s["status"],
                "tags": s["tags"],
            }
            for s in result
        ]

    def health_check(
        self,
        service_id: str,
        healthy: bool = True,
    ) -> dict[str, Any]:
        """Saglik kontrolu yapar.

        Args:
            service_id: Servis ID.
            healthy: Saglikli mi.

        Returns:
            Kontrol sonucu.
        """
        service = self._services.get(service_id)
        if not service:
            return {
                "status": "error",
                "reason": "service_not_found",
            }

        old_status = service["status"]
        service["status"] = (
            "healthy" if healthy else "unhealthy"
        )
        service["last_health_check"] = time.time()

        self._health_checks[service_id] = {
            "service_id": service_id,
            "healthy": healthy,
            "previous": old_status,
            "timestamp": time.time(),
        }

        return {
            "service_id": service_id,
            "status": service["status"],
            "changed": old_status != service[
                "status"
            ],
        }

    def check_stale_services(
        self,
    ) -> dict[str, Any]:
        """Bayat servisleri kontrol eder.

        Returns:
            Kontrol sonucu.
        """
        now = time.time()
        stale = []
        threshold = self._health_interval * 3

        for sid, svc in self._services.items():
            elapsed = (
                now - svc["last_health_check"]
            )
            if elapsed > threshold:
                svc["status"] = "unhealthy"
                stale.append(sid)

        return {
            "checked": len(self._services),
            "stale": len(stale),
            "stale_ids": stale,
        }

    def load_balance(
        self,
        name: str,
        strategy: str = "round_robin",
    ) -> dict[str, Any] | None:
        """Yuk dengeler.

        Args:
            name: Servis adi.
            strategy: Strateji.

        Returns:
            Secilen servis veya None.
        """
        healthy = self.discover(
            name=name, healthy_only=True,
        )
        if not healthy:
            return None

        if strategy == "round_robin":
            counter = self._lb_counters.get(
                name, 0,
            )
            selected = healthy[
                counter % len(healthy)
            ]
            self._lb_counters[name] = counter + 1
        elif strategy == "random":
            import random
            selected = random.choice(healthy)
        else:
            # Ilk saglikli
            selected = healthy[0]

        return selected

    def resolve_dns(
        self,
        name: str,
    ) -> list[dict[str, Any]]:
        """DNS cozumler.

        Args:
            name: Servis adi.

        Returns:
            Adres listesi.
        """
        services = self.discover(
            name=name, healthy_only=True,
        )
        return [
            {
                "host": s["host"],
                "port": s["port"],
                "service_id": s["service_id"],
            }
            for s in services
        ]

    def get_service(
        self,
        service_id: str,
    ) -> dict[str, Any] | None:
        """Servis bilgisi getirir.

        Args:
            service_id: Servis ID.

        Returns:
            Servis bilgisi veya None.
        """
        return self._services.get(service_id)

    @property
    def service_count(self) -> int:
        """Servis sayisi."""
        return len(self._services)

    @property
    def healthy_count(self) -> int:
        """Saglikli servis sayisi."""
        return sum(
            1 for s in self._services.values()
            if s["status"] == "healthy"
        )
