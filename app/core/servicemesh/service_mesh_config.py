"""ATLAS Mesh Konfigurasyon modulu.

Politika yonetimi, yonlendirme kurallari,
hiz limitleri, erisim politikalari
ve hata enjeksiyonu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ServiceMeshConfig:
    """Mesh konfigurasyonu.

    Mesh politikalarini yonetir.

    Attributes:
        _policies: Politikalar.
        _routes: Yonlendirme kurallari.
    """

    def __init__(self) -> None:
        """Mesh konfigurasyonunu baslatir."""
        self._policies: dict[
            str, dict[str, Any]
        ] = {}
        self._routes: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._rate_limits: dict[
            str, dict[str, Any]
        ] = {}
        self._access_policies: dict[
            str, dict[str, Any]
        ] = {}
        self._fault_injections: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "ServiceMeshConfig baslatildi",
        )

    def set_policy(
        self,
        name: str,
        policy_type: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Politika ayarlar.

        Args:
            name: Politika adi.
            policy_type: Politika tipi.
            config: Konfigurasyon.

        Returns:
            Politika bilgisi.
        """
        self._policies[name] = {
            "name": name,
            "type": policy_type,
            "config": config,
            "enabled": True,
            "created_at": time.time(),
        }
        return {"name": name, "type": policy_type}

    def get_policy(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Politika getirir.

        Args:
            name: Politika adi.

        Returns:
            Politika veya None.
        """
        return self._policies.get(name)

    def remove_policy(
        self,
        name: str,
    ) -> bool:
        """Politika kaldirir.

        Args:
            name: Politika adi.

        Returns:
            Basarili mi.
        """
        if name in self._policies:
            del self._policies[name]
            return True
        return False

    def add_route(
        self,
        service: str,
        path: str,
        destination: str,
        method: str = "*",
        priority: int = 0,
    ) -> dict[str, Any]:
        """Yonlendirme kurali ekler.

        Args:
            service: Servis adi.
            path: Yol deseni.
            destination: Hedef.
            method: HTTP metodu.
            priority: Oncelik.

        Returns:
            Kural bilgisi.
        """
        if service not in self._routes:
            self._routes[service] = []

        route = {
            "path": path,
            "destination": destination,
            "method": method,
            "priority": priority,
            "created_at": time.time(),
        }
        self._routes[service].append(route)
        self._routes[service].sort(
            key=lambda r: r["priority"],
            reverse=True,
        )

        return {
            "service": service,
            "path": path,
            "destination": destination,
        }

    def get_routes(
        self,
        service: str,
    ) -> list[dict[str, Any]]:
        """Yonlendirme kurallarini getirir.

        Args:
            service: Servis adi.

        Returns:
            Kural listesi.
        """
        return list(
            self._routes.get(service, []),
        )

    def match_route(
        self,
        service: str,
        path: str,
        method: str = "GET",
    ) -> dict[str, Any] | None:
        """Yolu eslestirir.

        Args:
            service: Servis adi.
            path: Istek yolu.
            method: HTTP metodu.

        Returns:
            Eslesen kural veya None.
        """
        routes = self._routes.get(service, [])
        for route in routes:
            if (
                route["method"] in ("*", method)
                and (
                    path.startswith(route["path"])
                    or route["path"] == "*"
                )
            ):
                return route
        return None

    def set_rate_limit(
        self,
        service: str,
        requests_per_second: int,
        burst: int | None = None,
    ) -> dict[str, Any]:
        """Hiz limiti ayarlar.

        Args:
            service: Servis adi.
            requests_per_second: Saniyede istek.
            burst: Patlama limiti.

        Returns:
            Limit bilgisi.
        """
        self._rate_limits[service] = {
            "rps": requests_per_second,
            "burst": burst or requests_per_second * 2,
            "current": 0,
            "last_reset": time.time(),
        }
        return {
            "service": service,
            "rps": requests_per_second,
        }

    def check_rate_limit(
        self,
        service: str,
    ) -> dict[str, Any]:
        """Hiz limiti kontrol eder.

        Args:
            service: Servis adi.

        Returns:
            Limit kontrolu.
        """
        limit = self._rate_limits.get(service)
        if not limit:
            return {"allowed": True, "limited": False}

        now = time.time()
        if now - limit["last_reset"] >= 1.0:
            limit["current"] = 0
            limit["last_reset"] = now

        limit["current"] += 1
        allowed = limit["current"] <= limit["burst"]

        return {
            "allowed": allowed,
            "limited": not allowed,
            "current": limit["current"],
            "limit": limit["burst"],
        }

    def set_access_policy(
        self,
        service: str,
        allowed_sources: list[str],
        denied_sources: list[str] | None = None,
    ) -> dict[str, Any]:
        """Erisim politikasi ayarlar.

        Args:
            service: Servis adi.
            allowed_sources: Izin verilen kaynaklar.
            denied_sources: Yasaklanan kaynaklar.

        Returns:
            Politika bilgisi.
        """
        self._access_policies[service] = {
            "allowed": set(allowed_sources),
            "denied": set(denied_sources or []),
        }
        return {
            "service": service,
            "allowed": len(allowed_sources),
        }

    def check_access(
        self,
        service: str,
        source: str,
    ) -> bool:
        """Erisim kontrol eder.

        Args:
            service: Servis adi.
            source: Kaynak.

        Returns:
            Izin var mi.
        """
        policy = self._access_policies.get(service)
        if not policy:
            return True
        if source in policy["denied"]:
            return False
        if policy["allowed"]:
            return source in policy["allowed"]
        return True

    def inject_fault(
        self,
        service: str,
        fault_type: str = "delay",
        probability: float = 0.0,
        delay_ms: int = 0,
        status_code: int = 500,
    ) -> dict[str, Any]:
        """Hata enjeksiyonu ayarlar.

        Args:
            service: Servis adi.
            fault_type: Hata tipi (delay/abort).
            probability: Olasilik (0-1).
            delay_ms: Gecikme (ms).
            status_code: Durum kodu.

        Returns:
            Enjeksiyon bilgisi.
        """
        self._fault_injections[service] = {
            "type": fault_type,
            "probability": probability,
            "delay_ms": delay_ms,
            "status_code": status_code,
            "enabled": True,
        }
        return {
            "service": service,
            "fault_type": fault_type,
        }

    def get_fault_injection(
        self,
        service: str,
    ) -> dict[str, Any] | None:
        """Hata enjeksiyonu getirir.

        Args:
            service: Servis adi.

        Returns:
            Enjeksiyon bilgisi veya None.
        """
        return self._fault_injections.get(service)

    def remove_fault_injection(
        self,
        service: str,
    ) -> bool:
        """Hata enjeksiyonunu kaldirir.

        Args:
            service: Servis adi.

        Returns:
            Basarili mi.
        """
        if service in self._fault_injections:
            del self._fault_injections[service]
            return True
        return False

    @property
    def policy_count(self) -> int:
        """Politika sayisi."""
        return len(self._policies)

    @property
    def route_count(self) -> int:
        """Yonlendirme sayisi."""
        return sum(
            len(r) for r in self._routes.values()
        )

    @property
    def rate_limit_count(self) -> int:
        """Hiz limiti sayisi."""
        return len(self._rate_limits)

    @property
    def fault_count(self) -> int:
        """Hata enjeksiyonu sayisi."""
        return len(self._fault_injections)
