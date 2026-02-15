"""ATLAS Proaktif Öncelik Kuyruğu modülü.

Öncelik yönetimi, kuyruk işleme,
son tarih yönetimi, yeniden sıralama,
taşma yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProactivePriorityQueue:
    """Proaktif öncelik kuyruğu.

    Görevleri önceliğe göre yönetir.

    Attributes:
        _queue: Kuyruk öğeleri.
        _processed: İşlenmiş öğeler.
    """

    def __init__(
        self,
        max_size: int = 1000,
    ) -> None:
        """Kuyruğu başlatır.

        Args:
            max_size: Maks boyut.
        """
        self._queue: list[
            dict[str, Any]
        ] = []
        self._processed: list[
            dict[str, Any]
        ] = []
        self._max_size = max_size
        self._counter = 0
        self._stats = {
            "items_added": 0,
            "items_processed": 0,
            "overflows": 0,
            "reorders": 0,
        }

        logger.info(
            "ProactivePriorityQueue "
            "baslatildi",
        )

    def enqueue(
        self,
        title: str,
        priority: int = 5,
        deadline: float | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Kuyruğa ekler.

        Args:
            title: Öğe başlığı.
            priority: Öncelik (1-10).
            deadline: Son tarih (timestamp).
            context: Bağlam.

        Returns:
            Ekleme bilgisi.
        """
        # Taşma kontrolü
        if len(self._queue) >= self._max_size:
            overflow = self._handle_overflow()
            if not overflow["space_made"]:
                return {
                    "error": "queue_full",
                    "size": len(self._queue),
                }

        self._counter += 1
        iid = f"qi_{self._counter}"
        priority = max(1, min(10, priority))

        item = {
            "item_id": iid,
            "title": title,
            "priority": priority,
            "deadline": deadline,
            "context": context or {},
            "status": "pending",
            "added_at": time.time(),
        }
        self._queue.append(item)
        self._sort_queue()
        self._stats["items_added"] += 1

        return {
            "item_id": iid,
            "position": self._get_position(iid),
            "queue_size": len(self._queue),
        }

    def dequeue(self) -> dict[str, Any]:
        """En yüksek öncelikli öğeyi alır.

        Returns:
            Öğe bilgisi.
        """
        if not self._queue:
            return {"error": "queue_empty"}

        item = self._queue.pop(0)
        item["status"] = "processing"
        item["dequeued_at"] = time.time()
        self._processed.append(item)
        self._stats["items_processed"] += 1

        return item

    def peek(self) -> dict[str, Any]:
        """Sıradaki öğeyi gösterir (çıkarmaz).

        Returns:
            Öğe bilgisi.
        """
        if not self._queue:
            return {"error": "queue_empty"}
        return dict(self._queue[0])

    def _sort_queue(self) -> None:
        """Kuyruğu sıralar."""
        now = time.time()

        def sort_key(
            item: dict[str, Any],
        ) -> tuple[float, float]:
            priority = item.get("priority", 5)
            deadline = item.get("deadline")

            # Son tarih yakınlığına göre bonus
            urgency_bonus = 0.0
            if deadline:
                remaining = deadline - now
                if remaining < 3600:
                    urgency_bonus = 5.0
                elif remaining < 86400:
                    urgency_bonus = 2.0

            return (
                -(priority + urgency_bonus),
                item.get("added_at", now),
            )

        self._queue.sort(key=sort_key)

    def _get_position(
        self,
        item_id: str,
    ) -> int:
        """Öğenin kuyruk pozisyonunu döner.

        Args:
            item_id: Öğe ID.

        Returns:
            Pozisyon (0-based).
        """
        for i, item in enumerate(self._queue):
            if item["item_id"] == item_id:
                return i
        return -1

    def _handle_overflow(self) -> dict[str, Any]:
        """Taşma yönetir.

        Returns:
            Taşma bilgisi.
        """
        # En düşük öncelikli öğeyi çıkar
        if not self._queue:
            return {"space_made": False}

        lowest = min(
            self._queue,
            key=lambda x: x.get("priority", 5),
        )
        self._queue.remove(lowest)
        lowest["status"] = "dropped"
        self._processed.append(lowest)
        self._stats["overflows"] += 1

        return {
            "space_made": True,
            "dropped_item": lowest["item_id"],
        }

    def update_priority(
        self,
        item_id: str,
        new_priority: int,
    ) -> dict[str, Any]:
        """Öncelik günceller.

        Args:
            item_id: Öğe ID.
            new_priority: Yeni öncelik.

        Returns:
            Güncelleme bilgisi.
        """
        for item in self._queue:
            if item["item_id"] == item_id:
                old_priority = item["priority"]
                item["priority"] = max(
                    1, min(10, new_priority),
                )
                self._sort_queue()
                self._stats["reorders"] += 1

                return {
                    "item_id": item_id,
                    "old_priority": old_priority,
                    "new_priority": item[
                        "priority"
                    ],
                    "new_position": (
                        self._get_position(
                            item_id,
                        )
                    ),
                }

        return {"error": "item_not_found"}

    def update_deadline(
        self,
        item_id: str,
        deadline: float,
    ) -> dict[str, Any]:
        """Son tarih günceller.

        Args:
            item_id: Öğe ID.
            deadline: Yeni son tarih.

        Returns:
            Güncelleme bilgisi.
        """
        for item in self._queue:
            if item["item_id"] == item_id:
                item["deadline"] = deadline
                self._sort_queue()

                return {
                    "item_id": item_id,
                    "deadline": deadline,
                    "new_position": (
                        self._get_position(
                            item_id,
                        )
                    ),
                }

        return {"error": "item_not_found"}

    def remove_item(
        self,
        item_id: str,
    ) -> dict[str, Any]:
        """Öğe çıkarır.

        Args:
            item_id: Öğe ID.

        Returns:
            Çıkarma bilgisi.
        """
        for item in self._queue:
            if item["item_id"] == item_id:
                self._queue.remove(item)
                item["status"] = "removed"
                self._processed.append(item)
                return {
                    "item_id": item_id,
                    "removed": True,
                }

        return {"error": "item_not_found"}

    def get_queue(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Kuyruğu getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Öğe listesi.
        """
        return list(self._queue[:limit])

    def get_overdue(self) -> list[dict[str, Any]]:
        """Gecikmiş öğeleri getirir.

        Returns:
            Gecikmiş öğeler.
        """
        now = time.time()
        return [
            item for item in self._queue
            if item.get("deadline")
            and item["deadline"] < now
        ]

    @property
    def size(self) -> int:
        """Kuyruk boyutu."""
        return len(self._queue)

    @property
    def processed_count(self) -> int:
        """İşlenmiş sayısı."""
        return self._stats["items_processed"]

    @property
    def is_empty(self) -> bool:
        """Kuyruk boş mu."""
        return len(self._queue) == 0
