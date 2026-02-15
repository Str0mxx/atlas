"""ATLAS Hiz Analitigi modulu.

Kullanim kaliplari, zirve tespiti,
trend analizi, kapasite planlama, raporlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RateAnalytics:
    """Hiz analitigi.

    Hiz siniri kullanim verileri analiz eder.

    Attributes:
        _events: Olay kayitlari.
        _hourly: Saatlik istatistikler.
    """

    def __init__(
        self,
        max_events: int = 10000,
    ) -> None:
        """Hiz analitigini baslatir.

        Args:
            max_events: Maks olay kaydi.
        """
        self._events: list[
            dict[str, Any]
        ] = []
        self._hourly: dict[
            int, dict[str, int]
        ] = {}
        self._subject_stats: dict[
            str, dict[str, Any]
        ] = {}
        self._endpoint_stats: dict[
            str, dict[str, Any]
        ] = {}
        self._max_events = max_events
        self._stats = {
            "total_requests": 0,
            "allowed": 0,
            "rejected": 0,
            "peak_rpm": 0,
        }

        logger.info(
            "RateAnalytics baslatildi",
        )

    def record_request(
        self,
        subject_id: str,
        endpoint: str = "",
        allowed: bool = True,
        latency_ms: float = 0,
    ) -> dict[str, Any]:
        """Istegi kaydeder.

        Args:
            subject_id: Konu ID.
            endpoint: Endpoint.
            allowed: Izin verildi mi.
            latency_ms: Gecikme (ms).

        Returns:
            Kayit bilgisi.
        """
        now = time.time()
        event = {
            "subject_id": subject_id,
            "endpoint": endpoint,
            "allowed": allowed,
            "latency_ms": latency_ms,
            "timestamp": now,
        }

        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[
                -self._max_events:
            ]

        # Genel istatistikler
        self._stats["total_requests"] += 1
        if allowed:
            self._stats["allowed"] += 1
        else:
            self._stats["rejected"] += 1

        # Saatlik
        hour = int(now / 3600)
        if hour not in self._hourly:
            self._hourly[hour] = {
                "total": 0,
                "allowed": 0,
                "rejected": 0,
            }
        self._hourly[hour]["total"] += 1
        if allowed:
            self._hourly[hour]["allowed"] += 1
        else:
            self._hourly[hour]["rejected"] += 1

        # Konu istatistikleri
        if subject_id not in self._subject_stats:
            self._subject_stats[subject_id] = {
                "total": 0,
                "allowed": 0,
                "rejected": 0,
                "first_seen": now,
                "last_seen": now,
            }
        s = self._subject_stats[subject_id]
        s["total"] += 1
        if allowed:
            s["allowed"] += 1
        else:
            s["rejected"] += 1
        s["last_seen"] = now

        # Endpoint istatistikleri
        if endpoint:
            if endpoint not in self._endpoint_stats:
                self._endpoint_stats[endpoint] = {
                    "total": 0,
                    "allowed": 0,
                    "rejected": 0,
                }
            e = self._endpoint_stats[endpoint]
            e["total"] += 1
            if allowed:
                e["allowed"] += 1
            else:
                e["rejected"] += 1

        return {
            "recorded": True,
            "total": self._stats[
                "total_requests"
            ],
        }

    def get_usage_pattern(
        self,
        subject_id: str,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Kullanim kalibini getirir.

        Args:
            subject_id: Konu ID.
            hours: Saat araligi.

        Returns:
            Kalip bilgisi.
        """
        cutoff = time.time() - (hours * 3600)
        events = [
            e for e in self._events
            if e["subject_id"] == subject_id
            and e["timestamp"] > cutoff
        ]

        if not events:
            return {
                "subject_id": subject_id,
                "requests": 0,
                "pattern": "inactive",
            }

        total = len(events)
        allowed = sum(
            1 for e in events if e["allowed"]
        )
        rejected = total - allowed

        # Zaman dagilimi
        hourly_counts: dict[int, int] = {}
        for e in events:
            h = int(e["timestamp"] / 3600)
            hourly_counts[h] = (
                hourly_counts.get(h, 0) + 1
            )

        peak = max(
            hourly_counts.values(),
        ) if hourly_counts else 0
        avg = (
            total / max(len(hourly_counts), 1)
        )

        pattern = "steady"
        if peak > avg * 3:
            pattern = "bursty"
        elif rejected > total * 0.3:
            pattern = "aggressive"

        return {
            "subject_id": subject_id,
            "requests": total,
            "allowed": allowed,
            "rejected": rejected,
            "peak_hourly": peak,
            "avg_hourly": round(avg, 1),
            "pattern": pattern,
        }

    def detect_peaks(
        self,
        threshold_multiplier: float = 2.0,
    ) -> list[dict[str, Any]]:
        """Zirveleri tespit eder.

        Args:
            threshold_multiplier: Esik carpani.

        Returns:
            Zirve listesi.
        """
        if not self._hourly:
            return []

        totals = [
            h["total"]
            for h in self._hourly.values()
        ]
        avg = sum(totals) / max(len(totals), 1)
        threshold = avg * threshold_multiplier

        peaks = []
        for hour, data in self._hourly.items():
            if data["total"] > threshold:
                peaks.append({
                    "hour": hour,
                    "total": data["total"],
                    "threshold": round(
                        threshold, 1,
                    ),
                    "multiplier": round(
                        data["total"]
                        / max(avg, 1),
                        1,
                    ),
                })

        return peaks

    def analyze_trends(
        self,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Trend analizi yapar.

        Args:
            hours: Analiz periyodu.

        Returns:
            Trend bilgisi.
        """
        now = time.time()
        current_hour = int(now / 3600)

        recent: list[int] = []
        older: list[int] = []

        half = hours // 2

        for h in range(hours):
            hour_key = current_hour - h
            data = self._hourly.get(hour_key)
            count = data["total"] if data else 0

            if h < half:
                recent.append(count)
            else:
                older.append(count)

        recent_avg = (
            sum(recent) / max(len(recent), 1)
        )
        older_avg = (
            sum(older) / max(len(older), 1)
        )

        if older_avg == 0:
            trend = "new" if recent_avg > 0 else "flat"
            change = 0.0
        else:
            change = (
                (recent_avg - older_avg)
                / older_avg
                * 100
            )
            if change > 20:
                trend = "increasing"
            elif change < -20:
                trend = "decreasing"
            else:
                trend = "stable"

        return {
            "trend": trend,
            "change_pct": round(change, 1),
            "recent_avg": round(recent_avg, 1),
            "older_avg": round(older_avg, 1),
            "hours_analyzed": hours,
        }

    def capacity_report(
        self,
    ) -> dict[str, Any]:
        """Kapasite raporu olusturur.

        Returns:
            Kapasite bilgisi.
        """
        total = self._stats["total_requests"]
        rejected = self._stats["rejected"]

        # Saatlik zirve
        peak_hourly = 0
        for data in self._hourly.values():
            if data["total"] > peak_hourly:
                peak_hourly = data["total"]

        rejection_rate = (
            rejected / max(total, 1) * 100
        )

        return {
            "total_requests": total,
            "rejection_rate": round(
                rejection_rate, 1,
            ),
            "peak_hourly": peak_hourly,
            "unique_subjects": len(
                self._subject_stats,
            ),
            "unique_endpoints": len(
                self._endpoint_stats,
            ),
            "recommendation": (
                self._capacity_recommendation(
                    rejection_rate, peak_hourly,
                )
            ),
        }

    def get_top_subjects(
        self,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """En cok istek yapan konulari getirir.

        Args:
            limit: Limit.

        Returns:
            Konu listesi.
        """
        subjects = [
            {"subject_id": sid, **stats}
            for sid, stats
            in self._subject_stats.items()
        ]
        subjects.sort(
            key=lambda s: s["total"],
            reverse=True,
        )
        return subjects[:limit]

    def get_top_endpoints(
        self,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """En cok istek alan endpoint'leri getirir.

        Args:
            limit: Limit.

        Returns:
            Endpoint listesi.
        """
        endpoints = [
            {"endpoint": ep, **stats}
            for ep, stats
            in self._endpoint_stats.items()
        ]
        endpoints.sort(
            key=lambda e: e["total"],
            reverse=True,
        )
        return endpoints[:limit]

    def get_report(self) -> dict[str, Any]:
        """Genel rapor olusturur.

        Returns:
            Rapor.
        """
        return {
            "total_requests": self._stats[
                "total_requests"
            ],
            "allowed": self._stats["allowed"],
            "rejected": self._stats["rejected"],
            "unique_subjects": len(
                self._subject_stats,
            ),
            "unique_endpoints": len(
                self._endpoint_stats,
            ),
            "hours_tracked": len(self._hourly),
            "timestamp": time.time(),
        }

    def _capacity_recommendation(
        self,
        rejection_rate: float,
        peak: int,
    ) -> str:
        """Kapasite onerisi.

        Args:
            rejection_rate: Red orani.
            peak: Zirve.

        Returns:
            Oneri metni.
        """
        if rejection_rate > 20:
            return "increase_limits"
        if rejection_rate > 10:
            return "monitor_closely"
        if peak > 1000:
            return "consider_scaling"
        return "healthy"

    @property
    def event_count(self) -> int:
        """Olay sayisi."""
        return len(self._events)

    @property
    def subject_count(self) -> int:
        """Konu sayisi."""
        return len(self._subject_stats)

    @property
    def endpoint_count(self) -> int:
        """Endpoint sayisi."""
        return len(self._endpoint_stats)
