"""ATLAS Takvim Analizcisi modülü.

Zaman tahsis analizi, toplantı yükü,
verimlilik kalıpları, öneriler,
eğilim takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CalendarAnalyzer:
    """Takvim analizcisi.

    Takvim verilerini analiz eder.

    Attributes:
        _events: Etkinlik kayıtları.
        _analyses: Analiz kayıtları.
    """

    def __init__(self) -> None:
        """Analizcisini başlatır."""
        self._events: list[
            dict[str, Any]
        ] = []
        self._analyses: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "analyses_performed": 0,
        }

        logger.info(
            "CalendarAnalyzer baslatildi",
        )

    def add_event(
        self,
        title: str = "",
        start_hour: int = 9,
        end_hour: int = 10,
        event_type: str = "meeting",
        day: str = "",
    ) -> dict[str, Any]:
        """Etkinlik ekler.

        Args:
            title: Başlık.
            start_hour: Başlangıç.
            end_hour: Bitiş.
            event_type: Etkinlik tipi.
            day: Gün.

        Returns:
            Ekleme bilgisi.
        """
        self._events.append({
            "title": title,
            "start_hour": start_hour,
            "end_hour": end_hour,
            "type": event_type,
            "day": day,
            "duration": (
                end_hour - start_hour
            ),
        })

        return {
            "title": title,
            "added": True,
        }

    def analyze_time_allocation(
        self,
        work_hours: int = 8,
    ) -> dict[str, Any]:
        """Zaman tahsis analizi yapar.

        Args:
            work_hours: Çalışma saati.

        Returns:
            Analiz bilgisi.
        """
        total_meeting_hours = sum(
            e["duration"]
            for e in self._events
        )

        by_type: dict[str, float] = {}
        for e in self._events:
            t = e["type"]
            by_type[t] = (
                by_type.get(t, 0)
                + e["duration"]
            )

        meeting_pct = round(
            total_meeting_hours
            / max(work_hours, 1) * 100,
            1,
        )

        self._stats[
            "analyses_performed"
        ] += 1

        return {
            "total_meeting_hours": (
                total_meeting_hours
            ),
            "work_hours": work_hours,
            "meeting_percentage": (
                meeting_pct
            ),
            "by_type": by_type,
            "analyzed": True,
        }

    def calculate_meeting_load(
        self,
        max_meeting_pct: float = 50.0,
        work_hours: int = 8,
    ) -> dict[str, Any]:
        """Toplantı yükü hesaplar.

        Args:
            max_meeting_pct: Maks yüzde.
            work_hours: Çalışma saati.

        Returns:
            Hesaplama bilgisi.
        """
        total_hours = sum(
            e["duration"]
            for e in self._events
        )

        current_pct = round(
            total_hours
            / max(work_hours, 1) * 100,
            1,
        )

        status = (
            "overloaded"
            if current_pct > max_meeting_pct
            else "optimal"
            if current_pct
            <= max_meeting_pct * 0.7
            else "heavy"
        )

        return {
            "total_hours": total_hours,
            "current_percentage": (
                current_pct
            ),
            "max_percentage": (
                max_meeting_pct
            ),
            "status": status,
            "calculated": True,
        }

    def detect_patterns(
        self,
    ) -> dict[str, Any]:
        """Verimlilik kalıpları tespit eder.

        Returns:
            Tespit bilgisi.
        """
        by_hour: dict[int, int] = {}
        for e in self._events:
            h = e["start_hour"]
            by_hour[h] = (
                by_hour.get(h, 0) + 1
            )

        busiest_hour = (
            max(by_hour, key=by_hour.get)
            if by_hour
            else None
        )

        by_day: dict[str, int] = {}
        for e in self._events:
            d = e.get("day", "")
            if d:
                by_day[d] = (
                    by_day.get(d, 0) + 1
                )

        busiest_day = (
            max(by_day, key=by_day.get)
            if by_day
            else None
        )

        avg_duration = round(
            sum(
                e["duration"]
                for e in self._events
            ) / max(len(self._events), 1),
            1,
        )

        return {
            "busiest_hour": busiest_hour,
            "busiest_day": busiest_day,
            "avg_duration": avg_duration,
            "by_hour": by_hour,
            "detected": True,
        }

    def get_recommendations(
        self,
        max_meeting_pct: float = 50.0,
        work_hours: int = 8,
    ) -> dict[str, Any]:
        """Öneriler verir.

        Args:
            max_meeting_pct: Maks yüzde.
            work_hours: Çalışma saati.

        Returns:
            Öneri bilgisi.
        """
        load = self.calculate_meeting_load(
            max_meeting_pct, work_hours,
        )

        recommendations = []

        if load["status"] == "overloaded":
            recommendations.append(
                "Reduce meeting count or "
                "duration."
            )
            recommendations.append(
                "Consider async alternatives."
            )

        patterns = self.detect_patterns()
        if patterns.get("avg_duration", 0) > 1:
            recommendations.append(
                "Shorten meetings to 45min."
            )

        if not recommendations:
            recommendations.append(
                "Calendar is well balanced."
            )

        return {
            "recommendations": (
                recommendations
            ),
            "load_status": load["status"],
            "count": len(recommendations),
            "generated": True,
        }

    def track_trend(
        self,
        period: str = "weekly",
    ) -> dict[str, Any]:
        """Eğilim takibi yapar.

        Args:
            period: Dönem.

        Returns:
            Takip bilgisi.
        """
        total_hours = sum(
            e["duration"]
            for e in self._events
        )
        total_events = len(self._events)

        self._analyses.append({
            "period": period,
            "total_hours": total_hours,
            "total_events": total_events,
            "timestamp": time.time(),
        })

        trend = "stable"
        if len(self._analyses) >= 2:
            prev = self._analyses[-2][
                "total_hours"
            ]
            if total_hours > prev * 1.2:
                trend = "increasing"
            elif total_hours < prev * 0.8:
                trend = "decreasing"

        return {
            "period": period,
            "total_hours": total_hours,
            "total_events": total_events,
            "trend": trend,
            "tracked": True,
        }

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "analyses_performed"
        ]

    @property
    def event_count(self) -> int:
        """Etkinlik sayısı."""
        return len(self._events)
