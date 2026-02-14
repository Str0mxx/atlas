"""ATLAS Coklu Kanal Yoneticisi modulu.

Telegram, e-posta, ses entegrasyonu,
kanallar arasi baglam senkronizasyonu
ve kanala ozel formatlama.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.assistant import ChannelType, SmartResponse

logger = logging.getLogger(__name__)


class MultiChannelHandler:
    """Coklu kanal yoneticisi.

    Farkli iletisim kanallarini birlestirip
    tutarli bir deneyim sunar.

    Attributes:
        _channels: Aktif kanallar.
        _channel_configs: Kanal yapilandirmalari.
        _message_log: Mesaj kaydi.
        _sync_state: Senkronizasyon durumu.
        _formatters: Kanal formatlaricilari.
    """

    def __init__(self) -> None:
        """Coklu kanal yoneticisini baslatir."""
        self._channels: dict[str, dict[str, Any]] = {}
        self._channel_configs: dict[str, dict[str, Any]] = {
            ChannelType.TELEGRAM.value: {
                "max_length": 4096,
                "supports_markdown": True,
                "supports_media": True,
            },
            ChannelType.EMAIL.value: {
                "max_length": 50000,
                "supports_html": True,
                "supports_attachments": True,
            },
            ChannelType.VOICE.value: {
                "max_length": 500,
                "requires_short": True,
                "supports_ssml": True,
            },
            ChannelType.API.value: {
                "max_length": 100000,
                "supports_json": True,
            },
            ChannelType.WEB.value: {
                "max_length": 50000,
                "supports_html": True,
                "supports_markdown": True,
            },
        }
        self._message_log: list[dict[str, Any]] = []
        self._sync_state: dict[str, Any] = {}
        self._formatters: dict[str, Any] = {}

        logger.info("MultiChannelHandler baslatildi")

    def register_channel(
        self,
        channel_type: ChannelType,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Kanal kaydeder.

        Args:
            channel_type: Kanal turu.
            config: Yapilandirma.

        Returns:
            Kayit bilgisi.
        """
        channel_key = channel_type.value
        self._channels[channel_key] = {
            "type": channel_type.value,
            "active": True,
            "config": config or {},
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "message_count": 0,
        }

        if config:
            self._channel_configs.setdefault(channel_key, {}).update(config)

        logger.info("Kanal kaydedildi: %s", channel_key)
        return self._channels[channel_key]

    def unregister_channel(self, channel_type: ChannelType) -> bool:
        """Kanal kaydini siler.

        Args:
            channel_type: Kanal turu.

        Returns:
            Basarili ise True.
        """
        key = channel_type.value
        if key in self._channels:
            self._channels[key]["active"] = False
            return True
        return False

    def send_message(
        self,
        content: str,
        channel: ChannelType,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mesaj gonderir.

        Args:
            content: Icerik.
            channel: Hedef kanal.
            metadata: Ek bilgi.

        Returns:
            Gonderim sonucu.
        """
        channel_key = channel.value
        config = self._channel_configs.get(channel_key, {})

        # Kanal formatlama
        formatted = self._format_for_channel(content, channel, config)

        # Uzunluk siniri
        max_len = config.get("max_length", 4096)
        if len(formatted) > max_len:
            formatted = formatted[:max_len - 3] + "..."

        record = {
            "channel": channel_key,
            "content": formatted,
            "original_length": len(content),
            "formatted_length": len(formatted),
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._message_log.append(record)

        # Mesaj sayacini guncelle
        if channel_key in self._channels:
            self._channels[channel_key]["message_count"] += 1

        return {
            "sent": True,
            "channel": channel_key,
            "content": formatted,
            "length": len(formatted),
        }

    def broadcast(
        self,
        content: str,
        channels: list[ChannelType] | None = None,
    ) -> list[dict[str, Any]]:
        """Tum kanallara mesaj gonderir.

        Args:
            content: Icerik.
            channels: Hedef kanallar (None=tumu).

        Returns:
            Gonderim sonuclari.
        """
        targets = channels or [
            ChannelType(ch["type"])
            for ch in self._channels.values()
            if ch["active"]
        ]

        results = []
        for channel in targets:
            result = self.send_message(content, channel)
            results.append(result)

        return results

    def sync_context(
        self,
        source_channel: ChannelType,
        target_channel: ChannelType,
        context_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Kanallar arasi baglam senkronize eder.

        Args:
            source_channel: Kaynak kanal.
            target_channel: Hedef kanal.
            context_data: Baglam verisi.

        Returns:
            Senkronizasyon sonucu.
        """
        sync_key = f"{source_channel.value}->{target_channel.value}"
        self._sync_state[sync_key] = {
            "data": context_data,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "synced": True,
            "source": source_channel.value,
            "target": target_channel.value,
            "data_keys": list(context_data.keys()),
        }

    def get_sync_state(
        self,
        source: ChannelType,
        target: ChannelType,
    ) -> dict[str, Any] | None:
        """Senkronizasyon durumunu getirir.

        Args:
            source: Kaynak kanal.
            target: Hedef kanal.

        Returns:
            Senkronizasyon durumu veya None.
        """
        key = f"{source.value}->{target.value}"
        return self._sync_state.get(key)

    def get_channel_config(
        self,
        channel: ChannelType,
    ) -> dict[str, Any]:
        """Kanal yapilandirmasini getirir.

        Args:
            channel: Kanal.

        Returns:
            Yapilandirma sozlugu.
        """
        return dict(
            self._channel_configs.get(channel.value, {}),
        )

    def get_channel_messages(
        self,
        channel: ChannelType,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Kanal mesajlarini getirir.

        Args:
            channel: Kanal.
            limit: Maks mesaj.

        Returns:
            Mesaj listesi.
        """
        channel_msgs = [
            m for m in self._message_log
            if m["channel"] == channel.value
        ]
        return channel_msgs[-limit:]

    def get_active_channels(self) -> list[str]:
        """Aktif kanallari getirir.

        Returns:
            Kanal adi listesi.
        """
        return [
            key for key, ch in self._channels.items()
            if ch["active"]
        ]

    def get_channel_stats(self) -> dict[str, Any]:
        """Kanal istatistiklerini getirir.

        Returns:
            Istatistik sozlugu.
        """
        stats: dict[str, int] = {}
        for key, ch in self._channels.items():
            stats[key] = ch.get("message_count", 0)

        return {
            "channels": stats,
            "active_count": len(self.get_active_channels()),
            "total_messages": len(self._message_log),
            "sync_pairs": len(self._sync_state),
        }

    def _format_for_channel(
        self,
        content: str,
        channel: ChannelType,
        config: dict[str, Any],
    ) -> str:
        """Kanala gore formatlar.

        Args:
            content: Ham icerik.
            channel: Kanal.
            config: Yapilandirma.

        Returns:
            Formatlanmis icerik.
        """
        if channel == ChannelType.VOICE:
            # Ses - kisa, net, noktalama
            sentences = [
                s.strip() for s in content.split(".")
                if s.strip()
            ]
            return ". ".join(sentences[:3]) + "." if sentences else content

        if channel == ChannelType.EMAIL:
            # E-posta
            return f"Merhaba,\n\n{content}\n\nSaygilarimla,\nATLAS Asistan"

        if channel == ChannelType.API:
            # API - ham icerik
            return content

        # Telegram / Web - olduğu gibi
        return content

    @property
    def channel_count(self) -> int:
        """Kanal sayisi."""
        return len(self._channels)

    @property
    def active_channel_count(self) -> int:
        """Aktif kanal sayisi."""
        return len(self.get_active_channels())

    @property
    def message_count(self) -> int:
        """Mesaj sayisi."""
        return len(self._message_log)

    @property
    def sync_count(self) -> int:
        """Senkronizasyon sayisi."""
        return len(self._sync_state)
