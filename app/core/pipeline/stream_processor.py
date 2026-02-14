"""ATLAS Akis Isleyici modulu.

Gercek zamanli isleme, pencereleme,
gruplama, olay siralama ve gec
veri islemleri.
"""

import logging
import time
from typing import Any, Callable

from app.models.pipeline import WindowType

logger = logging.getLogger(__name__)


class StreamProcessor:
    """Akis isleyici.

    Gercek zamanli veri akislarini
    isler ve pencereler.

    Attributes:
        _streams: Kayitli akislar.
        _windows: Pencere tanimlari.
        _handlers: Olay isleyicileri.
        _buffer: Olay tamponu.
    """

    def __init__(
        self,
        buffer_size: int = 1000,
    ) -> None:
        """Akis isleyiciyi baslatir.

        Args:
            buffer_size: Tampon boyutu.
        """
        self._streams: dict[str, dict[str, Any]] = {}
        self._windows: dict[str, dict[str, Any]] = {}
        self._handlers: dict[
            str, Callable[[dict[str, Any]], Any]
        ] = {}
        self._buffer: list[dict[str, Any]] = []
        self._buffer_size = buffer_size
        self._processed: int = 0
        self._late_count: int = 0

        logger.info("StreamProcessor baslatildi")

    def register_stream(
        self,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Akis kaydeder.

        Args:
            name: Akis adi.
            config: Yapilandirma.

        Returns:
            Akis bilgisi.
        """
        stream = {
            "name": name,
            "config": config or {},
            "active": True,
            "event_count": 0,
        }
        self._streams[name] = stream
        return stream

    def add_window(
        self,
        name: str,
        window_type: WindowType,
        size_seconds: int = 60,
        slide_seconds: int = 0,
    ) -> dict[str, Any]:
        """Pencere tanimlar.

        Args:
            name: Pencere adi.
            window_type: Pencere turu.
            size_seconds: Pencere boyutu.
            slide_seconds: Kayma suresi.

        Returns:
            Pencere bilgisi.
        """
        window = {
            "name": name,
            "type": window_type.value,
            "size": size_seconds,
            "slide": slide_seconds or size_seconds,
            "events": [],
        }
        self._windows[name] = window
        return window

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Olay isleyici kaydeder.

        Args:
            event_type: Olay turu.
            handler: Isleyici fonksiyon.
        """
        self._handlers[event_type] = handler

    def emit(
        self,
        stream_name: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """Olay yayinlar.

        Args:
            stream_name: Akis adi.
            event: Olay verisi.

        Returns:
            Islem sonucu.
        """
        stream = self._streams.get(stream_name)
        if not stream or not stream["active"]:
            return {
                "processed": False,
                "reason": "stream_not_found",
            }

        event["_stream"] = stream_name
        event["_timestamp"] = event.get(
            "_timestamp", time.time(),
        )

        # Tampon kontrolu
        if len(self._buffer) >= self._buffer_size:
            self._buffer.pop(0)
        self._buffer.append(event)

        stream["event_count"] += 1

        # Pencerelere ekle
        for window in self._windows.values():
            window["events"].append(event)

        # Isleyici cagir
        event_type = event.get("type", "default")
        handler = self._handlers.get(event_type)
        result_data: Any = None
        if handler:
            result_data = handler(event)

        self._processed += 1

        return {
            "processed": True,
            "stream": stream_name,
            "handler_result": result_data,
        }

    def process_window(
        self,
        window_name: str,
        agg_func: str = "count",
    ) -> dict[str, Any]:
        """Pencere isler.

        Args:
            window_name: Pencere adi.
            agg_func: Gruplama fonksiyonu.

        Returns:
            Pencere sonucu.
        """
        window = self._windows.get(window_name)
        if not window:
            return {
                "window": window_name,
                "result": None,
            }

        events = window["events"]
        now = time.time()
        window_size = window["size"]

        # Pencere icindeki olaylar
        in_window = [
            e for e in events
            if now - e.get("_timestamp", 0)
            <= window_size
        ]

        result: Any = None
        if agg_func == "count":
            result = len(in_window)
        elif agg_func == "last":
            result = in_window[-1] if in_window else None

        return {
            "window": window_name,
            "type": window["type"],
            "total_events": len(events),
            "in_window": len(in_window),
            "result": result,
        }

    def handle_late_event(
        self,
        stream_name: str,
        event: dict[str, Any],
        max_lateness: int = 300,
    ) -> dict[str, Any]:
        """Gec olay isler.

        Args:
            stream_name: Akis adi.
            event: Olay verisi.
            max_lateness: Maks gecikme (saniye).

        Returns:
            Islem sonucu.
        """
        ts = event.get("_timestamp", 0)
        now = time.time()
        lateness = now - ts

        if lateness > max_lateness:
            self._late_count += 1
            return {
                "processed": False,
                "reason": "too_late",
                "lateness": round(lateness, 2),
            }

        self._late_count += 1
        return self.emit(stream_name, event)

    def pause_stream(self, name: str) -> bool:
        """Akisi duraklatir.

        Args:
            name: Akis adi.

        Returns:
            Basarili ise True.
        """
        stream = self._streams.get(name)
        if stream:
            stream["active"] = False
            return True
        return False

    def resume_stream(self, name: str) -> bool:
        """Akisi devam ettirir.

        Args:
            name: Akis adi.

        Returns:
            Basarili ise True.
        """
        stream = self._streams.get(name)
        if stream:
            stream["active"] = True
            return True
        return False

    def clear_window(
        self,
        window_name: str,
    ) -> int:
        """Pencereyi temizler.

        Args:
            window_name: Pencere adi.

        Returns:
            Temizlenen olay sayisi.
        """
        window = self._windows.get(window_name)
        if not window:
            return 0
        count = len(window["events"])
        window["events"] = []
        return count

    @property
    def stream_count(self) -> int:
        """Akis sayisi."""
        return len(self._streams)

    @property
    def window_count(self) -> int:
        """Pencere sayisi."""
        return len(self._windows)

    @property
    def processed_count(self) -> int:
        """Islenen olay sayisi."""
        return self._processed

    @property
    def buffer_count(self) -> int:
        """Tampondaki olay sayisi."""
        return len(self._buffer)

    @property
    def late_count(self) -> int:
        """Gec olay sayisi."""
        return self._late_count
