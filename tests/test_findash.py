"""Financial Dashboard testleri."""

import pytest

from app.core.findash.revenue_chart import (
    RevenueChart,
)
from app.core.findash.expense_breakdown import (
    ExpenseBreakdown,
)
from app.core.findash.cashflow_graph import (
    CashFlowGraph,
)
from app.core.findash.budget_vs_actual import (
    BudgetVsActual,
)
from app.core.findash.forecast_projection import (
    ForecastProjection,
)
from app.core.findash.cost_per_system_view import (
    CostPerSystemView,
)
from app.core.findash.roi_tracker import (
    FinDashROITracker,
)
from app.core.findash.profit_margin_gauge import (
    ProfitMarginGauge,
)
from app.core.findash.findash_orchestrator import (
    FinDashOrchestrator,
)
from app.models.findash_models import (
    RevenueSource,
    ExpenseCategory,
    FlowType,
    ForecastMetric,
    BudgetStatus,
    MarginStatus,
    RevenueRecord,
    ExpenseRecord,
    CashFlowEntry,
    BudgetEntry,
    ForecastDataPoint,
    InvestmentRecord,
    MarginRecord,
)


class TestRevenueChart:
    """RevenueChart testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.chart = RevenueChart()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.chart.entry_count == 0

    def test_record_revenue(self) -> None:
        """Gelir kayit testi."""
        result = self.chart.record_revenue(
            amount=10000.0,
            source="mapa_health",
            period="2026-01",
        )
        assert result["recorded"] is True
        assert result["amount"] == 10000.0
        assert self.chart.entry_count == 1

    def test_get_time_series(self) -> None:
        """Zaman serisi testi."""
        self.chart.record_revenue(
            amount=10000, period="2026-01"
        )
        self.chart.record_revenue(
            amount=12000, period="2026-02"
        )
        result = self.chart.get_time_series()
        assert result["retrieved"] is True
        assert result["total_periods"] == 2
        assert result["total_revenue"] == 22000.0

    def test_get_breakdown_by_source(self) -> None:
        """Kaynak dagilimi testi."""
        self.chart.record_revenue(
            amount=10000, source="mapa"
        )
        self.chart.record_revenue(
            amount=5000, source="ftrk"
        )
        result = (
            self.chart.get_breakdown_by_source()
        )
        assert result["retrieved"] is True
        assert result["source_count"] == 2
        assert result["total_revenue"] == 15000.0

    def test_calculate_growth(self) -> None:
        """Buyume hesaplama testi."""
        self.chart.record_revenue(
            amount=10000, period="2026-01"
        )
        self.chart.record_revenue(
            amount=12000, period="2026-02"
        )
        result = self.chart.calculate_growth()
        assert result["calculated"] is True
        assert result["growth_rate"] == 20.0
        assert result["trend"] == "growing"

    def test_calculate_growth_insufficient(
        self,
    ) -> None:
        """Yetersiz veri buyume testi."""
        self.chart.record_revenue(amount=10000)
        result = self.chart.calculate_growth()
        assert result["calculated"] is True
        assert (
            result["trend"]
            == "insufficient_data"
        )

    def test_compare_periods(self) -> None:
        """Donem karsilastirma testi."""
        self.chart.record_revenue(
            amount=10000, period="2026-01"
        )
        self.chart.record_revenue(
            amount=15000, period="2026-02"
        )
        result = self.chart.compare_periods(
            period_a="2026-01",
            period_b="2026-02",
        )
        assert result["compared"] is True
        assert result["difference"] == 5000.0
        assert result["percentage_change"] == 50.0

    def test_generate_chart_data(self) -> None:
        """Grafik verisi testi."""
        self.chart.record_revenue(
            amount=10000,
            source="mapa",
            period="2026-01",
        )
        result = self.chart.generate_chart_data()
        assert result["generated"] is True
        assert len(result["time_series"]) == 1

    def test_record_revenue_with_currency(
        self,
    ) -> None:
        """Para birimli kayit testi."""
        result = self.chart.record_revenue(
            amount=5000,
            source="export",
            currency="USD",
        )
        assert result["recorded"] is True

    def test_multiple_sources_same_period(
        self,
    ) -> None:
        """Ayni donem coklu kaynak testi."""
        self.chart.record_revenue(
            amount=10000,
            source="a",
            period="2026-01",
        )
        self.chart.record_revenue(
            amount=5000,
            source="b",
            period="2026-01",
        )
        ts = self.chart.get_time_series()
        assert ts["data_points"][0]["revenue"] == 15000.0


class TestExpenseBreakdown:
    """ExpenseBreakdown testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.expense = ExpenseBreakdown()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.expense.expense_count == 0

    def test_record_expense(self) -> None:
        """Gider kayit testi."""
        result = self.expense.record_expense(
            amount=5000.0,
            category="api",
            period="2026-01",
        )
        assert result["recorded"] is True
        assert result["amount"] == 5000.0
        assert self.expense.expense_count == 1

    def test_get_category_breakdown(self) -> None:
        """Kategori dagilimi testi."""
        self.expense.record_expense(
            amount=5000, category="api"
        )
        self.expense.record_expense(
            amount=3000, category="infra"
        )
        result = (
            self.expense.get_category_breakdown()
        )
        assert result["retrieved"] is True
        assert result["category_count"] == 2
        assert result["total_expenses"] == 8000.0

    def test_get_trend(self) -> None:
        """Trend analizi testi."""
        self.expense.record_expense(
            amount=5000, period="2026-01"
        )
        self.expense.record_expense(
            amount=6000, period="2026-02"
        )
        result = self.expense.get_trend()
        assert result["analyzed"] is True
        assert result["direction"] == "increasing"

    def test_get_trend_insufficient(self) -> None:
        """Yetersiz veri trend testi."""
        self.expense.record_expense(amount=5000)
        result = self.expense.get_trend()
        assert result["analyzed"] is True
        assert (
            result["trend"]
            == "insufficient_data"
        )

    def test_get_top_expenses(self) -> None:
        """En yuksek giderler testi."""
        self.expense.record_expense(
            amount=10000, description="sunucu"
        )
        self.expense.record_expense(
            amount=5000, description="api"
        )
        self.expense.record_expense(
            amount=8000, description="reklam"
        )
        result = self.expense.get_top_expenses(
            limit=2
        )
        assert result["retrieved"] is True
        assert result["count"] == 2
        assert (
            result["top_expenses"][0]["amount"]
            == 10000
        )

    def test_detect_anomalies(self) -> None:
        """Anomali tespiti testi."""
        self.expense.record_expense(
            amount=1000, category="api"
        )
        self.expense.record_expense(
            amount=1200, category="api"
        )
        self.expense.record_expense(
            amount=5000, category="api"
        )
        result = self.expense.detect_anomalies(
            threshold_multiplier=2.0
        )
        assert result["detected"] is True
        assert result["anomaly_count"] > 0

    def test_detect_anomalies_no_anomaly(
        self,
    ) -> None:
        """Anomali yok testi."""
        self.expense.record_expense(
            amount=1000, category="api"
        )
        self.expense.record_expense(
            amount=1100, category="api"
        )
        result = self.expense.detect_anomalies()
        assert result["detected"] is True
        assert result["anomaly_count"] == 0

    def test_recurring_expense(self) -> None:
        """Tekrarli gider testi."""
        result = self.expense.record_expense(
            amount=500,
            category="saas",
            recurring=True,
        )
        assert result["recorded"] is True


