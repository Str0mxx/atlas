"""ATLAS Bildirim Tercihleri Yoneticisi modulu.

Kullanici tercihleri, sessiz saatler,
kanal tercihleri, siklik limitleri
ve kategori filtreleri.
"""

import logging
from typing import Any

from app.models.notification_system import (
    NotificationChannel,
    NotificationPriority,
)

logger = logging.getLogger(__name__)


class NotificationPreferenceManager:
    """Bildirim tercihleri yoneticisi.

    Kullanici bazli bildirim tercihlerini
    yonetir.

    Attributes:
        _preferences: Kullanici tercihleri.
        _quiet_hours: Sessiz saatler.
        _rate_limits: Siklik limitleri.
    """

    def __init__(
        self,
        quiet_start: str = "22:00",
        quiet_end: str = "08:00",
    ) -> None:
        """Tercih yoneticisini baslatir.

        Args:
            quiet_start: Sessiz baslangic.
            quiet_end: Sessiz bitis.
        """
        self._preferences: dict[
            str, dict[str, Any]
        ] = {}
        self._quiet_hours = {
            "start": quiet_start,
            "end": quiet_end,
        }
        self._rate_limits: dict[str, dict[str, Any]] = {}
        self._category_filters: dict[
            str, list[str]
        ] = {}

        logger.info(
            "NotificationPreferenceManager baslatildi",
        )

    def set_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
    ) -> None:
        """Tercih ayarlar.

        Args:
            user_id: Kullanici ID.
            key: Tercih anahtari.
            value: Deger.
        """
        if user_id not in self._preferences:
            self._preferences[user_id] = {}
        self._preferences[user_id][key] = value

    def get_preference(
        self,
        user_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """Tercih getirir.

        Args:
            user_id: Kullanici ID.
            key: Tercih anahtari.
            default: Varsayilan deger.

        Returns:
            Tercih degeri.
        """
        prefs = self._preferences.get(user_id, {})
        return prefs.get(key, default)

    def set_channel_preference(
        self,
        user_id: str,
        channel: NotificationChannel,
        enabled: bool = True,
    ) -> None:
        """Kanal tercihi ayarlar.

        Args:
            user_id: Kullanici ID.
            channel: Kanal.
            enabled: Aktif mi.
        """
        self.set_preference(
            user_id,
            f"channel:{channel.value}",
            enabled,
        )

    def get_channel_preference(
        self,
        user_id: str,
        channel: NotificationChannel,
    ) -> bool:
        """Kanal tercihi getirir.

        Args:
            user_id: Kullanici ID.
            channel: Kanal.

        Returns:
            Aktif ise True.
        """
        return self.get_preference(
            user_id,
            f"channel:{channel.value}",
            True,
        )

    def set_quiet_hours(
        self,
        user_id: str,
        start: str,
        end: str,
    ) -> None:
        """Kullanici sessiz saatleri ayarlar.

        Args:
            user_id: Kullanici ID.
            start: Baslangic (HH:MM).
            end: Bitis (HH:MM).
        """
        self.set_preference(
            user_id, "quiet_start", start,
        )
        self.set_preference(
            user_id, "quiet_end", end,
        )

    def is_quiet_hours(
        self,
        user_id: str,
        hour: int,
    ) -> bool:
        """Sessiz saat kontrolu.

        Args:
            user_id: Kullanici ID.
            hour: Saat (0-23).

        Returns:
            Sessiz saatte ise True.
        """
        start_str = self.get_preference(
            user_id, "quiet_start",
            self._quiet_hours["start"],
        )
        end_str = self.get_preference(
            user_id, "quiet_end",
            self._quiet_hours["end"],
        )

        start_h = int(start_str.split(":")[0])
        end_h = int(end_str.split(":")[0])

        if start_h > end_h:
            # Gece yarisi gecisi (orn: 22:00-08:00)
            return hour >= start_h or hour < end_h
        return start_h <= hour < end_h

    def set_rate_limit(
        self,
        user_id: str,
        max_per_hour: int = 10,
        max_per_day: int = 100,
    ) -> None:
        """Siklik limiti ayarlar.

        Args:
            user_id: Kullanici ID.
            max_per_hour: Saatlik limit.
            max_per_day: Gunluk limit.
        """
        self._rate_limits[user_id] = {
            "max_per_hour": max_per_hour,
            "max_per_day": max_per_day,
            "sent_hour": 0,
            "sent_day": 0,
        }

    def check_rate_limit(
        self,
        user_id: str,
    ) -> bool:
        """Siklik limiti kontrol eder.

        Args:
            user_id: Kullanici ID.

        Returns:
            Gonderim uygun ise True.
        """
        limits = self._rate_limits.get(user_id)
        if not limits:
            return True
        if limits["sent_hour"] >= limits["max_per_hour"]:
            return False
        if limits["sent_day"] >= limits["max_per_day"]:
            return False
        return True

    def record_sent(self, user_id: str) -> None:
        """Gonderim kaydeder.

        Args:
            user_id: Kullanici ID.
        """
        limits = self._rate_limits.get(user_id)
        if limits:
            limits["sent_hour"] += 1
            limits["sent_day"] += 1

    def set_category_filter(
        self,
        user_id: str,
        blocked: list[str],
    ) -> None:
        """Kategori filtresi ayarlar.

        Args:
            user_id: Kullanici ID.
            blocked: Engellenen kategoriler.
        """
        self._category_filters[user_id] = blocked

    def is_category_allowed(
        self,
        user_id: str,
        category: str,
    ) -> bool:
        """Kategori izin kontrolu.

        Args:
            user_id: Kullanici ID.
            category: Kategori.

        Returns:
            Izinli ise True.
        """
        blocked = self._category_filters.get(
            user_id, [],
        )
        return category not in blocked

    @property
    def user_count(self) -> int:
        """Kullanici sayisi."""
        return len(self._preferences)

    @property
    def rate_limit_count(self) -> int:
        """Siklik limiti sayisi."""
        return len(self._rate_limits)
