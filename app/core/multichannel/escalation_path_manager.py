"""ATLAS Eskalasyon Yolu Yöneticisi modülü.

Eskalasyon kuralları, kanal eskalasyonu,
zaman aşımı yönetimi, yedek kanallar,
acil durum yolları.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EscalationPathManager:
    """Eskalasyon yolu yöneticisi.

    Eskalasyon yollarını yönetir.

    Attributes:
        _rules: Eskalasyon kuralları.
        _escalations: Eskalasyon kayıtları.
        _paths: Eskalasyon yolları.
    """

    def __init__(
        self,
        auto_escalate: bool = True,
        default_timeout: int = 300,
    ) -> None:
        """Yöneticiyi başlatır.

        Args:
            auto_escalate: Otomatik eskalasyon.
            default_timeout: Varsayılan zaman aşımı (sn).
        """
        self._rules: list[dict[str, Any]] = []
        self._escalations: list[
            dict[str, Any]
        ] = []
        self._paths: dict[
            str, list[str]
        ] = {
            "default": [
                "telegram", "whatsapp",
                "email", "voice",
            ],
            "emergency": [
                "voice", "sms", "telegram",
            ],
            "business": [
                "email", "telegram",
                "whatsapp",
            ],
        }
        self._fallbacks: dict[str, str] = {
            "telegram": "email",
            "whatsapp": "telegram",
            "email": "telegram",
            "voice": "sms",
            "sms": "telegram",
        }
        self._auto_escalate = auto_escalate
        self._default_timeout = default_timeout
        self._counter = 0
        self._stats = {
            "escalations": 0,
            "timeouts": 0,
            "emergency_paths": 0,
        }

        logger.info(
            "EscalationPathManager "
            "baslatildi",
        )

    def add_rule(
        self,
        name: str,
        condition: str,
        target_channel: str,
        priority: int = 5,
    ) -> dict[str, Any]:
        """Eskalasyon kuralı ekler.

        Args:
            name: Kural adı.
            condition: Koşul.
            target_channel: Hedef kanal.
            priority: Öncelik.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "name": name,
            "condition": condition,
            "target_channel": target_channel,
            "priority": priority,
            "active": True,
            "created_at": time.time(),
        }
        self._rules.append(rule)

        return {"name": name, "added": True}

    def escalate(
        self,
        from_channel: str,
        reason: str = "no_response",
        level: str = "medium",
        path: str = "default",
    ) -> dict[str, Any]:
        """Eskalasyon yapar.

        Args:
            from_channel: Kaynak kanal.
            reason: Neden.
            level: Eskalasyon seviyesi.
            path: Eskalasyon yolu.

        Returns:
            Eskalasyon bilgisi.
        """
        self._counter += 1
        eid = f"esc_{self._counter}"

        # Yol üzerinde sonraki kanalı bul
        path_channels = self._paths.get(
            path, self._paths["default"],
        )
        to_channel = self._get_next_channel(
            from_channel, path_channels,
        )

        if not to_channel:
            to_channel = self._fallbacks.get(
                from_channel, "telegram",
            )

        escalation = {
            "escalation_id": eid,
            "from_channel": from_channel,
            "to_channel": to_channel,
            "reason": reason,
            "level": level,
            "path": path,
            "status": "active",
            "timestamp": time.time(),
        }
        self._escalations.append(escalation)
        self._stats["escalations"] += 1

        return escalation

    def _get_next_channel(
        self,
        current: str,
        path: list[str],
    ) -> str | None:
        """Yoldaki sonraki kanalı bulur."""
        try:
            idx = path.index(current)
            if idx + 1 < len(path):
                return path[idx + 1]
        except ValueError:
            pass

        if path:
            return path[0]
        return None

    def handle_timeout(
        self,
        channel: str,
        wait_seconds: float,
    ) -> dict[str, Any]:
        """Zaman aşımı yönetir.

        Args:
            channel: Kanal.
            wait_seconds: Bekleme süresi.

        Returns:
            Yönetim bilgisi.
        """
        timed_out = (
            wait_seconds >= self._default_timeout
        )

        result = {
            "channel": channel,
            "wait_seconds": wait_seconds,
            "timed_out": timed_out,
            "timeout_threshold": (
                self._default_timeout
            ),
        }

        if timed_out and self._auto_escalate:
            esc = self.escalate(
                channel, reason="timeout",
            )
            result["escalated_to"] = esc[
                "to_channel"
            ]
            self._stats["timeouts"] += 1

        return result

    def get_fallback(
        self,
        channel: str,
    ) -> dict[str, Any]:
        """Yedek kanal getirir.

        Args:
            channel: Kanal.

        Returns:
            Yedek bilgisi.
        """
        fallback = self._fallbacks.get(
            channel, "telegram",
        )
        return {
            "channel": channel,
            "fallback": fallback,
        }

    def set_fallback(
        self,
        channel: str,
        fallback: str,
    ) -> dict[str, Any]:
        """Yedek kanal ayarlar.

        Args:
            channel: Kanal.
            fallback: Yedek kanal.

        Returns:
            Ayar bilgisi.
        """
        self._fallbacks[channel] = fallback
        return {
            "channel": channel,
            "fallback": fallback,
            "set": True,
        }

    def trigger_emergency(
        self,
        reason: str,
    ) -> dict[str, Any]:
        """Acil durum yolu tetikler.

        Args:
            reason: Neden.

        Returns:
            Tetikleme bilgisi.
        """
        path = self._paths.get(
            "emergency",
            ["voice", "sms"],
        )
        self._stats["emergency_paths"] += 1

        result = self.escalate(
            from_channel="system",
            reason=reason,
            level="critical",
            path="emergency",
        )
        result["emergency"] = True
        result["path_channels"] = path

        return result

    def add_path(
        self,
        name: str,
        channels: list[str],
    ) -> dict[str, Any]:
        """Eskalasyon yolu ekler.

        Args:
            name: Yol adı.
            channels: Kanal sırası.

        Returns:
            Ekleme bilgisi.
        """
        self._paths[name] = channels
        return {
            "path": name,
            "channels": channels,
            "added": True,
        }

    def get_escalations(
        self,
        level: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Eskalasyonları getirir.

        Args:
            level: Seviye filtresi.
            limit: Maks kayıt.

        Returns:
            Eskalasyon listesi.
        """
        results = self._escalations
        if level:
            results = [
                e for e in results
                if e.get("level") == level
            ]
        return list(results[-limit:])

    @property
    def escalation_count(self) -> int:
        """Eskalasyon sayısı."""
        return self._stats["escalations"]

    @property
    def rule_count(self) -> int:
        """Kural sayısı."""
        return len(self._rules)

    @property
    def path_count(self) -> int:
        """Yol sayısı."""
        return len(self._paths)
