"""
Finansal panel orkestrator modulu.

Tam finansal gorunum,
Track -> Visualize -> Forecast -> Alert,
Executive view, analitik.
"""

import logging
from typing import Any

from app.core.findash.budget_vs_actual import (
    BudgetVsActual,
)
from app.core.findash.cashflow_graph import (
    CashFlowGraph,
)
from app.core.findash.cost_per_system_view import (
    CostPerSystemView,
)
from app.core.findash.expense_breakdown import (
    ExpenseBreakdown,
)
from app.core.findash.forecast_projection import (
    ForecastProjection,
)
from app.core.findash.profit_margin_gauge import (
    ProfitMarginGauge,
)
from app.core.findash.revenue_chart import (
    RevenueChart,
)
from app.core.findash.roi_tracker import (
    FinDashROITracker,
)

logger = logging.getLogger(__name__)


class FinDashOrchestrator:
    """Finansal panel orkestrator.

    Attributes:
        _revenue: Gelir grafigi.
        _expense: Gider dagilimi.
        _cashflow: Nakit akis grafigi.
        _budget: Butce vs gercek.
        _forecast: Tahmin projeksiyonu.
        _costs: Sistem maliyet gorunumu.
        _roi: ROI takipcisi.
        _margin: Kar marji gostergesi.
    """

    def __init__(self) -> None:
        """Orkestratoru baslatir."""
        self._revenue = RevenueChart()
        self._expense = ExpenseBreakdown()
        self._cashflow = CashFlowGraph()
        self._budget = BudgetVsActual()
        self._forecast = ForecastProjection()
        self._costs = CostPerSystemView()
        self._roi = FinDashROITracker()
        self._margin = ProfitMarginGauge()
        logger.info(
            "FinDashOrchestrator baslatildi"
        )

    def full_financial_dashboard(
        self,
        revenue: float = 0.0,
        cost: float = 0.0,
        period: str = "",
        source: str = "overall",
        category: str = "overall",
    ) -> dict[str, Any]:
        """Tam finansal gorunum olusturur.

        Track -> Visualize -> Forecast -> Alert.

        Args:
            revenue: Gelir.
            cost: Maliyet.
            period: Donem.
            source: Kaynak.
            category: Kategori.

        Returns:
            Tam gorunum bilgisi.
        """
        try:
            rev_result = (
                self._revenue.record_revenue(
                    amount=revenue,
                    source=source,
                    period=period,
                )
            )

            exp_result = (
                self._expense.record_expense(
                    category=category,
                    amount=cost,
                    period=period,
                )
            )

            self._cashflow.record_flow(
                flow_type="inflow",
                amount=revenue,
                period=period,
                source=source,
            )
            self._cashflow.record_flow(
                flow_type="outflow",
                amount=cost,
                period=period,
                source=category,
            )

            margin_result = (
                self._margin.record_margin(
                    revenue=revenue,
                    cost=cost,
                    period=period,
                    category=category,
                )
            )

            self._forecast.add_data_point(
                metric="revenue",
                value=revenue,
                period=period,
            )
            self._forecast.add_data_point(
                metric="expense",
                value=cost,
                period=period,
            )

            alerts = self._margin.check_alerts()

            return {
                "revenue": rev_result,
                "expense": exp_result,
                "margin": margin_result,
                "alerts": alerts,
                "period": period,
                "dashboard_ready": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "dashboard_ready": False,
                "error": str(e),
            }

    def executive_view(
        self,
    ) -> dict[str, Any]:
        """Yonetici gorunumu olusturur.

        Returns:
            Yonetici gorunum bilgisi.
        """
        try:
            revenue_growth = (
                self._revenue.calculate_growth()
            )
            expense_trend = (
                self._expense.get_trend()
            )
            cashflow = (
                self._cashflow.get_inflow_outflow()
            )
            margin = (
                self._margin.get_current_margin()
            )
            budget = (
                self._budget.get_variance_analysis()
            )
            investments = (
                self._roi.compare_investments()
            )

            return {
                "revenue_growth": revenue_growth,
                "expense_trend": expense_trend,
                "cashflow_summary": cashflow,
                "current_margin": margin,
                "budget_variance": budget,
                "investments": investments,
                "view_ready": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "view_ready": False,
                "error": str(e),
            }

    def forecast_and_project(
        self,
        months: int = 6,
    ) -> dict[str, Any]:
        """Tahmin ve projeksiyon olusturur.

        Args:
            months: Tahmin donemi.

        Returns:
            Tahmin bilgisi.
        """
        try:
            rev_forecast = (
                self._forecast.forecast_revenue(
                    months=months
                )
            )
            exp_forecast = (
                self._forecast.forecast_expense(
                    months=months
                )
            )
            confidence = (
                self._forecast.get_confidence_bands(
                    months=months
                )
            )
            cashflow_forecast = (
                self._cashflow.forecast_cashflow(
                    months=months
                )
            )
            margin_trend = (
                self._margin.get_trend()
            )

            return {
                "revenue_forecast": rev_forecast,
                "expense_forecast": exp_forecast,
                "confidence_bands": confidence,
                "cashflow_forecast": (
                    cashflow_forecast
                ),
                "margin_trend": margin_trend,
                "months": months,
                "projected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "projected": False,
                "error": str(e),
            }

    def cost_analysis(
        self,
    ) -> dict[str, Any]:
        """Maliyet analizi yapar.

        Returns:
            Maliyet analiz bilgisi.
        """
        try:
            system_costs = (
                self._costs.get_system_costs()
            )
            api_costs = (
                self._costs.get_api_costs()
            )
            infra_costs = (
                self._costs.get_infrastructure_costs()
            )
            optimizations = (
                self._costs.suggest_optimizations()
            )
            expense_breakdown = (
                self._expense.get_category_breakdown()
            )
            top_expenses = (
                self._expense.get_top_expenses()
            )

            return {
                "system_costs": system_costs,
                "api_costs": api_costs,
                "infra_costs": infra_costs,
                "optimizations": optimizations,
                "expense_breakdown": (
                    expense_breakdown
                ),
                "top_expenses": top_expenses,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def budget_tracking(
        self,
        category: str = "",
        budget_amount: float = 0.0,
        actual_amount: float = 0.0,
        period: str = "",
    ) -> dict[str, Any]:
        """Butce takibi yapar.

        Args:
            category: Kategori.
            budget_amount: Butce tutari.
            actual_amount: Gercek tutar.
            period: Donem.

        Returns:
            Takip bilgisi.
        """
        try:
            budget_set = self._budget.set_budget(
                category=category,
                amount=budget_amount,
                period=period,
            )

            actual_rec = (
                self._budget.record_actual(
                    category=category,
                    amount=actual_amount,
                    period=period,
                )
            )

            variance = (
                self._budget.get_variance_analysis(
                    period=period
                )
            )
            overruns = (
                self._budget.check_overruns()
            )
            utilization = (
                self._budget.get_utilization(
                    period=period
                )
            )

            return {
                "budget": budget_set,
                "actual": actual_rec,
                "variance": variance,
                "overruns": overruns,
                "utilization": utilization,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik bilgileri getirir.

        Returns:
            Analitik bilgisi.
        """
        try:
            return {
                "revenue_records": (
                    self._revenue.entry_count
                ),
                "expense_records": (
                    self._expense.expense_count
                ),
                "cashflow_records": (
                    self._cashflow.flow_count
                ),
                "budget_count": (
                    self._budget.budget_count
                ),
                "actual_count": (
                    self._budget.actual_count
                ),
                "forecast_points": (
                    self._forecast.data_point_count
                ),
                "cost_records": (
                    self._costs.cost_count
                ),
                "investment_count": (
                    self._roi.investment_count
                ),
                "margin_records": (
                    self._margin.record_count
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
