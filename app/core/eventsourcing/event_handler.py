"""ATLAS Olay Isleyici modulu.

Isleyici kaydi, olay yonlendirme,
isleyici yurutme, hata isleme
ve idempotency.
"""

import hashlib
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventHandler:
    """Olay isleyici.

    Olaylari isleyicilere yonlendirir.

    Attributes:
        _handlers: Isleyici haritasi.
        _processed: Islenmis olay ID'leri.
    """

    def __init__(self) -> None:
        """Olay isleyiciyi baslatir."""
        self._handlers: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._processed: set[str] = set()
        self._results: list[
            dict[str, Any]
        ] = []
        self._errors: list[
            dict[str, Any]
        ] = []

        logger.info("EventHandler baslatildi")

    def register(
        self,
        event_type: str,
        handler: Callable[..., Any],
        handler_id: str = "",
        idempotent: bool = True,
    ) -> dict[str, Any]:
        """Isleyici kaydeder.

        Args:
            event_type: Olay tipi.
            handler: Isleyici fonksiyon.
            handler_id: Isleyici ID.
            idempotent: Idempotent mi.

        Returns:
            Kayit bilgisi.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        h_id = handler_id or (
            f"h_{len(self._handlers[event_type])}"
        )

        entry = {
            "handler_id": h_id,
            "event_type": event_type,
            "handler": handler,
            "idempotent": idempotent,
            "call_count": 0,
        }
        self._handlers[event_type].append(entry)
        return {
            "handler_id": h_id,
            "event_type": event_type,
        }

    def unregister(
        self,
        event_type: str,
        handler_id: str,
    ) -> bool:
        """Isleyiciyi kaldirir.

        Args:
            event_type: Olay tipi.
            handler_id: Isleyici ID.

        Returns:
            Basarili mi.
        """
        handlers = self._handlers.get(
            event_type, [],
        )
        for i, h in enumerate(handlers):
            if h["handler_id"] == handler_id:
                handlers.pop(i)
                return True
        return False

    def handle(
        self,
        event_type: str,
        event_id: str = "",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Olagi isler.

        Args:
            event_type: Olay tipi.
            event_id: Olay ID.
            data: Olay verisi.

        Returns:
            Isleme sonucu.
        """
        # Idempotency kontrolu
        dedup_key = self._make_dedup_key(
            event_type, event_id, data,
        )
        if dedup_key in self._processed:
            return {
                "event_type": event_type,
                "status": "duplicate",
                "handlers_called": 0,
            }

        handlers = self._handlers.get(
            event_type, [],
        )

        called = 0
        errors = 0
        results = []

        for entry in handlers:
            try:
                result = entry["handler"](
                    data or {},
                )
                entry["call_count"] += 1
                called += 1
                results.append({
                    "handler_id": entry[
                        "handler_id"
                    ],
                    "result": result,
                })
            except Exception as e:
                errors += 1
                self._errors.append({
                    "event_type": event_type,
                    "handler_id": entry[
                        "handler_id"
                    ],
                    "error": str(e),
                    "timestamp": time.time(),
                })

        # Idempotent isleyiciler icin islendi isaretle
        if any(
            h["idempotent"] for h in handlers
        ):
            self._processed.add(dedup_key)

        record = {
            "event_type": event_type,
            "event_id": event_id,
            "status": (
                "success" if errors == 0
                else "partial"
            ),
            "handlers_called": called,
            "errors": errors,
            "results": results,
            "timestamp": time.time(),
        }
        self._results.append(record)
        return record

    def handle_batch(
        self,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Toplu olay isler.

        Args:
            events: Olay listesi.

        Returns:
            Toplam sonuc.
        """
        processed = 0
        duplicates = 0
        errors = 0

        for event in events:
            result = self.handle(
                event_type=event.get(
                    "event_type", "",
                ),
                event_id=event.get(
                    "event_id", "",
                ),
                data=event.get("data"),
            )
            if result["status"] == "duplicate":
                duplicates += 1
            elif result["errors"] > 0:
                errors += 1
            else:
                processed += 1

        return {
            "total": len(events),
            "processed": processed,
            "duplicates": duplicates,
            "errors": errors,
        }

    def _make_dedup_key(
        self,
        event_type: str,
        event_id: str,
        data: dict[str, Any] | None,
    ) -> str:
        """Tekillestime anahtari uretir.

        Args:
            event_type: Olay tipi.
            event_id: Olay ID.
            data: Olay verisi.

        Returns:
            Anahtar.
        """
        if event_id:
            return f"{event_type}:{event_id}"
        raw = f"{event_type}:{data}"
        return hashlib.md5(
            raw.encode(),
        ).hexdigest()

    def get_handlers(
        self,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Isleyicileri getirir.

        Args:
            event_type: Olay tipi filtresi.

        Returns:
            Isleyici listesi.
        """
        if event_type:
            return [
                {
                    "handler_id": h["handler_id"],
                    "event_type": h["event_type"],
                    "call_count": h["call_count"],
                }
                for h in self._handlers.get(
                    event_type, [],
                )
            ]

        result = []
        for handlers in self._handlers.values():
            for h in handlers:
                result.append({
                    "handler_id": h["handler_id"],
                    "event_type": h["event_type"],
                    "call_count": h["call_count"],
                })
        return result

    def clear_processed(self) -> int:
        """Islenmis kayitlari temizler.

        Returns:
            Temizlenen sayi.
        """
        count = len(self._processed)
        self._processed.clear()
        return count

    @property
    def handler_count(self) -> int:
        """Isleyici sayisi."""
        return sum(
            len(h) for h in
            self._handlers.values()
        )

    @property
    def processed_count(self) -> int:
        """Islenmis olay sayisi."""
        return len(self._results)

    @property
    def error_count(self) -> int:
        """Hata sayisi."""
        return len(self._errors)
