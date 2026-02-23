"""Kanal saglik izleme yoneticisi.

Kanal durumu, crash loop tespiti
ve otomatik yeniden baslatma.
"""

import logging
import time

from app.models.gateway_models import (
    ChannelHealthStatus,
    ChannelStatus,
)

logger = logging.getLogger(__name__)

_MAX_CRASHES = 5
_CRASH_WINDOW = 600  # 10 dakika


class ChannelHealthManager:
    """Kanal saglik izleme yoneticisi.

    Attributes:
        _channels: Kanal durumlari.
        _crash_history: Cokme gecmisi.
        _max_crashes: Maks cokme sayisi.
    """

    def __init__(
        self,
        max_crashes: int = _MAX_CRASHES,
        crash_window: int = _CRASH_WINDOW,
    ) -> None:
        """ChannelHealthManager baslatir."""
        self._channels: dict[
            str, ChannelHealthStatus
        ] = {}
        self._crash_history: dict[
            str, list[float]
        ] = {}
        self._max_crashes = max_crashes
        self._crash_window = crash_window

    def wire_check_minutes(
        self,
        channel: str,
        minutes: int,
    ) -> None:
        """checkMinutes'i dogrulama ile ayarlar.

        Args:
            channel: Kanal adi.
            minutes: Kontrol araligi (dakika).
        """
        if minutes < 1:
            minutes = 1
        if minutes > 60:
            minutes = 60

        status = self._get_or_create(channel)
        status.check_interval_minutes = minutes
        logger.debug(
            "%s icin kontrol araligi: %d dk",
            channel,
            minutes,
        )

    def harden_auto_restart(
        self,
        channel: str,
    ) -> bool:
        """Crash loop korumasiyla yeniden baslatir.

        10 dk icinde 5 cokme = crash loop.

        Args:
            channel: Kanal adi.

        Returns:
            Yeniden baslatma izni varsa True.
        """
        now = time.time()

        if channel not in self._crash_history:
            self._crash_history[channel] = []

        history = self._crash_history[channel]
        history.append(now)

        cutoff = now - self._crash_window
        self._crash_history[channel] = [
            t for t in history if t > cutoff
        ]

        recent = len(
            self._crash_history[channel],
        )
        if recent >= self._max_crashes:
            status = self._get_or_create(channel)
            status.status = ChannelStatus.CRASH_LOOP
            status.error_message = (
                f"Crash loop: {recent} cokme / "
                f"{self._crash_window}sn"
            )
            logger.warning(
                "Crash loop tespit edildi: %s "
                "(%d cokme)",
                channel,
                recent,
            )
            return False

        return True

    def check_health(
        self,
        channel: str,
    ) -> dict:
        """Kanal sagligini kontrol eder.

        Args:
            channel: Kanal adi.

        Returns:
            Saglik bilgisi.
        """
        status = self._get_or_create(channel)
        status.last_check = time.time()
        return status.model_dump()

    def restart_channel(
        self,
        channel: str,
    ) -> bool:
        """Kanali crash loop korumasiyla yeniden baslatir.

        Args:
            channel: Kanal adi.

        Returns:
            Basarili ise True.
        """
        if not self.harden_auto_restart(channel):
            return False

        status = self._get_or_create(channel)
        status.status = ChannelStatus.RESTARTING
        status.last_restart = time.time()
        status.crash_count += 1

        status.status = ChannelStatus.HEALTHY
        logger.info(
            "Kanal yeniden baslatildi: %s",
            channel,
        )
        return True

    def mark_down(
        self,
        channel: str,
        error: str = "",
    ) -> None:
        """Kanali down olarak isaretler.

        Args:
            channel: Kanal adi.
            error: Hata mesaji.
        """
        status = self._get_or_create(channel)
        status.status = ChannelStatus.DOWN
        status.error_message = error

    def get_all_status(
        self,
    ) -> dict[str, dict]:
        """Tum kanal durumlarini dondurur.

        Returns:
            Kanal durumlari.
        """
        return {
            ch: s.model_dump()
            for ch, s in self._channels.items()
        }

    def _get_or_create(
        self,
        channel: str,
    ) -> ChannelHealthStatus:
        """Kanal durumunu getirir veya olusturur."""
        if channel not in self._channels:
            self._channels[channel] = (
                ChannelHealthStatus(
                    channel=channel,
                )
            )
        return self._channels[channel]
