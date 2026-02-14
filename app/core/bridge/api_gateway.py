"""ATLAS API Gecidi modulu.

Birlesik API, istek yonlendirme, yanit birlestirme,
hiz siniri ve devre kesici.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


class APIGateway:
    """API gecidi.

    Tum sistemler icin birlesik API saglar,
    istekleri yonlendirir ve yonetir.

    Attributes:
        _routes: Yol -> isleyici eslesmesi.
        _rate_limits: Sistem -> limit.
        _rate_counters: Sistem -> sayac.
        _circuit_states: Devre durumu.
        _middleware: Ara katman listesi.
    """

    def __init__(self) -> None:
        """API gecidini baslatir."""
        self._routes: dict[str, Callable] = {}
        self._rate_limits: dict[str, int] = {}
        self._rate_counters: dict[str, int] = {}
        self._circuit_states: dict[str, bool] = {}  # True = open (blocked)
        self._failure_counts: dict[str, int] = {}
        self._failure_threshold: int = 5
        self._middleware: list[Callable] = []
        self._request_log: list[dict[str, Any]] = []

        logger.info("APIGateway baslatildi")

    def register_route(
        self,
        path: str,
        handler: Callable,
    ) -> None:
        """Yol kaydeder.

        Args:
            path: API yolu.
            handler: Isleyici.
        """
        self._routes[path] = handler

    def unregister_route(self, path: str) -> bool:
        """Yol kaydini siler.

        Args:
            path: API yolu.

        Returns:
            Basarili ise True.
        """
        return self._routes.pop(path, None) is not None

    def add_middleware(self, middleware: Callable) -> None:
        """Ara katman ekler.

        Args:
            middleware: Ara katman fonksiyonu.
        """
        self._middleware.append(middleware)

    def set_rate_limit(
        self,
        system_id: str,
        max_requests: int,
    ) -> None:
        """Hiz siniri ayarlar.

        Args:
            system_id: Sistem ID.
            max_requests: Maks istek.
        """
        self._rate_limits[system_id] = max_requests
        self._rate_counters[system_id] = 0

    def request(
        self,
        path: str,
        payload: dict[str, Any] | None = None,
        source: str = "",
    ) -> dict[str, Any]:
        """API istegi yapar.

        Args:
            path: API yolu.
            payload: Istek verisi.
            source: Kaynak sistem.

        Returns:
            Yanit sozlugu.
        """
        # Hiz siniri kontrolu
        if source and source in self._rate_limits:
            counter = self._rate_counters.get(source, 0)
            if counter >= self._rate_limits[source]:
                return {
                    "success": False,
                    "error": "rate_limited",
                    "message": "Hiz siniri asildi",
                }
            self._rate_counters[source] = counter + 1

        # Devre kesici kontrolu
        if source and self._circuit_states.get(source, False):
            return {
                "success": False,
                "error": "circuit_open",
                "message": "Devre acik, istek engellendi",
            }

        # Yol kontrolu
        handler = self._routes.get(path)
        if not handler:
            return {
                "success": False,
                "error": "not_found",
                "message": f"Yol bulunamadi: {path}",
            }

        # Ara katmanlari uygula
        context = {"path": path, "payload": payload or {}, "source": source}
        for mw in self._middleware:
            try:
                context = mw(context)
            except Exception as e:
                return {
                    "success": False,
                    "error": "middleware_error",
                    "message": str(e),
                }

        # Istegi isle
        try:
            result = handler(context.get("payload", payload or {}))
            self._log_request(path, source, True)
            self._reset_failures(source)
            return {"success": True, "data": result}
        except Exception as e:
            self._log_request(path, source, False)
            self._record_failure(source)
            return {
                "success": False,
                "error": "handler_error",
                "message": str(e),
            }

    def aggregate_requests(
        self,
        paths: list[str],
        payload: dict[str, Any] | None = None,
        source: str = "",
    ) -> dict[str, Any]:
        """Coklu istek birlestirme yapar.

        Args:
            paths: API yollari.
            payload: Ortak istek verisi.
            source: Kaynak.

        Returns:
            Birlesik yanit.
        """
        results: dict[str, Any] = {}
        for path in paths:
            results[path] = self.request(path, payload, source)

        success = all(r.get("success") for r in results.values())
        return {
            "success": success,
            "results": results,
            "total": len(paths),
        }

    def reset_rate_limits(self) -> None:
        """Hiz siniri sayaclarini sifirlar."""
        for key in self._rate_counters:
            self._rate_counters[key] = 0

    def close_circuit(self, system_id: str) -> None:
        """Devreyi kapatir (izin verir).

        Args:
            system_id: Sistem ID.
        """
        self._circuit_states[system_id] = False
        self._failure_counts[system_id] = 0

    def open_circuit(self, system_id: str) -> None:
        """Devreyi acar (engeller).

        Args:
            system_id: Sistem ID.
        """
        self._circuit_states[system_id] = True

    def is_circuit_open(self, system_id: str) -> bool:
        """Devre acik mi.

        Args:
            system_id: Sistem ID.

        Returns:
            Acik ise True.
        """
        return self._circuit_states.get(system_id, False)

    def get_request_log(
        self,
        path: str = "",
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Istek gecmisini getirir.

        Args:
            path: Yol filtresi.
            limit: Maks kayit.

        Returns:
            Istek listesi.
        """
        logs = list(self._request_log)
        if path:
            logs = [l for l in logs if l["path"] == path]
        if limit > 0:
            logs = logs[-limit:]
        return logs

    def _log_request(
        self,
        path: str,
        source: str,
        success: bool,
    ) -> None:
        """Istegi loglar."""
        self._request_log.append({
            "path": path,
            "source": source,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _record_failure(self, source: str) -> None:
        """Hata kaydeder ve devre kontrolu yapar."""
        if not source:
            return
        count = self._failure_counts.get(source, 0) + 1
        self._failure_counts[source] = count
        if count >= self._failure_threshold:
            self.open_circuit(source)

    def _reset_failures(self, source: str) -> None:
        """Hata sayacini sifirlar."""
        if source:
            self._failure_counts[source] = 0

    @property
    def total_routes(self) -> int:
        """Toplam yol sayisi."""
        return len(self._routes)

    @property
    def total_requests(self) -> int:
        """Toplam istek sayisi."""
        return len(self._request_log)
