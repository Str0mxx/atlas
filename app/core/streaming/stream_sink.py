"""ATLAS Akis Cikisi modulu.

Database sink, Kafka producer,
dosya ciktisi, API push
ve coklu cikislar.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class StreamSink:
    """Akis cikisi.

    Islenmis verileri hedeflere yazar.

    Attributes:
        _sinks: Kayitli cikislar.
        _buffers: Cikis tamponlari.
    """

    def __init__(self) -> None:
        """Cikisi baslatir."""
        self._sinks: dict[
            str, dict[str, Any]
        ] = {}
        self._buffers: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._writers: dict[
            str, Callable[
                [list[dict[str, Any]]], int
            ]
        ] = {}
        self._stats: dict[str, dict[str, int]] = {}

        logger.info("StreamSink baslatildi")

    def register(
        self,
        name: str,
        sink_type: str,
        config: dict[str, Any]
            | None = None,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """Cikis kaydeder.

        Args:
            name: Cikis adi.
            sink_type: Cikis tipi.
            config: Konfigurasyon.
            batch_size: Yigin boyutu.

        Returns:
            Kayit bilgisi.
        """
        self._sinks[name] = {
            "name": name,
            "type": sink_type,
            "config": config or {},
            "batch_size": batch_size,
            "status": "active",
            "created_at": time.time(),
        }
        self._buffers[name] = []
        self._stats[name] = {
            "written": 0,
            "errors": 0,
            "batches": 0,
        }

        return {
            "name": name,
            "type": sink_type,
            "status": "active",
        }

    def set_writer(
        self,
        name: str,
        writer: Callable[
            [list[dict[str, Any]]], int
        ],
    ) -> bool:
        """Yazici fonksiyonu ayarlar.

        Args:
            name: Cikis adi.
            writer: Yazici fonksiyonu.

        Returns:
            Basarili mi.
        """
        if name in self._sinks:
            self._writers[name] = writer
            return True
        return False

    def write(
        self,
        name: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """Olay yazar.

        Args:
            name: Cikis adi.
            event: Olay verisi.

        Returns:
            Yazma sonucu.
        """
        sink = self._sinks.get(name)
        if not sink:
            return {"error": "sink_not_found"}

        if sink["status"] != "active":
            return {"error": "sink_inactive"}

        self._buffers[name].append(event)
        self._stats[name]["written"] += 1

        # Otomatik flush
        if (
            len(self._buffers[name])
            >= sink["batch_size"]
        ):
            self.flush(name)

        return {
            "name": name,
            "buffered": len(self._buffers[name]),
        }

    def write_batch(
        self,
        name: str,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Toplu yazar.

        Args:
            name: Cikis adi.
            events: Olaylar.

        Returns:
            Yazma sonucu.
        """
        sink = self._sinks.get(name)
        if not sink:
            return {"error": "sink_not_found"}

        for event in events:
            self._buffers[name].append(event)
            self._stats[name]["written"] += 1

        return {
            "name": name,
            "written": len(events),
        }

    def flush(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Tamponu bosaltir.

        Args:
            name: Cikis adi.

        Returns:
            Flush sonucu.
        """
        buf = self._buffers.get(name, [])
        if not buf:
            return {"name": name, "flushed": 0}

        writer = self._writers.get(name)
        flushed = len(buf)

        if writer:
            try:
                writer(buf)
            except Exception:
                self._stats[name]["errors"] += 1

        self._stats[name]["batches"] += 1
        self._buffers[name] = []

        return {
            "name": name,
            "flushed": flushed,
        }

    def flush_all(self) -> dict[str, int]:
        """Tum tamponlari bosaltir.

        Returns:
            Cikis bazli flush sayilari.
        """
        result: dict[str, int] = {}
        for name in self._sinks:
            r = self.flush(name)
            result[name] = r.get("flushed", 0)
        return result

    def broadcast(
        self,
        event: dict[str, Any],
        sinks: list[str] | None = None,
    ) -> dict[str, Any]:
        """Birden fazla cikisa yazar.

        Args:
            event: Olay.
            sinks: Hedef cikislar (None=tumu).

        Returns:
            Yayin sonucu.
        """
        targets = sinks or list(self._sinks.keys())
        written = 0
        errors = 0

        for name in targets:
            r = self.write(name, event)
            if "error" in r:
                errors += 1
            else:
                written += 1

        return {
            "targets": len(targets),
            "written": written,
            "errors": errors,
        }

    def pause(self, name: str) -> bool:
        """Cikisi duraklatir.

        Args:
            name: Cikis adi.

        Returns:
            Basarili mi.
        """
        sink = self._sinks.get(name)
        if sink:
            sink["status"] = "paused"
            return True
        return False

    def resume(self, name: str) -> bool:
        """Cikisi devam ettirir.

        Args:
            name: Cikis adi.

        Returns:
            Basarili mi.
        """
        sink = self._sinks.get(name)
        if sink:
            sink["status"] = "active"
            return True
        return False

    def remove(self, name: str) -> bool:
        """Cikisi kaldirir.

        Args:
            name: Cikis adi.

        Returns:
            Basarili mi.
        """
        if name in self._sinks:
            self.flush(name)
            del self._sinks[name]
            self._buffers.pop(name, None)
            self._writers.pop(name, None)
            self._stats.pop(name, None)
            return True
        return False

    def get_sink(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Cikis bilgisini getirir.

        Args:
            name: Cikis adi.

        Returns:
            Cikis bilgisi veya None.
        """
        return self._sinks.get(name)

    def get_stats(
        self,
        name: str,
    ) -> dict[str, int] | None:
        """Istatistikleri getirir.

        Args:
            name: Cikis adi.

        Returns:
            Istatistikler veya None.
        """
        return self._stats.get(name)

    @property
    def sink_count(self) -> int:
        """Cikis sayisi."""
        return len(self._sinks)

    @property
    def active_count(self) -> int:
        """Aktif cikis sayisi."""
        return sum(
            1 for s in self._sinks.values()
            if s["status"] == "active"
        )

    @property
    def total_written(self) -> int:
        """Toplam yazilan olay sayisi."""
        return sum(
            s["written"]
            for s in self._stats.values()
        )

    @property
    def total_buffered(self) -> int:
        """Toplam tamponlanmis olay."""
        return sum(
            len(b)
            for b in self._buffers.values()
        )
