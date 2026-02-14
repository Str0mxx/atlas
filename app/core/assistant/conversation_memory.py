"""ATLAS Konusma Hafizasi modulu.

Uzun sureli konusma gecmisi, konu takibi,
referans cozumleme, gecmis konulara geri donus
ve baglam restorasyonu.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.assistant import ChannelType, ConversationEntry

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Konusma hafizasi.

    Uzun sureli konusma gecmisini yonetir,
    konulari takip eder ve baglami korur.

    Attributes:
        _entries: Konusma girdileri.
        _topics: Konu takibi.
        _active_topic: Aktif konu.
        _topic_history: Konu gecmisi.
        _bookmarks: Yer imleri.
        _max_entries: Maks girdi sayisi.
    """

    def __init__(self, max_entries: int = 1000) -> None:
        """Konusma hafizasini baslatir.

        Args:
            max_entries: Maks girdi sayisi.
        """
        self._entries: list[ConversationEntry] = []
        self._topics: dict[str, list[str]] = {}
        self._active_topic: str = ""
        self._topic_history: list[dict[str, Any]] = []
        self._bookmarks: dict[str, str] = {}
        self._max_entries = max(10, max_entries)

        logger.info(
            "ConversationMemory baslatildi (max=%d)",
            self._max_entries,
        )

    def add_entry(
        self,
        role: str,
        content: str,
        topic: str = "",
        channel: ChannelType = ChannelType.TELEGRAM,
        references: list[str] | None = None,
    ) -> ConversationEntry:
        """Konusma girdisi ekler.

        Args:
            role: Rol (user/assistant).
            content: Icerik.
            topic: Konu.
            channel: Kanal.
            references: Referanslar.

        Returns:
            ConversationEntry nesnesi.
        """
        entry = ConversationEntry(
            role=role,
            content=content,
            topic=topic or self._active_topic,
            channel=channel,
            references=references or [],
        )
        self._entries.append(entry)

        # Boyut sinirla
        if len(self._entries) > self._max_entries:
            overflow = self._entries[:-self._max_entries]
            overflow_ids = {e.entry_id for e in overflow}
            self._entries = self._entries[-self._max_entries:]
            # Konu referanslarindan eski girdileri temizle
            for topic_key in self._topics:
                self._topics[topic_key] = [
                    eid for eid in self._topics[topic_key]
                    if eid not in overflow_ids
                ]

        # Konu takibi
        effective_topic = topic or self._active_topic
        if effective_topic:
            self._topics.setdefault(effective_topic, []).append(
                entry.entry_id,
            )
            if effective_topic != self._active_topic:
                self._switch_topic(effective_topic)

        return entry

    def set_topic(self, topic: str) -> None:
        """Aktif konuyu ayarlar.

        Args:
            topic: Konu.
        """
        if topic != self._active_topic:
            self._switch_topic(topic)

    def get_topic_entries(
        self,
        topic: str,
    ) -> list[ConversationEntry]:
        """Konuya ait girdileri getirir.

        Args:
            topic: Konu.

        Returns:
            Girdi listesi.
        """
        entry_ids = set(self._topics.get(topic, []))
        return [
            e for e in self._entries
            if e.entry_id in entry_ids
        ]

    def get_recent_entries(
        self,
        limit: int = 10,
    ) -> list[ConversationEntry]:
        """Son girdileri getirir.

        Args:
            limit: Maks girdi.

        Returns:
            Girdi listesi.
        """
        return self._entries[-limit:]

    def search_entries(
        self,
        query: str,
        limit: int = 10,
    ) -> list[ConversationEntry]:
        """Girdilerde arar.

        Args:
            query: Arama metni.
            limit: Maks sonuc.

        Returns:
            Esleşen girdiler.
        """
        query_lower = query.lower()
        results: list[ConversationEntry] = []

        for entry in reversed(self._entries):
            if query_lower in entry.content.lower():
                results.append(entry)
                if len(results) >= limit:
                    break

        return results

    def resolve_reference(
        self,
        reference: str,
    ) -> ConversationEntry | None:
        """Referansi cozer.

        Args:
            reference: Referans metni.

        Returns:
            Cozumlenmis girdi veya None.
        """
        ref_lower = reference.lower()

        # ID ile ara
        for entry in self._entries:
            if entry.entry_id == reference:
                return entry

        # Son mesaj referanslari
        if ref_lower in ("onceki", "son", "previous", "last"):
            if self._entries:
                return self._entries[-1]
            return None

        # Konu referansi
        for topic, entry_ids in self._topics.items():
            if ref_lower in topic.lower() and entry_ids:
                target_id = entry_ids[-1]
                for entry in self._entries:
                    if entry.entry_id == target_id:
                        return entry

        # Icerik eslesmesi
        for entry in reversed(self._entries):
            if ref_lower in entry.content.lower():
                return entry

        return None

    def recall_topic(self, topic: str) -> dict[str, Any]:
        """Gecmis konuya geri doner.

        Args:
            topic: Konu.

        Returns:
            Konu bilgisi.
        """
        entries = self.get_topic_entries(topic)

        if not entries:
            return {
                "found": False,
                "topic": topic,
                "entries": [],
            }

        self._switch_topic(topic)

        return {
            "found": True,
            "topic": topic,
            "entry_count": len(entries),
            "entries": entries[-5:],
            "first_discussed": entries[0].timestamp.isoformat(),
            "last_discussed": entries[-1].timestamp.isoformat(),
        }

    def save_context(self, bookmark_name: str) -> dict[str, Any]:
        """Baglami kaydeder.

        Args:
            bookmark_name: Yer imi adi.

        Returns:
            Kayit bilgisi.
        """
        if not self._entries:
            return {"saved": False, "reason": "Girdi yok"}

        last_entry_id = self._entries[-1].entry_id
        self._bookmarks[bookmark_name] = last_entry_id

        return {
            "saved": True,
            "bookmark": bookmark_name,
            "entry_id": last_entry_id,
            "topic": self._active_topic,
            "entry_count": len(self._entries),
        }

    def restore_context(
        self,
        bookmark_name: str,
    ) -> dict[str, Any]:
        """Baglami geri yukler.

        Args:
            bookmark_name: Yer imi adi.

        Returns:
            Restorasyon bilgisi.
        """
        entry_id = self._bookmarks.get(bookmark_name)
        if not entry_id:
            return {"restored": False, "reason": "Yer imi bulunamadi"}

        # Bookmark noktasindan itibaren girdileri bul
        bookmark_idx = None
        for i, entry in enumerate(self._entries):
            if entry.entry_id == entry_id:
                bookmark_idx = i
                break

        if bookmark_idx is None:
            return {"restored": False, "reason": "Girdi bulunamadi"}

        context_entries = self._entries[
            max(0, bookmark_idx - 5):bookmark_idx + 1
        ]

        # Konuyu geri yukle
        if context_entries:
            last_topic = context_entries[-1].topic
            if last_topic:
                self._switch_topic(last_topic)

        return {
            "restored": True,
            "bookmark": bookmark_name,
            "entries_restored": len(context_entries),
            "topic": self._active_topic,
        }

    def get_topic_summary(self) -> dict[str, Any]:
        """Konu ozetini getirir.

        Returns:
            Ozet sozlugu.
        """
        summary: dict[str, int] = {}
        for topic, entry_ids in self._topics.items():
            summary[topic] = len(entry_ids)

        return {
            "active_topic": self._active_topic,
            "topics": summary,
            "total_topics": len(self._topics),
            "topic_switches": len(self._topic_history),
        }

    def get_channel_entries(
        self,
        channel: ChannelType,
    ) -> list[ConversationEntry]:
        """Kanala gore girdileri getirir.

        Args:
            channel: Kanal.

        Returns:
            Girdi listesi.
        """
        return [
            e for e in self._entries
            if e.channel == channel
        ]

    def _switch_topic(self, new_topic: str) -> None:
        """Konu degistirir.

        Args:
            new_topic: Yeni konu.
        """
        if self._active_topic:
            self._topic_history.append({
                "from": self._active_topic,
                "to": new_topic,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        self._active_topic = new_topic

    @property
    def entry_count(self) -> int:
        """Girdi sayisi."""
        return len(self._entries)

    @property
    def topic_count(self) -> int:
        """Konu sayisi."""
        return len(self._topics)

    @property
    def active_topic(self) -> str:
        """Aktif konu."""
        return self._active_topic

    @property
    def bookmark_count(self) -> int:
        """Yer imi sayisi."""
        return len(self._bookmarks)
