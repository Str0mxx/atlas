"""Akilli saat eslik modulu.

Giyilebilir cihaz kaydi, gelen kutusu yonetimi
ve cihaz durum takibi saglar.
"""

import logging
import time
import uuid
from typing import Optional

from app.models.wearable_models import (
    WearableConfig,
    WearableDevice,
    WearableType,
    WatchInboxItem,
    NotificationPriority,
)

logger = logging.getLogger(__name__)


class WatchCompanion:
    """Akilli saat eslik yoneticisi.

    Cihaz eslestirme, gelen kutusu yonetimi ve
    cihaz durum izleme islevleri saglar.
    """

    def __init__(self, config: Optional[WearableConfig] = None) -> None:
        """Eslik yoneticisini baslatir.

        Args:
            config: Giyilebilir cihaz yapilandirmasi
        """
        self.config = config or WearableConfig()
        self._devices: dict[str, WearableDevice] = {}
        self._inbox: dict[str, list[WatchInboxItem]] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, **kwargs) -> None:
        """Gecmis kaydina olay ekler."""
        self._history.append({
            "action": action,
            "timestamp": time.time(),
            **kwargs,
        })

    def register_device(
        self,
        device_id: str,
        device_type: WearableType = WearableType.GENERIC,
        name: str = "",
    ) -> WearableDevice:
        """Giyilebilir cihaz kaydeder.

        Args:
            device_id: Cihaz kimligi
            device_type: Cihaz turu
            name: Cihaz adi

        Returns:
            Kaydedilen cihaz
        """
        now = time.time()
        device = WearableDevice(
            device_id=device_id,
            device_type=device_type,
            name=name or f"Device-{device_id[:8]}",
            paired_at=now,
            last_seen=now,
            is_connected=True,
        )
        self._devices[device_id] = device
        self._inbox[device_id] = []
        self._record_history("register_device", device_id=device_id, device_type=device_type.value)
        logger.info(f"Cihaz kaydedildi: {device_id} ({device_type.value})")
        return device

    def unregister_device(self, device_id: str) -> bool:
        """Cihaz kaydini siler.

        Args:
            device_id: Silinecek cihaz kimligi

        Returns:
            Basarili ise True
        """
        if device_id not in self._devices:
            return False
        del self._devices[device_id]
        self._inbox.pop(device_id, None)
        self._record_history("unregister_device", device_id=device_id)
        logger.info(f"Cihaz kaydi silindi: {device_id}")
        return True

    def get_device(self, device_id: str) -> Optional[WearableDevice]:
        """Cihaz bilgisini dondurur.

        Args:
            device_id: Cihaz kimligi

        Returns:
            Cihaz bilgisi veya None
        """
        device = self._devices.get(device_id)
        if device:
            device.last_seen = time.time()
        return device

    def list_devices(self) -> list[WearableDevice]:
        """Tum kayitli cihazlari listeler.

        Returns:
            Cihaz listesi
        """
        return list(self._devices.values())

    def add_inbox_item(
        self,
        device_id: str,
        title: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> Optional[WatchInboxItem]:
        """Cihaz gelen kutusuna oge ekler.

        Args:
            device_id: Hedef cihaz kimligi
            title: Bildirim basligi
            body: Bildirim govdesi
            priority: Oncelik seviyesi

        Returns:
            Eklenen oge veya None
        """
        if device_id not in self._devices:
            logger.warning(f"Bilinmeyen cihaz: {device_id}")
            return None

        # Maksimum oge sayisi kontrolu
        inbox = self._inbox.get(device_id, [])
        if len(inbox) >= self.config.max_inbox_items:
            # En eski ogeyi kaldir
            inbox.pop(0)

        item = WatchInboxItem(
            item_id=str(uuid.uuid4()),
            device_id=device_id,
            title=title,
            body=body,
            priority=priority,
            created_at=time.time(),
        )
        self._inbox.setdefault(device_id, []).append(item)
        self._record_history("add_inbox_item", device_id=device_id, item_id=item.item_id)
        return item

    def get_inbox(
        self, device_id: str, unread_only: bool = False
    ) -> list[WatchInboxItem]:
        """Cihaz gelen kutusunu dondurur.

        Args:
            device_id: Cihaz kimligi
            unread_only: Sadece okunmamislari goster

        Returns:
            Gelen kutusu ogeleri
        """
        items = self._inbox.get(device_id, [])
        if unread_only:
            return [i for i in items if not i.is_read]
        return list(items)

    def mark_read(self, device_id: str, item_id: str) -> bool:
        """Gelen kutusu ogesini okundu olarak isaretler.

        Args:
            device_id: Cihaz kimligi
            item_id: Oge kimligi

        Returns:
            Basarili ise True
        """
        items = self._inbox.get(device_id, [])
        for item in items:
            if item.item_id == item_id:
                item.is_read = True
                item.read_at = time.time()
                self._record_history("mark_read", device_id=device_id, item_id=item_id)
                return True
        return False

    def clear_inbox(self, device_id: str) -> int:
        """Cihaz gelen kutusunu temizler.

        Args:
            device_id: Cihaz kimligi

        Returns:
            Temizlenen oge sayisi
        """
        items = self._inbox.get(device_id, [])
        count = len(items)
        self._inbox[device_id] = []
        self._record_history("clear_inbox", device_id=device_id, count=count)
        return count

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        total_inbox = sum(len(items) for items in self._inbox.values())
        connected = sum(1 for d in self._devices.values() if d.is_connected)
        return {
            "total_devices": len(self._devices),
            "connected_devices": connected,
            "total_inbox_items": total_inbox,
            "max_inbox_items": self.config.max_inbox_items,
            "history_count": len(self._history),
        }
