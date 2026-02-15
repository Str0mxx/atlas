"""ATLAS Mesaj Tamponu modülü.

Mesaj kuyruklama, toplu koleksiyon,
öncelik sıralama, tekilleştirme,
süre dolumu yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MessageBuffer:
    """Mesaj tamponu.

    Mesajları tamponlar ve önceliğe göre sıralar.

    Attributes:
        _buffer: Tamponlanmış mesajlar.
        _expired: Süresi dolmuş mesajlar.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,
    ) -> None:
        """Tamponu başlatır.

        Args:
            max_size: Maksimum tampon boyutu.
            default_ttl: Varsayılan yaşam süresi (sn).
        """
        self._buffer: list[
            dict[str, Any]
        ] = []
        self._expired: list[
            dict[str, Any]
        ] = []
        self._delivered: list[
            dict[str, Any]
        ] = []
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._counter = 0
        self._stats = {
            "queued": 0,
            "delivered": 0,
            "expired": 0,
            "deduplicated": 0,
        }

        logger.info(
            "MessageBuffer baslatildi",
        )

    def enqueue(
        self,
        content: str,
        priority: str = "medium",
        source: str = "",
        ttl: int | None = None,
        dedup_key: str | None = None,
    ) -> dict[str, Any]:
        """Mesaj kuyruğa ekler.

        Args:
            content: Mesaj içeriği.
            priority: Öncelik.
            source: Kaynak.
            ttl: Yaşam süresi (sn).
            dedup_key: Tekilleştirme anahtarı.

        Returns:
            Kuyruk bilgisi.
        """
        # Tekilleştirme kontrolü
        if dedup_key:
            for msg in self._buffer:
                if msg.get("dedup_key") == dedup_key:
                    self._stats[
                        "deduplicated"
                    ] += 1
                    return {
                        "queued": False,
                        "reason": "duplicate",
                        "existing_id": msg[
                            "message_id"
                        ],
                    }

        # Boyut kontrolü
        if len(self._buffer) >= self._max_size:
            self._evict_lowest()

        self._counter += 1
        mid = f"msg_{self._counter}"
        message_ttl = (
            ttl if ttl is not None
            else self._default_ttl
        )
        now = time.time()

        message = {
            "message_id": mid,
            "content": content,
            "priority": priority,
            "source": source,
            "dedup_key": dedup_key,
            "queued_at": now,
            "expires_at": now + message_ttl,
        }
        self._buffer.append(message)
        self._stats["queued"] += 1

        return {
            "message_id": mid,
            "queued": True,
            "priority": priority,
            "expires_in": message_ttl,
        }

    def _evict_lowest(self) -> None:
        """En düşük öncelikli mesajı çıkarır."""
        priority_order = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "informational": 1,
        }
        if self._buffer:
            self._buffer.sort(
                key=lambda m: priority_order.get(
                    m["priority"], 0,
                ),
            )
            evicted = self._buffer.pop(0)
            self._expired.append(evicted)

    def dequeue(
        self,
        count: int = 1,
    ) -> list[dict[str, Any]]:
        """Mesajları kuyruktan alır.

        Args:
            count: Alınacak sayı.

        Returns:
            Mesaj listesi.
        """
        self._cleanup_expired()
        self._sort_by_priority()

        results = []
        for _ in range(
            min(count, len(self._buffer)),
        ):
            msg = self._buffer.pop(0)
            msg["delivered_at"] = time.time()
            self._delivered.append(msg)
            self._stats["delivered"] += 1
            results.append(msg)

        return results

    def batch_collect(
        self,
        min_priority: str = "low",
    ) -> list[dict[str, Any]]:
        """Toplu mesaj toplar.

        Args:
            min_priority: Minimum öncelik.

        Returns:
            Mesaj listesi.
        """
        self._cleanup_expired()
        priority_order = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "informational": 1,
        }
        min_val = priority_order.get(
            min_priority, 0,
        )

        collected = []
        remaining = []

        for msg in self._buffer:
            msg_val = priority_order.get(
                msg["priority"], 0,
            )
            if msg_val >= min_val:
                msg["delivered_at"] = time.time()
                self._delivered.append(msg)
                self._stats["delivered"] += 1
                collected.append(msg)
            else:
                remaining.append(msg)

        self._buffer = remaining
        return collected

    def _sort_by_priority(self) -> None:
        """Önceliğe göre sıralar."""
        priority_order = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "informational": 1,
        }
        self._buffer.sort(
            key=lambda m: priority_order.get(
                m["priority"], 0,
            ),
            reverse=True,
        )

    def _cleanup_expired(self) -> None:
        """Süresi dolmuş mesajları temizler."""
        now = time.time()
        active = []
        for msg in self._buffer:
            if msg["expires_at"] > now:
                active.append(msg)
            else:
                self._expired.append(msg)
                self._stats["expired"] += 1
        self._buffer = active

    def peek(
        self,
        count: int = 5,
    ) -> list[dict[str, Any]]:
        """Tampondaki mesajlara bakar.

        Args:
            count: Görüntülenecek sayı.

        Returns:
            Mesaj listesi.
        """
        self._sort_by_priority()
        return list(self._buffer[:count])

    def get_stats(self) -> dict[str, Any]:
        """Tampon istatistikleri.

        Returns:
            İstatistik bilgisi.
        """
        return {
            "buffer_size": len(self._buffer),
            "total_queued": self._stats[
                "queued"
            ],
            "total_delivered": self._stats[
                "delivered"
            ],
            "total_expired": self._stats[
                "expired"
            ],
            "total_deduplicated": self._stats[
                "deduplicated"
            ],
            "max_size": self._max_size,
        }

    def clear(self) -> dict[str, Any]:
        """Tamponu temizler.

        Returns:
            Temizlik bilgisi.
        """
        count = len(self._buffer)
        self._buffer.clear()
        return {
            "cleared": True,
            "messages_removed": count,
        }

    @property
    def size(self) -> int:
        """Tampon boyutu."""
        return len(self._buffer)

    @property
    def queued_count(self) -> int:
        """Toplam kuyruklanan sayı."""
        return self._stats["queued"]

    @property
    def delivered_count(self) -> int:
        """Toplam teslim edilen sayı."""
        return self._stats["delivered"]
