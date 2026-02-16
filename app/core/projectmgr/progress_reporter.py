"""ATLAS Proje İlerleme Raporlayıcı modülü.

Durum raporları, burndown grafikleri,
hız takibi, paydaş güncellemeleri,
özel formatlar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProjectProgressReporter:
    """Proje ilerleme raporlayıcı.

    Proje ilerleme raporları üretir.

    Attributes:
        _reports: Rapor kayıtları.
        _velocities: Hız kayıtları.
    """

    def __init__(self) -> None:
        """Raporlayıcıyı başlatır."""
        self._reports: list[
            dict[str, Any]
        ] = []
        self._velocities: dict[
            str, list[float]
        ] = {}
        self._counter = 0
        self._stats = {
            "reports_generated": 0,
            "burndowns_created": 0,
            "updates_sent": 0,
        }

        logger.info(
            "ProjectProgressReporter "
            "baslatildi",
        )

    def generate_status_report(
        self,
        project_id: str,
        progress: float,
        tasks_done: int,
        tasks_total: int,
        blockers: int = 0,
        health_score: float = 100.0,
    ) -> dict[str, Any]:
        """Durum raporu üretir.

        Args:
            project_id: Proje ID.
            progress: İlerleme yüzdesi.
            tasks_done: Tamamlanan görev.
            tasks_total: Toplam görev.
            blockers: Engel sayısı.
            health_score: Sağlık puanı.

        Returns:
            Rapor bilgisi.
        """
        self._counter += 1
        rid = f"rpt_{self._counter}"

        status = (
            "on_track"
            if health_score >= 80
            else "at_risk"
            if health_score >= 50
            else "critical"
        )

        report = {
            "report_id": rid,
            "project_id": project_id,
            "progress": progress,
            "tasks_done": tasks_done,
            "tasks_total": tasks_total,
            "tasks_remaining": (
                tasks_total - tasks_done
            ),
            "blockers": blockers,
            "health_score": health_score,
            "status": status,
            "timestamp": time.time(),
        }
        self._reports.append(report)
        self._stats[
            "reports_generated"
        ] += 1

        return {
            "report_id": rid,
            "status": status,
            "progress": progress,
            "generated": True,
        }

    def create_burndown(
        self,
        project_id: str,
        total_points: int,
        completed_points: list[int],
        sprint_days: int = 14,
    ) -> dict[str, Any]:
        """Burndown grafiği oluşturur.

        Args:
            project_id: Proje ID.
            total_points: Toplam puan.
            completed_points: Günlük tamamlanan.
            sprint_days: Sprint süresi.

        Returns:
            Burndown bilgisi.
        """
        cumulative = 0
        remaining = []
        for pts in completed_points:
            cumulative += pts
            remaining.append(
                total_points - cumulative,
            )

        # İdeal çizgi
        ideal_rate = round(
            total_points / max(sprint_days, 1),
            1,
        )

        # Gerçek hız
        days_elapsed = len(completed_points)
        actual_rate = round(
            cumulative
            / max(days_elapsed, 1), 1,
        )

        on_track = actual_rate >= (
            ideal_rate * 0.9
        )

        self._stats[
            "burndowns_created"
        ] += 1

        return {
            "project_id": project_id,
            "total_points": total_points,
            "completed": cumulative,
            "remaining": remaining,
            "ideal_rate": ideal_rate,
            "actual_rate": actual_rate,
            "on_track": on_track,
            "days_elapsed": days_elapsed,
        }

    def track_velocity(
        self,
        project_id: str,
        points_completed: float,
        period_days: float = 14.0,
    ) -> dict[str, Any]:
        """Hız takip eder.

        Args:
            project_id: Proje ID.
            points_completed: Tamamlanan puan.
            period_days: Dönem süresi.

        Returns:
            Hız bilgisi.
        """
        velocity = round(
            points_completed
            / max(period_days, 1), 2,
        )

        if project_id not in self._velocities:
            self._velocities[
                project_id
            ] = []
        self._velocities[
            project_id
        ].append(velocity)

        history = self._velocities[
            project_id
        ]
        avg_velocity = round(
            sum(history)
            / len(history), 2,
        )

        trend = (
            "improving"
            if len(history) >= 2
            and history[-1] > history[-2]
            else "declining"
            if len(history) >= 2
            and history[-1] < history[-2]
            else "stable"
        )

        return {
            "project_id": project_id,
            "current_velocity": velocity,
            "avg_velocity": avg_velocity,
            "trend": trend,
            "data_points": len(history),
        }

    def send_stakeholder_update(
        self,
        project_id: str,
        stakeholders: list[str],
        summary: str = "",
        highlights: (
            list[str] | None
        ) = None,
        format_type: str = "brief",
    ) -> dict[str, Any]:
        """Paydaş güncellemesi gönderir.

        Args:
            project_id: Proje ID.
            stakeholders: Paydaşlar.
            summary: Özet.
            highlights: Öne çıkanlar.
            format_type: Format tipi.

        Returns:
            Gönderim bilgisi.
        """
        highlights = highlights or []

        update = {
            "project_id": project_id,
            "recipients": stakeholders,
            "summary": summary,
            "highlights": highlights,
            "format": format_type,
            "timestamp": time.time(),
        }

        self._stats["updates_sent"] += 1

        return {
            "project_id": project_id,
            "recipients_count": len(
                stakeholders,
            ),
            "format": format_type,
            "highlights_count": len(
                highlights,
            ),
            "sent": True,
        }

    def format_report(
        self,
        report_data: dict[str, Any],
        format_type: str = "summary",
    ) -> dict[str, Any]:
        """Rapor formatlar.

        Args:
            report_data: Rapor verisi.
            format_type: Format tipi.

        Returns:
            Formatlanmış rapor.
        """
        project_id = report_data.get(
            "project_id", "",
        )
        progress = report_data.get(
            "progress", 0,
        )

        if format_type == "detailed":
            sections = [
                "executive_summary",
                "progress_details",
                "risks_and_blockers",
                "next_steps",
                "metrics",
            ]
        elif format_type == "executive":
            sections = [
                "executive_summary",
                "key_metrics",
                "decisions_needed",
            ]
        else:
            sections = [
                "summary",
                "progress",
                "next_steps",
            ]

        return {
            "project_id": project_id,
            "format": format_type,
            "sections": sections,
            "section_count": len(sections),
            "progress": progress,
            "formatted": True,
        }

    def get_reports(
        self,
        project_id: str = "",
    ) -> list[dict[str, Any]]:
        """Raporları listeler."""
        if project_id:
            return [
                r for r in self._reports
                if r["project_id"]
                == project_id
            ]
        return list(self._reports)

    @property
    def report_count(self) -> int:
        """Rapor sayısı."""
        return self._stats[
            "reports_generated"
        ]

    @property
    def update_count(self) -> int:
        """Güncelleme sayısı."""
        return self._stats[
            "updates_sent"
        ]
