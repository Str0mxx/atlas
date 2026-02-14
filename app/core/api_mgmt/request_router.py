"""ATLAS Istek Yonlendirici modulu.

Yol tabanli yonlendirme, metot
yonlendirme, surum yonlendirme,
yuk dengeleme ve failover.
"""

import logging
import time
from typing import Any

from app.models.api_mgmt import RouteRecord

logger = logging.getLogger(__name__)


class RequestRouter:
    """Istek yonlendirici.

    Gelen istekleri uygun hedefe
    yonlendirir.

    Attributes:
        _routes: Rota kayitlari.
        _backends: Arka plan servisleri.
    """

    def __init__(self) -> None:
        """Istek yonlendiriciyi baslatir."""
        self._routes: dict[
            str, RouteRecord
        ] = {}
        self._backends: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._fallbacks: dict[str, str] = {}
        self._route_index: dict[
            str, list[str]
        ] = {}

        logger.info(
            "RequestRouter baslatildi",
        )

    def add_route(
        self,
        path: str,
        target: str,
        method: str = "GET",
        version: str = "v1",
        weight: int = 100,
    ) -> RouteRecord:
        """Rota ekler.

        Args:
            path: Yol.
            target: Hedef.
            method: HTTP metodu.
            version: Surum.
            weight: Agirlik.

        Returns:
            Rota kaydi.
        """
        route = RouteRecord(
            path=path,
            target=target,
            method=method,
            version=version,
            weight=weight,
        )
        self._routes[route.route_id] = route

        key = f"{method}:{path}"
        if key not in self._route_index:
            self._route_index[key] = []
        self._route_index[key].append(
            route.route_id,
        )

        return route

    def resolve(
        self,
        path: str,
        method: str = "GET",
        version: str | None = None,
    ) -> dict[str, Any]:
        """Rotayi cozumler.

        Args:
            path: Istek yolu.
            method: HTTP metodu.
            version: Surum.

        Returns:
            Cozumleme sonucu.
        """
        key = f"{method}:{path}"
        route_ids = self._route_index.get(key, [])

        candidates = [
            self._routes[rid]
            for rid in route_ids
            if rid in self._routes
            and self._routes[rid].active
        ]

        if version:
            versioned = [
                r for r in candidates
                if r.version == version
            ]
            if versioned:
                candidates = versioned

        if not candidates:
            # Fallback kontrolu
            fb_target = self._fallbacks.get(path)
            if fb_target:
                return {
                    "resolved": True,
                    "target": fb_target,
                    "fallback": True,
                }
            return {
                "resolved": False,
                "reason": "no_matching_route",
            }

        # Agirlik tabanli secim
        selected = max(
            candidates, key=lambda r: r.weight,
        )
        return {
            "resolved": True,
            "target": selected.target,
            "route_id": selected.route_id,
            "version": selected.version,
            "fallback": False,
        }

    def add_backend(
        self,
        name: str,
        url: str,
        weight: int = 100,
        healthy: bool = True,
    ) -> dict[str, Any]:
        """Arka plan servisi ekler.

        Args:
            name: Servis adi.
            url: Servis URL.
            weight: Agirlik.
            healthy: Saglikli mi.

        Returns:
            Backend bilgisi.
        """
        backend = {
            "url": url,
            "weight": weight,
            "healthy": healthy,
        }
        if name not in self._backends:
            self._backends[name] = []
        self._backends[name].append(backend)
        return backend

    def load_balance(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Yuk dengeler.

        Args:
            name: Servis adi.

        Returns:
            Secilen backend.
        """
        backends = self._backends.get(name, [])
        healthy = [
            b for b in backends
            if b["healthy"]
        ]

        if not healthy:
            return {
                "success": False,
                "reason": "no_healthy_backends",
            }

        selected = max(
            healthy, key=lambda b: b["weight"],
        )
        return {
            "success": True,
            "url": selected["url"],
            "weight": selected["weight"],
        }

    def set_fallback(
        self,
        path: str,
        target: str,
    ) -> None:
        """Fallback ayarlar.

        Args:
            path: Yol.
            target: Yedek hedef.
        """
        self._fallbacks[path] = target

    def disable_route(
        self,
        route_id: str,
    ) -> bool:
        """Rotayi devre disi birakir.

        Args:
            route_id: Rota ID.

        Returns:
            Basarili ise True.
        """
        route = self._routes.get(route_id)
        if not route:
            return False
        route.active = False
        return True

    def enable_route(
        self,
        route_id: str,
    ) -> bool:
        """Rotayi etkinlestirir.

        Args:
            route_id: Rota ID.

        Returns:
            Basarili ise True.
        """
        route = self._routes.get(route_id)
        if not route:
            return False
        route.active = True
        return True

    def remove_route(
        self,
        route_id: str,
    ) -> bool:
        """Rota kaldirir.

        Args:
            route_id: Rota ID.

        Returns:
            Basarili ise True.
        """
        route = self._routes.pop(route_id, None)
        if not route:
            return False
        key = f"{route.method}:{route.path}"
        ids = self._route_index.get(key, [])
        if route_id in ids:
            ids.remove(route_id)
        return True

    @property
    def route_count(self) -> int:
        """Rota sayisi."""
        return len(self._routes)

    @property
    def backend_count(self) -> int:
        """Backend sayisi."""
        return sum(
            len(b)
            for b in self._backends.values()
        )

    @property
    def active_route_count(self) -> int:
        """Aktif rota sayisi."""
        return sum(
            1 for r in self._routes.values()
            if r.active
        )
