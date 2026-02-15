"""ATLAS Uyumluluk Raporlayıcı modulu.

Uyumluluk durumu, ihlal raporları,
trend analizi, denetim raporları, export.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RegulatoryComplianceReporter:
    """Uyumluluk raporlayıcı.

    Uyumluluk raporları üretir.

    Attributes:
        _reports: Rapor kayıtları.
    """

    def __init__(self) -> None:
        """Raporlayıcıyı başlatır."""
        self._reports: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "reports_generated": 0,
        }

        logger.info(
            "RegulatoryComplianceReporter "
            "baslatildi",
        )

    def generate_compliance_report(
        self,
        checks: list[dict[str, Any]],
        violations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Uyumluluk raporu üretir.

        Args:
            checks: Kontrol kayıtları.
            violations: İhlal kayıtları.

        Returns:
            Rapor bilgisi.
        """
        self._counter += 1
        rid = f"rpt_{self._counter}"

        total_checks = len(checks)
        total_violations = len(violations)
        passed = sum(
            1 for c in checks
            if c.get("compliant", False)
        )
        rate = (
            round(passed / total_checks, 3)
            if total_checks > 0 else 1.0
        )

        report = {
            "report_id": rid,
            "report_type": "compliance",
            "total_checks": total_checks,
            "passed": passed,
            "failed": total_checks - passed,
            "compliance_rate": rate,
            "total_violations": total_violations,
            "generated_at": time.time(),
        }
        self._reports.append(report)
        self._stats["reports_generated"] += 1

        return report

    def generate_violation_report(
        self,
        violations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """İhlal raporu üretir.

        Args:
            violations: İhlaller.

        Returns:
            Rapor bilgisi.
        """
        self._counter += 1
        rid = f"rpt_{self._counter}"

        # Şiddet dağılımı
        severity_dist: dict[str, int] = {}
        for v in violations:
            sev = v.get("severity", "medium")
            severity_dist[sev] = (
                severity_dist.get(sev, 0) + 1
            )

        # Kural dağılımı
        rule_dist: dict[str, int] = {}
        for v in violations:
            rid_v = v.get("rule_id", "unknown")
            rule_dist[rid_v] = (
                rule_dist.get(rid_v, 0) + 1
            )

        top_violated = sorted(
            rule_dist.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        report = {
            "report_id": rid,
            "report_type": "violation",
            "total_violations": len(violations),
            "severity_distribution": (
                severity_dist
            ),
            "top_violated_rules": [
                {"rule_id": r, "count": c}
                for r, c in top_violated
            ],
            "generated_at": time.time(),
        }
        self._reports.append(report)
        self._stats["reports_generated"] += 1

        return report

    def analyze_trends(
        self,
        violations: list[dict[str, Any]],
        period_days: int = 30,
    ) -> dict[str, Any]:
        """Trend analizi yapar.

        Args:
            violations: İhlaller.
            period_days: Analiz süresi.

        Returns:
            Trend bilgisi.
        """
        now = time.time()
        cutoff = now - period_days * 86400
        mid = now - (period_days / 2) * 86400

        recent = [
            v for v in violations
            if v.get("timestamp", 0) >= cutoff
        ]

        first_half = [
            v for v in recent
            if v.get("timestamp", 0) < mid
        ]
        second_half = [
            v for v in recent
            if v.get("timestamp", 0) >= mid
        ]

        trend = "stable"
        if (
            len(second_half)
            > len(first_half) * 1.2
        ):
            trend = "increasing"
        elif (
            len(second_half)
            < len(first_half) * 0.8
        ):
            trend = "decreasing"

        return {
            "period_days": period_days,
            "total_violations": len(recent),
            "first_half": len(first_half),
            "second_half": len(second_half),
            "trend": trend,
        }

    def generate_audit_report(
        self,
        checks: list[dict[str, Any]],
        violations: list[dict[str, Any]],
        exceptions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Denetim raporu üretir.

        Args:
            checks: Kontroller.
            violations: İhlaller.
            exceptions: İstisnalar.

        Returns:
            Rapor bilgisi.
        """
        self._counter += 1
        rid = f"rpt_{self._counter}"

        report = {
            "report_id": rid,
            "report_type": "audit",
            "total_checks": len(checks),
            "total_violations": len(violations),
            "total_exceptions": len(exceptions),
            "active_exceptions": sum(
                1 for e in exceptions
                if e.get("status") == "approved"
            ),
            "compliance_rate": (
                round(
                    sum(
                        1 for c in checks
                        if c.get("compliant")
                    ) / max(len(checks), 1),
                    3,
                )
            ),
            "generated_at": time.time(),
        }
        self._reports.append(report)
        self._stats["reports_generated"] += 1

        return report

    def export_report(
        self,
        report_id: str,
        format_type: str = "json",
    ) -> dict[str, Any]:
        """Rapor export eder.

        Args:
            report_id: Rapor ID.
            format_type: Format tipi.

        Returns:
            Export bilgisi.
        """
        report = None
        for r in self._reports:
            if r.get("report_id") == report_id:
                report = r
                break

        if not report:
            return {"error": "report_not_found"}

        return {
            "report_id": report_id,
            "format": format_type,
            "data": report,
            "exported": True,
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
