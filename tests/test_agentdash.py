"""Agent Performance Dashboard testleri."""

import pytest

from app.core.agentdash import (
    AgentDashOrchestrator,
    AgentImprovementTracker,
    AgentLifecycleView,
    AgentRanking,
    AgentScorecard,
    ConfidenceTrend,
    CostEfficiencyChart,
    PerformanceComparison,
    TaskCompletionRate,
)
from app.models.agentdash_models import (
    AgentLifecycleRecord,
    AgentMetricRecord,
    AgentStatus,
    ConfidenceRecord,
    CostRecord,
    HealthLevel,
    ImprovementRecord,
    MetricType,
    RankingMetric,
    TaskRecord,
    TaskStatus,
    TrendDirection,
)


# ==================== AgentScorecard ====================


class TestAgentScorecard:
    """AgentScorecard testleri."""

    def setup_method(self) -> None:
        self.sc = AgentScorecard()

    def test_init(self) -> None:
        assert self.sc.agent_count == 0

    def test_register_agent(self) -> None:
        r = self.sc.register_agent(
            agent_id="a1",
            agent_name="Test",
            agent_type="coding",
        )
        assert r["registered"] is True
        assert r["agent_id"] == "a1"
        assert self.sc.agent_count == 1

    def test_register_agent_auto_id(self) -> None:
        r = self.sc.register_agent(
            agent_name="Auto"
        )
        assert r["registered"] is True
        assert r["agent_id"].startswith("ag_")

    def test_record_metric(self) -> None:
        self.sc.register_agent(agent_id="a1")
        r = self.sc.record_metric(
            agent_id="a1",
            success=True,
            quality_score=85.0,
            duration_ms=100,
        )
        assert r["recorded"] is True
        assert r["success"] is True

    def test_record_metric_updates_agent(self) -> None:
        self.sc.register_agent(agent_id="a1")
        self.sc.record_metric(
            agent_id="a1",
            success=True,
            quality_score=90.0,
        )
        self.sc.record_metric(
            agent_id="a1",
            success=False,
        )
        card = self.sc.get_scorecard(agent_id="a1")
        assert card["total_tasks"] == 2
        assert card["completed_tasks"] == 1
        assert card["failed_tasks"] == 1

    def test_get_scorecard(self) -> None:
        self.sc.register_agent(agent_id="a1")
        self.sc.record_metric(
            agent_id="a1",
            success=True,
            quality_score=80.0,
            duration_ms=200,
        )
        card = self.sc.get_scorecard(agent_id="a1")
        assert card["retrieved"] is True
        assert card["found"] is True
        assert card["success_rate"] == 100.0
        assert card["avg_quality"] == 80.0

    def test_get_scorecard_not_found(self) -> None:
        card = self.sc.get_scorecard(agent_id="xx")
        assert card["found"] is False

    def test_get_trend_insufficient(self) -> None:
        self.sc.register_agent(agent_id="a1")
        self.sc.record_metric(agent_id="a1")
        t = self.sc.get_trend(agent_id="a1")
        assert t["trend"] == "insufficient_data"

    def test_get_trend_improving(self) -> None:
        self.sc.register_agent(agent_id="a1")
        for _ in range(3):
            self.sc.record_metric(
                agent_id="a1", success=False
            )
        for _ in range(3):
            self.sc.record_metric(
                agent_id="a1", success=True
            )
        t = self.sc.get_trend(agent_id="a1")
        assert t["analyzed"] is True
        assert t["direction"] == "improving"

    def test_get_all_scorecards(self) -> None:
        self.sc.register_agent(agent_id="a1")
        self.sc.register_agent(agent_id="a2")
        self.sc.record_metric(agent_id="a1")
        r = self.sc.get_all_scorecards()
        assert r["retrieved"] is True
        assert r["agent_count"] >= 1


# ==================== TaskCompletionRate ====================


