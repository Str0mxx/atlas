"""ATLAS Geri Bildirim Toplayici modulu.

Acik geri bildirim, ortuk sinyaller,
kullanici tepkileri, sistem metrikleri, dis sinyaller.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Geri bildirim toplayici.

    Cesitli kaynaklardan geri bildirim toplar.

    Attributes:
        _feedback: Geri bildirim kayitlari.
        _signals: Sinyal kayitlari.
    """

    def __init__(self) -> None:
        """Geri bildirim toplayiciyi baslatir."""
        self._feedback: list[
            dict[str, Any]
        ] = []
        self._action_feedback: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._signals: list[
            dict[str, Any]
        ] = []
        self._metrics_history: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "explicit": 0,
            "implicit": 0,
            "system": 0,
            "external": 0,
        }

        logger.info(
            "FeedbackCollector baslatildi",
        )

    def collect_explicit(
        self,
        action_id: str,
        rating: float,
        comment: str = "",
        source: str = "user",
    ) -> dict[str, Any]:
        """Acik geri bildirim toplar.

        Args:
            action_id: Aksiyon ID.
            rating: Puanlama (-1.0 ile 1.0).
            comment: Yorum.
            source: Kaynak.

        Returns:
            Kayit bilgisi.
        """
        rating = max(-1.0, min(1.0, rating))

        fb = {
            "action_id": action_id,
            "type": "explicit",
            "rating": rating,
            "comment": comment,
            "source": source,
            "timestamp": time.time(),
        }

        self._feedback.append(fb)
        if action_id not in self._action_feedback:
            self._action_feedback[action_id] = []
        self._action_feedback[action_id].append(fb)
        self._stats["explicit"] += 1

        return {
            "action_id": action_id,
            "type": "explicit",
            "rating": rating,
            "recorded": True,
        }

    def collect_implicit(
        self,
        action_id: str,
        signal_type: str,
        value: float = 0.0,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ortuk sinyal toplar.

        Args:
            action_id: Aksiyon ID.
            signal_type: Sinyal tipi.
            value: Deger.
            context: Baglam.

        Returns:
            Kayit bilgisi.
        """
        fb = {
            "action_id": action_id,
            "type": "implicit",
            "signal_type": signal_type,
            "value": value,
            "context": context or {},
            "timestamp": time.time(),
        }

        self._feedback.append(fb)
        if action_id not in self._action_feedback:
            self._action_feedback[action_id] = []
        self._action_feedback[action_id].append(fb)
        self._stats["implicit"] += 1

        return {
            "action_id": action_id,
            "type": "implicit",
            "signal_type": signal_type,
            "recorded": True,
        }

    def collect_user_reaction(
        self,
        action_id: str,
        reaction: str,
        intensity: float = 0.5,
    ) -> dict[str, Any]:
        """Kullanici tepkisi toplar.

        Args:
            action_id: Aksiyon ID.
            reaction: Tepki (approve, reject, ignore, modify).
            intensity: Yogunluk (0.0-1.0).

        Returns:
            Kayit bilgisi.
        """
        rating_map = {
            "approve": 1.0,
            "reject": -1.0,
            "ignore": 0.0,
            "modify": 0.3,
        }
        rating = rating_map.get(reaction, 0.0) * intensity

        fb = {
            "action_id": action_id,
            "type": "explicit",
            "signal_type": "user_reaction",
            "reaction": reaction,
            "intensity": intensity,
            "rating": rating,
            "timestamp": time.time(),
        }

        self._feedback.append(fb)
        if action_id not in self._action_feedback:
            self._action_feedback[action_id] = []
        self._action_feedback[action_id].append(fb)
        self._stats["explicit"] += 1

        return {
            "action_id": action_id,
            "reaction": reaction,
            "rating": round(rating, 2),
            "recorded": True,
        }

    def collect_system_metric(
        self,
        metric_name: str,
        value: float,
        action_id: str = "",
    ) -> dict[str, Any]:
        """Sistem metrigi toplar.

        Args:
            metric_name: Metrik adi.
            value: Deger.
            action_id: Iliskili aksiyon ID.

        Returns:
            Kayit bilgisi.
        """
        entry = {
            "metric_name": metric_name,
            "value": value,
            "action_id": action_id,
            "timestamp": time.time(),
        }

        if metric_name not in self._metrics_history:
            self._metrics_history[metric_name] = []
        self._metrics_history[metric_name].append(
            entry,
        )

        if action_id:
            fb = {
                "action_id": action_id,
                "type": "system",
                "metric_name": metric_name,
                "value": value,
                "timestamp": time.time(),
            }
            self._feedback.append(fb)
            if action_id not in self._action_feedback:
                self._action_feedback[action_id] = []
            self._action_feedback[action_id].append(
                fb,
            )

        self._stats["system"] += 1

        return {
            "metric_name": metric_name,
            "value": value,
            "recorded": True,
        }

    def collect_external_signal(
        self,
        source: str,
        signal_type: str,
        data: dict[str, Any] | None = None,
        action_id: str = "",
    ) -> dict[str, Any]:
        """Dis sinyal toplar.

        Args:
            source: Kaynak.
            signal_type: Sinyal tipi.
            data: Veri.
            action_id: Iliskili aksiyon ID.

        Returns:
            Kayit bilgisi.
        """
        signal = {
            "source": source,
            "signal_type": signal_type,
            "data": data or {},
            "action_id": action_id,
            "timestamp": time.time(),
        }

        self._signals.append(signal)

        if action_id:
            fb = {
                "action_id": action_id,
                "type": "external",
                "source": source,
                "signal_type": signal_type,
                "data": data or {},
                "timestamp": time.time(),
            }
            self._feedback.append(fb)
            if action_id not in self._action_feedback:
                self._action_feedback[action_id] = []
            self._action_feedback[action_id].append(
                fb,
            )

        self._stats["external"] += 1

        return {
            "source": source,
            "signal_type": signal_type,
            "recorded": True,
        }

    def get_action_feedback(
        self,
        action_id: str,
    ) -> list[dict[str, Any]]:
        """Aksiyon geri bildirimlerini getirir.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Geri bildirim listesi.
        """
        return list(
            self._action_feedback.get(
                action_id, [],
            ),
        )

    def get_average_rating(
        self,
        action_id: str,
    ) -> float:
        """Ortalama puanlamayi hesaplar.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Ortalama puan.
        """
        fbs = self._action_feedback.get(
            action_id, [],
        )
        ratings = [
            fb["rating"]
            for fb in fbs
            if "rating" in fb
        ]
        if not ratings:
            return 0.0
        return round(
            sum(ratings) / len(ratings), 2,
        )

    def get_metric_history(
        self,
        metric_name: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Metrik gecmisini getirir.

        Args:
            metric_name: Metrik adi.
            limit: Limit.

        Returns:
            Gecmis kayitlari.
        """
        return list(
            self._metrics_history.get(
                metric_name, [],
            )[-limit:],
        )

    @property
    def feedback_count(self) -> int:
        """Geri bildirim sayisi."""
        return len(self._feedback)

    @property
    def signal_count(self) -> int:
        """Sinyal sayisi."""
        return len(self._signals)
