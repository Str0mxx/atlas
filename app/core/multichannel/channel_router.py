"""ATLAS Kanal Yönlendirici modülü.

Mesaj yönlendirme, kanal tespiti,
protokol yönetimi, yük dengeleme, failover.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ChannelRouter:
    """Kanal yönlendirici.

    Mesajları uygun kanallara yönlendirir.

    Attributes:
        _channels: Kanal yapılandırmaları.
        _routes: Yönlendirme kayıtları.
    """

    def __init__(self) -> None:
        """Yönlendiriciyi başlatır."""
        self._channels: dict[
            str, dict[str, Any]
        ] = {
            "telegram": {
                "enabled": True,
                "priority": 1,
                "protocol": "bot_api",
                "weight": 1.0,
            },
            "whatsapp": {
                "enabled": True,
                "priority": 2,
                "protocol": "cloud_api",
                "weight": 1.0,
            },
            "email": {
                "enabled": True,
                "priority": 3,
                "protocol": "smtp",
                "weight": 1.0,
            },
            "voice": {
                "enabled": True,
                "priority": 4,
                "protocol": "sip",
                "weight": 0.5,
            },
            "sms": {
                "enabled": True,
                "priority": 5,
                "protocol": "smpp",
                "weight": 0.5,
            },
        }
        self._routes: list[dict[str, Any]] = []
        self._failover_map: dict[
            str, list[str]
        ] = {
            "telegram": ["whatsapp", "email"],
            "whatsapp": ["telegram", "email"],
            "email": ["telegram", "sms"],
            "voice": ["telegram", "sms"],
            "sms": ["telegram", "email"],
        }
        self._counter = 0
        self._stats = {
            "messages_routed": 0,
            "failovers": 0,
        }

        logger.info("ChannelRouter baslatildi")

    def route_message(
        self,
        content: str,
        target_channel: str | None = None,
        sender: str = "",
        priority: int = 5,
    ) -> dict[str, Any]:
        """Mesaj yönlendirir.

        Args:
            content: Mesaj içeriği.
            target_channel: Hedef kanal.
            sender: Gönderici.
            priority: Öncelik.

        Returns:
            Yönlendirme bilgisi.
        """
        self._counter += 1
        rid = f"route_{self._counter}"

        channel = target_channel or self._detect_best_channel(priority)

        if channel not in self._channels:
            return {"error": "channel_not_found"}

        if not self._channels[channel]["enabled"]:
            channel = self._failover(channel)
            if not channel:
                return {"error": "no_available_channel"}

        route = {
            "route_id": rid,
            "content": content,
            "channel": channel,
            "sender": sender,
            "priority": priority,
            "protocol": self._channels[channel]["protocol"],
            "status": "routed",
            "timestamp": time.time(),
        }
        self._routes.append(route)
        self._stats["messages_routed"] += 1

        return route

    def detect_channel(
        self,
        source: str,
    ) -> dict[str, Any]:
        """Kanal tespit eder.

        Args:
            source: Kaynak tanımlayıcı.

        Returns:
            Kanal bilgisi.
        """
        source_lower = source.lower()

        if "telegram" in source_lower or source_lower.startswith("t_"):
            detected = "telegram"
        elif "whatsapp" in source_lower or source_lower.startswith("wa_"):
            detected = "whatsapp"
        elif "@" in source_lower:
            detected = "email"
        elif source_lower.startswith("+") or source_lower.isdigit():
            detected = "sms"
        elif "voice" in source_lower or "call" in source_lower:
            detected = "voice"
        else:
            detected = "telegram"

        return {
            "source": source,
            "detected_channel": detected,
            "protocol": self._channels.get(
                detected, {},
            ).get("protocol", "unknown"),
        }

    def _detect_best_channel(
        self,
        priority: int,
    ) -> str:
        """En iyi kanalı tespit eder.

        Args:
            priority: Öncelik.

        Returns:
            Kanal adı.
        """
        if priority >= 9:
            return "voice"
        if priority >= 7:
            return "telegram"

        enabled = [
            (n, c) for n, c in self._channels.items()
            if c["enabled"]
        ]
        if not enabled:
            return "telegram"

        enabled.sort(key=lambda x: x[1]["priority"])
        return enabled[0][0]

    def _failover(
        self,
        channel: str,
    ) -> str | None:
        """Failover yapar.

        Args:
            channel: Başarısız kanal.

        Returns:
            Alternatif kanal veya None.
        """
        alternatives = self._failover_map.get(
            channel, [],
        )
        for alt in alternatives:
            if (
                alt in self._channels
                and self._channels[alt]["enabled"]
            ):
                self._stats["failovers"] += 1
                return alt
        return None

    def configure_channel(
        self,
        name: str,
        enabled: bool = True,
        priority: int = 5,
        protocol: str = "custom",
        weight: float = 1.0,
    ) -> dict[str, Any]:
        """Kanal yapılandırır.

        Args:
            name: Kanal adı.
            enabled: Etkin mi.
            priority: Öncelik.
            protocol: Protokol.
            weight: Ağırlık.

        Returns:
            Yapılandırma bilgisi.
        """
        self._channels[name] = {
            "enabled": enabled,
            "priority": priority,
            "protocol": protocol,
            "weight": weight,
        }
        return {"channel": name, "configured": True}

    def set_failover(
        self,
        channel: str,
        alternatives: list[str],
    ) -> dict[str, Any]:
        """Failover ayarlar.

        Args:
            channel: Kanal.
            alternatives: Alternatifler.

        Returns:
            Ayar bilgisi.
        """
        self._failover_map[channel] = alternatives
        return {
            "channel": channel,
            "alternatives": alternatives,
        }

    def get_channel_status(self) -> dict[str, Any]:
        """Kanal durumlarını getirir.

        Returns:
            Durum bilgisi.
        """
        statuses = {}
        for name, config in self._channels.items():
            statuses[name] = {
                "enabled": config["enabled"],
                "protocol": config["protocol"],
            }
        return statuses

    def get_routes(
        self,
        channel: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Yönlendirmeleri getirir.

        Args:
            channel: Kanal filtresi.
            limit: Maks kayıt.

        Returns:
            Yönlendirme listesi.
        """
        results = self._routes
        if channel:
            results = [
                r for r in results
                if r.get("channel") == channel
            ]
        return list(results[-limit:])

    @property
    def channel_count(self) -> int:
        """Kanal sayısı."""
        return len(self._channels)

    @property
    def active_channel_count(self) -> int:
        """Aktif kanal sayısı."""
        return sum(
            1 for c in self._channels.values()
            if c["enabled"]
        )

    @property
    def routed_count(self) -> int:
        """Yönlendirilen mesaj sayısı."""
        return self._stats["messages_routed"]
