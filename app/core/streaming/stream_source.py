"""ATLAS Akis Kaynagi modulu.

Kafka consumer, WebSocket akislari,
dosya takibi, API yoklama
ve olay ureticileri.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class StreamSource:
    """Akis kaynagi.

    Farkli kaynaklardan veri akisi saglar.

    Attributes:
        _sources: Kayitli kaynaklar.
        _buffers: Olay tamponlari.
    """

    def __init__(self) -> None:
        """Kaynagi baslatir."""
        self._sources: dict[
            str, dict[str, Any]
        ] = {}
        self._buffers: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._generators: dict[
            str, Callable[[], dict[str, Any]]
        ] = {}
        self._stats: dict[str, dict[str, int]] = {}

        logger.info("StreamSource baslatildi")

    def register(
        self,
        name: str,
        source_type: str,
        config: dict[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        """Kaynak kaydeder.

        Args:
            name: Kaynak adi.
            source_type: Kaynak tipi.
            config: Konfigurasyon.

        Returns:
            Kayit bilgisi.
        """
        self._sources[name] = {
            "name": name,
            "type": source_type,
            "config": config or {},
            "status": "active",
            "created_at": time.time(),
        }
        self._buffers[name] = []
        self._stats[name] = {
            "received": 0,
            "errors": 0,
        }

        return {
            "name": name,
            "type": source_type,
            "status": "active",
        }

    def emit(
        self,
        source: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """Olay yayar.

        Args:
            source: Kaynak adi.
            event: Olay verisi.

        Returns:
            Yayim bilgisi.
        """
        if source not in self._sources:
            return {"error": "source_not_found"}

        enriched = {
            **event,
            "source": source,
            "timestamp": event.get(
                "timestamp", time.time(),
            ),
        }
        self._buffers[source].append(enriched)
        self._stats[source]["received"] += 1

        return {
            "source": source,
            "buffered": len(self._buffers[source]),
        }

    def emit_batch(
        self,
        source: str,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Toplu olay yayar.

        Args:
            source: Kaynak adi.
            events: Olaylar.

        Returns:
            Yayim bilgisi.
        """
        if source not in self._sources:
            return {"error": "source_not_found"}

        for event in events:
            self.emit(source, event)

        return {
            "source": source,
            "emitted": len(events),
        }

    def consume(
        self,
        source: str,
        max_events: int = 100,
    ) -> list[dict[str, Any]]:
        """Olaylari tuketir.

        Args:
            source: Kaynak adi.
            max_events: Maks olay.

        Returns:
            Olay listesi.
        """
        buf = self._buffers.get(source, [])
        events = buf[:max_events]
        self._buffers[source] = buf[max_events:]
        return events

    def register_generator(
        self,
        name: str,
        generator: Callable[
            [], dict[str, Any]
        ],
    ) -> dict[str, Any]:
        """Olay ureticisi kaydeder.

        Args:
            name: Uretici adi.
            generator: Uretici fonksiyonu.

        Returns:
            Kayit bilgisi.
        """
        self._generators[name] = generator
        self.register(name, "generator")
        return {"name": name, "type": "generator"}

    def generate(
        self,
        name: str,
        count: int = 1,
    ) -> list[dict[str, Any]]:
        """Olay uretir.

        Args:
            name: Uretici adi.
            count: Uretilecek sayi.

        Returns:
            Uretilen olaylar.
        """
        gen = self._generators.get(name)
        if not gen:
            return []

        events: list[dict[str, Any]] = []
        for _ in range(count):
            event = gen()
            self.emit(name, event)
            events.append(event)

        return events

    def pause(self, name: str) -> bool:
        """Kaynagi duraklatir.

        Args:
            name: Kaynak adi.

        Returns:
            Basarili mi.
        """
        src = self._sources.get(name)
        if src:
            src["status"] = "paused"
            return True
        return False

    def resume(self, name: str) -> bool:
        """Kaynagi devam ettirir.

        Args:
            name: Kaynak adi.

        Returns:
            Basarili mi.
        """
        src = self._sources.get(name)
        if src:
            src["status"] = "active"
            return True
        return False

    def remove(self, name: str) -> bool:
        """Kaynagi kaldirir.

        Args:
            name: Kaynak adi.

        Returns:
            Basarili mi.
        """
        if name in self._sources:
            del self._sources[name]
            self._buffers.pop(name, None)
            self._stats.pop(name, None)
            self._generators.pop(name, None)
            return True
        return False

    def get_source(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Kaynak bilgisini getirir.

        Args:
            name: Kaynak adi.

        Returns:
            Kaynak bilgisi veya None.
        """
        return self._sources.get(name)

    def get_stats(
        self,
        name: str,
    ) -> dict[str, int] | None:
        """Kaynak istatistiklerini getirir.

        Args:
            name: Kaynak adi.

        Returns:
            Istatistikler veya None.
        """
        return self._stats.get(name)

    @property
    def source_count(self) -> int:
        """Kaynak sayisi."""
        return len(self._sources)

    @property
    def active_count(self) -> int:
        """Aktif kaynak sayisi."""
        return sum(
            1 for s in self._sources.values()
            if s["status"] == "active"
        )

    @property
    def total_buffered(self) -> int:
        """Toplam tamponlanmis olay sayisi."""
        return sum(
            len(b)
            for b in self._buffers.values()
        )

    @property
    def total_received(self) -> int:
        """Toplam alinan olay sayisi."""
        return sum(
            s["received"]
            for s in self._stats.values()
        )
