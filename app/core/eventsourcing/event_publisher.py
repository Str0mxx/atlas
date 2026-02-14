"""ATLAS Olay Yayincisi modulu.

Olay yayinlama, abone yonetimi,
asenkron yayinlama, yeniden deneme
ve dead letter kuyrugu.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventPublisher:
    """Olay yayincisi.

    Olaylari abonelere yayinlar.

    Attributes:
        _subscribers: Abone listesi.
        _dead_letter: Basarisiz olaylar.
    """

    def __init__(
        self,
        max_retries: int = 3,
    ) -> None:
        """Olay yayincisini baslatir.

        Args:
            max_retries: Maks yeniden deneme.
        """
        self._subscribers: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._dead_letter: list[
            dict[str, Any]
        ] = []
        self._published: list[
            dict[str, Any]
        ] = []
        self._max_retries = max_retries

        logger.info("EventPublisher baslatildi")

    def subscribe(
        self,
        event_type: str,
        handler: Callable[..., Any],
        subscriber_id: str = "",
    ) -> dict[str, Any]:
        """Abone olur.

        Args:
            event_type: Olay tipi.
            handler: Isleyici fonksiyon.
            subscriber_id: Abone ID.

        Returns:
            Abonelik bilgisi.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        sub_id = subscriber_id or (
            f"sub_{len(self._subscribers[event_type])}"
        )

        sub = {
            "subscriber_id": sub_id,
            "event_type": event_type,
            "handler": handler,
            "active": True,
        }
        self._subscribers[event_type].append(sub)
        return {
            "subscriber_id": sub_id,
            "event_type": event_type,
        }

    def unsubscribe(
        self,
        event_type: str,
        subscriber_id: str,
    ) -> bool:
        """Aboneligi iptal eder.

        Args:
            event_type: Olay tipi.
            subscriber_id: Abone ID.

        Returns:
            Basarili mi.
        """
        subs = self._subscribers.get(
            event_type, [],
        )
        for sub in subs:
            if sub["subscriber_id"] == subscriber_id:
                sub["active"] = False
                return True
        return False

    def publish(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Olay yayinlar.

        Args:
            event_type: Olay tipi.
            data: Olay verisi.

        Returns:
            Yayinlama sonucu.
        """
        subs = self._subscribers.get(
            event_type, [],
        )
        active_subs = [
            s for s in subs if s["active"]
        ]

        delivered = 0
        failed = 0

        for sub in active_subs:
            success = self._deliver(
                sub, event_type, data or {},
            )
            if success:
                delivered += 1
            else:
                failed += 1

        result = {
            "event_type": event_type,
            "subscribers": len(active_subs),
            "delivered": delivered,
            "failed": failed,
            "timestamp": time.time(),
        }
        self._published.append(result)
        return result

    def _deliver(
        self,
        subscriber: dict[str, Any],
        event_type: str,
        data: dict[str, Any],
    ) -> bool:
        """Olagi aboneye iletir.

        Args:
            subscriber: Abone.
            event_type: Olay tipi.
            data: Olay verisi.

        Returns:
            Basarili mi.
        """
        handler = subscriber["handler"]
        for attempt in range(self._max_retries):
            try:
                handler(event_type, data)
                return True
            except Exception as e:
                logger.warning(
                    "Olay iletim hatasi "
                    "(deneme %d/%d): %s",
                    attempt + 1,
                    self._max_retries,
                    e,
                )

        # Dead letter'a ekle
        self._dead_letter.append({
            "event_type": event_type,
            "data": data,
            "subscriber_id": subscriber[
                "subscriber_id"
            ],
            "reason": "max_retries_exceeded",
            "timestamp": time.time(),
        })
        return False

    def broadcast(
        self,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Tum abonelere yayinlar.

        Args:
            data: Olay verisi.

        Returns:
            Yayinlama sonucu.
        """
        total_delivered = 0
        total_failed = 0
        types_published = 0

        for event_type in self._subscribers:
            result = self.publish(
                event_type, data,
            )
            total_delivered += result["delivered"]
            total_failed += result["failed"]
            types_published += 1

        return {
            "types_published": types_published,
            "total_delivered": total_delivered,
            "total_failed": total_failed,
        }

    def retry_dead_letters(
        self,
    ) -> dict[str, Any]:
        """Dead letter'lari yeniden dener.

        Returns:
            Sonuc bilgisi.
        """
        recovered = 0
        still_dead = []

        for item in self._dead_letter:
            event_type = item["event_type"]
            subs = self._subscribers.get(
                event_type, [],
            )
            target = None
            for s in subs:
                if (
                    s["subscriber_id"]
                    == item["subscriber_id"]
                    and s["active"]
                ):
                    target = s
                    break

            if target:
                try:
                    target["handler"](
                        event_type, item["data"],
                    )
                    recovered += 1
                except Exception:
                    still_dead.append(item)
            else:
                still_dead.append(item)

        self._dead_letter = still_dead
        return {
            "recovered": recovered,
            "remaining": len(still_dead),
        }

    def get_subscribers(
        self,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aboneleri getirir.

        Args:
            event_type: Olay tipi filtresi.

        Returns:
            Abone listesi.
        """
        if event_type:
            subs = self._subscribers.get(
                event_type, [],
            )
            return [
                {
                    "subscriber_id": s[
                        "subscriber_id"
                    ],
                    "event_type": s["event_type"],
                    "active": s["active"],
                }
                for s in subs
            ]

        result = []
        for subs in self._subscribers.values():
            for s in subs:
                result.append({
                    "subscriber_id": s[
                        "subscriber_id"
                    ],
                    "event_type": s["event_type"],
                    "active": s["active"],
                })
        return result

    @property
    def subscriber_count(self) -> int:
        """Aktif abone sayisi."""
        count = 0
        for subs in self._subscribers.values():
            count += sum(
                1 for s in subs if s["active"]
            )
        return count

    @property
    def published_count(self) -> int:
        """Yayinlanan olay sayisi."""
        return len(self._published)

    @property
    def dead_letter_count(self) -> int:
        """Dead letter sayisi."""
        return len(self._dead_letter)