class TestTaskCompletionRate:
    """TaskCompletionRate testleri."""

    def setup_method(self) -> None:
        self.tc = TaskCompletionRate()

    def test_init(self) -> None:
        assert self.tc.task_count == 0

    def test_record_task(self) -> None:
        r = self.tc.record_task(
            agent_id="a1",
            status="completed",
            duration_ms=500,
        )
        assert r["recorded"] is True
        assert self.tc.task_count == 1

    def test_get_completion_rate_empty(self) -> None:
        r = self.tc.get_completion_rate()
        assert r["retrieved"] is True
        assert r["completion_rate"] == 0.0

    def test_get_completion_rate(self) -> None:
        self.tc.record_task(
            agent_id="a1", status="completed"
        )
        self.tc.record_task(
            agent_id="a1", status="failed"
        )
        r = self.tc.get_completion_rate(
            agent_id="a1"
        )
        assert r["completion_rate"] == 50.0
        assert r["completed"] == 1
        assert r["failed"] == 1

    def test_get_completion_rate_all(self) -> None:
        self.tc.record_task(
            agent_id="a1", status="completed"
        )
        self.tc.record_task(
            agent_id="a2", status="completed"
        )
        r = self.tc.get_completion_rate()
        assert r["total_tasks"] == 2

    def test_get_time_analysis(self) -> None:
        self.tc.record_task(
            agent_id="a1", duration_ms=100
        )
        self.tc.record_task(
            agent_id="a1", duration_ms=300
        )
        r = self.tc.get_time_analysis(
            agent_id="a1"
        )
        assert r["analyzed"] is True
        assert r["avg_duration_ms"] == 200
        assert r["min_duration_ms"] == 100
        assert r["max_duration_ms"] == 300

    def test_get_time_analysis_empty(self) -> None:
        r = self.tc.get_time_analysis()
        assert r["avg_duration_ms"] == 0

    def test_get_failure_reasons(self) -> None:
        self.tc.record_task(
            agent_id="a1",
            status="failed",
            failure_reason="timeout",
        )
        self.tc.record_task(
            agent_id="a1",
            status="failed",
            failure_reason="timeout",
        )
        self.tc.record_task(
            agent_id="a1",
            status="failed",
            failure_reason="error",
        )
        r = self.tc.get_failure_reasons()
        assert r["retrieved"] is True
        assert r["total_failures"] == 3
        assert r["reasons"][0]["reason"] == "timeout"

    def test_compare_agents(self) -> None:
        self.tc.record_task(
            agent_id="a1", status="completed"
        )
        self.tc.record_task(
            agent_id="a2", status="failed"
        )
        r = self.tc.compare_agents()
        assert r["compared"] is True
        assert r["agent_count"] == 2

    def test_get_historical_view(self) -> None:
        self.tc.record_task(
            agent_id="a1",
            status="completed",
            period="2024-01",
        )
        self.tc.record_task(
            agent_id="a1",
            status="failed",
            period="2024-02",
        )
        r = self.tc.get_historical_view()
        assert r["retrieved"] is True
        assert r["period_count"] == 2


# ==================== ConfidenceTrend ====================


