"""ATLAS Kanal Dagitici modulu.

Telegram, email, SMS, push ve
webhook kanallarina bildirim dagitimi.
"""

import logging
import time
from typing import Any

from app.models.notification_system import (
    NotificationChannel,
    NotificationStatus,
)

logger = logging.getLogger(__name__)


class ChannelDispatcher:
    """Kanal dagitici.

    Bildirimleri uygun kanallara
    dagitir ve sonuclari takip eder.

    Attributes:
        _channels: Kayitli kanallar.
        _dispatch_log: Dagitim gecmisi.
    """

    def __init__(self) -> None:
        """Kanal dagiticiyi baslatir."""
        self._channels: dict[str, dict[str, Any]] = {}
        self._dispatch_log: list[dict[str, Any]] = []
        self._channel_stats: dict[str, dict[str, int]] = {}

        # Varsayilan kanallari kaydet
        for ch in NotificationChannel:
            self._channels[ch.value] = {
                "name": ch.value,
                "enabled": True,
                "config": {},
            }
            self._channel_stats[ch.value] = {
                "sent": 0, "failed": 0,
            }

        logger.info("ChannelDispatcher baslatildi")

    def dispatch(
        self,
        channel: NotificationChannel,
        recipient: str,
        title: str,
        message: str,
    ) -> dict[str, Any]:
        """Bildirim gonderir.

        Args:
            channel: Kanal.
            recipient: Alici.
            title: Baslik.
            message: Mesaj.

        Returns:
            Gonderim sonucu.
        """
        ch_config = self._channels.get(channel.value)
        if not ch_config or not ch_config["enabled"]:
            return {
                "status": NotificationStatus.FAILED.value,
                "channel": channel.value,
                "reason": "channel_disabled",
            }

        # Simule edilmis gonderim
        result = {
            "status": NotificationStatus.SENT.value,
            "channel": channel.value,
            "recipient": recipient,
            "title": title,
            "sent_at": time.time(),
        }

        self._dispatch_log.append(result)
        self._channel_stats[channel.value]["sent"] += 1

        logger.info(
            "Bildirim gonderildi: [%s] %s -> %s",
            channel.value, title, recipient,
        )
        return result

    def dispatch_multi(
        self,
        channels: list[NotificationChannel],
        recipient: str,
        title: str,
        message: str,
    ) -> list[dict[str, Any]]:
        """Coklu kanal gonderimi.

        Args:
            channels: Kanallar.
            recipient: Alici.
            title: Baslik.
            message: Mesaj.

        Returns:
            Gonderim sonuclari.
        """
        results: list[dict[str, Any]] = []
        for ch in channels:
            result = self.dispatch(
                ch, recipient, title, message,
            )
            results.append(result)
        return results

    def enable_channel(
        self,
        channel: NotificationChannel,
    ) -> bool:
        """Kanali aktif eder.

        Args:
            channel: Kanal.

        Returns:
            Basarili ise True.
        """
        ch = self._channels.get(channel.value)
        if ch:
            ch["enabled"] = True
            return True
        return False

    def disable_channel(
        self,
        channel: NotificationChannel,
    ) -> bool:
        """Kanali devre disi birakir.

        Args:
            channel: Kanal.

        Returns:
            Basarili ise True.
        """
        ch = self._channels.get(channel.value)
        if ch:
            ch["enabled"] = False
            return True
        return False

    def is_enabled(
        self,
        channel: NotificationChannel,
    ) -> bool:
        """Kanal aktif mi kontrol eder.

        Args:
            channel: Kanal.

        Returns:
            Aktif ise True.
        """
        ch = self._channels.get(channel.value)
        return ch["enabled"] if ch else False

    def configure_channel(
        self,
        channel: NotificationChannel,
        config: dict[str, Any],
    ) -> None:
        """Kanal yapilandirmasi.

        Args:
            channel: Kanal.
            config: Yapilandirma.
        """
        ch = self._channels.get(channel.value)
        if ch:
            ch["config"] = config

    def get_stats(self) -> dict[str, dict[str, int]]:
        """Kanal istatistikleri.

        Returns:
            Istatistikler.
        """
        return dict(self._channel_stats)

    @property
    def channel_count(self) -> int:
        """Kanal sayisi."""
        return len(self._channels)

    @property
    def dispatch_count(self) -> int:
        """Dagitim sayisi."""
        return len(self._dispatch_log)

    @property
    def enabled_count(self) -> int:
        """Aktif kanal sayisi."""
        return sum(
            1 for ch in self._channels.values()
            if ch["enabled"]
        )