class TestCashFlowGraph:
    """CashFlowGraph testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.cashflow = CashFlowGraph()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.cashflow.flow_count == 0

    def test_record_inflow(self) -> None:
        """Giris kayit testi."""
        result = self.cashflow.record_flow(
            amount=10000,
            flow_type="inflow",
            period="2026-01",
        )
        assert result["recorded"] is True
        assert result["flow_type"] == "inflow"

    def test_record_outflow(self) -> None:
        """Cikis kayit testi."""
        result = self.cashflow.record_flow(
            amount=5000,
            flow_type="outflow",
            period="2026-01",
        )
        assert result["recorded"] is True
        assert result["flow_type"] == "outflow"

    def test_get_inflow_outflow(self) -> None:
        """Giris/cikis ozeti testi."""
        self.cashflow.record_flow(
            amount=10000, flow_type="inflow"
        )
        self.cashflow.record_flow(
            amount=4000, flow_type="outflow"
        )
        result = (
            self.cashflow.get_inflow_outflow()
        )
        assert result["retrieved"] is True
        assert result["total_inflow"] == 10000.0
        assert result["total_outflow"] == 4000.0
        assert result["net_cash_flow"] == 6000.0
        assert result["is_positive"] is True

    def test_negative_net(self) -> None:
        """Negatif net akis testi."""
        self.cashflow.record_flow(
            amount=3000, flow_type="inflow"
        )
        self.cashflow.record_flow(
            amount=5000, flow_type="outflow"
        )
        result = (
            self.cashflow.get_inflow_outflow()
        )
        assert result["is_positive"] is False

    def test_get_period_breakdown(self) -> None:
        """Donem dagilimi testi."""
        self.cashflow.record_flow(
            amount=10000,
            flow_type="inflow",
            period="2026-01",
        )
        self.cashflow.record_flow(
            amount=4000,
            flow_type="outflow",
            period="2026-01",
        )
        result = (
            self.cashflow.get_period_breakdown()
        )
        assert result["retrieved"] is True
        assert result["period_count"] == 1
        assert (
            result["periods"][0]["net"] == 6000.0
        )

    def test_calculate_runway(self) -> None:
        """Pist hesaplama testi."""
        self.cashflow.record_flow(
            amount=5000,
            flow_type="outflow",
            period="2026-01",
        )
        result = self.cashflow.calculate_runway(
            current_balance=30000
        )
        assert result["calculated"] is True
        assert result["runway_months"] == 6
        assert result["status"] == "adequate"

    def test_calculate_runway_critical(
        self,
    ) -> None:
        """Kritik pist testi."""
        self.cashflow.record_flow(
            amount=10000,
            flow_type="outflow",
            period="2026-01",
        )
        result = self.cashflow.calculate_runway(
            current_balance=15000
        )
        assert result["status"] == "critical"

    def test_forecast_cashflow(self) -> None:
        """Nakit akis tahmini testi."""
        self.cashflow.record_flow(
            amount=10000,
            flow_type="inflow",
            period="2026-01",
        )
        self.cashflow.record_flow(
            amount=6000,
            flow_type="outflow",
            period="2026-01",
        )
        result = (
            self.cashflow.forecast_cashflow(
                months=3
            )
        )
        assert result["forecasted"] is True
        assert len(result["forecast"]) == 3

    def test_find_critical_points(self) -> None:
        """Kritik noktalar testi."""
        self.cashflow.record_flow(
            amount=3000,
            flow_type="inflow",
            period="2026-01",
        )
        self.cashflow.record_flow(
            amount=8000,
            flow_type="outflow",
            period="2026-01",
        )
        result = (
            self.cashflow.find_critical_points()
        )
        assert result["retrieved"] is True
        assert result["has_critical"] is True

    def test_find_no_critical_points(self) -> None:
        """Kritik nokta yok testi."""
        self.cashflow.record_flow(
            amount=10000,
            flow_type="inflow",
            period="2026-01",
        )
        self.cashflow.record_flow(
            amount=3000,
            flow_type="outflow",
            period="2026-01",
        )
        result = (
            self.cashflow.find_critical_points()
        )
        assert result["has_critical"] is False

    def test_empty_forecast(self) -> None:
        """Bos tahmin testi."""
        result = (
            self.cashflow.forecast_cashflow()
        )
        assert result["forecasted"] is True
        assert result["forecast"] == []


class TestBudgetVsActual:
    """BudgetVsActual testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.bva = BudgetVsActual()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.bva.budget_count == 0
        assert self.bva.actual_count == 0

    def test_set_budget(self) -> None:
        """Butce belirleme testi."""
        result = self.bva.set_budget(
            category="marketing",
            amount=10000,
            period="2026-01",
        )
        assert result["set"] is True
        assert self.bva.budget_count == 1

    def test_record_actual(self) -> None:
        """Gercek harcama testi."""
        result = self.bva.record_actual(
            category="marketing",
            amount=8000,
            period="2026-01",
        )
        assert result["recorded"] is True
        assert self.bva.actual_count == 1

    def test_variance_analysis(self) -> None:
        """Sapma analizi testi."""
        self.bva.set_budget(
            category="marketing",
            amount=10000,
        )
        self.bva.record_actual(
            category="marketing",
            amount=12000,
        )
        result = (
            self.bva.get_variance_analysis()
        )
        assert result["analyzed"] is True
        assert result["category_count"] == 1
        v = result["variances"][0]
        assert v["status"] == "over_budget"
        assert v["variance"] == 2000.0

    def test_under_budget(self) -> None:
        """Butce altinda testi."""
        self.bva.set_budget(
            category="ops", amount=10000
        )
        self.bva.record_actual(
            category="ops", amount=7000
        )
        result = (
            self.bva.get_variance_analysis()
        )
        v = result["variances"][0]
        assert v["status"] == "under_budget"

    def test_check_overruns(self) -> None:
        """Asim kontrolu testi."""
        self.bva.set_budget(
            category="api", amount=5000
        )
        self.bva.record_actual(
            category="api", amount=6000
        )
        result = self.bva.check_overruns(
            threshold_pct=10.0
        )
        assert result["checked"] is True
        assert result["overrun_count"] == 1

    def test_get_utilization(self) -> None:
        """Kullanim orani testi."""
        self.bva.set_budget(
            category="infra", amount=10000
        )
        self.bva.record_actual(
            category="infra", amount=7500
        )
        result = self.bva.get_utilization()
        assert result["retrieved"] is True
        assert result["utilization_pct"] == 75.0

    def test_drill_down(self) -> None:
        """Detaya inme testi."""
        self.bva.set_budget(
            category="marketing", amount=10000
        )
        self.bva.record_actual(
            category="marketing",
            amount=3000,
            description="ads",
        )
        self.bva.record_actual(
            category="marketing",
            amount=5000,
            description="content",
        )
        result = self.bva.drill_down(
            category="marketing"
        )
        assert result["retrieved"] is True
        assert result["line_count"] == 2
        assert result["total_actual"] == 8000.0

    def test_period_filter(self) -> None:
        """Donem filtresi testi."""
        self.bva.set_budget(
            category="ops",
            amount=5000,
            period="2026-01",
        )
        self.bva.set_budget(
            category="ops",
            amount=6000,
            period="2026-02",
        )
        result = (
            self.bva.get_variance_analysis(
                period="2026-01"
            )
        )
        assert result["analyzed"] is True