class TestConfidenceTrend:
    """ConfidenceTrend testleri."""

    def setup_method(self) -> None:
        self.ct = ConfidenceTrend()

    def test_init(self) -> None:
        assert self.ct.record_count == 0

    def test_record_confidence(self) -> None:
        r = self.ct.record_confidence(
            agent_id="a1",
            predicted_confidence=85.0,
            actual_outcome=True,
        )
        assert r["recorded"] is True
        assert self.ct.record_count == 1

    def test_get_calibration_empty(self) -> None:
        r = self.ct.get_calibration()
        assert r["analyzed"] is True
        assert r["calibration_score"] == 0.0

    def test_get_calibration(self) -> None:
        for i in range(5):
            self.ct.record_confidence(
                agent_id="a1",
                predicted_confidence=80.0,
                actual_outcome=True,
            )
        r = self.ct.get_calibration(
            agent_id="a1"
        )
        assert r["analyzed"] is True
        assert r["total_records"] == 5

    def test_detect_over_confidence(self) -> None:
        for _ in range(5):
            self.ct.record_confidence(
                agent_id="a1",
                predicted_confidence=95.0,
                actual_outcome=False,
            )
        r = self.ct.detect_over_under_confidence(
            agent_id="a1"
        )
        assert r["detected"] is True
        assert r["status"] == "over_confident"

    def test_detect_under_confidence(self) -> None:
        for _ in range(5):
            self.ct.record_confidence(
                agent_id="a1",
                predicted_confidence=20.0,
                actual_outcome=True,
            )
        r = self.ct.detect_over_under_confidence(
            agent_id="a1"
        )
        assert r["detected"] is True
        assert r["status"] == "under_confident"

    def test_detect_well_calibrated(self) -> None:
        for _ in range(5):
            self.ct.record_confidence(
                agent_id="a1",
                predicted_confidence=95.0,
                actual_outcome=True,
            )
        r = self.ct.detect_over_under_confidence(
            agent_id="a1"
        )
        assert r["detected"] is True
        assert r["status"] == "well_calibrated"

    def test_detect_no_data(self) -> None:
        r = self.ct.detect_over_under_confidence(
            agent_id="xx"
        )
        assert r["status"] == "no_data"

    def test_get_trend(self) -> None:
        self.ct.record_confidence(
            agent_id="a1",
            predicted_confidence=60.0,
            period="p1",
        )
        self.ct.record_confidence(
            agent_id="a1",
            predicted_confidence=80.0,
            period="p2",
        )
        r = self.ct.get_trend(agent_id="a1")
        assert r["retrieved"] is True
        assert r["direction"] == "increasing"

    def test_get_trend_insufficient(self) -> None:
        self.ct.record_confidence(
            agent_id="a1",
            predicted_confidence=60.0,
            period="p1",
        )
        r = self.ct.get_trend(agent_id="a1")
        assert r["direction"] == "insufficient_data"

    def test_check_alerts_low(self) -> None:
        for _ in range(5):
            self.ct.record_confidence(
                agent_id="a1",
                predicted_confidence=10.0,
            )
        r = self.ct.check_alerts()
        assert r["checked"] is True
        assert r["alert_count"] >= 1

    def test_check_alerts_none(self) -> None:
        for _ in range(5):
            self.ct.record_confidence(
                agent_id="a1",
                predicted_confidence=70.0,
                actual_outcome=True,
            )
        r = self.ct.check_alerts()
        assert r["checked"] is True
        assert r["alert_count"] == 0


# ==================== CostEfficiencyChart ====================


class TestCostEfficiencyChart:
    """CostEfficiencyChart testleri."""

    def setup_method(self) -> None:
        self.ce = CostEfficiencyChart()

    def test_init(self) -> None:
        assert self.ce.cost_count == 0

    def test_record_cost(self) -> None:
        r = self.ce.record_cost(
            agent_id="a1",
            api_cost=0.05,
            compute_cost=0.10,
        )
        assert r["recorded"] is True
        assert r["total_cost"] == 0.15
        assert self.ce.cost_count == 1

    def test_get_cost_per_task_empty(self) -> None:
        r = self.ce.get_cost_per_task()
        assert r["avg_cost"] == 0.0

    def test_get_cost_per_task(self) -> None:
        self.ce.record_cost(
            agent_id="a1",
            api_cost=0.10,
            compute_cost=0.10,
        )
        self.ce.record_cost(
            agent_id="a1",
            api_cost=0.20,
            compute_cost=0.10,
        )
        r = self.ce.get_cost_per_task(
            agent_id="a1"
        )
        assert r["retrieved"] is True
        assert r["total_tasks"] == 2
        assert r["avg_cost"] == 0.25

    def test_get_resource_usage(self) -> None:
        self.ce.record_cost(
            agent_id="a1", api_cost=0.10
        )
        self.ce.record_cost(
            agent_id="a2", api_cost=0.30
        )
        r = self.ce.get_resource_usage()
        assert r["retrieved"] is True
        assert r["agent_count"] == 2

    def test_track_optimization(self) -> None:
        for i in range(6):
            self.ce.record_cost(
                agent_id="a1",
                api_cost=0.10 - i * 0.01,
            )
        r = self.ce.track_optimization()
        assert r["tracked"] is True

    def test_compare_efficiency(self) -> None:
        self.ce.record_cost(
            agent_id="a1",
            api_cost=0.10,
            success=True,
        )
        self.ce.record_cost(
            agent_id="a2",
            api_cost=0.50,
            success=True,
        )
        r = self.ce.compare_efficiency()
        assert r["compared"] is True

    def test_calculate_savings_empty(self) -> None:
        r = self.ce.calculate_savings()
        assert r["total_savings"] == 0.0

    def test_calculate_savings(self) -> None:
        self.ce.record_cost(
            agent_id="a1", api_cost=0.10
        )
        self.ce.record_cost(
            agent_id="a1", api_cost=0.10
        )
        r = self.ce.calculate_savings(
            baseline_cost=0.50
        )
        assert r["calculated"] is True
        assert r["total_savings"] == 0.8


