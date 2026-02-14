"""ATLAS Teshis Orkestratoru modulu.

Tam teshis boru hatti, otomatik onarim
koordinasyonu, surekli izleme, oz-iyilesme
tetikleri ve insan eskalasyonu.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.diagnostic import (
    DiagnosticPhase,
    DiagnosticSnapshot,
    ErrorSeverity,
    FixType,
    HealthStatus,
    MaintenanceType,
)

from app.core.diagnostic.auto_fixer import AutoFixer
from app.core.diagnostic.bottleneck_detector import BottleneckDetector
from app.core.diagnostic.dependency_checker import DependencyChecker
from app.core.diagnostic.diagnostic_reporter import DiagnosticReporter
from app.core.diagnostic.error_analyzer import ErrorAnalyzer
from app.core.diagnostic.health_scanner import HealthScanner
from app.core.diagnostic.preventive_care import PreventiveCare
from app.core.diagnostic.recovery_manager import RecoveryManager

logger = logging.getLogger(__name__)


class DiagnosticOrchestrator:
    """Teshis orkestratoru.

    Tum teshis alt sistemlerini birlestiren
    merkezi kontrol noktasi.

    Attributes:
        _scanner: Saglik tarayici.
        _analyzer: Hata analizcisi.
        _detector: Darbogaz tespit.
        _checker: Bagimlilik kontrolcu.
        _fixer: Otomatik duzeltici.
        _recovery: Kurtarma yoneticisi.
        _care: Onleyici bakim.
        _reporter: Teshis raporlayici.
    """

    def __init__(
        self,
        auto_repair: bool = False,
        alert_threshold: float = 0.5,
    ) -> None:
        """Teshis orkestratoru baslatir.

        Args:
            auto_repair: Otomatik onarim.
            alert_threshold: Uyari esigi.
        """
        self._scanner = HealthScanner()
        self._analyzer = ErrorAnalyzer()
        self._detector = BottleneckDetector()
        self._checker = DependencyChecker()
        self._fixer = AutoFixer(auto_approve=auto_repair)
        self._recovery = RecoveryManager()
        self._care = PreventiveCare()
        self._reporter = DiagnosticReporter(
            alert_threshold=alert_threshold,
        )

        self._auto_repair = auto_repair
        self._phase = DiagnosticPhase.IDLE
        self._started_at = datetime.now(timezone.utc)
        self._cycle_count = 0
        self._escalations: list[dict[str, Any]] = []

        logger.info(
            "DiagnosticOrchestrator baslatildi "
            "(auto_repair=%s, threshold=%.2f)",
            auto_repair, alert_threshold,
        )

    def run_full_diagnostic(
        self,
        component_metrics: dict[str, dict[str, float]],
    ) -> dict[str, Any]:
        """Tam teshis calistirir.

        Args:
            component_metrics: Bilesen metrikleri.

        Returns:
            Teshis sonucu.
        """
        self._cycle_count += 1

        # 1. Tarama
        self._phase = DiagnosticPhase.SCANNING
        scan = self._scanner.full_scan(component_metrics)

        # 2. Saglik kaydet
        self._care.record_health(
            scan["overall_score"],
            {"issues": scan["total_issues"]},
        )

        # 3. Rapor uret
        self._phase = DiagnosticPhase.REPORTING
        report = self._reporter.generate_health_report(scan)

        # 4. Otomatik onarim
        fixes_applied = 0
        if self._auto_repair and scan["total_issues"] > 0:
            self._phase = DiagnosticPhase.FIXING
            fixes_applied = self._auto_fix_issues(scan)

        self._phase = DiagnosticPhase.IDLE

        return {
            "cycle": self._cycle_count,
            "scan": scan,
            "report": report,
            "fixes_applied": fixes_applied,
            "phase": self._phase.value,
        }

    def report_error(
        self,
        error_type: str,
        message: str,
        component: str = "",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ) -> dict[str, Any]:
        """Hata raporlar.

        Args:
            error_type: Hata turu.
            message: Mesaj.
            component: Bilesen.
            severity: Ciddiyet.

        Returns:
            Isleme sonucu.
        """
        self._phase = DiagnosticPhase.ANALYZING
        record = self._analyzer.record_error(
            error_type, message, component, severity,
        )

        # Kok neden analizi
        root_cause = self._analyzer.analyze_root_cause(record.error_id)

        # Etki degerlendirmesi
        impact = self._analyzer.assess_impact(record.error_id)

        # Otomatik duzeltme dene
        fix_result = None
        if self._auto_repair and impact.get("requires_immediate"):
            self._phase = DiagnosticPhase.FIXING
            fix_result = self._fixer.auto_fix(error_type, component)

        # Kritik ise eskale et
        if severity == ErrorSeverity.CRITICAL:
            self._escalate(
                f"Kritik hata: {error_type}",
                component,
                f"{message} - {root_cause.get('root_cause', '')}",
            )

        self._phase = DiagnosticPhase.IDLE

        return {
            "error_id": record.error_id,
            "root_cause": root_cause,
            "impact": impact,
            "fix_applied": fix_result,
        }

    def check_performance(
        self,
        operations: dict[str, float],
        resource_usage: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Performans kontrol eder.

        Args:
            operations: Islem -> sure (ms) eslesmesi.
            resource_usage: Kaynak kullanimi.

        Returns:
            Performans raporu.
        """
        # Islemleri profille
        for op, duration in operations.items():
            self._detector.profile_operation(op, duration)

        # Yavas islemler
        slow = self._detector.detect_slow_operations()

        # Kaynak kontrolleri
        bottlenecks: list[dict[str, Any]] = []
        resources = resource_usage or {}
        if "cpu_percent" in resources:
            bn = self._detector.check_cpu(
                "system", resources["cpu_percent"],
            )
            if bn:
                bottlenecks.append({
                    "type": "cpu",
                    "value": resources["cpu_percent"],
                })
        if "memory_percent" in resources:
            bn = self._detector.check_memory(
                "system", resources["memory_percent"],
            )
            if bn:
                bottlenecks.append({
                    "type": "memory",
                    "value": resources["memory_percent"],
                })

        return {
            "slow_operations": slow,
            "bottlenecks": bottlenecks,
            "total_bottlenecks": self._detector.bottleneck_count,
        }

    def check_dependencies(self) -> dict[str, Any]:
        """Bagimliliklari kontrol eder.

        Returns:
            Kontrol sonucu.
        """
        return self._checker.full_check()

    def trigger_recovery(
        self,
        target: str,
        recovery_type: str = "service_restore",
    ) -> dict[str, Any]:
        """Kurtarma tetikler.

        Args:
            target: Hedef.
            recovery_type: Kurtarma turu.

        Returns:
            Kurtarma sonucu.
        """
        self._phase = DiagnosticPhase.RECOVERING

        if recovery_type == "backup_restore":
            record = self._recovery.restore_backup(target)
        elif recovery_type == "rollback":
            record = self._recovery.execute_rollback()
        else:
            record = self._recovery.restore_service(target)

        self._phase = DiagnosticPhase.IDLE

        return {
            "recovery_id": record.recovery_id,
            "success": record.success,
            "target": target,
            "type": recovery_type,
        }

    def run_maintenance(self) -> dict[str, Any]:
        """Bakim calistirir.

        Returns:
            Bakim sonucu.
        """
        due = self._care.get_due_maintenance()
        predictions = self._care.predict_maintenance()
        trend = self._care.analyze_trend()

        return {
            "due_maintenance": len(due),
            "predictions": predictions,
            "trend": trend,
            "schedules": self._care.schedule_count,
        }

    def get_snapshot(self) -> DiagnosticSnapshot:
        """Teshis goruntusu getirir.

        Returns:
            DiagnosticSnapshot nesnesi.
        """
        uptime = (
            datetime.now(timezone.utc) - self._started_at
        ).total_seconds()

        # Genel saglik
        trend = self._care.analyze_trend()
        score = trend.get("recent_avg", 0.5)
        if score >= 0.7:
            overall = HealthStatus.HEALTHY
        elif score >= 0.4:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.UNHEALTHY

        return DiagnosticSnapshot(
            overall_health=overall,
            health_score=score,
            components_scanned=self._scanner.component_count,
            errors_found=self._analyzer.error_count,
            bottlenecks_found=self._detector.bottleneck_count,
            fixes_applied=self._fixer.fix_count,
            recoveries_performed=self._recovery.recovery_count,
            maintenance_runs=self._care.run_count,
            uptime_seconds=round(uptime, 2),
        )

    def _auto_fix_issues(
        self,
        scan_results: dict[str, Any],
    ) -> int:
        """Sorunlari otomatik duzeltir.

        Args:
            scan_results: Tarama sonuclari.

        Returns:
            Uygulanan duzeltme sayisi.
        """
        fixed = 0
        reports = scan_results.get("reports", [])

        for report in reports:
            if hasattr(report, "issues") and report.issues:
                for issue in report.issues:
                    result = self._fixer.auto_fix(
                        issue, report.component,
                    )
                    if result.get("fixed"):
                        fixed += 1

        return fixed

    def _escalate(
        self,
        title: str,
        component: str,
        details: str,
    ) -> None:
        """Insan eskalasyonu yapar.

        Args:
            title: Baslik.
            component: Bilesen.
            details: Detaylar.
        """
        escalation = {
            "title": title,
            "component": component,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._escalations.append(escalation)
        logger.warning("ESKALASYON: %s (%s)", title, component)

    # Alt sistem erisimi
    @property
    def scanner(self) -> HealthScanner:
        """Saglik tarayici."""
        return self._scanner

    @property
    def analyzer(self) -> ErrorAnalyzer:
        """Hata analizcisi."""
        return self._analyzer

    @property
    def detector(self) -> BottleneckDetector:
        """Darbogaz tespit."""
        return self._detector

    @property
    def checker(self) -> DependencyChecker:
        """Bagimlilik kontrolcu."""
        return self._checker

    @property
    def fixer(self) -> AutoFixer:
        """Otomatik duzeltici."""
        return self._fixer

    @property
    def recovery(self) -> RecoveryManager:
        """Kurtarma yoneticisi."""
        return self._recovery

    @property
    def care(self) -> PreventiveCare:
        """Onleyici bakim."""
        return self._care

    @property
    def reporter(self) -> DiagnosticReporter:
        """Teshis raporlayici."""
        return self._reporter

    @property
    def phase(self) -> DiagnosticPhase:
        """Mevcut asama."""
        return self._phase

    @property
    def cycle_count(self) -> int:
        """Dongu sayisi."""
        return self._cycle_count

    @property
    def escalation_count(self) -> int:
        """Eskalasyon sayisi."""
        return len(self._escalations)
