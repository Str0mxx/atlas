"""ATLAS Fatura Raporlayici modulu.

Maliyet raporlari, kullanim raporlari,
sistem bazli doküm, gorev bazli doküm, export.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BillingReporter:
    """Fatura raporlayici.

    Maliyet raporlari uretir.

    Attributes:
        _reports: Rapor gecmisi.
    """

    def __init__(self) -> None:
        """Fatura raporlayiciyi baslatir."""
        self._reports: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "generated": 0,
        }

        logger.info(
            "BillingReporter baslatildi",
        )

    def generate_cost_report(
        self,
        costs: list[dict[str, Any]],
        period: str = "",
    ) -> dict[str, Any]:
        """Maliyet raporu uretir.

        Args:
            costs: Maliyet kayitlari.
            period: Donem.

        Returns:
            Rapor.
        """
        total = sum(
            c.get("amount", 0) for c in costs
        )
        by_category: dict[str, float] = {}
        for c in costs:
            cat = c.get("category", "other")
            by_category[cat] = (
                by_category.get(cat, 0.0)
                + c.get("amount", 0)
            )

        report = {
            "type": "cost",
            "period": period,
            "total_cost": round(total, 4),
            "item_count": len(costs),
            "by_category": {
                k: round(v, 4)
                for k, v in by_category.items()
            },
            "avg_cost": round(
                total / max(len(costs), 1), 4,
            ),
            "generated_at": time.time(),
        }

        self._reports.append(report)
        self._stats["generated"] += 1

        return report

    def generate_usage_report(
        self,
        usage: dict[str, int],
        costs: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Kullanim raporu uretir.

        Args:
            usage: Kullanim verileri {servis: sayi}.
            costs: Maliyet verileri {servis: tutar}.

        Returns:
            Rapor.
        """
        total_usage = sum(usage.values())
        total_cost = (
            sum(costs.values()) if costs else 0.0
        )

        items = []
        for service, count in usage.items():
            cost = (
                costs.get(service, 0)
                if costs
                else 0
            )
            items.append({
                "service": service,
                "usage": count,
                "cost": round(cost, 4),
                "cost_per_unit": round(
                    cost / max(count, 1), 6,
                ),
            })

        items.sort(
            key=lambda x: x["cost"],
            reverse=True,
        )

        report = {
            "type": "usage",
            "total_usage": total_usage,
            "total_cost": round(total_cost, 4),
            "services": len(usage),
            "items": items,
            "generated_at": time.time(),
        }

        self._reports.append(report)
        self._stats["generated"] += 1

        return report

    def generate_system_breakdown(
        self,
        system_costs: dict[str, float],
    ) -> dict[str, Any]:
        """Sistem bazli doküm uretir.

        Args:
            system_costs: Sistem maliyetleri.

        Returns:
            Rapor.
        """
        total = sum(system_costs.values())

        breakdown = []
        for system, cost in sorted(
            system_costs.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            pct = (
                cost / total * 100
                if total > 0
                else 0
            )
            breakdown.append({
                "system": system,
                "cost": round(cost, 4),
                "pct": round(pct, 1),
            })

        report = {
            "type": "system_breakdown",
            "total_cost": round(total, 4),
            "systems": len(system_costs),
            "breakdown": breakdown,
            "generated_at": time.time(),
        }

        self._reports.append(report)
        self._stats["generated"] += 1

        return report

    def generate_task_breakdown(
        self,
        task_costs: dict[str, float],
    ) -> dict[str, Any]:
        """Gorev bazli doküm uretir.

        Args:
            task_costs: Gorev maliyetleri.

        Returns:
            Rapor.
        """
        total = sum(task_costs.values())
        avg = (
            total / len(task_costs)
            if task_costs
            else 0
        )

        breakdown = []
        for task, cost in sorted(
            task_costs.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            breakdown.append({
                "task": task,
                "cost": round(cost, 4),
            })

        report = {
            "type": "task_breakdown",
            "total_cost": round(total, 4),
            "task_count": len(task_costs),
            "avg_cost_per_task": round(avg, 4),
            "most_expensive": (
                breakdown[0]["task"]
                if breakdown
                else None
            ),
            "breakdown": breakdown,
            "generated_at": time.time(),
        }

        self._reports.append(report)
        self._stats["generated"] += 1

        return report

    def generate_summary(
        self,
        total_cost: float,
        budget_limit: float,
        decisions: int,
        period: str = "",
    ) -> dict[str, Any]:
        """Ozet rapor uretir.

        Args:
            total_cost: Toplam maliyet.
            budget_limit: Butce limiti.
            decisions: Karar sayisi.
            period: Donem.

        Returns:
            Ozet rapor.
        """
        usage_pct = (
            total_cost / budget_limit * 100
            if budget_limit > 0
            else 0
        )
        avg_per_decision = (
            total_cost / decisions
            if decisions > 0
            else 0
        )

        status = "good"
        if usage_pct > 90:
            status = "critical"
        elif usage_pct > 70:
            status = "warning"

        report = {
            "type": "summary",
            "period": period,
            "total_cost": round(total_cost, 4),
            "budget_limit": budget_limit,
            "usage_pct": round(usage_pct, 1),
            "decisions": decisions,
            "avg_cost_per_decision": round(
                avg_per_decision, 6,
            ),
            "remaining": round(
                max(
                    budget_limit - total_cost, 0,
                ),
                4,
            ),
            "status": status,
            "generated_at": time.time(),
        }

        self._reports.append(report)
        self._stats["generated"] += 1

        return report

    def export_report(
        self,
        report: dict[str, Any],
        format: str = "json",
    ) -> dict[str, Any]:
        """Raporu export eder.

        Args:
            report: Rapor verisi.
            format: Format (json/csv/text).

        Returns:
            Export bilgisi.
        """
        if format == "json":
            content = str(report)
        elif format == "csv":
            lines = []
            for key, val in report.items():
                if not isinstance(val, (dict, list)):
                    lines.append(f"{key},{val}")
            content = "\n".join(lines)
        else:
            lines = []
            for key, val in report.items():
                if not isinstance(val, (dict, list)):
                    lines.append(f"{key}: {val}")
            content = "\n".join(lines)

        return {
            "format": format,
            "content": content,
            "size": len(content),
            "exported": True,
        }

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

    @property
    def report_count(self) -> int:
        """Rapor sayisi."""
        return len(self._reports)