# ==================== AgentRanking ====================


class TestAgentRanking:
    """AgentRanking testleri."""

    def setup_method(self) -> None:
        self.ar = AgentRanking()

    def test_init(self) -> None:
        assert self.ar.agent_count == 0

    def test_add_agent(self) -> None:
        r = self.ar.add_agent(
            agent_id="a1",
            agent_name="Agent1",
            category="coding",
        )
        assert r["added"] is True
        assert self.ar.agent_count == 1

    def test_add_agent_auto_id(self) -> None:
        r = self.ar.add_agent(
            agent_name="Auto"
        )
        assert r["added"] is True
        assert r["agent_id"].startswith("ar_")

    def test_record_score(self) -> None:
        self.ar.add_agent(agent_id="a1")
        r = self.ar.record_score(
            agent_id="a1", score=85.0
        )
        assert r["recorded"] is True

    def test_get_ranking(self) -> None:
        self.ar.add_agent(
            agent_id="a1",
            agent_name="A1",
        )
        self.ar.add_agent(
            agent_id="a2",
            agent_name="A2",
        )
        self.ar.record_score(
            agent_id="a1", score=90.0
        )
        self.ar.record_score(
            agent_id="a2", score=70.0
        )
        r = self.ar.get_ranking()
        assert r["retrieved"] is True
        assert r["rankings"][0]["agent_id"] == "a1"
        assert r["rankings"][0]["rank"] == 1

    def test_get_ranking_by_category(self) -> None:
        self.ar.add_agent(
            agent_id="a1", category="coding"
        )
        self.ar.add_agent(
            agent_id="a2", category="research"
        )
        self.ar.record_score(
            agent_id="a1", score=80.0
        )
        self.ar.record_score(
            agent_id="a2", score=90.0
        )
        r = self.ar.get_ranking(
            category="coding"
        )
        assert r["total_agents"] == 1

    def test_get_ranking_success_rate(self) -> None:
        self.ar.add_agent(agent_id="a1")
        self.ar.record_score(
            agent_id="a1",
            score=80.0,
            success=True,
        )
        self.ar.record_score(
            agent_id="a1",
            score=60.0,
            success=False,
        )
        r = self.ar.get_ranking(
            metric="success_rate"
        )
        assert r["retrieved"] is True
        assert r["rankings"][0]["avg_score"] == 50.0

    def test_get_category_leaders(self) -> None:
        self.ar.add_agent(
            agent_id="a1", category="coding"
        )
        self.ar.add_agent(
            agent_id="a2", category="coding"
        )
        self.ar.record_score(
            agent_id="a1", score=90.0
        )
        self.ar.record_score(
            agent_id="a2", score=80.0
        )
        r = self.ar.get_category_leaders()
        assert r["retrieved"] is True
        assert "coding" in r["leaders"]
        assert (
            r["leaders"]["coding"]["agent_id"]
            == "a1"
        )

    def test_get_improvement_ranking(self) -> None:
        self.ar.add_agent(agent_id="a1")
        for i in range(6):
            self.ar.record_score(
                agent_id="a1",
                score=50.0 + i * 5,
            )
        r = self.ar.get_improvement_ranking()
        assert r["retrieved"] is True
        assert len(r["improvements"]) == 1

    def test_get_improvement_insufficient(self) -> None:
        self.ar.add_agent(agent_id="a1")
        self.ar.record_score(
            agent_id="a1", score=80.0
        )
        r = self.ar.get_improvement_ranking()
        assert r["improvements"] == []

    def test_get_leaderboard(self) -> None:
        self.ar.add_agent(
            agent_id="a1",
            agent_name="Top",
        )
        self.ar.record_score(
            agent_id="a1", score=95.0
        )
        r = self.ar.get_leaderboard()
        assert r["retrieved"] is True
        assert r["leaderboard"][0]["position"] == 1

    def test_get_leaderboard_by_period(self) -> None:
        self.ar.add_agent(agent_id="a1")
        self.ar.record_score(
            agent_id="a1",
            score=80.0,
            period="2024-01",
        )
        r = self.ar.get_leaderboard(
            period="2024-01"
        )
        assert r["retrieved"] is True
        assert r["period"] == "2024-01"


