"""ATLAS Gelir Takipçisi modülü.

Gelir izleme, akış dağılımı,
trend analizi, anomali tespiti,
hedef takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RevenueTracker:
    """Gelir takipçisi.

    Gelir akışlarını izler ve analiz eder.

    Attributes:
        _records: Gelir kayıtları.
        _goals: Hedef kayıtları.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._records: list[
            dict[str, Any]
        ] = []
        self._goals: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "records_tracked": 0,
            "anomalies_detected": 0,
        }

        logger.info(
            "RevenueTracker baslatildi",
        )

    def monitor_revenue(
        self,
        stream: str = "product",
        amount: float = 0.0,
        period: str = "",
    ) -> dict[str, Any]:
        """Gelir izler.

        Args:
            stream: Gelir akışı.
            amount: Miktar.
            period: Dönem.

        Returns:
            İzleme bilgisi.
        """
        self._counter += 1
        rid = f"rev_{self._counter}"

        record = {
            "record_id": rid,
            "stream": stream,
            "amount": amount,
            "period": period,
            "timestamp": time.time(),
        }
        self._records.append(record)
        self._stats[
            "records_tracked"
        ] += 1

        return {
            "record_id": rid,
            "stream": stream,
            "amount": amount,
            "monitored": True,
        }

    def breakdown_streams(
        self,
    ) -> dict[str, Any]:
        """Akış dağılımı verir.

        Returns:
            Dağılım bilgisi.
        """
        streams: dict[str, float] = {}
        for r in self._records:
            s = r["stream"]
            streams[s] = (
                streams.get(s, 0)
                + r["amount"]
            )

        total = sum(streams.values())
        pcts = {
            s: round(
                (v / total) * 100, 1,
            )
            if total > 0
            else 0.0
            for s, v in streams.items()
        }

        return {
            "streams": streams,
            "percentages": pcts,
            "total": total,
            "breakdown": True,
        }

    def analyze_trend(
        self,
        stream: str | None = None,
    ) -> dict[str, Any]:
        """Trend analizi yapar.

        Args:
            stream: Gelir akışı filtresi.

        Returns:
            Trend bilgisi.
        """
        filtered = [
            r for r in self._records
            if stream is None
            or r["stream"] == stream
        ]

        if len(filtered) < 2:
            return {
                "trend": "insufficient_data",
                "data_points": len(filtered),
                "analyzed": True,
            }

        amounts = [
            r["amount"] for r in filtered
        ]
        first_half = amounts[
            : len(amounts) // 2
        ]
        second_half = amounts[
            len(amounts) // 2 :
        ]

        avg_first = (
            sum(first_half)
            / len(first_half)
        )
        avg_second = (
            sum(second_half)
            / len(second_half)
        )

        if avg_second > avg_first * 1.05:
            trend = "growing"
        elif avg_second < avg_first * 0.95:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "avg_early": round(
                avg_first, 2,
            ),
            "avg_recent": round(
                avg_second, 2,
            ),
            "data_points": len(filtered),
            "analyzed": True,
        }

    def detect_anomaly(
        self,
        amount: float = 0.0,
        stream: str = "product",
    ) -> dict[str, Any]:
        """Anomali tespiti yapar.

        Args:
            amount: Kontrol miktarı.
            stream: Gelir akışı.

        Returns:
            Tespit bilgisi.
        """
        stream_records = [
            r["amount"]
            for r in self._records
            if r["stream"] == stream
        ]

        if not stream_records:
            return {
                "is_anomaly": False,
                "reason": "no_baseline",
                "detected": True,
            }

        avg = (
            sum(stream_records)
            / len(stream_records)
        )
        std = (
            (
                sum(
                    (x - avg) ** 2
                    for x in stream_records
                )
                / len(stream_records)
            )
            ** 0.5
            if len(stream_records) > 1
            else avg * 0.1
        )

        z_score = (
            abs(amount - avg) / std
            if std > 0
            else 0
        )
        is_anomaly = z_score > 2.0

        if is_anomaly:
            self._stats[
                "anomalies_detected"
            ] += 1

        return {
            "amount": amount,
            "stream": stream,
            "avg": round(avg, 2),
            "z_score": round(z_score, 2),
            "is_anomaly": is_anomaly,
            "detected": True,
        }

    def track_goal(
        self,
        goal_name: str,
        target: float = 0.0,
        current: float = 0.0,
    ) -> dict[str, Any]:
        """Hedef takibi yapar.

        Args:
            goal_name: Hedef adı.
            target: Hedef miktar.
            current: Güncel miktar.

        Returns:
            Takip bilgisi.
        """
        progress = (
            (current / target) * 100
            if target > 0
            else 0.0
        )
        on_track = progress >= 80

        self._goals[goal_name] = {
            "target": target,
            "current": current,
            "progress_pct": round(
                progress, 1,
            ),
            "on_track": on_track,
        }

        return {
            "goal_name": goal_name,
            "target": target,
            "current": current,
            "progress_pct": round(
                progress, 1,
            ),
            "on_track": on_track,
            "tracked": True,
        }

    @property
    def record_count(self) -> int:
        """Kayıt sayısı."""
        return self._stats[
            "records_tracked"
        ]

    @property
    def anomaly_count(self) -> int:
        """Anomali sayısı."""
        return self._stats[
            "anomalies_detected"
        ]