class TestForecastProjection:
    """ForecastProjection testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.forecast = ForecastProjection()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.forecast.data_point_count == 0

    def test_add_data_point(self) -> None:
        """Veri noktasi ekleme testi."""
        result = self.forecast.add_data_point(
            metric="revenue",
            value=10000,
            period="2026-01",
        )
        assert result["added"] is True
        assert (
            self.forecast.data_point_count == 1
        )

    def test_forecast_revenue(self) -> None:
        """Gelir tahmini testi."""
        for i, v in enumerate(
            [10000, 11000, 12000, 13000]
        ):
            self.forecast.add_data_point(
                metric="revenue",
                value=v,
                period=f"2026-0{i + 1}",
            )
        result = (
            self.forecast.forecast_revenue(
                months=3
            )
        )
        assert result["forecasted"] is True
        assert len(result["forecast"]) == 3
        assert result["slope"] > 0

    def test_forecast_revenue_insufficient(
        self,
    ) -> None:
        """Yetersiz veri gelir tahmini testi."""
        self.forecast.add_data_point(
            metric="revenue", value=10000
        )
        result = (
            self.forecast.forecast_revenue()
        )
        assert result["forecasted"] is True
        assert (
            result["trend"]
            == "insufficient_data"
        )

    def test_forecast_expense(self) -> None:
        """Gider tahmini testi."""
        for i, v in enumerate(
            [5000, 5500, 6000]
        ):
            self.forecast.add_data_point(
                metric="expense",
                value=v,
                period=f"2026-0{i + 1}",
            )
        result = (
            self.forecast.forecast_expense(
                months=3
            )
        )
        assert result["forecasted"] is True
        assert len(result["forecast"]) == 3

    def test_create_scenario(self) -> None:
        """Senaryo olusturma testi."""
        self.forecast.add_data_point(
            metric="revenue", value=10000
        )
        self.forecast.add_data_point(
            metric="expense", value=6000
        )
        result = self.forecast.create_scenario(
            name="optimistic",
            scenario_type="best",
            revenue_growth=10.0,
            expense_growth=3.0,
            months=6,
        )
        assert result["created"] is True
        assert len(result["projections"]) == 6
        assert (
            result["projections"][0]["revenue"]
            > 10000
        )

    def test_add_assumption(self) -> None:
        """Varsayim ekleme testi."""
        result = self.forecast.add_assumption(
            name="buyume",
            value="%10 yillik",
            category="gelir",
        )
        assert result["added"] is True

    def test_get_confidence_bands(self) -> None:
        """Guven bantlari testi."""
        for v in [10000, 11000, 12000, 13000]:
            self.forecast.add_data_point(
                metric="revenue", value=v
            )
        result = (
            self.forecast.get_confidence_bands(
                months=3
            )
        )
        assert result["retrieved"] is True
        assert len(result["bands"]) == 3
        assert result["confidence"] == "calculated"
        for band in result["bands"]:
            assert band["lower"] < band["upper"]

    def test_get_confidence_insufficient(
        self,
    ) -> None:
        """Yetersiz veri guven bantlari testi."""
        self.forecast.add_data_point(
            metric="revenue", value=10000
        )
        result = (
            self.forecast.get_confidence_bands()
        )
        assert result["retrieved"] is True
        assert (
            result["confidence"]
            == "insufficient_data"
        )

    def test_get_assumptions(self) -> None:
        """Varsayim listesi testi."""
        self.forecast.add_assumption(
            name="a1", value="v1"
        )
        self.forecast.add_assumption(
            name="a2", value="v2"
        )
        result = self.forecast.get_assumptions()
        assert result["retrieved"] is True
        assert result["assumption_count"] == 2


class TestCostPerSystemView:
    """CostPerSystemView testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.costs = CostPerSystemView()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.costs.cost_count == 0

    def test_record_cost(self) -> None:
        """Maliyet kayit testi."""
        result = self.costs.record_cost(
            system_name="nlp_engine",
            cost_type="api",
            amount=500.0,
            period="2026-01",
        )
        assert result["recorded"] is True
        assert self.costs.cost_count == 1

    def test_get_system_costs(self) -> None:
        """Sistem bazli maliyet testi."""
        self.costs.record_cost(
            system_name="nlp", amount=500
        )
        self.costs.record_cost(
            system_name="vision", amount=300
        )
        result = self.costs.get_system_costs()
        assert result["retrieved"] is True
        assert result["system_count"] == 2
        assert result["total_cost"] == 800.0

    def test_get_api_costs(self) -> None:
        """API maliyet testi."""
        self.costs.record_cost(
            system_name="nlp",
            cost_type="api",
            amount=500,
        )
        self.costs.record_cost(
            system_name="nlp",
            cost_type="infrastructure",
            amount=300,
        )
        result = self.costs.get_api_costs()
        assert result["retrieved"] is True
        assert result["total_api_cost"] == 500.0

    def test_get_infrastructure_costs(
        self,
    ) -> None:
        """Altyapi maliyet testi."""
        self.costs.record_cost(
            system_name="db",
            cost_type="infrastructure",
            amount=1000,
        )
        result = (
            self.costs.get_infrastructure_costs()
        )
        assert result["retrieved"] is True
        assert (
            result["total_infra_cost"] == 1000.0
        )

    def test_suggest_optimizations(self) -> None:
        """Optimizasyon oneri testi."""
        self.costs.record_cost(
            system_name="nlp", amount=8000
        )
        self.costs.record_cost(
            system_name="other", amount=2000
        )
        result = (
            self.costs.suggest_optimizations(
                threshold_pct=20.0
            )
        )
        assert result["suggested"] is True
        assert result["suggestion_count"] >= 1

    def test_suggest_trend_optimization(
        self,
    ) -> None:
        """Artan trend optimizasyon testi."""
        for v in [100, 200, 300]:
            self.costs.record_cost(
                system_name="api_gw",
                amount=v,
            )
        result = (
            self.costs.suggest_optimizations()
        )
        assert result["suggested"] is True

    def test_get_cost_trend(self) -> None:
        """Maliyet trendi testi."""
        self.costs.record_cost(
            system_name="nlp",
            amount=500,
            period="2026-01",
        )
        self.costs.record_cost(
            system_name="nlp",
            amount=600,
            period="2026-02",
        )
        result = self.costs.get_cost_trend(
            system_name="nlp"
        )
        assert result["retrieved"] is True
        assert result["direction"] == "increasing"

    def test_get_cost_trend_insufficient(
        self,
    ) -> None:
        """Yetersiz veri trend testi."""
        self.costs.record_cost(
            system_name="nlp", amount=500
        )
        result = self.costs.get_cost_trend(
            system_name="nlp"
        )
        assert (
            result["direction"]
            == "insufficient_data"
        )


