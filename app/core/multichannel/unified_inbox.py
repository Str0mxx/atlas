"""ATLAS Birleşik Gelen Kutusu modülü.

Tüm kanallar tek yerde, öncelik sıralaması,
konuşma dizisi, kanallar arası arama,
arşiv yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class UnifiedInbox:
    """Birleşik gelen kutusu.

    Tüm kanal mesajlarını birleştirir.

    Attributes:
        _messages: Mesaj kayıtları.
        _threads: Konuşma dizileri.
        _archive: Arşiv.
    """

    def __init__(self) -> None:
        """Gelen kutusunu başlatır."""
        self._messages: list[
            dict[str, Any]
        ] = []
        self._threads: dict[
            str, list[str]
        ] = {}
        self._archive: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "messages_received": 0,
            "messages_archived": 0,
            "threads_created": 0,
        }

        logger.info("UnifiedInbox baslatildi")

    def receive_message(
        self,
        content: str,
        channel: str,
        sender: str = "",
        priority: int = 5,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Mesaj alır.

        Args:
            content: İçerik.
            channel: Kanal.
            sender: Gönderici.
            priority: Öncelik.
            thread_id: Konuşma dizisi ID.

        Returns:
            Mesaj bilgisi.
        """
        self._counter += 1
        mid = f"msg_{self._counter}"

        message = {
            "message_id": mid,
            "content": content,
            "channel": channel,
            "sender": sender,
            "priority": max(1, min(10, priority)),
            "thread_id": thread_id,
            "read": False,
            "archived": False,
            "received_at": time.time(),
        }
        self._messages.append(message)
        self._stats["messages_received"] += 1

        # Konuşma dizisine ekle
        if thread_id:
            if thread_id not in self._threads:
                self._threads[thread_id] = []
                self._stats[
                    "threads_created"
                ] += 1
            self._threads[thread_id].append(mid)

        return message

    def get_inbox(
        self,
        channel: str | None = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Gelen kutusunu getirir.

        Args:
            channel: Kanal filtresi.
            unread_only: Sadece okunmamışlar.
            limit: Maks kayıt.

        Returns:
            Mesaj listesi.
        """
        results = [
            m for m in self._messages
            if not m["archived"]
        ]
        if channel:
            results = [
                m for m in results
                if m["channel"] == channel
            ]
        if unread_only:
            results = [
                m for m in results
                if not m["read"]
            ]

        # Önceliğe göre sırala
        results.sort(
            key=lambda x: (
                -x["priority"],
                -x["received_at"],
            ),
        )

        return results[:limit]

    def mark_read(
        self,
        message_id: str,
    ) -> dict[str, Any]:
        """Okundu olarak işaretler.

        Args:
            message_id: Mesaj ID.

        Returns:
            İşaretleme bilgisi.
        """
        msg = self._find_message(message_id)
        if not msg:
            return {"error": "message_not_found"}

        msg["read"] = True
        return {
            "message_id": message_id,
            "read": True,
        }

    def get_thread(
        self,
        thread_id: str,
    ) -> dict[str, Any]:
        """Konuşma dizisini getirir.

        Args:
            thread_id: Dizi ID.

        Returns:
            Dizi bilgisi.
        """
        msg_ids = self._threads.get(
            thread_id, [],
        )
        messages = [
            m for m in self._messages
            if m["message_id"] in msg_ids
        ]
        messages.sort(
            key=lambda x: x["received_at"],
        )

        return {
            "thread_id": thread_id,
            "messages": messages,
            "message_count": len(messages),
        }

    def search(
        self,
        query: str,
        channel: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Kanallar arası arama yapar.

        Args:
            query: Arama sorgusu.
            channel: Kanal filtresi.
            limit: Maks sonuç.

        Returns:
            Arama sonucu.
        """
        query_lower = query.lower()
        all_msgs = (
            self._messages + self._archive
        )
        results = []

        for msg in all_msgs:
            if query_lower in msg.get(
                "content", "",
            ).lower():
                if channel and msg.get(
                    "channel",
                ) != channel:
                    continue
                results.append(msg)

        results.sort(
            key=lambda x: x.get(
                "received_at", 0,
            ),
            reverse=True,
        )

        return {
            "query": query,
            "results": results[:limit],
            "total_matches": len(results),
        }

    def archive_message(
        self,
        message_id: str,
    ) -> dict[str, Any]:
        """Mesajı arşivler.

        Args:
            message_id: Mesaj ID.

        Returns:
            Arşivleme bilgisi.
        """
        msg = self._find_message(message_id)
        if not msg:
            return {"error": "message_not_found"}

        msg["archived"] = True
        self._archive.append(msg)
        self._stats["messages_archived"] += 1

        return {
            "message_id": message_id,
            "archived": True,
        }

    def get_archive(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Arşivi getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Arşiv listesi.
        """
        return list(self._archive[-limit:])

    def get_stats(self) -> dict[str, Any]:
        """İstatistikleri getirir.

        Returns:
            İstatistik bilgisi.
        """
        channel_counts: dict[str, int] = {}
        for msg in self._messages:
            ch = msg.get("channel", "unknown")
            channel_counts[ch] = (
                channel_counts.get(ch, 0) + 1
            )

        unread = sum(
            1 for m in self._messages
            if not m["read"] and not m["archived"]
        )

        return {
            "total_messages": len(
                self._messages,
            ),
            "unread": unread,
            "archived": len(self._archive),
            "threads": len(self._threads),
            "by_channel": channel_counts,
        }

    def _find_message(
        self,
        message_id: str,
    ) -> dict[str, Any] | None:
        """Mesaj bulur."""
        for m in self._messages:
            if m["message_id"] == message_id:
                return m
        return None

    @property
    def message_count(self) -> int:
        """Mesaj sayısı."""
        return self._stats["messages_received"]

    @property
    def unread_count(self) -> int:
        """Okunmamış sayısı."""
        return sum(
            1 for m in self._messages
            if not m["read"] and not m["archived"]
        )

    @property
    def thread_count(self) -> int:
        """Konuşma dizisi sayısı."""
        return len(self._threads)
