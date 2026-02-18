"""
Olay dongusu modulu.

Async olay dongusu, olay dagitimi,
oncelik isleme, geri basinc,
hata kurtarma.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class CoreEventLoop:
    """Cekirdek olay dongusu.

    Attributes:
        _handlers: Olay isleyicileri.
        _queue: Olay kuyrugu.
        _running: Calisiyor durumu.
        _stats: Istatistikler.
    """

    PRIORITY_LEVELS: dict[str, int] = {
        "critical": 0,
        "high": 1,
        "normal": 2,
        "low": 3,
        "background": 4,
    }

    def __init__(
        self,
        max_queue_size: int = 10000,
        backpressure_threshold: float = 0.8,
    ) -> None:
        """Donguyu baslatir.

        Args:
            max_queue_size: Max kuyruk.
            backpressure_threshold: Geri basinc esigi.
        """
        self._max_queue_size = (
            max_queue_size
        )
        self._backpressure_threshold = (
            backpressure_threshold
        )
        self._handlers: dict[
            str, list[Callable]
        ] = {}
        self._queue: list[dict] = []
        self._running = False
        self._processed: list[dict] = []
        self._errors: list[dict] = []
        self._stats: dict[str, int] = {
            "events_dispatched": 0,
            "events_processed": 0,
            "events_dropped": 0,
            "errors_recovered": 0,
            "backpressure_events": 0,
        }
        logger.info(
            "CoreEventLoop baslatildi"
        )

    @property
    def queue_size(self) -> int:
        """Kuyruk boyutu."""
        return len(self._queue)

    @property
    def is_running(self) -> bool:
        """Calisiyor mu."""
        return self._running

    def start(self) -> dict[str, Any]:
        """Donguyu baslatir.

        Returns:
            Baslatma bilgisi.
        """
        try:
            self._running = True
            return {
                "running": True,
                "started": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "started": False,
                "error": str(e),
            }

    def stop(self) -> dict[str, Any]:
        """Donguyu durdurur.

        Returns:
            Durdurma bilgisi.
        """
        try:
            self._running = False
            remaining = len(self._queue)
            return {
                "running": False,
                "remaining_events": (
                    remaining
                ),
                "stopped": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "stopped": False,
                "error": str(e),
            }

    def on(
        self,
        event_type: str = "",
        handler: Callable | None = None,
    ) -> dict[str, Any]:
        """Olay isleyici kaydeder.

        Args:
            event_type: Olay tipi.
            handler: Isleyici.

        Returns:
            Kayit bilgisi.
        """
        try:
            self._handlers.setdefault(
                event_type, []
            )
            if handler:
                self._handlers[
                    event_type
                ].append(handler)
            return {
                "event_type": event_type,
                "registered": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def off(
        self,
        event_type: str = "",
        handler: Callable | None = None,
    ) -> dict[str, Any]:
        """Olay isleyiciyi kaldirir.

        Args:
            event_type: Olay tipi.
            handler: Isleyici.

        Returns:
            Kaldirma bilgisi.
        """
        try:
            handlers = (
                self._handlers.get(
                    event_type, []
                )
            )
            if handler in handlers:
                handlers.remove(handler)
                return {
                    "removed": True,
                }
            return {
                "removed": False,
                "error": (
                    "Isleyici bulunamadi"
                ),
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "removed": False,
                "error": str(e),
            }

    def dispatch(
        self,
        event_type: str = "",
        data: Any = None,
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Olay dagitir.

        Args:
            event_type: Olay tipi.
            data: Olay verisi.
            priority: Oncelik.

        Returns:
            Dagitim bilgisi.
        """
        try:
            # Geri basinc kontrolu
            fill_ratio = (
                len(self._queue)
                / max(
                    1, self._max_queue_size
                )
            )
            if fill_ratio >= 1.0:
                self._stats[
                    "events_dropped"
                ] += 1
                return {
                    "dispatched": False,
                    "error": (
                        "Kuyruk dolu"
                    ),
                    "backpressure": True,
                }

            if (
                fill_ratio
                >= self._backpressure_threshold
            ):
                self._stats[
                    "backpressure_events"
                ] += 1

            eid = f"evt_{uuid4()!s:.8}"
            pri = self.PRIORITY_LEVELS.get(
                priority, 2
            )

            event = {
                "event_id": eid,
                "event_type": event_type,
                "data": data,
                "priority": priority,
                "priority_val": pri,
                "dispatched_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._queue.append(event)
            # Oncelik sirala
            self._queue.sort(
                key=lambda x: x.get(
                    "priority_val", 2
                )
            )

            self._stats[
                "events_dispatched"
            ] += 1

            return {
                "event_id": eid,
                "queue_size": len(
                    self._queue
                ),
                "backpressure": (
                    fill_ratio
                    >= self._backpressure_threshold
                ),
                "dispatched": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "dispatched": False,
                "error": str(e),
            }

    def process_next(
        self,
    ) -> dict[str, Any]:
        """Siradaki olayi isler.

        Returns:
            Isleme bilgisi.
        """
        try:
            if not self._queue:
                return {
                    "processed": False,
                    "error": (
                        "Kuyruk bos"
                    ),
                }

            event = self._queue.pop(0)
            etype = event["event_type"]
            handlers = (
                self._handlers.get(
                    etype, []
                )
            )

            results: list[Any] = []
            errors: list[str] = []

            for h in handlers:
                try:
                    r = h(event["data"])
                    results.append(r)
                except Exception as he:
                    errors.append(str(he))
                    self._errors.append({
                        "event_id": event[
                            "event_id"
                        ],
                        "error": str(he),
                        "recovered": True,
                    })
                    self._stats[
                        "errors_recovered"
                    ] += 1

            event["results"] = results
            event["errors"] = errors
            event["processed_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            self._processed.append(event)
            self._stats[
                "events_processed"
            ] += 1

            return {
                "event_id": event[
                    "event_id"
                ],
                "event_type": etype,
                "handlers_called": len(
                    handlers
                ),
                "error_count": len(
                    errors
                ),
                "processed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "processed": False,
                "error": str(e),
            }

    def process_all(
        self,
    ) -> dict[str, Any]:
        """Tum olaylari isler.

        Returns:
            Isleme bilgisi.
        """
        try:
            processed = 0
            errors = 0
            while self._queue:
                r = self.process_next()
                if r.get("processed"):
                    processed += 1
                    errors += r.get(
                        "error_count", 0
                    )

            return {
                "processed_count": (
                    processed
                ),
                "error_count": errors,
                "processed": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "processed": False,
                "error": str(e),
            }

    def drain(
        self,
    ) -> dict[str, Any]:
        """Kuyruktaki olaylari bosaltir.

        Returns:
            Bosaltma bilgisi.
        """
        try:
            count = len(self._queue)
            self._queue.clear()
            return {
                "drained": count,
                "success": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "running": self._running,
                "queue_size": len(
                    self._queue
                ),
                "handlers": {
                    k: len(v)
                    for k, v in
                    self._handlers.items()
                },
                "total_processed": len(
                    self._processed
                ),
                "total_errors": len(
                    self._errors
                ),
                "stats": dict(
                    self._stats
                ),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