class TestFinDashROITracker:
    """FinDashROITracker testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.roi = FinDashROITracker()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.roi.investment_count == 0

    def test_track_investment(self) -> None:
        """Yatirim takip testi."""
        result = self.roi.track_investment(
            name="AI Platform",
            amount=50000,
            category="technology",
        )
        assert result["tracked"] is True
        assert self.roi.investment_count == 1

    def test_record_return(self) -> None:
        """Getiri kayit testi."""
        inv = self.roi.track_investment(
            name="Proje A", amount=10000
        )
        iid = inv["investment_id"]
        result = self.roi.record_return(
            investment_id=iid,
            amount=3000,
            period="2026-01",
        )
        assert result["recorded"] is True
        assert result["total_return"] == 3000.0

    def test_record_return_not_found(
        self,
    ) -> None:
        """Bulunamayan yatirim getiri testi."""
        result = self.roi.record_return(
            investment_id="invalid",
            amount=1000,
        )
        assert result["recorded"] is False
        assert result["reason"] == "not_found"

    def test_calculate_roi(self) -> None:
        """ROI hesaplama testi."""
        inv = self.roi.track_investment(
            name="Proje B", amount=10000
        )
        iid = inv["investment_id"]
        self.roi.record_return(
            investment_id=iid, amount=15000
        )
        result = self.roi.calculate_roi(
            investment_id=iid
        )
        assert result["calculated"] is True
        assert result["roi_percentage"] == 50.0
        assert result["status"] == "profitable"

    def test_calculate_roi_loss(self) -> None:
        """Zarar ROI testi."""
        inv = self.roi.track_investment(
            name="Proje C", amount=10000
        )
        iid = inv["investment_id"]
        self.roi.record_return(
            investment_id=iid, amount=5000
        )
        result = self.roi.calculate_roi(
            investment_id=iid
        )
        assert result["status"] == "loss"

    def test_calculate_roi_not_found(
        self,
    ) -> None:
        """Bulunamayan ROI testi."""
        result = self.roi.calculate_roi(
            investment_id="invalid"
        )
        assert result["calculated"] is False

    def test_payback_period(self) -> None:
        """Geri odeme suresi testi."""
        inv = self.roi.track_investment(
            name="D", amount=10000
        )
        iid = inv["investment_id"]
        for _ in range(5):
            self.roi.record_return(
                investment_id=iid, amount=3000
            )
        result = (
            self.roi.calculate_payback_period(
                investment_id=iid
            )
        )
        assert result["calculated"] is True
        assert result["paid_back"] is True
        assert result["payback_months"] == 4

    def test_payback_no_returns(self) -> None:
        """Getiri yok geri odeme testi."""
        inv = self.roi.track_investment(
            name="E", amount=10000
        )
        iid = inv["investment_id"]
        result = (
            self.roi.calculate_payback_period(
                investment_id=iid
            )
        )
        assert result["calculated"] is True
        assert result["status"] == "no_returns"

    def test_compare_investments(self) -> None:
        """Yatirim karsilastirma testi."""
        inv1 = self.roi.track_investment(
            name="A", amount=10000
        )
        inv2 = self.roi.track_investment(
            name="B", amount=5000
        )
        self.roi.record_return(
            investment_id=inv1["investment_id"],
            amount=15000,
        )
        self.roi.record_return(
            investment_id=inv2["investment_id"],
            amount=10000,
        )
        result = self.roi.compare_investments()
        assert result["compared"] is True
        assert result["investment_count"] == 2
        assert (
            result["best_roi"]["roi"] == 100.0
        )

    def test_compare_empty(self) -> None:
        """Bos karsilastirma testi."""
        result = self.roi.compare_investments()
        assert result["compared"] is True
        assert result["investment_count"] == 0


class TestProfitMarginGauge:
    """ProfitMarginGauge testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.gauge = ProfitMarginGauge()

    def test_init(self) -> None:
        """Baslatma testi."""
        assert self.gauge.record_count == 0

    def test_record_margin(self) -> None:
        """Marj kayit testi."""
        result = self.gauge.record_margin(
            revenue=10000,
            cost=7000,
            period="2026-01",
        )
        assert result["recorded"] is True
        assert result["margin_pct"] == 30.0
        assert result["profit"] == 3000.0

    def test_record_margin_zero_revenue(
        self,
    ) -> None:
        """Sifir gelir marj testi."""
        result = self.gauge.record_margin(
            revenue=0, cost=1000
        )
        assert result["recorded"] is True
        assert result["margin_pct"] == 0.0

    def test_get_current_margin(self) -> None:
        """Mevcut marj testi."""
        self.gauge.record_margin(
            revenue=10000, cost=7000
        )
        result = self.gauge.get_current_margin()
        assert result["retrieved"] is True
        assert result["margin_pct"] == 30.0

    def test_get_current_margin_empty(
        self,
    ) -> None:
        """Bos mevcut marj testi."""
        result = self.gauge.get_current_margin()
        assert result["retrieved"] is True
        assert result["margin_pct"] == 0.0

    def test_set_target(self) -> None:
        """Hedef belirleme testi."""
        result = self.gauge.set_target(
            category="overall",
            target_pct=25.0,
            min_pct=15.0,
        )
        assert result["set"] is True
        assert result["target_pct"] == 25.0

    def test_compare_to_target_above(
        self,
    ) -> None:
        """Hedef ustu testi."""
        self.gauge.record_margin(
            revenue=10000, cost=6000
        )
        self.gauge.set_target(target_pct=20.0)
        result = self.gauge.compare_to_target()
        assert result["compared"] is True
        assert result["status"] == "above_target"

    def test_compare_to_target_acceptable(
        self,
    ) -> None:
        """Kabul edilebilir marj testi."""
        self.gauge.record_margin(
            revenue=10000, cost=8500
        )
        self.gauge.set_target(
            target_pct=20.0, min_pct=10.0
        )
        result = self.gauge.compare_to_target()
        assert result["compared"] is True
        assert result["status"] == "acceptable"

    def test_compare_to_target_below(
        self,
    ) -> None:
        """Minimum alti testi."""
        self.gauge.record_margin(
            revenue=10000, cost=9500
        )
        self.gauge.set_target(
            target_pct=20.0, min_pct=10.0
        )
        result = self.gauge.compare_to_target()
        assert result["compared"] is True
        assert (
            result["status"] == "below_minimum"
        )

    def test_compare_no_target(self) -> None:
        """Hedefsiz karsilastirma testi."""
        self.gauge.record_margin(
            revenue=10000, cost=7000
        )
        result = self.gauge.compare_to_target()
        assert result["compared"] is True
        assert result["target"] is None

    def test_get_trend(self) -> None:
        """Marj trendi testi."""
        self.gauge.record_margin(
            revenue=10000, cost=8000
        )
        self.gauge.record_margin(
            revenue=10000, cost=7000
        )
        self.gauge.record_margin(
            revenue=10000, cost=6000
        )
        result = self.gauge.get_trend()
        assert result["analyzed"] is True
        assert result["direction"] == "improving"

    def test_get_trend_declining(self) -> None:
        """Azalan marj trendi testi."""
        self.gauge.record_margin(
            revenue=10000, cost=6000
        )
        self.gauge.record_margin(
            revenue=10000, cost=7000
        )
        self.gauge.record_margin(
            revenue=10000, cost=8000
        )
        result = self.gauge.get_trend()
        assert result["direction"] == "declining"

    def test_get_trend_insufficient(
        self,
    ) -> None:
        """Yetersiz veri trend testi."""
        self.gauge.record_margin(
            revenue=10000, cost=7000
        )
        result = self.gauge.get_trend()
        assert (
            result["trend"]
            == "insufficient_data"
        )

    def test_check_alerts(self) -> None:
        """Uyari kontrolu testi."""
        self.gauge.record_margin(
            revenue=10000,
            cost=9500,
            category="service",
        )
        result = self.gauge.check_alerts(
            alert_threshold=10.0
        )
        assert result["checked"] is True
        assert result["alert_count"] == 1
        assert (
            result["alerts"][0]["severity"]
            == "warning"
        )

    def test_check_alerts_critical(self) -> None:
        """Kritik uyari testi."""
        self.gauge.record_margin(
            revenue=10000,
            cost=12000,
            category="product",
        )
        result = self.gauge.check_alerts(
            alert_threshold=10.0
        )
        assert result["alert_count"] == 1
        assert (
            result["alerts"][0]["severity"]
            == "critical"
        )

    def test_check_no_alerts(self) -> None:
        """Uyari yok testi."""
        self.gauge.record_margin(
            revenue=10000, cost=5000
        )
        result = self.gauge.check_alerts()
        assert result["alert_count"] == 0


