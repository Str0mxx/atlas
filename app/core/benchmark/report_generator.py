"""ATLAS Benchmark Rapor Uretici modulu.

Performans raporlari, trend raporlari,
yonetici ozetleri, detayli dokumler, gorsellestirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BenchmarkReportGenerator:
    """Benchmark rapor uretici.

    Benchmark raporlari uretir.

    Attributes:
        _reports: Rapor gecmisi.
    """

    def __init__(self) -> None:
        """Rapor ureticiyi baslatir."""
        self._reports: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "generated": 0,
        }

        logger.info(
            "BenchmarkReportGenerator baslatildi",
        )

    def generate_performance_report(
        self,
        scores: dict[str, dict[str, Any]],
        period: str = "",
    ) -> dict[str, Any]:
        """Performans raporu uretir.

        Args:
            scores: KPI puanlari.
            period: Donem.

        Returns:
            Rapor.
        """
        total = len(scores)
        met = sum(
            1
            for s in scores.values()
            if s.get("meets_target")
        )
        avg_score = (
            sum(
                s.get("score", 0.0)
                for s in scores.values()
            )
            / max(total, 1)
        )

        report = {
            "type": "performance",
            "period": period,
            "total_kpis": total,
            "targets_met": met,
            "met_rate": round(
                met / max(total, 1), 4,
            ),
            "avg_score": round(avg_score, 4),
            "scores": scores,
            "generated_at": time.time(),
        }

        self._reports.append(report)
        self._stats["generated"] += 1

        return report

    def generate_trend_report(
        self,
        trends: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Trend raporu uretir.

        Args:
            trends: KPI trendleri.

        Returns:
            Rapor.
        """
        improving = sum(
            1
            for t in trends.values()
            if t.get("direction") == "improving"
        )
        degrading = sum(
            1
            for t in trends.values()
            if t.get("direction") == "degrading"
        )
        stable = sum(
            1
            for t in trends.values()
            if t.get("direction") == "stable"
        )

        report = {
            "type": "trend",
            "total_kpis": len(trends),
            "improving": improving,
            "degrading": degrading,
            "stable": stable,
            "trends": trends,
            "generated_at": time.time(),
        }

        self._reports.append(report)
        self._stats["generated"] += 1

        return report

    def generate_executive_summary(
        self,
        performance: dict[str, Any],
        trends: dict[str, Any] | None = None,
        alerts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Yonetici ozeti uretir.

        Args:
            performance: Performans verisi.
            trends: Trend verisi.
            alerts: Uyari listesi.

        Returns:
            Ozet rapor.
        """
        active_alerts = alerts or []
        critical_alerts = [
            a for a in active_alerts
            if a.get("severity") == "critical"
        ]

        health = "good"
        if critical_alerts:
            health = "critical"
        elif performance.get("met_rate", 0) < 0.5:
            health = "needs_attention"

        report = {
            "type": "executive",
            "health": health,
            "overall_score": performance.get(
                "avg_score", 0.0,
            ),
            "targets_met_rate": performance.get(
                "met_rate", 0.0,
            ),
            "active_alerts": len(active_alerts),
            "critical_alerts": len(
                critical_alerts,
            ),
            "key_insights": self._generate_insights(
                performance, trends,
            ),
            "generated_at": time.time(),
        }

        self._reports.append(report)
        self._stats["generated"] += 1

        return report

    def generate_detailed_breakdown(
        self,
        kpi_id: str,
        score_history: list[dict[str, Any]],
        trend: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Detayli doküm uretir.

        Args:
            kpi_id: KPI ID.
            score_history: Puan gecmisi.
            trend: Trend verisi.

        Returns:
            Detayli rapor.
        """
        scores = [
            s.get("score", 0.0)
            for s in score_history
        ]
        avg = (
            sum(scores) / len(scores)
            if scores
            else 0.0
        )
        best = max(scores) if scores else 0.0
        worst = min(scores) if scores else 0.0

        report = {
            "type": "detailed",
            "kpi_id": kpi_id,
            "data_points": len(scores),
            "avg_score": round(avg, 4),
            "best_score": best,
            "worst_score": worst,
            "trend": trend,
            "history": score_history,
            "generated_at": time.time(),
        }

        self._reports.append(report)
        self._stats["generated"] += 1

        return report

    def get_reports(
        self,
        report_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Raporlari getirir.

        Args:
            report_type: Rapor tipi filtresi.
            limit: Limit.

        Returns:
            Rapor listesi.
        """
        reports = self._reports
        if report_type:
            reports = [
                r for r in reports
                if r.get("type") == report_type
            ]
        return list(reports[-limit:])

    def _generate_insights(
        self,
        performance: dict[str, Any],
        trends: dict[str, Any] | None,
    ) -> list[str]:
        """Icegoruler uretir.

        Args:
            performance: Performans verisi.
            trends: Trend verisi.

        Returns:
            Icegoru listesi.
        """
        insights = []

        met_rate = performance.get("met_rate", 0)
        if met_rate >= 0.9:
            insights.append(
                "Excellent: 90%+ targets met",
            )
        elif met_rate >= 0.7:
            insights.append(
                "Good: 70%+ targets met",
            )
        else:
            insights.append(
                "Needs improvement: <70% targets met",
            )

        if trends:
            degrading = trends.get("degrading", 0)
            if degrading > 0:
                insights.append(
                    f"{degrading} KPI(s) degrading",
                )

        return insights

    @property
    def report_count(self) -> int:
        """Rapor sayisi."""
        return len(self._reports)
