"""ATLAS Yan Araba Vekili modulu.

Istek yakalama, yanit isleme,
mTLS sonlandirma, baslik enjeksiyonu
ve loglama.
"""

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SidecarProxy:
    """Yan araba vekili.

    Istekleri yakalar ve isler.

    Attributes:
        _interceptors: Yakalayicilar.
        _log: Istek loglari.
    """

    def __init__(
        self,
        proxy_id: str = "default",
    ) -> None:
        """Vekili baslatir.

        Args:
            proxy_id: Vekil ID.
        """
        self._proxy_id = proxy_id
        self._request_interceptors: list[
            dict[str, Any]
        ] = []
        self._response_interceptors: list[
            dict[str, Any]
        ] = []
        self._injected_headers: dict[
            str, str
        ] = {}
        self._mtls_enabled = False
        self._mtls_certs: dict[
            str, str
        ] = {}
        self._access_log: list[
            dict[str, Any]
        ] = []
        self._stats: dict[str, int] = {
            "total_requests": 0,
            "total_responses": 0,
            "total_errors": 0,
        }

        logger.info(
            "SidecarProxy baslatildi: %s",
            proxy_id,
        )

    def intercept_request(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Istegi yakalar ve isler.

        Args:
            request: Istek verisi.

        Returns:
            Islenmis istek.
        """
        self._stats["total_requests"] += 1
        processed = dict(request)

        # Baslik enjeksiyonu
        if "headers" not in processed:
            processed["headers"] = {}
        processed["headers"].update(
            self._injected_headers,
        )
        processed["headers"]["x-proxy-id"] = (
            self._proxy_id
        )
        processed["headers"]["x-request-time"] = (
            str(time.time())
        )

        # mTLS kontrolu
        if self._mtls_enabled:
            processed["mtls"] = True
            processed["headers"][
                "x-mtls-verified"
            ] = "true"

        # Yakalayicilari calistir
        for interceptor in (
            self._request_interceptors
        ):
            try:
                fn = interceptor["fn"]
                processed = fn(processed)
            except Exception as e:
                logger.error(
                    "Interceptor hatasi: %s", e,
                )

        # Logla
        self._log_access(
            "request", processed,
        )

        return processed

    def intercept_response(
        self,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """Yaniti yakalar ve isler.

        Args:
            response: Yanit verisi.

        Returns:
            Islenmis yanit.
        """
        self._stats["total_responses"] += 1
        processed = dict(response)

        if "headers" not in processed:
            processed["headers"] = {}
        processed["headers"]["x-proxy-id"] = (
            self._proxy_id
        )

        # Yanit yakalayicilari
        for interceptor in (
            self._response_interceptors
        ):
            try:
                fn = interceptor["fn"]
                processed = fn(processed)
            except Exception:
                pass

        # Hata kontrolu
        status = processed.get("status_code", 200)
        if status >= 400:
            self._stats["total_errors"] += 1

        self._log_access(
            "response", processed,
        )

        return processed

    def add_request_interceptor(
        self,
        name: str,
        fn: Any,
        priority: int = 0,
    ) -> None:
        """Istek yakalayici ekler.

        Args:
            name: Yakalayici adi.
            fn: Fonksiyon.
            priority: Oncelik.
        """
        self._request_interceptors.append({
            "name": name,
            "fn": fn,
            "priority": priority,
        })
        self._request_interceptors.sort(
            key=lambda x: x["priority"],
        )

    def add_response_interceptor(
        self,
        name: str,
        fn: Any,
        priority: int = 0,
    ) -> None:
        """Yanit yakalayici ekler.

        Args:
            name: Yakalayici adi.
            fn: Fonksiyon.
            priority: Oncelik.
        """
        self._response_interceptors.append({
            "name": name,
            "fn": fn,
            "priority": priority,
        })

    def inject_header(
        self,
        key: str,
        value: str,
    ) -> None:
        """Baslik enjekte eder.

        Args:
            key: Baslik adi.
            value: Deger.
        """
        self._injected_headers[key] = value

    def remove_header(
        self,
        key: str,
    ) -> bool:
        """Enjekte edilen basligi kaldirir.

        Args:
            key: Baslik adi.

        Returns:
            Basarili mi.
        """
        if key in self._injected_headers:
            del self._injected_headers[key]
            return True
        return False

    def enable_mtls(
        self,
        cert: str = "",
        key: str = "",
    ) -> None:
        """mTLS etkinlestirir.

        Args:
            cert: Sertifika.
            key: Anahtar.
        """
        self._mtls_enabled = True
        if cert:
            self._mtls_certs["cert"] = cert
        if key:
            self._mtls_certs["key"] = key

    def disable_mtls(self) -> None:
        """mTLS devre disi birakir."""
        self._mtls_enabled = False

    def _log_access(
        self,
        log_type: str,
        data: dict[str, Any],
    ) -> None:
        """Erisim loglar.

        Args:
            log_type: Log tipi.
            data: Log verisi.
        """
        self._access_log.append({
            "type": log_type,
            "proxy_id": self._proxy_id,
            "path": data.get("path", ""),
            "method": data.get("method", ""),
            "status_code": data.get(
                "status_code", 0,
            ),
            "timestamp": time.time(),
        })

    def get_access_log(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Erisim loglarini getirir.

        Args:
            limit: Limit.

        Returns:
            Log listesi.
        """
        return self._access_log[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return {
            "proxy_id": self._proxy_id,
            "mtls_enabled": self._mtls_enabled,
            **self._stats,
            "injected_headers": len(
                self._injected_headers,
            ),
            "interceptors": (
                len(self._request_interceptors)
                + len(self._response_interceptors)
            ),
        }

    @property
    def proxy_id(self) -> str:
        """Vekil ID."""
        return self._proxy_id

    @property
    def mtls_enabled(self) -> bool:
        """mTLS aktif mi."""
        return self._mtls_enabled

    @property
    def log_count(self) -> int:
        """Log sayisi."""
        return len(self._access_log)

    @property
    def interceptor_count(self) -> int:
        """Yakalayici sayisi."""
        return (
            len(self._request_interceptors)
            + len(self._response_interceptors)
        )
