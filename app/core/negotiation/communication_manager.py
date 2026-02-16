"""ATLAS Müzakere İletişim Yöneticisi modülü.

Mesaj oluşturma, ton yönetimi,
zamanlama optimizasyonu, kanal seçimi,
yanıt yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class NegotiationCommunicationManager:
    """Müzakere iletişim yöneticisi.

    Müzakere iletişimini yönetir.

    Attributes:
        _messages: Mesaj kayıtları.
        _channels: Kanal tercihleri.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._messages: list[
            dict[str, Any]
        ] = []
        self._channels: dict[
            str, str
        ] = {}
        self._responses: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "messages_crafted": 0,
            "responses_handled": 0,
            "timing_optimized": 0,
        }

        logger.info(
            "NegotiationCommunicationManager"
            " baslatildi",
        )

    def craft_message(
        self,
        content: str,
        tone: str = "professional",
        purpose: str = "inform",
        recipient: str = "",
        urgency: str = "normal",
    ) -> dict[str, Any]:
        """Mesaj oluşturur.

        Args:
            content: İçerik.
            tone: Ton.
            purpose: Amaç.
            recipient: Alıcı.
            urgency: Aciliyet.

        Returns:
            Mesaj bilgisi.
        """
        self._counter += 1
        mid = f"msg_{self._counter}"

        # Ton ayarı
        if tone == "firm":
            prefix = (
                "We need to clearly "
                "state that"
            )
        elif tone == "friendly":
            prefix = (
                "We're happy to share that"
            )
        elif tone == "urgent":
            prefix = (
                "This requires your "
                "immediate attention:"
            )
        else:
            prefix = ""

        formatted = (
            f"{prefix} {content}".strip()
            if prefix
            else content
        )

        message = {
            "message_id": mid,
            "content": formatted,
            "original": content,
            "tone": tone,
            "purpose": purpose,
            "recipient": recipient,
            "urgency": urgency,
            "status": "draft",
            "timestamp": time.time(),
        }
        self._messages.append(message)
        self._stats[
            "messages_crafted"
        ] += 1

        return {
            "message_id": mid,
            "content": formatted,
            "tone": tone,
            "purpose": purpose,
            "crafted": True,
        }

    def adjust_tone(
        self,
        message_id: str,
        new_tone: str,
    ) -> dict[str, Any]:
        """Ton ayarlar.

        Args:
            message_id: Mesaj ID.
            new_tone: Yeni ton.

        Returns:
            Ayarlama bilgisi.
        """
        for msg in self._messages:
            if (
                msg["message_id"]
                == message_id
            ):
                old_tone = msg["tone"]
                msg["tone"] = new_tone
                return {
                    "message_id": message_id,
                    "old_tone": old_tone,
                    "new_tone": new_tone,
                    "adjusted": True,
                }

        return {
            "message_id": message_id,
            "adjusted": False,
            "reason": "not_found",
        }

    def optimize_timing(
        self,
        recipient: str,
        message_type: str = "offer",
        timezone: str = "UTC+3",
    ) -> dict[str, Any]:
        """Zamanlama optimize eder.

        Args:
            recipient: Alıcı.
            message_type: Mesaj tipi.
            timezone: Saat dilimi.

        Returns:
            Zamanlama bilgisi.
        """
        # Mesaj tipine göre en iyi zaman
        timing_map = {
            "offer": {
                "best_day": "Tuesday",
                "best_time": "10:00",
                "avoid": "Friday_afternoon",
            },
            "counter": {
                "best_day": "Wednesday",
                "best_time": "14:00",
                "avoid": "Monday_morning",
            },
            "follow_up": {
                "best_day": "Thursday",
                "best_time": "11:00",
                "avoid": "weekend",
            },
            "closing": {
                "best_day": "Tuesday",
                "best_time": "09:00",
                "avoid": "end_of_day",
            },
        }

        timing = timing_map.get(
            message_type,
            {
                "best_day": "midweek",
                "best_time": "10:00",
                "avoid": "none",
            },
        )

        # Gecikme stratejisi
        if message_type == "counter":
            delay = "wait_24h"
        elif message_type == "closing":
            delay = "send_immediately"
        else:
            delay = "next_business_day"

        self._stats[
            "timing_optimized"
        ] += 1

        return {
            "recipient": recipient,
            "message_type": message_type,
            "timing": timing,
            "delay_strategy": delay,
            "timezone": timezone,
            "optimized": True,
        }

    def select_channel(
        self,
        recipient: str,
        message_type: str = "offer",
        formality: str = "formal",
    ) -> dict[str, Any]:
        """Kanal seçer.

        Args:
            recipient: Alıcı.
            message_type: Mesaj tipi.
            formality: Resmiyet.

        Returns:
            Kanal bilgisi.
        """
        # Kayıtlı tercih
        if recipient in self._channels:
            preferred = self._channels[
                recipient
            ]
        else:
            preferred = None

        # Varsayılan kanal mantığı
        if formality == "formal":
            channel = "email"
        elif formality == "semi_formal":
            channel = "video_call"
        else:
            channel = "messaging"

        # Mesaj tipine göre ayar
        if message_type == "closing":
            channel = "in_person"
            backup = "video_call"
        elif message_type == "offer":
            channel = "email"
            backup = "video_call"
        else:
            backup = "email"

        return {
            "recommended": (
                preferred or channel
            ),
            "backup": backup,
            "formality": formality,
            "recipient": recipient,
        }

    def handle_response(
        self,
        response_content: str,
        from_party: str,
        sentiment: str = "neutral",
        requires_action: bool = False,
    ) -> dict[str, Any]:
        """Yanıt yönetir.

        Args:
            response_content: Yanıt içeriği.
            from_party: Gönderen.
            sentiment: Duygu.
            requires_action: Aksiyon gerekiyor mu.

        Returns:
            Yanıt bilgisi.
        """
        self._counter += 1
        rid = f"resp_{self._counter}"

        # Duyguya göre öneri
        if sentiment == "positive":
            suggested_action = "proceed"
            priority = "normal"
        elif sentiment == "negative":
            suggested_action = (
                "reassess_approach"
            )
            priority = "high"
        elif sentiment == "urgent":
            suggested_action = (
                "respond_quickly"
            )
            priority = "critical"
        else:
            suggested_action = "review"
            priority = "normal"

        response = {
            "response_id": rid,
            "content": response_content,
            "from_party": from_party,
            "sentiment": sentiment,
            "requires_action": (
                requires_action
            ),
            "suggested_action": (
                suggested_action
            ),
            "priority": priority,
            "timestamp": time.time(),
        }
        self._responses.append(response)
        self._stats[
            "responses_handled"
        ] += 1

        return {
            "response_id": rid,
            "sentiment": sentiment,
            "suggested_action": (
                suggested_action
            ),
            "priority": priority,
            "handled": True,
        }

    def set_channel_preference(
        self,
        recipient: str,
        channel: str,
    ) -> dict[str, Any]:
        """Kanal tercihi ayarlar."""
        self._channels[recipient] = channel
        return {
            "recipient": recipient,
            "channel": channel,
            "set": True,
        }

    @property
    def message_count(self) -> int:
        """Mesaj sayısı."""
        return self._stats[
            "messages_crafted"
        ]

    @property
    def response_count(self) -> int:
        """Yanıt sayısı."""
        return self._stats[
            "responses_handled"
        ]
