"""
Kanal Yapilandirici modulu.

Telegram, WhatsApp, Discord, Slack,
Web chat kurulumu ve yonetimi.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ChannelConfigurator:
    """Kanal yapilandirici.

    Attributes:
        _channels: Kanal kayitlari.
        _stats: Istatistikler.
    """

    SUPPORTED_CHANNELS: list[str] = [
        "telegram",
        "whatsapp",
        "discord",
        "slack",
        "webchat",
    ]

    def __init__(self) -> None:
        """Yapilandiriciyi baslatir."""
        self._channels: dict[str, dict] = {}
        self._stats: dict[str, int] = {
            "channels_configured": 0,
            "channels_enabled": 0,
            "channels_disabled": 0,
            "validations_run": 0,
        }
        logger.info("ChannelConfigurator baslatildi")

    @property
    def channel_count(self) -> int:
        """Konfigüre kanal sayisi."""
        return len(self._channels)

    def setup_telegram(
        self,
        token: str = "",
        chat_id: str = "",
        webhook_url: str = "",
    ) -> dict[str, Any]:
        """Telegram kanalini kurar.

        Args:
            token: Bot token.
            chat_id: Chat ID.
            webhook_url: Webhook URL.

        Returns:
            Kurulum bilgisi.
        """
        try:
            if not token:
                return {
                    "configured": False,
                    "channel": "telegram",
                    "error": "token_gerekli",
                }

            config = {
                "channel": "telegram",
                "token": token,
                "chat_id": chat_id,
                "webhook_url": webhook_url,
                "enabled": True,
                "status": "configured",
            }
            self._channels["telegram"] = config
            self._stats["channels_configured"] += 1

            return {
                "configured": True,
                "channel": "telegram",
                "has_webhook": bool(webhook_url),
            }
        except Exception as e:
            logger.error("Telegram kurulum hatasi: %s", e)
            return {"configured": False, "error": str(e)}

    def setup_whatsapp(
        self,
        phone: str = "",
        api_key: str = "",
        business_id: str = "",
    ) -> dict[str, Any]:
        """WhatsApp kanalini kurar.

        Args:
            phone: Telefon numarasi.
            api_key: API anahtari.
            business_id: Is hesap ID.

        Returns:
            Kurulum bilgisi.
        """
        try:
            if not phone or not api_key:
                return {
                    "configured": False,
                    "channel": "whatsapp",
                    "error": "telefon_ve_api_key_gerekli",
                }

            config = {
                "channel": "whatsapp",
                "phone": phone,
                "api_key": api_key,
                "business_id": business_id,
                "enabled": True,
                "status": "configured",
            }
            self._channels["whatsapp"] = config
            self._stats["channels_configured"] += 1

            return {
                "configured": True,
                "channel": "whatsapp",
                "phone": phone,
            }
        except Exception as e:
            logger.error("WhatsApp kurulum hatasi: %s", e)
            return {"configured": False, "error": str(e)}

    def setup_discord(
        self,
        token: str = "",
        guild_id: str = "",
        channel_id: str = "",
    ) -> dict[str, Any]:
        """Discord kanalini kurar.

        Args:
            token: Bot token.
            guild_id: Sunucu ID.
            channel_id: Kanal ID.

        Returns:
            Kurulum bilgisi.
        """
        try:
            if not token:
                return {
                    "configured": False,
                    "channel": "discord",
                    "error": "token_gerekli",
                }

            config = {
                "channel": "discord",
                "token": token,
                "guild_id": guild_id,
                "channel_id": channel_id,
                "enabled": True,
                "status": "configured",
            }
            self._channels["discord"] = config
            self._stats["channels_configured"] += 1

            return {
                "configured": True,
                "channel": "discord",
                "guild_id": guild_id,
            }
        except Exception as e:
            logger.error("Discord kurulum hatasi: %s", e)
            return {"configured": False, "error": str(e)}

    def setup_slack(
        self,
        token: str = "",
        workspace: str = "",
        default_channel: str = "#general",
    ) -> dict[str, Any]:
        """Slack kanalini kurar.

        Args:
            token: Bot token.
            workspace: Calisma alani.
            default_channel: Varsayilan kanal.

        Returns:
            Kurulum bilgisi.
        """
        try:
            if not token:
                return {
                    "configured": False,
                    "channel": "slack",
                    "error": "token_gerekli",
                }

            config = {
                "channel": "slack",
                "token": token,
                "workspace": workspace,
                "default_channel": default_channel,
                "enabled": True,
                "status": "configured",
            }
            self._channels["slack"] = config
            self._stats["channels_configured"] += 1

            return {
                "configured": True,
                "channel": "slack",
                "workspace": workspace,
            }
        except Exception as e:
            logger.error("Slack kurulum hatasi: %s", e)
            return {"configured": False, "error": str(e)}

    def setup_webchat(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        cors_origins: list | None = None,
    ) -> dict[str, Any]:
        """Web chat kanalini kurar.

        Args:
            host: Host adresi.
            port: Port numarasi.
            cors_origins: CORS izinleri.

        Returns:
            Kurulum bilgisi.
        """
        try:
            if port < 1 or port > 65535:
                return {
                    "configured": False,
                    "channel": "webchat",
                    "error": "gecersiz_port",
                }

            config = {
                "channel": "webchat",
                "host": host,
                "port": port,
                "cors_origins": cors_origins or ["*"],
                "enabled": True,
                "status": "configured",
            }
            self._channels["webchat"] = config
            self._stats["channels_configured"] += 1

            return {
                "configured": True,
                "channel": "webchat",
                "host": host,
                "port": port,
            }
        except Exception as e:
            logger.error("WebChat kurulum hatasi: %s", e)
            return {"configured": False, "error": str(e)}

    def get_channel(
        self, name: str = ""
    ) -> dict[str, Any]:
        """Kanal getirir.

        Args:
            name: Kanal adi.

        Returns:
            Kanal bilgisi.
        """
        try:
            ch = self._channels.get(name)
            if not ch:
                return {"found": False, "error": "kanal_bulunamadi"}
            return {"found": True, **ch}
        except Exception as e:
            logger.error("Kanal getirme hatasi: %s", e)
            return {"found": False, "error": str(e)}

    def enable_channel(
        self, name: str = ""
    ) -> dict[str, Any]:
        """Kanali etkinlestirir.

        Args:
            name: Kanal adi.

        Returns:
            Etkinlestirme bilgisi.
        """
        try:
            ch = self._channels.get(name)
            if not ch:
                return {"enabled": False, "error": "kanal_bulunamadi"}
            ch["enabled"] = True
            ch["status"] = "enabled"
            self._stats["channels_enabled"] += 1
            return {"enabled": True, "channel": name}
        except Exception as e:
            logger.error("Kanal etkinlestirme hatasi: %s", e)
            return {"enabled": False, "error": str(e)}

    def disable_channel(
        self, name: str = ""
    ) -> dict[str, Any]:
        """Kanali devre disi birakir.

        Args:
            name: Kanal adi.

        Returns:
            Devre disi birakma bilgisi.
        """
        try:
            ch = self._channels.get(name)
            if not ch:
                return {"disabled": False, "error": "kanal_bulunamadi"}
            ch["enabled"] = False
            ch["status"] = "disabled"
            self._stats["channels_disabled"] += 1
            return {"disabled": True, "channel": name}
        except Exception as e:
            logger.error("Kanal devre disi birakma hatasi: %s", e)
            return {"disabled": False, "error": str(e)}

    def get_channels(
        self, only_enabled: bool = False
    ) -> list[dict]:
        """Kanal listesini dondurur.

        Args:
            only_enabled: Sadece aktif kanallar.

        Returns:
            Kanal listesi.
        """
        channels = list(self._channels.values())
        if only_enabled:
            channels = [c for c in channels if c.get("enabled")]
        return channels

    def validate_channel(
        self, name: str = ""
    ) -> dict[str, Any]:
        """Kanal yapilandirmasini dogrular.

        Args:
            name: Kanal adi.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            self._stats["validations_run"] += 1
            ch = self._channels.get(name)
            if not ch:
                return {
                    "valid": False,
                    "channel": name,
                    "error": "kanal_bulunamadi",
                }

            # Zorunlu alanlari kontrol et
            required = {
                "telegram": ["token"],
                "whatsapp": ["phone", "api_key"],
                "discord": ["token"],
                "slack": ["token"],
                "webchat": ["host", "port"],
            }
            required_fields = required.get(name, [])
            missing = [
                f for f in required_fields if not ch.get(f)
            ]

            valid = len(missing) == 0
            return {
                "valid": valid,
                "channel": name,
                "missing_fields": missing,
            }
        except Exception as e:
            logger.error("Kanal dogrulama hatasi: %s", e)
            return {"valid": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            enabled = sum(
                1 for c in self._channels.values() if c.get("enabled")
            )
            return {
                "retrieved": True,
                "channel_count": len(self._channels),
                "enabled_count": enabled,
                "supported_channels": self.SUPPORTED_CHANNELS,
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}
