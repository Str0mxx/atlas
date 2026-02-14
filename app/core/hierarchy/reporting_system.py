"""ATLAS Raporlama Sistemi modulu.

Durum toplama, ilerleme birlestirme,
istisna raporlama, gunluk/haftalik ozetler ve ozel rapor uretimi.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from app.models.hierarchy import (
    HierarchyReport,
    ReportType,
)

logger = logging.getLogger(__name__)


class ReportingSystem:
    """Raporlama sistemi.

    Agent hiyerarsisindan raporlari toplar,
    birlestirir ve ozetler.

    Attributes:
        _reports: Rapor gecmisi.
        _agent_statuses: Agent durum haritasi.
    """

    def __init__(self) -> None:
        """Raporlama sistemini baslatir."""
        self._reports: list[HierarchyReport] = []
        self._agent_statuses: dict[str, dict[str, Any]] = {}

        logger.info("ReportingSystem baslatildi")

    def submit_status(
        self,
        agent_id: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> HierarchyReport:
        """Durum raporu gonderir.

        Args:
            agent_id: Agent ID.
            status: Durum metni.
            details: Ek detaylar.

        Returns:
            HierarchyReport nesnesi.
        """
        content = {"status": status}
        if details:
            content.update(details)

        self._agent_statuses[agent_id] = content

        report = HierarchyReport(
            report_type=ReportType.STATUS,
            agent_id=agent_id,
            title=f"Durum: {status}",
            content=content,
        )

        self._reports.append(report)
        return report

    def submit_progress(
        self,
        agent_id: str,
        task_id: str,
        progress: float,
        notes: str = "",
    ) -> HierarchyReport:
        """Ilerleme raporu gonderir.

        Args:
            agent_id: Agent ID.
            task_id: Gorev ID.
            progress: Ilerleme (0-1).
            notes: Notlar.

        Returns:
            HierarchyReport nesnesi.
        """
        content = {
            "task_id": task_id,
            "progress": min(max(progress, 0.0), 1.0),
            "notes": notes,
        }

        report = HierarchyReport(
            report_type=ReportType.PROGRESS,
            agent_id=agent_id,
            title=f"Ilerleme: {task_id} ({progress:.0%})",
            content=content,
        )

        self._reports.append(report)
        return report

    def submit_exception(
        self,
        agent_id: str,
        error: str,
        severity: str = "error",
        context: dict[str, Any] | None = None,
    ) -> HierarchyReport:
        """Istisna raporu gonderir.

        Args:
            agent_id: Agent ID.
            error: Hata mesaji.
            severity: Ciddiyet.
            context: Baglam bilgisi.

        Returns:
            HierarchyReport nesnesi.
        """
        content: dict[str, Any] = {
            "error": error,
            "severity": severity,
        }
        if context:
            content["context"] = context

        report = HierarchyReport(
            report_type=ReportType.EXCEPTION,
            agent_id=agent_id,
            title=f"Istisna: {error[:50]}",
            content=content,
        )

        self._reports.append(report)
        return report

    def aggregate_status(
        self, agent_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Durumlari toplar.

        Args:
            agent_ids: Agent ID filtresi.

        Returns:
            Toplu durum bilgisi.
        """
        statuses = self._agent_statuses
        if agent_ids:
            statuses = {
                k: v for k, v in statuses.items()
                if k in agent_ids
            }

        return {
            "total_agents": len(statuses),
            "statuses": statuses,
            "active": sum(
                1 for s in statuses.values()
                if s.get("status") != "idle"
            ),
        }

    def rollup_progress(
        self, agent_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Ilerlemeyi birlestirir.

        Args:
            agent_ids: Agent ID filtresi.

        Returns:
            Birlestirilmis ilerleme.
        """
        progress_reports = [
            r for r in self._reports
            if r.report_type == ReportType.PROGRESS
            and (agent_ids is None or r.agent_id in agent_ids)
        ]

        if not progress_reports:
            return {"total_tasks": 0, "avg_progress": 0.0}

        # Son ilerleme kaydi gorev basina
        task_progress: dict[str, float] = {}
        for r in progress_reports:
            tid = r.content.get("task_id", "")
            prog = r.content.get("progress", 0.0)
            task_progress[tid] = prog

        values = list(task_progress.values())
        avg = sum(values) / len(values) if values else 0.0
        completed = sum(1 for v in values if v >= 1.0)

        return {
            "total_tasks": len(task_progress),
            "avg_progress": round(avg, 3),
            "completed_tasks": completed,
            "task_details": task_progress,
        }

    def generate_daily_summary(
        self, agent_ids: list[str] | None = None,
    ) -> HierarchyReport:
        """Gunluk ozet olusturur.

        Args:
            agent_ids: Agent ID filtresi.

        Returns:
            HierarchyReport nesnesi.
        """
        now = datetime.now(timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        today_reports = [
            r for r in self._reports
            if r.timestamp >= day_start
            and (agent_ids is None or r.agent_id in agent_ids)
        ]

        status_count = sum(
            1 for r in today_reports if r.report_type == ReportType.STATUS
        )
        progress_count = sum(
            1 for r in today_reports if r.report_type == ReportType.PROGRESS
        )
        exception_count = sum(
            1 for r in today_reports if r.report_type == ReportType.EXCEPTION
        )

        content = {
            "period": "daily",
            "total_reports": len(today_reports),
            "status_reports": status_count,
            "progress_reports": progress_count,
            "exception_reports": exception_count,
            "progress_summary": self.rollup_progress(agent_ids),
        }

        report = HierarchyReport(
            report_type=ReportType.DAILY,
            title="Gunluk Ozet",
            content=content,
            period_start=day_start,
            period_end=now,
        )

        self._reports.append(report)
        return report

    def generate_weekly_summary(
        self, agent_ids: list[str] | None = None,
    ) -> HierarchyReport:
        """Haftalik ozet olusturur.

        Args:
            agent_ids: Agent ID filtresi.

        Returns:
            HierarchyReport nesnesi.
        """
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=7)

        week_reports = [
            r for r in self._reports
            if r.timestamp >= week_start
            and (agent_ids is None or r.agent_id in agent_ids)
        ]

        exceptions = [
            r for r in week_reports
            if r.report_type == ReportType.EXCEPTION
        ]

        content = {
            "period": "weekly",
            "total_reports": len(week_reports),
            "exception_count": len(exceptions),
            "exceptions": [
                {
                    "agent": e.agent_id,
                    "error": e.content.get("error", ""),
                }
                for e in exceptions[:10]
            ],
            "progress_summary": self.rollup_progress(agent_ids),
        }

        report = HierarchyReport(
            report_type=ReportType.WEEKLY,
            title="Haftalik Ozet",
            content=content,
            period_start=week_start,
            period_end=now,
        )

        self._reports.append(report)
        return report

    def generate_custom_report(
        self,
        title: str,
        agent_ids: list[str] | None = None,
        report_types: list[ReportType] | None = None,
    ) -> HierarchyReport:
        """Ozel rapor uretir.

        Args:
            title: Rapor basligi.
            agent_ids: Agent filtresi.
            report_types: Rapor tipi filtresi.

        Returns:
            HierarchyReport nesnesi.
        """
        filtered = self._reports
        if agent_ids:
            filtered = [r for r in filtered if r.agent_id in agent_ids]
        if report_types:
            filtered = [r for r in filtered if r.report_type in report_types]

        content = {
            "title": title,
            "total_matching": len(filtered),
            "by_type": {},
            "agents": list({r.agent_id for r in filtered if r.agent_id}),
        }

        for r in filtered:
            rt = r.report_type.value
            content["by_type"][rt] = content["by_type"].get(rt, 0) + 1

        report = HierarchyReport(
            report_type=ReportType.CUSTOM,
            title=title,
            content=content,
        )

        self._reports.append(report)
        return report

    def get_reports(
        self,
        agent_id: str | None = None,
        report_type: ReportType | None = None,
    ) -> list[HierarchyReport]:
        """Raporlari getirir.

        Args:
            agent_id: Agent filtresi.
            report_type: Tip filtresi.

        Returns:
            HierarchyReport listesi.
        """
        results = self._reports
        if agent_id:
            results = [r for r in results if r.agent_id == agent_id]
        if report_type:
            results = [r for r in results if r.report_type == report_type]
        return results

    @property
    def report_count(self) -> int:
        """Rapor sayisi."""
        return len(self._reports)

    @property
    def exception_count(self) -> int:
        """Istisna sayisi."""
        return sum(
            1 for r in self._reports
            if r.report_type == ReportType.EXCEPTION
        )
