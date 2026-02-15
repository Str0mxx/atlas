"""ATLAS Kayan Pencere modulu.

Zaman tabanli pencereler, istek sayma,
kayma, hassasiyet, bellek verimliligi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SlidingWindow:
    """Kayan pencere algoritması.

    Zaman penceresinde istek sayisini izler.

    Attributes:
        _windows: Pencere kayitlari.
    """

    def __init__(
        self,
        default_window_size: int = 60,
        default_max_requests: int = 100,
        precision: int = 10,
    ) -> None:
        """Kayan pencereyi baslatir.

        Args:
            default_window_size: Pencere boyutu (sn).
            default_max_requests: Maks istek.
            precision: Alt pencere sayisi.
        """
        self._windows: dict[
            str, dict[str, Any]
        ] = {}
        self._default_window_size = default_window_size
        self._default_max_requests = default_max_requests
        self._precision = precision
        self._stats = {
            "allowed": 0,
            "rejected": 0,
            "total_requests": 0,
        }

        logger.info(
            "SlidingWindow baslatildi",
        )

    def create_window(
        self,
        key: str,
        window_size: int | None = None,
        max_requests: int | None = None,
    ) -> dict[str, Any]:
        """Pencere olusturur.

        Args:
            key: Pencere anahtari.
            window_size: Pencere boyutu (sn).
            max_requests: Maks istek.

        Returns:
            Pencere bilgisi.
        """
        size = window_size or self._default_window_size
        max_req = (
            max_requests or self._default_max_requests
        )
        sub_size = size / self._precision

        self._windows[key] = {
            "key": key,
            "window_size": size,
            "max_requests": max_req,
            "sub_window_size": sub_size,
            "counters": {},
            "created_at": time.time(),
        }

        return {
            "key": key,
            "window_size": size,
            "max_requests": max_req,
            "status": "created",
        }

    def record(
        self,
        key: str,
        count: int = 1,
    ) -> dict[str, Any]:
        """Istek kaydeder ve kontrol eder.

        Args:
            key: Pencere anahtari.
            count: Istek sayisi.

        Returns:
            Kontrol sonucu.
        """
        window = self._windows.get(key)
        if not window:
            return {
                "allowed": False,
                "reason": "window_not_found",
            }

        now = time.time()
        self._cleanup(key, now)

        current = self._count_requests(key, now)
        self._stats["total_requests"] += count

        if current + count > window["max_requests"]:
            self._stats["rejected"] += 1
            retry_after = self._calc_retry_after(
                key, now,
            )
            return {
                "allowed": False,
                "reason": "rate_exceeded",
                "current": current,
                "limit": window["max_requests"],
                "retry_after": round(
                    retry_after, 2,
                ),
            }

        # Kaydet
        sub_key = self._sub_window_key(
            now, window["sub_window_size"],
        )
        counters = window["counters"]
        counters[sub_key] = (
            counters.get(sub_key, 0) + count
        )

        self._stats["allowed"] += 1

        return {
            "allowed": True,
            "current": current + count,
            "limit": window["max_requests"],
            "remaining": (
                window["max_requests"]
                - current - count
            ),
        }

    def get_count(
        self,
        key: str,
    ) -> int:
        """Mevcut istek sayisini getirir.

        Args:
            key: Pencere anahtari.

        Returns:
            Istek sayisi.
        """
        window = self._windows.get(key)
        if not window:
            return 0

        now = time.time()
        self._cleanup(key, now)
        return self._count_requests(key, now)

    def get_remaining(
        self,
        key: str,
    ) -> int:
        """Kalan istek sayisini getirir.

        Args:
            key: Pencere anahtari.

        Returns:
            Kalan istek.
        """
        window = self._windows.get(key)
        if not window:
            return 0

        current = self.get_count(key)
        return max(
            window["max_requests"] - current, 0,
        )

    def reset_window(
        self,
        key: str,
    ) -> dict[str, Any]:
        """Pencereyi sifirlar.

        Args:
            key: Pencere anahtari.

        Returns:
            Sifirlama sonucu.
        """
        window = self._windows.get(key)
        if not window:
            return {"error": "window_not_found"}

        window["counters"] = {}

        return {
            "key": key,
            "status": "reset",
        }

    def delete_window(
        self,
        key: str,
    ) -> bool:
        """Pencereyi siler.

        Args:
            key: Pencere anahtari.

        Returns:
            Basarili mi.
        """
        if key not in self._windows:
            return False
        del self._windows[key]
        return True

    def update_limits(
        self,
        key: str,
        max_requests: int | None = None,
        window_size: int | None = None,
    ) -> dict[str, Any]:
        """Pencere limitlerini gunceller.

        Args:
            key: Pencere anahtari.
            max_requests: Yeni maks istek.
            window_size: Yeni pencere boyutu.

        Returns:
            Guncelleme sonucu.
        """
        window = self._windows.get(key)
        if not window:
            return {"error": "window_not_found"}

        if max_requests is not None:
            window["max_requests"] = max_requests
        if window_size is not None:
            window["window_size"] = window_size
            window["sub_window_size"] = (
                window_size / self._precision
            )

        return {
            "key": key,
            "status": "updated",
        }

    def get_window(
        self,
        key: str,
    ) -> dict[str, Any] | None:
        """Pencere bilgisi getirir.

        Args:
            key: Pencere anahtari.

        Returns:
            Pencere bilgisi veya None.
        """
        window = self._windows.get(key)
        if not window:
            return None
        result = dict(window)
        result["current_count"] = self.get_count(
            key,
        )
        return result

    def list_windows(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Pencereleri listeler.

        Args:
            limit: Limit.

        Returns:
            Pencere listesi.
        """
        items = []
        for key in self._windows:
            w = dict(self._windows[key])
            w["current_count"] = self.get_count(
                key,
            )
            items.append(w)
        return items[-limit:]

    def _count_requests(
        self,
        key: str,
        now: float,
    ) -> int:
        """Penceredeki istek sayisini hesaplar.

        Args:
            key: Pencere anahtari.
            now: Simdiki zaman.

        Returns:
            Istek sayisi.
        """
        window = self._windows[key]
        cutoff = now - window["window_size"]
        sub_size = window["sub_window_size"]

        total = 0
        for sub_key, count in window[
            "counters"
        ].items():
            sub_start = sub_key * sub_size
            if sub_start >= cutoff:
                total += count

        return total

    def _cleanup(
        self,
        key: str,
        now: float,
    ) -> None:
        """Eski alt pencereleri temizler.

        Args:
            key: Pencere anahtari.
            now: Simdiki zaman.
        """
        window = self._windows[key]
        cutoff = now - window["window_size"]
        sub_size = window["sub_window_size"]

        expired = [
            sk for sk in window["counters"]
            if sk * sub_size < cutoff
        ]
        for sk in expired:
            del window["counters"][sk]

    def _sub_window_key(
        self,
        now: float,
        sub_size: float,
    ) -> int:
        """Alt pencere anahtari hesaplar.

        Args:
            now: Simdiki zaman.
            sub_size: Alt pencere boyutu.

        Returns:
            Alt pencere anahtari.
        """
        return int(now / sub_size)

    def _calc_retry_after(
        self,
        key: str,
        now: float,
    ) -> float:
        """Yeniden deneme suresini hesaplar.

        Args:
            key: Pencere anahtari.
            now: Simdiki zaman.

        Returns:
            Bekleme suresi (sn).
        """
        window = self._windows[key]
        sub_size = window["sub_window_size"]
        if not window["counters"]:
            return 0

        oldest_key = min(window["counters"])
        oldest_time = oldest_key * sub_size
        return max(
            oldest_time
            + window["window_size"]
            - now,
            0,
        )

    @property
    def window_count(self) -> int:
        """Pencere sayisi."""
        return len(self._windows)

    @property
    def allowed_count(self) -> int:
        """Izin verilen sayisi."""
        return self._stats["allowed"]

    @property
    def rejected_count(self) -> int:
        """Reddedilen sayisi."""
        return self._stats["rejected"]
