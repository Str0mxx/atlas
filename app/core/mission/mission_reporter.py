"""ATLAS Gorev Raporlayici modulu.

Durum raporlari, yonetici ozetleri, detayli loglar,
gorev-sonrasi analiz ve basari metrikleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.mission import MissionReport, ReportType

logger = logging.getLogger(__name__)


class MissionReporter:
    """Gorev raporlayici.

    Cesitli rapor tipleri uretir, metrikleri
    hesaplar ve gorev-sonrasi analiz yapar.

    Attributes:
        _reports: Uretilen raporlar.
        _logs: Detayli loglar.
        _metrics: Basari metrikleri.
    """

    def __init__(self) -> None:
        """Raporlayiciyi baslatir."""
        self._reports: dict[str, MissionReport] = {}
        self._logs: dict[str, list[dict[str, Any]]] = {}
        self._metrics: dict[str, dict[str, Any]] = {}

        logger.info("MissionReporter baslatildi")

    def generate_status_report(
        self,
        mission_id: str,
        progress: float = 0.0,
        active_phases: int = 0,
        completed_phases: int = 0,
        total_phases: int = 0,
        blockers: int = 0,
        alerts: int = 0,
    ) -> MissionReport:
        """Durum raporu uretir.

        Args:
            mission_id: Gorev ID.
            progress: Ilerleme.
            active_phases: Aktif faz sayisi.
            completed_phases: Tamamlanan faz sayisi.
            total_phases: Toplam faz sayisi.
            blockers: Engelleyici sayisi.
            alerts: Uyari sayisi.

        Returns:
            MissionReport nesnesi.
        """
        report = MissionReport(
            mission_id=mission_id,
            report_type=ReportType.STATUS,
            title=f"Durum Raporu - {mission_id}",
            content={
                "progress": progress,
                "active_phases": active_phases,
                "completed_phases": completed_phases,
                "total_phases": total_phases,
                "blockers": blockers,
                "alerts": alerts,
                "health": "good" if blockers == 0 else "at_risk",
            },
        )
        self._reports[report.report_id] = report
        return report

    def generate_executive_summary(
        self,
        mission_id: str,
        mission_name: str = "",
        progress: float = 0.0,
        key_achievements: list[str] | None = None,
        risks: list[str] | None = None,
        next_steps: list[str] | None = None,
        budget_status: dict[str, float] | None = None,
    ) -> MissionReport:
        """Yonetici ozeti uretir.

        Args:
            mission_id: Gorev ID.
            mission_name: Gorev adi.
            progress: Ilerleme.
            key_achievements: Onemli basarilar.
            risks: Riskler.
            next_steps: Sonraki adimlar.
            budget_status: Butce durumu.

        Returns:
            MissionReport nesnesi.
        """
        report = MissionReport(
            mission_id=mission_id,
            report_type=ReportType.EXECUTIVE,
            title=f"Yonetici Ozeti - {mission_name or mission_id}",
            content={
                "mission_name": mission_name,
                "progress": progress,
                "key_achievements": key_achievements or [],
                "risks": risks or [],
                "next_steps": next_steps or [],
                "budget": budget_status or {},
            },
        )
        self._reports[report.report_id] = report
        return report

    def generate_detailed_report(
        self,
        mission_id: str,
        sections: dict[str, Any] | None = None,
    ) -> MissionReport:
        """Detayli rapor uretir.

        Args:
            mission_id: Gorev ID.
            sections: Rapor bolumleri.

        Returns:
            MissionReport nesnesi.
        """
        # Loglari dahil et
        logs = self._logs.get(mission_id, [])

        report = MissionReport(
            mission_id=mission_id,
            report_type=ReportType.DETAILED,
            title=f"Detayli Rapor - {mission_id}",
            content={
                "sections": sections or {},
                "log_count": len(logs),
                "recent_logs": logs[-10:] if logs else [],
            },
        )
        self._reports[report.report_id] = report
        return report

    def generate_post_mission_report(
        self,
        mission_id: str,
        outcome: str = "completed",
        duration_hours: float = 0.0,
        lessons_learned: list[str] | None = None,
        success_metrics: dict[str, Any] | None = None,
        recommendations: list[str] | None = None,
    ) -> MissionReport:
        """Gorev-sonrasi rapor uretir.

        Args:
            mission_id: Gorev ID.
            outcome: Sonuc.
            duration_hours: Sure (saat).
            lessons_learned: Alinan dersler.
            success_metrics: Basari metrikleri.
            recommendations: Oneriler.

        Returns:
            MissionReport nesnesi.
        """
        report = MissionReport(
            mission_id=mission_id,
            report_type=ReportType.POST_MISSION,
            title=f"Gorev-Sonrasi Rapor - {mission_id}",
            content={
                "outcome": outcome,
                "duration_hours": duration_hours,
                "lessons_learned": lessons_learned or [],
                "success_metrics": success_metrics or {},
                "recommendations": recommendations or [],
            },
        )
        self._reports[report.report_id] = report

        # Metrikleri kaydet
        if success_metrics:
            self._metrics[mission_id] = success_metrics

        return report

    def add_log(
        self,
        mission_id: str,
        message: str,
        level: str = "info",
        source: str = "",
    ) -> None:
        """Detayli log ekler.

        Args:
            mission_id: Gorev ID.
            message: Log mesaji.
            level: Log seviyesi.
            source: Kaynak.
        """
        self._logs.setdefault(mission_id, []).append({
            "message": message,
            "level": level,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_logs(
        self,
        mission_id: str,
        level: str = "",
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Loglari getirir.

        Args:
            mission_id: Gorev ID.
            level: Seviye filtresi.
            limit: Maks kayit.

        Returns:
            Log listesi.
        """
        logs = self._logs.get(mission_id, [])
        if level:
            logs = [l for l in logs if l["level"] == level]
        if limit > 0:
            logs = logs[-limit:]
        return logs

    def get_reports(
        self,
        mission_id: str = "",
        report_type: ReportType | None = None,
    ) -> list[MissionReport]:
        """Raporlari getirir.

        Args:
            mission_id: Gorev filtresi.
            report_type: Tip filtresi.

        Returns:
            Rapor listesi.
        """
        reports = list(self._reports.values())
        if mission_id:
            reports = [r for r in reports if r.mission_id == mission_id]
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        return reports

    def get_success_metrics(
        self,
        mission_id: str,
    ) -> dict[str, Any]:
        """Basari metriklerini getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Metrik sozlugu.
        """
        return dict(self._metrics.get(mission_id, {}))

    def get_report(self, report_id: str) -> MissionReport | None:
        """Raporu getirir.

        Args:
            report_id: Rapor ID.

        Returns:
            MissionReport veya None.
        """
        return self._reports.get(report_id)

    @property
    def total_reports(self) -> int:
        """Toplam rapor sayisi."""
        return len(self._reports)

    @property
    def total_logs(self) -> int:
        """Toplam log sayisi."""
        return sum(len(logs) for logs in self._logs.values())
