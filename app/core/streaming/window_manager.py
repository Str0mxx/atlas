"""ATLAS Pencere Yoneticisi modulu.

Tumbling, sliding, session,
count-based pencereler
ve gec veri yonetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class WindowManager:
    """Pencere yoneticisi.

    Zaman ve sayac tabanli pencereleri yonetir.

    Attributes:
        _windows: Aktif pencereler.
        _closed: Kapatilmis pencereler.
    """

    def __init__(
        self,
        default_size: int = 60,
        max_lateness: int = 10,
    ) -> None:
        """Yoneticiyi baslatir.

        Args:
            default_size: Varsayilan pencere boyutu (sn).
            max_lateness: Maks gecikme (sn).
        """
        self._default_size = default_size
        self._max_lateness = max_lateness
        self._windows: dict[
            str, dict[str, Any]
        ] = {}
        self._closed: list[
            dict[str, Any]
        ] = []

        logger.info(
            "WindowManager baslatildi: "
            "size=%d, lateness=%d",
            default_size, max_lateness,
        )

    def create_tumbling(
        self,
        name: str,
        size: int | None = None,
    ) -> dict[str, Any]:
        """Tumbling pencere olusturur.

        Args:
            name: Pencere adi.
            size: Boyut (sn).

        Returns:
            Pencere bilgisi.
        """
        sz = size or self._default_size
        now = time.time()

        self._windows[name] = {
            "name": name,
            "type": "tumbling",
            "size": sz,
            "start": now,
            "end": now + sz,
            "events": [],
            "count": 0,
            "created_at": now,
        }

        return {"name": name, "type": "tumbling", "size": sz}

    def create_sliding(
        self,
        name: str,
        size: int | None = None,
        slide: int = 10,
    ) -> dict[str, Any]:
        """Sliding pencere olusturur.

        Args:
            name: Pencere adi.
            size: Boyut (sn).
            slide: Kayma (sn).

        Returns:
            Pencere bilgisi.
        """
        sz = size or self._default_size
        now = time.time()

        self._windows[name] = {
            "name": name,
            "type": "sliding",
            "size": sz,
            "slide": slide,
            "start": now,
            "end": now + sz,
            "events": [],
            "count": 0,
            "created_at": now,
        }

        return {"name": name, "type": "sliding", "size": sz}

    def create_session(
        self,
        name: str,
        gap: int = 30,
    ) -> dict[str, Any]:
        """Session pencere olusturur.

        Args:
            name: Pencere adi.
            gap: Oturum boslugu (sn).

        Returns:
            Pencere bilgisi.
        """
        now = time.time()

        self._windows[name] = {
            "name": name,
            "type": "session",
            "gap": gap,
            "start": now,
            "last_event": now,
            "events": [],
            "count": 0,
            "created_at": now,
        }

        return {"name": name, "type": "session", "gap": gap}

    def create_count(
        self,
        name: str,
        max_count: int = 100,
    ) -> dict[str, Any]:
        """Count-based pencere olusturur.

        Args:
            name: Pencere adi.
            max_count: Maks olay sayisi.

        Returns:
            Pencere bilgisi.
        """
        self._windows[name] = {
            "name": name,
            "type": "count",
            "max_count": max_count,
            "events": [],
            "count": 0,
            "created_at": time.time(),
        }

        return {"name": name, "type": "count", "max_count": max_count}

    def add_event(
        self,
        window: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """Pencereye olay ekler.

        Args:
            window: Pencere adi.
            event: Olay.

        Returns:
            Ekleme sonucu.
        """
        win = self._windows.get(window)
        if not win:
            return {"error": "window_not_found"}

        event_ts = event.get(
            "timestamp", time.time(),
        )

        # Gec veri kontrolu
        if win["type"] in ("tumbling", "sliding"):
            end = win.get("end", float("inf"))
            if event_ts > end + self._max_lateness:
                return {
                    "status": "late_dropped",
                    "lateness": event_ts - end,
                }

        win["events"].append(event)
        win["count"] += 1

        if win["type"] == "session":
            win["last_event"] = time.time()

        # Count pencere doldu mu
        if (
            win["type"] == "count"
            and win["count"] >= win["max_count"]
        ):
            return {
                "status": "added",
                "window_full": True,
                "count": win["count"],
            }

        return {
            "status": "added",
            "window_full": False,
            "count": win["count"],
        }

    def get_events(
        self,
        window: str,
    ) -> list[dict[str, Any]]:
        """Pencere olaylarini getirir.

        Args:
            window: Pencere adi.

        Returns:
            Olay listesi.
        """
        win = self._windows.get(window)
        if not win:
            return []
        return list(win["events"])

    def close_window(
        self,
        window: str,
    ) -> dict[str, Any]:
        """Pencereyi kapatir.

        Args:
            window: Pencere adi.

        Returns:
            Kapatma bilgisi.
        """
        win = self._windows.pop(window, None)
        if not win:
            return {"error": "window_not_found"}

        win["closed_at"] = time.time()
        self._closed.append(win)

        return {
            "name": window,
            "events": win["count"],
            "status": "closed",
        }

    def check_expired(self) -> list[str]:
        """Suresi dolmus pencereleri bulur.

        Returns:
            Dolmus pencere adlari.
        """
        now = time.time()
        expired: list[str] = []

        for name, win in self._windows.items():
            if win["type"] == "tumbling":
                if now > win["end"]:
                    expired.append(name)
            elif win["type"] == "sliding":
                if now > win["end"]:
                    expired.append(name)
            elif win["type"] == "session":
                gap = win.get("gap", 30)
                if now - win["last_event"] > gap:
                    expired.append(name)
            elif win["type"] == "count":
                if win["count"] >= win["max_count"]:
                    expired.append(name)

        return expired

    def get_window(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Pencere bilgisini getirir.

        Args:
            name: Pencere adi.

        Returns:
            Pencere bilgisi veya None.
        """
        return self._windows.get(name)

    def get_closed(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kapatilmis pencereleri getirir.

        Args:
            limit: Limit.

        Returns:
            Pencere listesi.
        """
        return self._closed[-limit:]

    @property
    def window_count(self) -> int:
        """Aktif pencere sayisi."""
        return len(self._windows)

    @property
    def closed_count(self) -> int:
        """Kapatilmis pencere sayisi."""
        return len(self._closed)

    @property
    def total_events(self) -> int:
        """Toplam olay sayisi."""
        return sum(
            w["count"]
            for w in self._windows.values()
        )

    @property
    def default_size(self) -> int:
        """Varsayilan pencere boyutu."""
        return self._default_size