# ==================== PerformanceComparison ====================


class TestPerformanceComparison:
    """PerformanceComparison testleri."""

    def setup_method(self) -> None:
        self.pc = PerformanceComparison()

    def test_init(self) -> None:
        assert self.pc.record_count == 0

    def test_add_record(self) -> None:
        r = self.pc.add_record(
            agent_id="a1",
            metric="speed",
            value=85.0,
        )
        assert r["added"] is True
        assert self.pc.record_count == 1

    def test_compare_side_by_side(self) -> None:
        self.pc.add_record(
            agent_id="a1",
            metric="speed",
            value=90.0,
        )
        self.pc.add_record(
            agent_id="a2",
            metric="speed",
            value=70.0,
        )
        r = self.pc.compare_side_by_side()
        assert r["compared"] is True
        assert r["agent_count"] == 2

    def test_compare_side_by_side_specific(self) -> None:
        self.pc.add_record(
            agent_id="a1", value=90.0
        )
        self.pc.add_record(
            agent_id="a2", value=70.0
        )
        self.pc.add_record(
            agent_id="a3", value=80.0
        )
        r = self.pc.compare_side_by_side(
            agent_ids=["a1", "a2"]
        )
        assert r["agent_count"] == 2

    def test_compare_metric(self) -> None:
        self.pc.add_record(
            agent_id="a1",
            metric="quality",
            value=95.0,
        )
        self.pc.add_record(
            agent_id="a2",
            metric="quality",
            value=85.0,
        )
        r = self.pc.compare_metric(
            metric="quality"
        )
        assert r["compared"] is True
        assert r["results"][0]["agent_id"] == "a1"

    def test_compare_periods(self) -> None:
        self.pc.add_record(
            agent_id="a1",
            value=70.0,
            period="p1",
        )
        self.pc.add_record(
            agent_id="a1",
            value=90.0,
            period="p2",
        )
        r = self.pc.compare_periods(
            agent_id="a1",
            period_a="p1",
            period_b="p2",
        )
        assert r["compared"] is True
        assert r["change"] == 20.0

    def test_compare_periods_all(self) -> None:
        self.pc.add_record(
            agent_id="a1",
            value=50.0,
            period="p1",
        )
        self.pc.add_record(
            agent_id="a1",
            value=100.0,
            period="p2",
        )
        r = self.pc.compare_periods(
            period_a="p1", period_b="p2"
        )
        assert r["change_pct"] == 100.0

    def test_analyze_gaps(self) -> None:
        self.pc.add_record(
            agent_id="a1", value=95.0
        )
        self.pc.add_record(
            agent_id="a2", value=70.0
        )
        r = self.pc.analyze_gaps()
        assert r["analyzed"] is True
        assert r["best_agent"] == "a1"
        assert len(r["gaps"]) == 1

    def test_analyze_gaps_insufficient(self) -> None:
        self.pc.add_record(
            agent_id="a1", value=90.0
        )
        r = self.pc.analyze_gaps()
        assert r["gaps"] == []

    def test_get_visualization_data(self) -> None:
        self.pc.add_record(
            agent_id="a1",
            metric="speed",
            value=80.0,
            period="p1",
        )
        r = self.pc.get_visualization_data(
            metric="speed"
        )
        assert r["retrieved"] is True
        assert len(r["series"]) == 1

    def test_get_visualization_all(self) -> None:
        self.pc.add_record(
            agent_id="a1", value=80.0
        )
        r = self.pc.get_visualization_data()
        assert r["metric"] == "all"


# ==================== AgentImprovementTracker ====================


