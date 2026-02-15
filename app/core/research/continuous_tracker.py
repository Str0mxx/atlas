"""ATLAS Sürekli Takipçi modülü.

Konu izleme, değişiklik tespiti,
uyarı üretme, trend takibi,
güncelleme bildirimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ContinuousTracker:
    """Sürekli takipçi.

    Konuları sürekli izler ve değişiklikleri
    bildirir.

    Attributes:
        _topics: İzlenen konular.
        _changes: Değişiklik kayıtları.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._topics: dict[
            str, dict[str, Any]
        ] = {}
        self._changes: list[
            dict[str, Any]
        ] = []
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._trends: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "topics_tracked": 0,
            "changes_detected": 0,
            "alerts_generated": 0,
            "trends_tracked": 0,
        }

        logger.info(
            "ContinuousTracker baslatildi",
        )

    def track_topic(
        self,
        topic: str,
        frequency: str = "daily",
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """Konu izlemeye alır.

        Args:
            topic: Konu adı.
            frequency: İzleme sıklığı.
            keywords: Anahtar kelimeler.

        Returns:
            İzleme bilgisi.
        """
        self._counter += 1
        tid = f"topic_{self._counter}"

        tracker = {
            "tracker_id": tid,
            "topic": topic,
            "frequency": frequency,
            "keywords": keywords or [],
            "active": True,
            "last_check": None,
            "change_count": 0,
            "created_at": time.time(),
        }
        self._topics[tid] = tracker
        self._trends[tid] = []
        self._stats["topics_tracked"] += 1

        return {
            "tracker_id": tid,
            "topic": topic,
            "frequency": frequency,
            "tracking": True,
        }

    def detect_change(
        self,
        tracker_id: str,
        new_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Değişiklik tespit eder.

        Args:
            tracker_id: Takip ID.
            new_data: Yeni veri.

        Returns:
            Değişiklik bilgisi.
        """
        topic = self._topics.get(tracker_id)
        if not topic:
            return {
                "error": "tracker_not_found",
            }

        change = {
            "tracker_id": tracker_id,
            "topic": topic["topic"],
            "change_type": new_data.get(
                "type", "update",
            ),
            "summary": new_data.get(
                "summary", "",
            ),
            "significance": new_data.get(
                "significance", "low",
            ),
            "data": new_data,
            "detected_at": time.time(),
        }
        self._changes.append(change)
        topic["change_count"] += 1
        topic["last_check"] = time.time()
        self._stats["changes_detected"] += 1

        # Trend kaydı
        self._trends[tracker_id].append({
            "change_type": change["change_type"],
            "significance": change[
                "significance"
            ],
            "timestamp": change["detected_at"],
        })

        # Yüksek önemli değişiklik = uyarı
        if new_data.get(
            "significance",
        ) in ("high", "critical"):
            self._generate_alert(change)

        return {
            "tracker_id": tracker_id,
            "change_detected": True,
            "change_type": change["change_type"],
            "significance": change[
                "significance"
            ],
        }

    def _generate_alert(
        self,
        change: dict[str, Any],
    ) -> None:
        """Uyarı üretir."""
        alert = {
            "tracker_id": change[
                "tracker_id"
            ],
            "topic": change["topic"],
            "message": (
                f"Significant change detected "
                f"in '{change['topic']}': "
                f"{change['summary']}"
            ),
            "significance": change[
                "significance"
            ],
            "timestamp": time.time(),
        }
        self._alerts.append(alert)
        self._stats["alerts_generated"] += 1

    def get_trends(
        self,
        tracker_id: str,
    ) -> dict[str, Any]:
        """Trend bilgisi getirir.

        Args:
            tracker_id: Takip ID.

        Returns:
            Trend bilgisi.
        """
        topic = self._topics.get(tracker_id)
        if not topic:
            return {
                "error": "tracker_not_found",
            }

        trend_data = self._trends.get(
            tracker_id, [],
        )

        # Önem dağılımı
        significance_counts: dict[
            str, int
        ] = {}
        for t in trend_data:
            sig = t["significance"]
            significance_counts[sig] = (
                significance_counts.get(sig, 0)
                + 1
            )

        self._stats["trends_tracked"] += 1

        return {
            "tracker_id": tracker_id,
            "topic": topic["topic"],
            "total_changes": len(trend_data),
            "significance_distribution": (
                significance_counts
            ),
            "trend_direction": (
                "increasing"
                if len(trend_data) > 3
                else "stable"
            ),
        }

    def stop_tracking(
        self,
        tracker_id: str,
    ) -> dict[str, Any]:
        """İzlemeyi durdurur.

        Args:
            tracker_id: Takip ID.

        Returns:
            Durdurma bilgisi.
        """
        topic = self._topics.get(tracker_id)
        if not topic:
            return {
                "error": "tracker_not_found",
            }

        topic["active"] = False
        return {
            "tracker_id": tracker_id,
            "topic": topic["topic"],
            "stopped": True,
        }

    def get_alerts(
        self,
        tracker_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Uyarıları getirir.

        Args:
            tracker_id: Takip filtresi.
            limit: Maks kayıt.

        Returns:
            Uyarı listesi.
        """
        results = self._alerts
        if tracker_id:
            results = [
                a for a in results
                if a["tracker_id"]
                == tracker_id
            ]
        return list(results[-limit:])

    def get_changes(
        self,
        tracker_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Değişiklikleri getirir.

        Args:
            tracker_id: Takip filtresi.
            limit: Maks kayıt.

        Returns:
            Değişiklik listesi.
        """
        results = self._changes
        if tracker_id:
            results = [
                c for c in results
                if c["tracker_id"]
                == tracker_id
            ]
        return list(results[-limit:])

    def get_tracked_topics(
        self,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """İzlenen konuları getirir.

        Args:
            active_only: Sadece aktif.

        Returns:
            Konu listesi.
        """
        results = list(self._topics.values())
        if active_only:
            results = [
                t for t in results
                if t["active"]
            ]
        return results

    @property
    def topic_count(self) -> int:
        """Konu sayısı."""
        return self._stats["topics_tracked"]

    @property
    def change_count(self) -> int:
        """Değişiklik sayısı."""
        return self._stats["changes_detected"]

    @property
    def alert_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats["alerts_generated"]
