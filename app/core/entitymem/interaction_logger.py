"""ATLAS Etkileşim Kaydedici modulu.

Etkileşim loglama, kanal takibi,
zaman damgası, bağlam yakalama, duygu etiketleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class InteractionLogger:
    """Etkileşim kaydedici.

    Tüm varlık etkileşimlerini kaydeder.

    Attributes:
        _interactions: Etkileşim kayıtları.
        _channels: Kanal istatistikleri.
    """

    def __init__(
        self,
        max_stored: int = 10000,
    ) -> None:
        """Kaydediciyi başlatır.

        Args:
            max_stored: Maks kayıt sayısı.
        """
        self._interactions: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._channels: dict[str, int] = {}
        self._max_stored = max_stored
        self._counter = 0
        self._stats = {
            "logged": 0,
        }

        logger.info(
            "InteractionLogger baslatildi",
        )

    def log_interaction(
        self,
        entity_id: str,
        channel: str,
        content: str,
        context: dict[str, Any] | None = None,
        sentiment: float = 0.0,
    ) -> dict[str, Any]:
        """Etkileşim kaydeder.

        Args:
            entity_id: Varlık ID.
            channel: Kanal.
            content: İçerik.
            context: Bağlam.
            sentiment: Duygu puanı (-1 ile 1).

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        iid = f"int_{self._counter}"

        record = {
            "interaction_id": iid,
            "entity_id": entity_id,
            "channel": channel,
            "content": content,
            "context": context or {},
            "sentiment": max(
                -1.0, min(1.0, sentiment),
            ),
            "timestamp": time.time(),
        }

        if entity_id not in self._interactions:
            self._interactions[entity_id] = []

        self._interactions[entity_id].append(
            record,
        )

        # Limit kontrolü
        if (
            len(self._interactions[entity_id])
            > self._max_stored
        ):
            self._interactions[
                entity_id
            ] = self._interactions[entity_id][
                -self._max_stored :
            ]

        # Kanal istatistik
        self._channels[channel] = (
            self._channels.get(channel, 0) + 1
        )
        self._stats["logged"] += 1

        return {
            "interaction_id": iid,
            "entity_id": entity_id,
            "channel": channel,
            "logged": True,
        }

    def get_interactions(
        self,
        entity_id: str,
        limit: int = 50,
        channel: str | None = None,
    ) -> list[dict[str, Any]]:
        """Etkileşimleri getirir.

        Args:
            entity_id: Varlık ID.
            limit: Maks kayıt.
            channel: Kanal filtresi.

        Returns:
            Etkileşim listesi.
        """
        ints = self._interactions.get(
            entity_id, [],
        )
        if channel:
            ints = [
                i for i in ints
                if i["channel"] == channel
            ]
        return list(ints[-limit:])

    def get_channel_stats(
        self,
    ) -> dict[str, Any]:
        """Kanal istatistikleri getirir.

        Returns:
            Kanal dağılımı.
        """
        total = sum(self._channels.values())
        distribution = {}
        if total > 0:
            distribution = {
                ch: round(cnt / total * 100, 1)
                for ch, cnt in (
                    self._channels.items()
                )
            }

        return {
            "channels": dict(self._channels),
            "distribution": distribution,
            "total": total,
        }

    def get_sentiment_summary(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Duygu özeti getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Duygu bilgisi.
        """
        ints = self._interactions.get(
            entity_id, [],
        )
        if not ints:
            return {
                "entity_id": entity_id,
                "avg_sentiment": 0.0,
                "interaction_count": 0,
            }

        sentiments = [
            i["sentiment"] for i in ints
        ]
        avg = round(
            sum(sentiments) / len(sentiments),
            3,
        )
        positive = sum(
            1 for s in sentiments if s > 0.2
        )
        negative = sum(
            1 for s in sentiments if s < -0.2
        )
        neutral = (
            len(sentiments)
            - positive
            - negative
        )

        return {
            "entity_id": entity_id,
            "avg_sentiment": avg,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "interaction_count": len(ints),
        }

    def get_recent(
        self,
        entity_id: str,
        count: int = 5,
    ) -> list[dict[str, Any]]:
        """Son etkileşimleri getirir.

        Args:
            entity_id: Varlık ID.
            count: Kayıt sayısı.

        Returns:
            Son etkileşimler.
        """
        ints = self._interactions.get(
            entity_id, [],
        )
        return list(ints[-count:])

    def entity_interaction_count(
        self,
        entity_id: str,
    ) -> int:
        """Varlık etkileşim sayısı.

        Args:
            entity_id: Varlık ID.

        Returns:
            Etkileşim sayısı.
        """
        return len(
            self._interactions.get(
                entity_id, [],
            ),
        )

    @property
    def interaction_count(self) -> int:
        """Toplam etkileşim sayısı."""
        return self._stats["logged"]

    @property
    def channel_count(self) -> int:
        """Kanal sayısı."""
        return len(self._channels)