class TestAgentImprovementTracker:
    """AgentImprovementTracker testleri."""

    def setup_method(self) -> None:
        self.it = AgentImprovementTracker()

    def test_init(self) -> None:
        assert self.it.improvement_count == 0

    def test_record_improvement(self) -> None:
        r = self.it.record_improvement(
            agent_id="a1",
            before_value=70.0,
            after_value=85.0,
        )
        assert r["recorded"] is True
        assert r["change"] == 15.0
        assert self.it.improvement_count == 1

    def test_record_improvement_pct(self) -> None:
        r = self.it.record_improvement(
            agent_id="a1",
            before_value=50.0,
            after_value=75.0,
        )
        assert r["change_pct"] == 50.0

    def test_get_before_after(self) -> None:
        self.it.record_improvement(
            agent_id="a1",
            before_value=60.0,
            after_value=80.0,
        )
        self.it.record_improvement(
            agent_id="a1",
            before_value=70.0,
            after_value=75.0,
        )
        r = self.it.get_before_after(
            agent_id="a1"
        )
        assert r["analyzed"] is True
        assert r["positive_changes"] == 2

    def test_get_before_after_empty(self) -> None:
        r = self.it.get_before_after()
        assert r["improvements"] == []

    def test_get_before_after_by_metric(self) -> None:
        self.it.record_improvement(
            agent_id="a1",
            metric="speed",
            before_value=50.0,
            after_value=80.0,
        )
        self.it.record_improvement(
            agent_id="a1",
            metric="quality",
            before_value=60.0,
            after_value=90.0,
        )
        r = self.it.get_before_after(
            metric="speed"
        )
        assert r["total_improvements"] == 1

    def test_get_learning_curve(self) -> None:
        for i in range(4):
            self.it.record_improvement(
                agent_id="a1",
                before_value=50.0,
                after_value=50.0 + (i + 1) * 5,
            )
        r = self.it.get_learning_curve(
            agent_id="a1"
        )
        assert r["retrieved"] is True
        assert len(r["curve"]) == 4

    def test_get_learning_curve_insufficient(self) -> None:
        self.it.record_improvement(
            agent_id="a1",
            before_value=50.0,
            after_value=60.0,
        )
        r = self.it.get_learning_curve(
            agent_id="a1"
        )
        assert r["trend"] == "insufficient_data"

    def test_add_milestone(self) -> None:
        r = self.it.add_milestone(
            agent_id="a1",
            milestone_name="90% accuracy",
            target_metric="accuracy",
            target_value=90.0,
        )
        assert r["added"] is True
        assert r["achieved"] is False

    def test_add_milestone_achieved(self) -> None:
        r = self.it.add_milestone(
            agent_id="a1",
            milestone_name="Test",
            achieved=True,
        )
        assert r["achieved"] is True

    def test_get_milestones(self) -> None:
        self.it.add_milestone(
            agent_id="a1",
            milestone_name="M1",
            achieved=True,
        )
        self.it.add_milestone(
            agent_id="a1",
            milestone_name="M2",
            achieved=False,
        )
        r = self.it.get_milestones(
            agent_id="a1"
        )
        assert r["retrieved"] is True
        assert r["achieved"] == 1
        assert r["pending"] == 1

    def test_get_recommendations_no_data(self) -> None:
        r = self.it.get_recommendations()
        assert r["retrieved"] is True
        assert r["recommendations"][0]["type"] == "start_tracking"

    def test_get_recommendations_declining(self) -> None:
        for _ in range(4):
            self.it.record_improvement(
                agent_id="a1",
                before_value=80.0,
                after_value=70.0,
            )
        r = self.it.get_recommendations(
            agent_id="a1"
        )
        assert any(
            rec["type"] == "declining"
            for rec in r["recommendations"]
        )

    def test_get_recommendations_milestones(self) -> None:
        self.it.record_improvement(
            agent_id="a1",
            before_value=70.0,
            after_value=80.0,
        )
        self.it.add_milestone(
            agent_id="a1",
            milestone_name="Goal",
            achieved=False,
        )
        r = self.it.get_recommendations(
            agent_id="a1"
        )
        assert any(
            rec["type"] == "pending_milestones"
            for rec in r["recommendations"]
        )


# ==================== AgentLifecycleView ====================


