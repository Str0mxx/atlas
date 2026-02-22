"""Izin listesi yoneticisi - kanal bazli izin listesi yonetimi.

Belirli kanallarda kimlerin mesaj gonderebilecegini kontrol eden
izin listesi (allowlist) mekanizmasi saglar.
"""

import logging
import time
import uuid
from typing import Optional

from app.models.access_models import AllowlistEntry, ChannelType

logger = logging.getLogger(__name__)


class AllowlistManager:
    """Kanal bazli izin listesi yoneticisi.

    Izin listesine ekleme, cikarma, kontrol ve toplu islemler saglar.
    Wildcard destegi ve string ID zorlama ozelligi icerir.
    """

    def __init__(self) -> None:
        """AllowlistManager baslatici."""
        self._entries: dict[str, AllowlistEntry] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: dict) -> None:
        """Gecmis kaydini tutar."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details})

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        channels: dict[str, int] = {}
        wildcards = 0
        for entry in self._entries.values():
            ch = entry.channel.value
            channels[ch] = channels.get(ch, 0) + 1
            if entry.is_wildcard:
                wildcards += 1
        return {"total_entries": len(self._entries), "channels": channels, "wildcards": wildcards, "history_count": len(self._history)}

    def _make_key(self, sender_id: str, channel: ChannelType) -> str:
        """Izin listesi anahtari olusturur."""
        return f"{channel.value}:{sender_id}"

    def add(self, sender_id: str, channel: ChannelType = ChannelType.GENERIC, added_by: str = "system", notes: str = "") -> AllowlistEntry:
        """Izin listesine ekler."""
        key = self._make_key(sender_id, channel)
        entry = AllowlistEntry(entry_id=str(uuid.uuid4()), sender_id=str(sender_id), channel=channel, added_at=time.time(), added_by=added_by, is_wildcard=False, notes=notes)
        self._entries[key] = entry
        self._record_history("add", {"sender_id": sender_id, "channel": channel.value})
        return entry

    def remove(self, sender_id: str, channel: ChannelType = ChannelType.GENERIC) -> bool:
        """Izin listesinden cikarir."""
        key = self._make_key(sender_id, channel)
        if key in self._entries:
            del self._entries[key]
            self._record_history("remove", {"sender_id": sender_id, "channel": channel.value})
            return True
        return False

    def is_allowed(self, sender_id: str, channel: ChannelType = ChannelType.GENERIC) -> bool:
        """Gondericinin izinli olup olmadigini kontrol eder."""
        key = self._make_key(sender_id, channel)
        if key in self._entries:
            return True
        wildcard_key = self._make_key("*", channel)
        if wildcard_key in self._entries:
            return True
        return False

    def get_entries(self, channel: Optional[ChannelType] = None) -> list[AllowlistEntry]:
        """Izin listesi girislerini dondurur."""
        if channel is None:
            return list(self._entries.values())
        return [e for e in self._entries.values() if e.channel == channel]

    def clear(self, channel: ChannelType) -> int:
        """Kanal izin listesini temizler."""
        to_remove = [k for k, v in self._entries.items() if v.channel == channel]
        for key in to_remove:
            del self._entries[key]
        self._record_history("clear", {"channel": channel.value, "count": len(to_remove)})
        return len(to_remove)

    def add_wildcard(self, channel: ChannelType, added_by: str = "system") -> AllowlistEntry:
        """Kanal icin wildcard izni ekler (herkese acik)."""
        key = self._make_key("*", channel)
        entry = AllowlistEntry(entry_id=str(uuid.uuid4()), sender_id="*", channel=channel, added_at=time.time(), added_by=added_by, is_wildcard=True, notes="Wildcard: all senders allowed")
        self._entries[key] = entry
        self._record_history("add_wildcard", {"channel": channel.value})
        return entry

    def enforce_string_ids(self) -> int:
        """Sayisal kimlikleri string formata donusturur."""
        converted = 0
        new_entries: dict[str, AllowlistEntry] = {}
        for key, entry in self._entries.items():
            if entry.sender_id.isdigit():
                entry.sender_id = str(entry.sender_id)
                converted += 1
            new_key = self._make_key(entry.sender_id, entry.channel)
            new_entries[new_key] = entry
        self._entries = new_entries
        self._record_history("enforce_string_ids", {"converted": converted})
        return converted

    def doctor_repair(self) -> list[str]:
        """Gecersiz girisleri bulur ve duzeltir."""
        repairs: list[str] = []
        to_remove: list[str] = []
        for key, entry in self._entries.items():
            if not entry.sender_id:
                to_remove.append(key)
                repairs.append(f"Removed empty sender_id entry: {key}")
            elif not entry.entry_id:
                entry.entry_id = str(uuid.uuid4())
                repairs.append(f"Generated missing entry_id for: {key}")
        for key in to_remove:
            del self._entries[key]
        self._record_history("doctor_repair", {"repairs": len(repairs)})
        return repairs

    def import_list(self, entries: list[dict]) -> int:
        """Toplu ithalat yapar."""
        count = 0
        for data in entries:
            sender_id = data.get("sender_id", "")
            channel_str = data.get("channel", "generic")
            try:
                channel = ChannelType(channel_str)
            except ValueError:
                channel = ChannelType.GENERIC
            if sender_id:
                self.add(sender_id=sender_id, channel=channel, added_by=data.get("added_by", "import"), notes=data.get("notes", ""))
                count += 1
        self._record_history("import_list", {"count": count})
        return count

    def export_list(self, channel: Optional[ChannelType] = None) -> list[dict]:
        """Izin listesini disa aktarir."""
        entries = self.get_entries(channel)
        return [e.model_dump() for e in entries]
