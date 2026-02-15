"""ATLAS Periyodik Raporlayıcı modülü.

Günlük özetler, haftalık raporlar,
özel zamanlamalar, anahtar metrikler,
trend vurguları.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PeriodicReporter:
    """Periyodik raporlayıcı.

    Zamanlanmış raporlar üretir.

    Attributes:
        _reports: Rapor kayıtları.
        _schedules: Zamanlama kayıtları.
        _metrics_history: Metrik geçmişi.
    """

    def __init__(self) -> None:
        """Raporlayıcıyı başlatır."""
        self._reports: list[
            dict[str, Any]
        ] = []
        self._schedules: list[
            dict[str, Any]
        ] = []
        self._metrics_history: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "reports_generated": 0,
            "schedules_active": 0,
        }

        logger.info(
            "PeriodicReporter baslatildi",
        )

    def generate_daily_summary(
        self,
        metrics: dict[str, Any],
        events: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Günlük özet üretir.

        Args:
            metrics: Günlük metrikler.
            events: Önemli olaylar.

        Returns:
            Özet bilgisi.
        """
        self._counter += 1
        rid = f"daily_{self._counter}"

        # Metrik geçmişine ekle
        self._metrics_history.append({
            "type": "daily",
            "metrics": metrics,
            "timestamp": time.time(),
        })

        # Trend hesaplama
        trends = self._calculate_trends(
            metrics,
        )

        report = {
            "report_id": rid,
            "report_type": "daily",
            "metrics": metrics,
            "events": events or [],
            "event_count": len(events or []),
            "trends": trends,
            "generated_at": time.time(),
        }
        self._reports.append(report)
        self._stats["reports_generated"] += 1

        return report

    def generate_weekly_report(
        self,
        metrics: dict[str, Any],
        highlights: list[str] | None = None,
        issues: list[str] | None = None,
    ) -> dict[str, Any]:
        """Haftalık rapor üretir.

        Args:
            metrics: Haftalık metrikler.
            highlights: Önemli gelişmeler.
            issues: Sorunlar.

        Returns:
            Rapor bilgisi.
        """
        self._counter += 1
        rid = f"weekly_{self._counter}"

        self._metrics_history.append({
            "type": "weekly",
            "metrics": metrics,
            "timestamp": time.time(),
        })

        trends = self._calculate_trends(
            metrics,
        )

        report = {
            "report_id": rid,
            "report_type": "weekly",
            "metrics": metrics,
            "highlights": highlights or [],
            "issues": issues or [],
            "trends": trends,
            "generated_at": time.time(),
        }
        self._reports.append(report)
        self._stats["reports_generated"] += 1

        return report

    def generate_custom_report(
        self,
        title: str,
        frequency: str,
        metrics: dict[str, Any],
        sections: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Özel rapor üretir.

        Args:
            title: Rapor başlığı.
            frequency: Sıklık.
            metrics: Metrikler.
            sections: Ek bölümler.

        Returns:
            Rapor bilgisi.
        """
        self._counter += 1
        rid = f"custom_{self._counter}"

        report = {
            "report_id": rid,
            "report_type": "custom",
            "title": title,
            "frequency": frequency,
            "metrics": metrics,
            "sections": sections or [],
            "generated_at": time.time(),
        }
        self._reports.append(report)
        self._stats["reports_generated"] += 1

        return report

    def _calculate_trends(
        self,
        current: dict[str, Any],
    ) -> dict[str, str]:
        """Trend hesaplar.

        Args:
            current: Güncel metrikler.

        Returns:
            Metrik-trend eşlemesi.
        """
        trends: dict[str, str] = {}
        if len(self._metrics_history) < 2:
            return trends

        prev = self._metrics_history[-2].get(
            "metrics", {},
        )

        for key, val in current.items():
            if not isinstance(
                val, (int, float),
            ):
                continue
            prev_val = prev.get(key)
            if prev_val is None or not isinstance(
                prev_val, (int, float),
            ):
                continue

            if val > prev_val * 1.1:
                trends[key] = "increasing"
            elif val < prev_val * 0.9:
                trends[key] = "decreasing"
            else:
                trends[key] = "stable"

        return trends

    def add_schedule(
        self,
        name: str,
        frequency: str = "daily",
        hour: int = 9,
        day_of_week: int | None = None,
    ) -> dict[str, Any]:
        """Zamanlama ekler.

        Args:
            name: Zamanlama adı.
            frequency: Sıklık.
            hour: Çalışma saati.
            day_of_week: Haftanın günü (0=Pzt).

        Returns:
            Zamanlama bilgisi.
        """
        schedule = {
            "name": name,
            "frequency": frequency,
            "hour": hour,
            "day_of_week": day_of_week,
            "active": True,
            "created_at": time.time(),
        }
        self._schedules.append(schedule)
        self._stats["schedules_active"] += 1

        return {
            "name": name,
            "scheduled": True,
            "frequency": frequency,
        }

    def track_key_metrics(
        self,
        metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Anahtar metrikleri takip eder.

        Args:
            metrics: Metrikler.

        Returns:
            Takip bilgisi.
        """
        self._metrics_history.append({
            "type": "tracking",
            "metrics": metrics,
            "timestamp": time.time(),
        })

        return {
            "tracked": True,
            "metric_count": len(metrics),
            "history_length": len(
                self._metrics_history,
            ),
        }

    def get_trend_highlights(
        self,
        min_entries: int = 3,
    ) -> dict[str, Any]:
        """Trend vurgularını getirir.

        Args:
            min_entries: Min kayıt sayısı.

        Returns:
            Vurgu bilgisi.
        """
        if len(self._metrics_history) < min_entries:
            return {
                "highlights": [],
                "insufficient_data": True,
            }

        # Son 3 kayıttaki trendleri analiz et
        recent = self._metrics_history[
            -min_entries:
        ]
        all_keys: set[str] = set()
        for entry in recent:
            for k, v in entry.get(
                "metrics", {},
            ).items():
                if isinstance(v, (int, float)):
                    all_keys.add(k)

        highlights = []
        for key in all_keys:
            values = [
                entry["metrics"].get(key)
                for entry in recent
                if key in entry.get(
                    "metrics", {},
                )
            ]
            values = [
                v for v in values
                if isinstance(v, (int, float))
            ]

            if len(values) >= min_entries:
                if all(
                    values[i] < values[i + 1]
                    for i in range(
                        len(values) - 1,
                    )
                ):
                    highlights.append({
                        "metric": key,
                        "trend": "consistently_increasing",
                        "values": values,
                    })
                elif all(
                    values[i] > values[i + 1]
                    for i in range(
                        len(values) - 1,
                    )
                ):
                    highlights.append({
                        "metric": key,
                        "trend": "consistently_decreasing",
                        "values": values,
                    })

        return {
            "highlights": highlights,
            "metrics_analyzed": len(all_keys),
        }

    def get_reports(
        self,
        report_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Raporları getirir.

        Args:
            report_type: Tip filtresi.
            limit: Maks kayıt.

        Returns:
            Rapor listesi.
        """
        results = self._reports
        if report_type:
            results = [
                r for r in results
                if r.get("report_type")
                == report_type
            ]
        return list(results[-limit:])

    @property
    def report_count(self) -> int:
        """Rapor sayısı."""
        return self._stats[
            "reports_generated"
        ]

    @property
    def schedule_count(self) -> int:
        """Zamanlama sayısı."""
        return len(self._schedules)