class TestAgentLifecycleView:
    """AgentLifecycleView testleri."""

    def setup_method(self) -> None:
        self.lc = AgentLifecycleView()

    def test_init(self) -> None:
        assert self.lc.agent_count == 0

    def test_register_agent(self) -> None:
        r = self.lc.register_agent(
            agent_id="a1",
            agent_name="Test",
            version="1.0.0",
        )
        assert r["registered"] is True
        assert self.lc.agent_count == 1

    def test_register_agent_auto_id(self) -> None:
        r = self.lc.register_agent(
            agent_name="Auto"
        )
        assert r["agent_id"].startswith("al_")

    def test_update_status(self) -> None:
        self.lc.register_agent(agent_id="a1")
        r = self.lc.update_status(
            agent_id="a1",
            status="paused",
            reason="maintenance",
        )
        assert r["updated"] is True
        assert r["new_status"] == "paused"

    def test_update_status_retire(self) -> None:
        self.lc.register_agent(agent_id="a1")
        r = self.lc.update_status(
            agent_id="a1", status="retired"
        )
        assert r["updated"] is True
        lc = self.lc.get_lifecycle(agent_id="a1")
        assert lc["status"] == "retired"

    def test_update_status_not_found(self) -> None:
        r = self.lc.update_status(
            agent_id="xx"
        )
        assert r["updated"] is False

    def test_update_version(self) -> None:
        self.lc.register_agent(
            agent_id="a1", version="1.0.0"
        )
        r = self.lc.update_version(
            agent_id="a1",
            version="1.1.0",
            changes="Bug fix",
        )
        assert r["updated"] is True
        assert r["new_version"] == "1.1.0"

    def test_update_version_not_found(self) -> None:
        r = self.lc.update_version(
            agent_id="xx", version="2.0.0"
        )
        assert r["updated"] is False

    def test_get_lifecycle(self) -> None:
        self.lc.register_agent(
            agent_id="a1",
            agent_name="Test",
            agent_type="coding",
        )
        r = self.lc.get_lifecycle(
            agent_id="a1"
        )
        assert r["found"] is True
        assert r["status"] == "active"

    def test_get_lifecycle_not_found(self) -> None:
        r = self.lc.get_lifecycle(
            agent_id="xx"
        )
        assert r["found"] is False

    def test_get_version_history(self) -> None:
        self.lc.register_agent(
            agent_id="a1", version="1.0.0"
        )
        self.lc.update_version(
            agent_id="a1", version="1.1.0"
        )
        r = self.lc.get_version_history(
            agent_id="a1"
        )
        assert r["retrieved"] is True
        assert r["total_versions"] == 2

    def test_get_version_history_empty(self) -> None:
        r = self.lc.get_version_history(
            agent_id="xx"
        )
        assert r["versions"] == []

    def test_get_activity_timeline(self) -> None:
        self.lc.register_agent(agent_id="a1")
        self.lc.update_status(
            agent_id="a1", status="paused"
        )
        r = self.lc.get_activity_timeline(
            agent_id="a1"
        )
        assert r["retrieved"] is True
        assert r["total_events"] >= 2

    def test_get_activity_timeline_limit(self) -> None:
        self.lc.register_agent(agent_id="a1")
        r = self.lc.get_activity_timeline(
            limit=1
        )
        assert r["showing"] <= 1

    def test_update_health(self) -> None:
        self.lc.register_agent(agent_id="a1")
        r = self.lc.update_health(
            agent_id="a1",
            health_score=60.0,
        )
        assert r["updated"] is True
        assert r["new_health"] == 60.0

    def test_update_health_warning(self) -> None:
        self.lc.register_agent(agent_id="a1")
        self.lc.update_health(
            agent_id="a1",
            health_score=30.0,
            reason="high errors",
        )
        timeline = (
            self.lc.get_activity_timeline(
                agent_id="a1"
            )
        )
        events = timeline["events"]
        assert any(
            e["event_type"] == "health_warning"
            for e in events
        )

    def test_update_health_not_found(self) -> None:
        r = self.lc.update_health(
            agent_id="xx"
        )
        assert r["updated"] is False

    def test_get_health_indicators(self) -> None:
        self.lc.register_agent(agent_id="a1")
        self.lc.register_agent(agent_id="a2")
        self.lc.update_health(
            agent_id="a1", health_score=90.0
        )
        self.lc.update_health(
            agent_id="a2", health_score=30.0
        )
        r = self.lc.get_health_indicators()
        assert r["retrieved"] is True
        assert r["healthy"] >= 1
        assert r["critical"] >= 1

    def test_health_excludes_retired(self) -> None:
        self.lc.register_agent(agent_id="a1")
        self.lc.update_status(
            agent_id="a1", status="retired"
        )
        r = self.lc.get_health_indicators()
        assert r["total_active"] == 0