class TestFinDashOrchestrator:
    """FinDashOrchestrator testleri."""

    def setup_method(self) -> None:
        """Test baslatma."""
        self.orch = FinDashOrchestrator()

    def test_init(self) -> None:
        """Baslatma testi."""
        analytics = self.orch.get_analytics()
        assert analytics["retrieved"] is True
        assert analytics["revenue_records"] == 0

    def test_full_financial_dashboard(
        self,
    ) -> None:
        """Tam gorunum testi."""
        result = (
            self.orch.full_financial_dashboard(
                revenue=50000,
                cost=30000,
                period="2026-01",
                source="mapa_health",
                category="operations",
            )
        )
        assert result["dashboard_ready"] is True
        assert (
            result["revenue"]["recorded"] is True
        )
        assert (
            result["expense"]["recorded"] is True
        )
        assert (
            result["margin"]["recorded"] is True
        )

    def test_executive_view(self) -> None:
        """Yonetici gorunumu testi."""
        self.orch.full_financial_dashboard(
            revenue=50000,
            cost=30000,
            period="2026-01",
        )
        result = self.orch.executive_view()
        assert result["view_ready"] is True
        assert "revenue_growth" in result
        assert "current_margin" in result

    def test_forecast_and_project(self) -> None:
        """Tahmin ve projeksiyon testi."""
        for i, (r, c) in enumerate([
            (50000, 30000),
            (55000, 32000),
            (60000, 35000),
        ]):
            self.orch.full_financial_dashboard(
                revenue=r,
                cost=c,
                period=f"2026-0{i + 1}",
            )
        result = (
            self.orch.forecast_and_project(
                months=3
            )
        )
        assert result["projected"] is True
        assert "revenue_forecast" in result
        assert "expense_forecast" in result

    def test_cost_analysis(self) -> None:
        """Maliyet analizi testi."""
        result = self.orch.cost_analysis()
        assert result["analyzed"] is True
        assert "system_costs" in result
        assert "api_costs" in result

    def test_budget_tracking(self) -> None:
        """Butce takibi testi."""
        result = self.orch.budget_tracking(
            category="marketing",
            budget_amount=10000,
            actual_amount=8000,
            period="2026-01",
        )
        assert result["tracked"] is True
        assert result["budget"]["set"] is True
        assert (
            result["actual"]["recorded"] is True
        )

    def test_get_analytics(self) -> None:
        """Analitik testi."""
        self.orch.full_financial_dashboard(
            revenue=50000, cost=30000
        )
        result = self.orch.get_analytics()
        assert result["retrieved"] is True
        assert result["revenue_records"] == 1
        assert result["expense_records"] == 1
        assert result["cashflow_records"] == 2
        assert result["margin_records"] == 1

    def test_multiple_periods(self) -> None:
        """Coklu donem testi."""
        for i in range(1, 4):
            self.orch.full_financial_dashboard(
                revenue=50000 + i * 5000,
                cost=30000 + i * 2000,
                period=f"2026-0{i}",
            )
        analytics = self.orch.get_analytics()
        assert analytics["revenue_records"] == 3
        assert (
            analytics["forecast_points"] == 6
        )

    def test_budget_overrun_detection(
        self,
    ) -> None:
        """Butce asim tespiti testi."""
        self.orch.budget_tracking(
            category="ads",
            budget_amount=5000,
            actual_amount=7000,
            period="2026-01",
        )
        result = self.orch.budget_tracking(
            category="dev",
            budget_amount=10000,
            actual_amount=9000,
            period="2026-01",
        )
        assert result["tracked"] is True


