"""ATLAS Cost Engine Orkestrator modulu.

Tam maliyet yonetimi, on-karar maliyetlendirme,
gercek zamanli izleme, butce zorlama, analitik.
"""

import logging
import time
from typing import Any

from app.core.costengine.alternative_analyzer import (
    AlternativeAnalyzer,
)
from app.core.costengine.billing_reporter import (
    BillingReporter,
)
from app.core.costengine.budget_manager import (
    BudgetManager,
)
from app.core.costengine.cost_calculator import (
    CostCalculator,
)
from app.core.costengine.cost_tracker import (
    DecisionCostTracker,
)
from app.core.costengine.optimization_advisor import (
    CostOptimizationAdvisor,
)
from app.core.costengine.price_catalog import (
    PriceCatalog,
)
from app.core.costengine.spending_controller import (
    SpendingController,
)

logger = logging.getLogger(__name__)


class CostEngineOrchestrator:
    """Cost engine orkestrator.

    Tum maliyet bilesenleri koordine eder.

    Attributes:
        calculator: Maliyet hesaplayici.
        catalog: Fiyat katalogu.
        budget: Butce yoneticisi.
        tracker: Maliyet takipcisi.
        alternatives: Alternatif analizcisi.
        spending: Harcama kontrolcusu.
        optimizer: Optimizasyon danismani.
        reporter: Fatura raporlayici.
    """

    def __init__(
        self,
        default_budget: float = 100.0,
        pause_on_exceed: bool = True,
        require_approval_above: float = 50.0,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            default_budget: Varsayilan butce.
            pause_on_exceed: Limit asiminda durdur.
            require_approval_above: Onay esigi.
        """
        self.calculator = CostCalculator()
        self.catalog = PriceCatalog()
        self.budget = BudgetManager(
            default_daily_limit=default_budget,
        )
        self.tracker = DecisionCostTracker()
        self.alternatives = AlternativeAnalyzer()
        self.spending = SpendingController(
            pause_on_exceed=pause_on_exceed,
            require_approval_above=(
                require_approval_above
            ),
        )
        self.optimizer = (
            CostOptimizationAdvisor()
        )
        self.reporter = BillingReporter()

        self._stats = {
            "decisions_costed": 0,
        }

        logger.info(
            "CostEngineOrchestrator baslatildi",
        )

    def pre_decision_cost(
        self,
        decision_id: str,
        components: list[dict[str, Any]],
        budget_id: str | None = None,
    ) -> dict[str, Any]:
        """On-karar maliyetlendirme.

        Args:
            decision_id: Karar ID.
            components: Maliyet bilesenleri
                [{type, ...params}].
            budget_id: Butce ID.

        Returns:
            Tahmin bilgisi.
        """
        estimated_costs = []

        for comp in components:
            cost_type = comp.get("type", "")

            if cost_type == "api_call":
                r = self.calculator.calculate_api_cost(
                    comp.get("service", "default"),
                    comp.get("calls", 1),
                    comp.get("rate"),
                )
            elif cost_type == "compute":
                r = self.calculator.calculate_compute_cost(
                    comp.get("duration", 1.0),
                    comp.get("cpu_units", 1.0),
                )
            elif cost_type == "storage":
                r = self.calculator.calculate_storage_cost(
                    comp.get("size_mb", 1.0),
                    comp.get("hours", 1.0),
                )
            elif cost_type == "time":
                r = self.calculator.calculate_time_cost(
                    comp.get("hours", 0.1),
                )
            else:
                r = {"cost": 0.0, "category": cost_type}

            estimated_costs.append(r)

        total = self.calculator.calculate_total(
            estimated_costs,
        )
        estimated = total["total_cost"]

        # Butce kontrolu
        budget_ok = True
        if budget_id:
            check = self.budget.check_budget(
                budget_id, estimated,
            )
            budget_ok = check.get(
                "can_afford", True,
            )

        # Harcama kontrolu
        spend_check = (
            self.spending.check_spending(
                estimated,
                context=decision_id,
            )
        )

        self._stats["decisions_costed"] += 1

        return {
            "decision_id": decision_id,
            "estimated_cost": estimated,
            "components": len(components),
            "by_category": total["by_category"],
            "budget_ok": budget_ok,
            "spending_action": spend_check[
                "action"
            ],
            "proceed": (
                budget_ok
                and spend_check["action"]
                in ("allow", "warn")
            ),
        }

    def track_decision(
        self,
        decision_id: str,
        system: str = "",
        costs: list[dict[str, Any]] | None = None,
        budget_id: str | None = None,
    ) -> dict[str, Any]:
        """Karar maliyetini takip eder.

        Args:
            decision_id: Karar ID.
            system: Sistem adi.
            costs: Maliyet listesi.
            budget_id: Butce ID.

        Returns:
            Takip bilgisi.
        """
        # Takip baslat
        self.tracker.start_tracking(
            decision_id, system=system,
        )

        # Maliyetleri ekle
        total = 0.0
        if costs:
            for c in costs:
                self.tracker.add_cost(
                    decision_id,
                    c.get("category", "other"),
                    c.get("amount", 0),
                    c.get("description", ""),
                )
                total += c.get("amount", 0)

        # Butceden harcarc
        if budget_id:
            self.budget.allocate(
                budget_id, total,
            )

        # Harcama kaydi
        self.spending.record_spending(
            total,
            context=decision_id,
        )

        # Takibi tamamla
        result = self.tracker.complete_tracking(
            decision_id,
        )

        self._stats["decisions_costed"] += 1

        return result

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "total_spent": (
                self.tracker.total_cost
            ),
            "decisions_tracked": (
                self.tracker.decision_count
            ),
            "avg_cost_per_decision": (
                self.tracker.get_avg_cost()
            ),
            "active_budgets": (
                self.budget.budget_count
            ),
            "catalog_entries": (
                self.catalog.price_count
            ),
            "pending_approvals": (
                self.spending.pending_count
            ),
            "optimization_suggestions": (
                self.optimizer.suggestion_count
            ),
            "reports_generated": (
                self.reporter.report_count
            ),
            "is_paused": self.spending.is_paused,
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        cost_by_system = (
            self.tracker.get_cost_by_system()
        )
        cost_by_category = (
            self.tracker.get_cost_by_category()
        )
        trend = self.tracker.get_trend()

        return {
            "total_cost": (
                self.tracker.total_cost
            ),
            "by_system": cost_by_system,
            "by_category": cost_by_category,
            "trend": trend,
            "avg_cost": (
                self.tracker.get_avg_cost()
            ),
            "budget_summary": (
                self.budget.get_total_spending()
            ),
        }

    def generate_report(
        self,
        period: str = "",
    ) -> dict[str, Any]:
        """Rapor uretir.

        Returns:
            Rapor.
        """
        costs = self.tracker.get_history()
        return self.reporter.generate_cost_report(
            costs, period=period,
        )

    @property
    def decisions_costed(self) -> int:
        """Maliyetlendirilen karar sayisi."""
        return self._stats["decisions_costed"]