# ==================== AgentDashOrchestrator ====================


class TestAgentDashOrchestrator:
    """AgentDashOrchestrator testleri."""

    def setup_method(self) -> None:
        self.orch = AgentDashOrchestrator()

    def test_init(self) -> None:
        a = self.orch.get_analytics()
        assert a["retrieved"] is True
        assert a["scorecard_agents"] == 0

    def test_full_agent_dashboard(self) -> None:
        r = self.orch.full_agent_dashboard(
            agent_id="a1"
        )
        assert r["retrieved"] is True
        assert "scorecard" in r
        assert "completion" in r
        assert "confidence" in r
        assert "cost" in r
        assert "lifecycle" in r

    def test_all_agents_overview(self) -> None:
        r = self.orch.all_agents_overview()
        assert r["retrieved"] is True
        assert "scorecards" in r
        assert "rankings" in r
        assert "health" in r

    def test_monitor_and_rank(self) -> None:
        r = self.orch.monitor_and_rank()
        assert r["retrieved"] is True
        assert "leaderboard" in r
        assert "alerts" in r

    def test_compare_and_improve(self) -> None:
        r = self.orch.compare_and_improve()
        assert r["retrieved"] is True
        assert "gaps" in r
        assert "recommendations" in r

    def test_get_analytics(self) -> None:
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert "scorecard_agents" in r
        assert "tasks_tracked" in r
        assert "confidence_records" in r
        assert "cost_records" in r
        assert "ranked_agents" in r
        assert "comparison_records" in r
        assert "improvements" in r
        assert "lifecycle_agents" in r


# ==================== Models ====================


class TestAgentdashModels:
    """Agentdash model testleri."""

    def test_agent_status_enum(self) -> None:
        assert AgentStatus.ACTIVE == "active"
        assert AgentStatus.RETIRED == "retired"

    def test_metric_type_enum(self) -> None:
        assert MetricType.TASK == "task"
        assert MetricType.QUALITY == "quality"

    def test_task_status_enum(self) -> None:
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"

    def test_ranking_metric_enum(self) -> None:
        assert RankingMetric.OVERALL == "overall"

    def test_health_level_enum(self) -> None:
        assert HealthLevel.HEALTHY == "healthy"
        assert HealthLevel.CRITICAL == "critical"

    def test_trend_direction_enum(self) -> None:
        assert TrendDirection.IMPROVING == "improving"
        assert TrendDirection.STABLE == "stable"

    def test_agent_metric_record(self) -> None:
        m = AgentMetricRecord(
            agent_id="a1",
            metric_type=MetricType.TASK,
            success=True,
            quality_score=85.0,
        )
        assert m.agent_id == "a1"
        assert m.quality_score == 85.0

    def test_task_record(self) -> None:
        t = TaskRecord(
            agent_id="a1",
            status=TaskStatus.COMPLETED,
            duration_ms=500,
        )
        assert t.status == TaskStatus.COMPLETED

    def test_confidence_record(self) -> None:
        c = ConfidenceRecord(
            agent_id="a1",
            predicted_confidence=80.0,
            actual_outcome=True,
        )
        assert c.predicted_confidence == 80.0

    def test_cost_record(self) -> None:
        c = CostRecord(
            api_cost=0.10,
            compute_cost=0.05,
        )
        assert c.api_cost == 0.10

    def test_improvement_record(self) -> None:
        i = ImprovementRecord(
            before_value=60.0,
            after_value=80.0,
            change=20.0,
        )
        assert i.change == 20.0

    def test_agent_lifecycle_record(self) -> None:
        a = AgentLifecycleRecord(
            agent_id="a1",
            status=AgentStatus.ACTIVE,
            health_score=95.0,
        )
        assert a.health_score == 95.0
        assert a.health_level == HealthLevel.HEALTHY
