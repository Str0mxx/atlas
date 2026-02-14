"""ATLAS Dagitik Kuyruk modulu.

Mesaj kuyrugu, oncelik kuyruklari,
dead letter isleme, en az bir kez
teslim ve tam bir kez semantigi.
"""

import logging
import time
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DistributedQueue:
    """Dagitik mesaj kuyrugu.

    Dagitik mesaj kuyrugu yonetimi.

    Attributes:
        _queues: Kuyruk tanimlari.
        _dead_letter: Dead letter kuyrugu.
    """

    def __init__(
        self,
        max_retries: int = 3,
    ) -> None:
        """Dagitik kuyrugu baslatir.

        Args:
            max_retries: Maks yeniden deneme.
        """
        self._queues: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._dead_letter: list[
            dict[str, Any]
        ] = []
        self._processed_ids: set[str] = set()
        self._in_flight: dict[
            str, dict[str, Any]
        ] = {}
        self._stats: dict[str, int] = {
            "enqueued": 0,
            "dequeued": 0,
            "acked": 0,
            "nacked": 0,
        }
        self._max_retries = max_retries

        logger.info(
            "DistributedQueue baslatildi",
        )

    def create_queue(
        self,
        queue_name: str,
    ) -> dict[str, Any]:
        """Kuyruk olusturur.

        Args:
            queue_name: Kuyruk adi.

        Returns:
            Kuyruk bilgisi.
        """
        if queue_name not in self._queues:
            self._queues[queue_name] = []
        return {
            "queue_name": queue_name,
            "status": "created",
        }

    def enqueue(
        self,
        queue_name: str,
        data: dict[str, Any] | None = None,
        priority: int = 5,
        dedup_id: str = "",
    ) -> dict[str, Any]:
        """Kuyruga ekler.

        Args:
            queue_name: Kuyruk adi.
            data: Mesaj verisi.
            priority: Oncelik (1=en yuksek).
            dedup_id: Tekillestime ID.

        Returns:
            Ekleme sonucu.
        """
        if queue_name not in self._queues:
            self._queues[queue_name] = []

        # Exactly-once: tekillestime
        if dedup_id and dedup_id in self._processed_ids:
            return {
                "status": "duplicate",
                "dedup_id": dedup_id,
            }

        msg_id = str(uuid4())[:8]
        message = {
            "message_id": msg_id,
            "queue_name": queue_name,
            "data": data or {},
            "priority": priority,
            "dedup_id": dedup_id,
            "retry_count": 0,
            "enqueued_at": time.time(),
        }

        # Oncelik sirasi: kucuk = yuksek oncelik
        queue = self._queues[queue_name]
        inserted = False
        for i, existing in enumerate(queue):
            if priority < existing["priority"]:
                queue.insert(i, message)
                inserted = True
                break
        if not inserted:
            queue.append(message)

        self._stats["enqueued"] += 1
        return {
            "message_id": msg_id,
            "queue_name": queue_name,
            "status": "enqueued",
            "priority": priority,
        }

    def dequeue(
        self,
        queue_name: str,
    ) -> dict[str, Any] | None:
        """Kuyruktan alir.

        Args:
            queue_name: Kuyruk adi.

        Returns:
            Mesaj veya None.
        """
        queue = self._queues.get(
            queue_name, [],
        )
        if not queue:
            return None

        message = queue.pop(0)
        self._in_flight[
            message["message_id"]
        ] = message
        self._stats["dequeued"] += 1
        return message

    def ack(
        self,
        message_id: str,
    ) -> bool:
        """Mesaji onaylar.

        Args:
            message_id: Mesaj ID.

        Returns:
            Basarili mi.
        """
        message = self._in_flight.pop(
            message_id, None,
        )
        if not message:
            return False

        if message.get("dedup_id"):
            self._processed_ids.add(
                message["dedup_id"],
            )

        self._stats["acked"] += 1
        return True

    def nack(
        self,
        message_id: str,
    ) -> dict[str, Any]:
        """Mesaji reddeder.

        Args:
            message_id: Mesaj ID.

        Returns:
            Red sonucu.
        """
        message = self._in_flight.pop(
            message_id, None,
        )
        if not message:
            return {
                "status": "error",
                "reason": "not_in_flight",
            }

        message["retry_count"] += 1
        self._stats["nacked"] += 1

        if message["retry_count"] >= self._max_retries:
            self._dead_letter.append(message)
            return {
                "message_id": message_id,
                "status": "dead_lettered",
                "retries": message["retry_count"],
            }

        # Kuyruga geri ekle
        queue_name = message["queue_name"]
        if queue_name not in self._queues:
            self._queues[queue_name] = []
        self._queues[queue_name].append(message)

        return {
            "message_id": message_id,
            "status": "requeued",
            "retry_count": message["retry_count"],
        }

    def peek(
        self,
        queue_name: str,
    ) -> dict[str, Any] | None:
        """Kuyruk basini gosterir.

        Args:
            queue_name: Kuyruk adi.

        Returns:
            Mesaj veya None.
        """
        queue = self._queues.get(
            queue_name, [],
        )
        if not queue:
            return None
        return dict(queue[0])

    def get_queue_depth(
        self,
        queue_name: str,
    ) -> int:
        """Kuyruk derinligini getirir.

        Args:
            queue_name: Kuyruk adi.

        Returns:
            Derinlik.
        """
        return len(
            self._queues.get(queue_name, []),
        )

    def purge_queue(
        self,
        queue_name: str,
    ) -> int:
        """Kuyrugu temizler.

        Args:
            queue_name: Kuyruk adi.

        Returns:
            Temizlenen mesaj sayisi.
        """
        queue = self._queues.get(queue_name)
        if not queue:
            return 0
        count = len(queue)
        queue.clear()
        return count

    def retry_dead_letters(
        self,
        queue_name: str | None = None,
    ) -> dict[str, Any]:
        """Dead letter'lari yeniden dener.

        Args:
            queue_name: Kuyruk filtresi.

        Returns:
            Sonuc bilgisi.
        """
        retried = 0
        remaining = []

        for msg in self._dead_letter:
            if (
                queue_name
                and msg["queue_name"] != queue_name
            ):
                remaining.append(msg)
                continue

            msg["retry_count"] = 0
            qn = msg["queue_name"]
            if qn not in self._queues:
                self._queues[qn] = []
            self._queues[qn].append(msg)
            retried += 1

        self._dead_letter = remaining
        return {
            "retried": retried,
            "remaining": len(remaining),
        }

    def get_stats(self) -> dict[str, Any]:
        """Istatistik getirir.

        Returns:
            Istatistik bilgisi.
        """
        total_depth = sum(
            len(q) for q in self._queues.values()
        )
        return {
            **self._stats,
            "queues": len(self._queues),
            "total_depth": total_depth,
            "in_flight": len(self._in_flight),
            "dead_letters": len(
                self._dead_letter,
            ),
        }

    @property
    def queue_count(self) -> int:
        """Kuyruk sayisi."""
        return len(self._queues)

    @property
    def total_depth(self) -> int:
        """Toplam derinlik."""
        return sum(
            len(q) for q in self._queues.values()
        )

    @property
    def dead_letter_count(self) -> int:
        """Dead letter sayisi."""
        return len(self._dead_letter)

    @property
    def in_flight_count(self) -> int:
        """Havadaki mesaj sayisi."""
        return len(self._in_flight)