class TestFindashModels:
    """Findash model testleri."""

    def test_revenue_source_enum(self) -> None:
        """Gelir kaynagi enum testi."""
        assert (
            RevenueSource.PRODUCT == "product"
        )
        assert (
            RevenueSource.SUBSCRIPTION
            == "subscription"
        )

    def test_expense_category_enum(self) -> None:
        """Gider kategorisi enum testi."""
        assert (
            ExpenseCategory.API == "api"
        )
        assert (
            ExpenseCategory.INFRASTRUCTURE
            == "infrastructure"
        )

    def test_flow_type_enum(self) -> None:
        """Akis turu enum testi."""
        assert FlowType.INFLOW == "inflow"
        assert FlowType.OUTFLOW == "outflow"

    def test_forecast_metric_enum(self) -> None:
        """Tahmin metrik enum testi."""
        assert (
            ForecastMetric.REVENUE == "revenue"
        )
        assert (
            ForecastMetric.PROFIT == "profit"
        )

    def test_budget_status_enum(self) -> None:
        """Butce durum enum testi."""
        assert (
            BudgetStatus.ON_BUDGET == "on_budget"
        )
        assert (
            BudgetStatus.OVER_BUDGET
            == "over_budget"
        )

    def test_margin_status_enum(self) -> None:
        """Marj durum enum testi."""
        assert (
            MarginStatus.ABOVE_TARGET
            == "above_target"
        )
        assert (
            MarginStatus.BELOW_MINIMUM
            == "below_minimum"
        )

    def test_revenue_record_model(self) -> None:
        """Gelir kaydi modeli testi."""
        record = RevenueRecord(
            amount=10000, source="mapa"
        )
        assert record.amount == 10000
        assert record.source == "mapa"

    def test_expense_record_model(self) -> None:
        """Gider kaydi modeli testi."""
        record = ExpenseRecord(
            category="api", amount=5000
        )
        assert record.category == "api"
        assert record.amount == 5000

    def test_cashflow_entry_model(self) -> None:
        """Nakit akis kaydi modeli testi."""
        entry = CashFlowEntry(
            flow_type=FlowType.INFLOW,
            amount=10000,
        )
        assert (
            entry.flow_type == FlowType.INFLOW
        )
        assert entry.amount == 10000

    def test_budget_entry_model(self) -> None:
        """Butce kaydi modeli testi."""
        entry = BudgetEntry(
            category="ops", amount=10000
        )
        assert entry.category == "ops"

    def test_forecast_data_point_model(
        self,
    ) -> None:
        """Tahmin veri noktasi modeli testi."""
        point = ForecastDataPoint(
            metric=ForecastMetric.REVENUE,
            value=10000,
        )
        assert (
            point.metric
            == ForecastMetric.REVENUE
        )

    def test_investment_record_model(
        self,
    ) -> None:
        """Yatirim kaydi modeli testi."""
        record = InvestmentRecord(
            name="AI", amount=50000
        )
        assert record.name == "AI"
        assert record.period_months == 12

    def test_margin_record_model(self) -> None:
        """Marj kaydi modeli testi."""
        record = MarginRecord(
            revenue=10000, cost=7000
        )
        assert record.revenue == 10000
        assert record.category == "overall"
