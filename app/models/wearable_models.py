"""Wearable Companion modelleri.

Apple Watch / akilli saat / giyilebilir cihaz eslik sistemi
icin veri modelleri. APNs, bildirim aktarimi ve komut yuzeyi.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WearableType(str, Enum):
    """Giyilebilir cihaz turleri."""
    APPLE_WATCH = "apple_watch"
    ANDROID_WEAR = "android_wear"
    FITBIT = "fitbit"
    GENERIC = "generic"


class NotificationPriority(str, Enum):
    """Bildirim oncelik seviyeleri."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class WearableDevice(BaseModel):
    """Giyilebilir cihaz modeli.

    Attributes:
        device_id: Benzersiz cihaz kimligi
        device_type: Cihaz turu
        name: Cihaz adi
        paired_at: Eslestirme zamani
        last_seen: Son gorulme zamani
        is_connected: Baglanti durumu
        capabilities: Desteklenen yetenekler
        os_version: Isletim sistemi surumu
        app_version: Uygulama surumu
    """
    device_id: str = ""
    device_type: WearableType = WearableType.GENERIC
    name: str = ""
    paired_at: float = 0.0
    last_seen: float = 0.0
    is_connected: bool = False
    capabilities: list[str] = Field(default_factory=list)
    os_version: str = ""
    app_version: str = ""


class WatchInboxItem(BaseModel):
    """Saat gelen kutusu ogesi modeli.

    Attributes:
        item_id: Benzersiz oge kimligi
        device_id: Hedef cihaz kimligi
        title: Bildirim basligi
        body: Bildirim govdesi
        priority: Oncelik seviyesi
        created_at: Olusturulma zamani
        read_at: Okunma zamani
        is_read: Okundu mu
        actions: Kullanilabilir aksiyonlar
        metadata: Ek veri
    """
    item_id: str = ""
    device_id: str = ""
    title: str = ""
    body: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    created_at: float = 0.0
    read_at: float = 0.0
    is_read: bool = False
    actions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class APNsPayload(BaseModel):
    """Apple Push Notification Service yuklemesi modeli.

    Attributes:
        device_token: Cihaz push token
        alert_title: Uyari basligi
        alert_body: Uyari govdesi
        badge: Rozet sayisi
        sound: Bildirim sesi
        category: Bildirim kategorisi
        is_silent: Sessiz bildirim mi
        custom_data: Ozel veri
        expiry: Gecerlilik suresi (saniye)
    """
    device_token: str = ""
    alert_title: str = ""
    alert_body: str = ""
    badge: int = 0
    sound: str = "default"
    category: str = ""
    is_silent: bool = False
    custom_data: dict[str, Any] = Field(default_factory=dict)
    expiry: int = 3600


class CommandSurface(BaseModel):
    """Komut yuzeyi modeli.

    Attributes:
        surface_id: Benzersiz yuzey kimligi
        device_id: Cihaz kimligi
        command_type: Komut turu
        payload: Komut verisi
        status: Islem durumu
        result: Islem sonucu
        created_at: Olusturulma zamani
        completed_at: Tamamlanma zamani
    """
    surface_id: str = ""
    device_id: str = ""
    command_type: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    result: dict[str, Any] = Field(default_factory=dict)
    created_at: float = 0.0
    completed_at: float = 0.0


class WearableConfig(BaseModel):
    """Giyilebilir cihaz yapilandirma modeli.

    Attributes:
        apns_key_path: APNs anahtar dosya yolu
        apns_key_id: APNs anahtar kimligi
        apns_team_id: APNs takim kimligi
        apns_bundle_id: APNs paket kimligi
        apns_use_sandbox: Sandbox kullanimi
        max_inbox_items: Maksimum gelen kutusu ogesi
        notification_ttl: Bildirim yasam suresi (saniye)
        auto_reconnect: Otomatik yeniden baglanti
        reconnect_interval: Yeniden baglanti araligi (saniye)
    """
    apns_key_path: str = ""
    apns_key_id: str = ""
    apns_team_id: str = ""
    apns_bundle_id: str = ""
    apns_use_sandbox: bool = True
    max_inbox_items: int = 100
    notification_ttl: int = 86400
    auto_reconnect: bool = True
    reconnect_interval: int = 30
