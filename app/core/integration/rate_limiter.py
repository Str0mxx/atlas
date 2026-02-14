"""ATLAS Hiz Sinirlandirici modulu.

Servis bazli limitler, kota yonetimi,
backoff stratejileri, kuyruk ve oncelik.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """Hiz sinirlandirici.

    Dis servislere yapilan istekleri
    hiz sinirina gore yonetir.

    Attributes:
        _limits: Servis limitleri.
        _counters: Istek sayaclari.
        _queue: Bekleyen istekler.
        _default_limit: Varsayilan limit.
    """

    def __init__(self, default_limit: int = 100) -> None:
        """Hiz sinirlandiriciyi baslatir.

        Args:
            default_limit: Varsayilan limit (istek/dk).
        """
        self._limits: dict[str, dict[str, Any]] = {}
        self._counters: dict[str, list[str]] = {}
        self._queue: list[dict[str, Any]] = []
        self._default_limit = max(1, default_limit)
        self._blocked_count = 0

        logger.info(
            "RateLimiter baslatildi (default=%d/dk)",
            self._default_limit,
        )

    def set_limit(
        self,
        service: str,
        requests_per_minute: int,
        burst_limit: int | None = None,
        priority_bypass: bool = False,
    ) -> dict[str, Any]:
        """Servis limiti ayarlar.

        Args:
            service: Servis adi.
            requests_per_minute: Dakikadaki istek limiti.
            burst_limit: Ani yigin limiti.
            priority_bypass: Oncelik atlama.

        Returns:
            Limit bilgisi.
        """
        limit = {
            "service": service,
            "requests_per_minute": max(1, requests_per_minute),
            "burst_limit": burst_limit or requests_per_minute * 2,
            "priority_bypass": priority_bypass,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._limits[service] = limit

        if service not in self._counters:
            self._counters[service] = []

        logger.info(
            "Limit ayarlandi: %s (%d/dk)",
            service, requests_per_minute,
        )
        return limit

    def check_limit(
        self,
        service: str,
        priority: int = 0,
    ) -> dict[str, Any]:
        """Limit kontrolu yapar.

        Args:
            service: Servis adi.
            priority: Oncelik (0=normal, >0=yuksek).

        Returns:
            Kontrol sonucu.
        """
        limit_config = self._limits.get(service)
        rpm = self._default_limit
        priority_bypass = False

        if limit_config:
            rpm = limit_config["requests_per_minute"]
            priority_bypass = limit_config["priority_bypass"]

        # Oncelik atlama
        if priority > 0 and priority_bypass:
            return {
                "allowed": True,
                "service": service,
                "reason": "priority_bypass",
            }

        # Sayac temizle (eski kayitlari)
        self._cleanup_counters(service)

        current = len(self._counters.get(service, []))

        if current >= rpm:
            self._blocked_count += 1
            return {
                "allowed": False,
                "service": service,
                "current": current,
                "limit": rpm,
                "retry_after_seconds": 60,
            }

        return {
            "allowed": True,
            "service": service,
            "current": current,
            "limit": rpm,
            "remaining": rpm - current,
        }

    def record_request(
        self,
        service: str,
    ) -> None:
        """Istek kaydeder.

        Args:
            service: Servis adi.
        """
        if service not in self._counters:
            self._counters[service] = []
        self._counters[service].append(
            datetime.now(timezone.utc).isoformat(),
        )

    def enqueue(
        self,
        service: str,
        request_data: dict[str, Any],
        priority: int = 0,
    ) -> dict[str, Any]:
        """Istegi kuyruga ekler.

        Args:
            service: Servis adi.
            request_data: Istek verisi.
            priority: Oncelik.

        Returns:
            Kuyruk bilgisi.
        """
        item = {
            "service": service,
            "data": request_data,
            "priority": priority,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        }
        self._queue.append(item)

        # Oncelik sirala
        self._queue.sort(
            key=lambda x: x.get("priority", 0),
            reverse=True,
        )

        return {
            "position": self._queue.index(item) + 1,
            "total_queued": len(self._queue),
        }

    def dequeue(
        self,
        service: str = "",
    ) -> dict[str, Any] | None:
        """Kuyruktan istek alir.

        Args:
            service: Servis filtresi.

        Returns:
            Istek verisi veya None.
        """
        if service:
            for i, item in enumerate(self._queue):
                if item["service"] == service:
                    return self._queue.pop(i)
            return None

        if self._queue:
            return self._queue.pop(0)
        return None

    def get_quota(
        self,
        service: str,
    ) -> dict[str, Any]:
        """Kota bilgisi getirir.

        Args:
            service: Servis adi.

        Returns:
            Kota bilgisi.
        """
        limit_config = self._limits.get(service)
        rpm = self._default_limit
        if limit_config:
            rpm = limit_config["requests_per_minute"]

        self._cleanup_counters(service)
        current = len(self._counters.get(service, []))

        return {
            "service": service,
            "limit": rpm,
            "used": current,
            "remaining": max(0, rpm - current),
            "utilization": round(current / rpm, 3) if rpm > 0 else 0,
        }

    def apply_backoff(
        self,
        service: str,
        attempt: int,
        strategy: str = "exponential",
    ) -> dict[str, Any]:
        """Backoff stratejisi uygular.

        Args:
            service: Servis adi.
            attempt: Deneme sayisi.
            strategy: Strateji.

        Returns:
            Backoff bilgisi.
        """
        if strategy == "exponential":
            wait = min(2 ** attempt, 300)
        elif strategy == "linear":
            wait = min(attempt * 5, 300)
        elif strategy == "fixed":
            wait = 10
        else:
            wait = min(2 ** attempt, 300)

        return {
            "service": service,
            "attempt": attempt,
            "strategy": strategy,
            "wait_seconds": wait,
        }

    def reset_counter(self, service: str) -> None:
        """Sayaci sifirlar.

        Args:
            service: Servis adi.
        """
        self._counters[service] = []

    def _cleanup_counters(self, service: str) -> None:
        """Eski sayaclari temizler.

        Args:
            service: Servis adi.
        """
        if service not in self._counters:
            return

        now = datetime.now(timezone.utc)
        self._counters[service] = [
            ts for ts in self._counters[service]
            if (now - datetime.fromisoformat(ts)).total_seconds() < 60
        ]

    @property
    def service_count(self) -> int:
        """Limitli servis sayisi."""
        return len(self._limits)

    @property
    def queue_size(self) -> int:
        """Kuyruk boyutu."""
        return len(self._queue)

    @property
    def blocked_count(self) -> int:
        """Engellenen istek sayisi."""
        return self._blocked_count
