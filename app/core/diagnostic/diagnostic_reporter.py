"""ATLAS Teshis Raporlayici modulu.

Saglik raporlari, sorun ozetleri,
trend analizi, oneriler
ve uyari uretimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.diagnostic import HealthStatus

logger = logging.getLogger(__name__)


class DiagnosticReporter:
    """Teshis raporlayici.

    Teshis sonuclarindan anlamli
    raporlar ve oneriler uretir.

    Attributes:
        _reports: Uretilen raporlar.
        _alerts: Uyarilar.
        _recommendations: Oneriler.
        _alert_threshold: Uyari esigi.
    """

    def __init__(self, alert_threshold: float = 0.5) -> None:
        """Teshis raporlayiciyi baslatir.

        Args:
            alert_threshold: Uyari esigi.
        """
        self._reports: list[dict[str, Any]] = []
        self._alerts: list[dict[str, Any]] = []
        self._recommendations: list[dict[str, Any]] = []
        self._alert_threshold = max(0.0, min(1.0, alert_threshold))

        logger.info(
            "DiagnosticReporter baslatildi (threshold=%.2f)",
            self._alert_threshold,
        )

    def generate_health_report(
        self,
        scan_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Saglik raporu uretir.

        Args:
            scan_results: Tarama sonuclari.

        Returns:
            Rapor sozlugu.
        """
        overall = scan_results.get("overall_status", "unknown")
        score = scan_results.get("overall_score", 0.0)
        issues = scan_results.get("total_issues", 0)

        report = {
            "type": "health",
            "overall_status": overall,
            "overall_score": score,
            "components_scanned": scan_results.get(
                "components_scanned", 0,
            ),
            "total_issues": issues,
            "summary": self._generate_summary(overall, score, issues),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._reports.append(report)

        # Uyari kontrolu
        if score < self._alert_threshold:
            self._create_alert(
                "health_low",
                f"Sistem sagligi dusuk: {score:.2f}",
                severity="high",
            )

        return report

    def generate_issue_summary(
        self,
        errors: list[dict[str, Any]],
        bottlenecks: list[dict[str, Any]],
        dependency_issues: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Sorun ozeti uretir.

        Args:
            errors: Hatalar.
            bottlenecks: Darbogazar.
            dependency_issues: Bagimlilik sorunlari.

        Returns:
            Ozet sozlugu.
        """
        total = len(errors) + len(bottlenecks) + len(dependency_issues)

        report = {
            "type": "issue_summary",
            "total_issues": total,
            "errors": len(errors),
            "bottlenecks": len(bottlenecks),
            "dependency_issues": len(dependency_issues),
            "critical_count": sum(
                1 for e in errors
                if e.get("severity") == "critical"
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._reports.append(report)

        if total > 0:
            self._generate_recommendations(
                errors, bottlenecks, dependency_issues,
            )

        return report

    def generate_trend_report(
        self,
        health_trend: dict[str, Any],
    ) -> dict[str, Any]:
        """Trend raporu uretir.

        Args:
            health_trend: Trend verisi.

        Returns:
            Rapor sozlugu.
        """
        trend = health_trend.get("trend", "unknown")

        report = {
            "type": "trend",
            "trend_direction": trend,
            "overall_avg": health_trend.get("overall_avg", 0.0),
            "recent_avg": health_trend.get("recent_avg", 0.0),
            "data_points": health_trend.get("data_points", 0),
            "outlook": self._determine_outlook(trend),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._reports.append(report)

        if trend == "declining":
            self._create_alert(
                "trend_declining",
                "Sistem sagligi dusus trendinde",
                severity="medium",
            )

        return report

    def add_recommendation(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        category: str = "general",
    ) -> dict[str, Any]:
        """Oneri ekler.

        Args:
            title: Baslik.
            description: Aciklama.
            priority: Oncelik.
            category: Kategori.

        Returns:
            Oneri kaydi.
        """
        rec = {
            "title": title,
            "description": description,
            "priority": priority,
            "category": category,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._recommendations.append(rec)
        return rec

    def get_alerts(
        self,
        severity: str = "",
    ) -> list[dict[str, Any]]:
        """Uyarilari getirir.

        Args:
            severity: Ciddiyet filtresi.

        Returns:
            Uyari listesi.
        """
        if severity:
            return [
                a for a in self._alerts
                if a.get("severity") == severity
            ]
        return list(self._alerts)

    def get_recommendations(
        self,
        priority: str = "",
    ) -> list[dict[str, Any]]:
        """Onerileri getirir.

        Args:
            priority: Oncelik filtresi.

        Returns:
            Oneri listesi.
        """
        if priority:
            return [
                r for r in self._recommendations
                if r.get("priority") == priority
            ]
        return list(self._recommendations)

    def get_recent_reports(
        self,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Son raporlari getirir.

        Args:
            limit: Maks rapor.

        Returns:
            Rapor listesi.
        """
        return self._reports[-limit:]

    def clear_alerts(self) -> int:
        """Uyarilari temizler.

        Returns:
            Temizlenen uyari sayisi.
        """
        count = len(self._alerts)
        self._alerts.clear()
        return count

    def _generate_summary(
        self,
        status: str,
        score: float,
        issues: int,
    ) -> str:
        """Ozet metni uretir.

        Args:
            status: Durum.
            score: Skor.
            issues: Sorun sayisi.

        Returns:
            Ozet metni.
        """
        if status == HealthStatus.HEALTHY.value:
            return "Sistem saglikli. Sorun tespit edilmedi."
        if status == HealthStatus.DEGRADED.value:
            return f"Sistem dusumus. {issues} sorun tespit edildi."
        if status == HealthStatus.UNHEALTHY.value:
            return f"Sistem sagliksiz! {issues} sorun acil mudahale bekliyor."
        if status == HealthStatus.CRITICAL.value:
            return f"KRITIK! Sistem kritik durumda. {issues} ciddi sorun."
        return f"Durum belirsiz (skor: {score:.2f})"

    def _create_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "medium",
    ) -> None:
        """Uyari olusturur.

        Args:
            alert_type: Uyari turu.
            message: Mesaj.
            severity: Ciddiyet.
        """
        alert = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._alerts.append(alert)
        logger.warning("Uyari: %s - %s", alert_type, message)

    def _generate_recommendations(
        self,
        errors: list[dict[str, Any]],
        bottlenecks: list[dict[str, Any]],
        deps: list[dict[str, Any]],
    ) -> None:
        """Oneriler uretir.

        Args:
            errors: Hatalar.
            bottlenecks: Darbogazar.
            deps: Bagimlilik sorunlari.
        """
        if errors:
            self.add_recommendation(
                "Hata cozumu",
                f"{len(errors)} hata analiz edilip cozulmeli",
                priority="high",
                category="errors",
            )
        if bottlenecks:
            self.add_recommendation(
                "Performans iyilestirme",
                f"{len(bottlenecks)} darbogaz giderilmeli",
                priority="medium",
                category="performance",
            )
        if deps:
            self.add_recommendation(
                "Bagimlilik guncelleme",
                f"{len(deps)} bagimlilik sorunu cozulmeli",
                priority="medium",
                category="dependencies",
            )

    def _determine_outlook(self, trend: str) -> str:
        """Gorunumu belirler.

        Args:
            trend: Trend yonu.

        Returns:
            Gorunum metni.
        """
        outlooks = {
            "improving": "Olumlu - sistem iyilesiyor",
            "stable": "Notr - sistem stabil",
            "declining": "Olumsuz - dikkat gerekli",
        }
        return outlooks.get(trend, "Belirsiz")

    @property
    def report_count(self) -> int:
        """Rapor sayisi."""
        return len(self._reports)

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    @property
    def recommendation_count(self) -> int:
        """Oneri sayisi."""
        return len(self._recommendations)
