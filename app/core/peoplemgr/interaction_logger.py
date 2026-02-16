"""ATLAS Etkileşim Kaydedici modülü.

Tüm temas noktaları, kanal takibi,
içerik kaydı, duygu yakalama,
zaman çizelgesi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PeopleInteractionLogger:
    """Etkileşim kaydedici.

    Kişi etkileşimlerini kaydeder.

    Attributes:
        _interactions: Etkileşim kayıtları.
        _timelines: Zaman çizelgeleri.
    """

    def __init__(self) -> None:
        """Kaydediciyi başlatır."""
        self._interactions: list[
            dict[str, Any]
        ] = []
        self._timelines: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "interactions_logged": 0,
            "channels_used": set(),
            "sentiments_captured": 0,
        }

        logger.info(
            "PeopleInteractionLogger "
            "baslatildi",
        )

    def log_interaction(
        self,
        contact_id: str,
        channel: str = "other",
        content: str = "",
        sentiment: str = "neutral",
        direction: str = "outbound",
        metadata: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Etkileşim kaydeder.

        Args:
            contact_id: Kişi ID.
            channel: Kanal.
            content: İçerik.
            sentiment: Duygu.
            direction: Yön.
            metadata: Ek bilgi.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        iid = f"int_{self._counter}"

        interaction = {
            "interaction_id": iid,
            "contact_id": contact_id,
            "channel": channel,
            "content": content,
            "sentiment": sentiment,
            "direction": direction,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        self._interactions.append(
            interaction,
        )

        # Zaman çizelgesine ekle
        if (
            contact_id
            not in self._timelines
        ):
            self._timelines[
                contact_id
            ] = []
        self._timelines[
            contact_id
        ].append(interaction)

        self._stats[
            "interactions_logged"
        ] += 1
        self._stats[
            "channels_used"
        ].add(channel)
        if sentiment != "neutral":
            self._stats[
                "sentiments_captured"
            ] += 1

        return {
            "interaction_id": iid,
            "contact_id": contact_id,
            "channel": channel,
            "logged": True,
        }

    def get_channel_stats(
        self,
        contact_id: str = "",
    ) -> dict[str, Any]:
        """Kanal istatistikleri döndürür.

        Args:
            contact_id: Kişi ID (opsiyonel).

        Returns:
            Kanal bilgisi.
        """
        interactions = self._interactions
        if contact_id:
            interactions = [
                i for i in interactions
                if i["contact_id"]
                == contact_id
            ]

        channels: dict[str, int] = {}
        for i in interactions:
            ch = i["channel"]
            channels[ch] = (
                channels.get(ch, 0) + 1
            )

        primary = max(
            channels, key=channels.get,
        ) if channels else ""

        return {
            "channels": channels,
            "primary_channel": primary,
            "total_interactions": len(
                interactions,
            ),
        }

    def get_content_log(
        self,
        contact_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """İçerik logunu döndürür.

        Args:
            contact_id: Kişi ID.
            limit: Limit.

        Returns:
            İçerik listesi.
        """
        timeline = self._timelines.get(
            contact_id, [],
        )
        return [
            {
                "interaction_id": i[
                    "interaction_id"
                ],
                "channel": i["channel"],
                "content": i["content"],
                "sentiment": i["sentiment"],
                "timestamp": i["timestamp"],
            }
            for i in timeline[-limit:]
        ]

    def capture_sentiment(
        self,
        contact_id: str,
        sentiment: str,
        context: str = "",
    ) -> dict[str, Any]:
        """Duygu yakalar.

        Args:
            contact_id: Kişi ID.
            sentiment: Duygu.
            context: Bağlam.

        Returns:
            Duygu bilgisi.
        """
        return self.log_interaction(
            contact_id=contact_id,
            channel="sentiment_capture",
            content=context,
            sentiment=sentiment,
        )

    def get_timeline(
        self,
        contact_id: str,
    ) -> list[dict[str, Any]]:
        """Zaman çizelgesi döndürür.

        Args:
            contact_id: Kişi ID.

        Returns:
            Zaman çizelgesi.
        """
        return self._timelines.get(
            contact_id, [],
        )

    def get_last_interaction(
        self,
        contact_id: str,
    ) -> dict[str, Any] | None:
        """Son etkileşimi döndürür."""
        timeline = self._timelines.get(
            contact_id, [],
        )
        return timeline[-1] if timeline else None

    @property
    def interaction_count(self) -> int:
        """Etkileşim sayısı."""
        return self._stats[
            "interactions_logged"
        ]

    @property
    def channel_count(self) -> int:
        """Kullanılan kanal sayısı."""
        return len(
            self._stats["channels_used"],
        )
