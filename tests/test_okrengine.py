"""Goal Tracking & OKR Engine testleri."""

import pytest

from app.models.okrengine_models import (
    ObjectiveLevel,
    OKRStatus,
    CadenceType,
    AlignmentType,
    ScoreMethod,
    ReviewType,
    ObjectiveRecord,
    KeyResultRecord,
    CheckInRecord,
    ReviewRecord,
)
from app.core.okrengine.objective_definer import (
    ObjectiveDefiner,
)
from app.core.okrengine.key_result_tracker import (
    KeyResultTracker,
)
from app.core.okrengine.progress_visualizer import (
    OKRProgressVisualizer,
)
from app.core.okrengine.alignment_checker import (
    AlignmentChecker,
)
from app.core.okrengine.cadence_manager import (
    CadenceManager,
)
from app.core.okrengine.okr_score_calculator import (
    OKRScoreCalculator,
)
from app.core.okrengine.strategic_reviewer import (
    StrategicReviewer,
)
from app.core.okrengine.okr_coach import (
    OKRCoach,
)
from app.core.okrengine.okrengine_orchestrator import (
    OKREngineOrchestrator,
)


# ── Enum testleri ──


class TestObjectiveLevel:
    def test_values(self):
        assert ObjectiveLevel.COMPANY == "company"
        assert ObjectiveLevel.DEPARTMENT == "department"
        assert ObjectiveLevel.TEAM == "team"
        assert ObjectiveLevel.INDIVIDUAL == "individual"

    def test_member_count(self):
        assert len(ObjectiveLevel) == 4


class TestOKRStatus:
    def test_values(self):
        assert OKRStatus.DRAFT == "draft"
        assert OKRStatus.ACTIVE == "active"
        assert OKRStatus.AT_RISK == "at_risk"
        assert OKRStatus.ON_TRACK == "on_track"
        assert OKRStatus.COMPLETED == "completed"
        assert OKRStatus.ABANDONED == "abandoned"

    def test_member_count(self):
        assert len(OKRStatus) == 6


class TestCadenceType:
    def test_values(self):
        assert CadenceType.WEEKLY == "weekly"
        assert CadenceType.BIWEEKLY == "biweekly"
        assert CadenceType.MONTHLY == "monthly"
        assert CadenceType.QUARTERLY == "quarterly"
        assert CadenceType.ANNUAL == "annual"

    def test_member_count(self):
        assert len(CadenceType) == 5


class TestAlignmentType:
    def test_values(self):
        assert AlignmentType.VERTICAL == "vertical"
        assert AlignmentType.HORIZONTAL == "horizontal"
        assert AlignmentType.CROSS_FUNCTIONAL == "cross_functional"

    def test_member_count(self):
        assert len(AlignmentType) == 3


class TestScoreMethod:
    def test_values(self):
        assert ScoreMethod.SIMPLE_AVERAGE == "simple_average"
        assert ScoreMethod.WEIGHTED == "weighted"
        assert ScoreMethod.BINARY == "binary"
        assert ScoreMethod.PERCENTAGE == "percentage"

    def test_member_count(self):
        assert len(ScoreMethod) == 4


class TestReviewType:
    def test_values(self):
        assert ReviewType.CHECK_IN == "check_in"
        assert ReviewType.MONTHLY_REVIEW == "monthly_review"
        assert ReviewType.QUARTERLY_REVIEW == "quarterly_review"
        assert ReviewType.ANNUAL_REVIEW == "annual_review"

    def test_member_count(self):
        assert len(ReviewType) == 4


# ── Model testleri ──


class TestObjectiveRecord:
    def test_defaults(self):
        r = ObjectiveRecord()
        assert len(r.objective_id) == 8
        assert r.title == ""
        assert r.level == ObjectiveLevel.COMPANY
        assert r.status == OKRStatus.DRAFT
        assert r.owner == ""
        assert r.parent_id == ""
        assert r.created_at is not None

    def test_custom(self):
        r = ObjectiveRecord(
            title="Grow Revenue",
            level=ObjectiveLevel.TEAM,
            owner="sales",
        )
        assert r.title == "Grow Revenue"
        assert r.level == ObjectiveLevel.TEAM
        assert r.owner == "sales"


class TestKeyResultRecord:
    def test_defaults(self):
        r = KeyResultRecord()
        assert len(r.kr_id) == 8
        assert r.objective_id == ""
        assert r.target_value == 100.0
        assert r.current_value == 0.0
        assert r.confidence == 0.5

    def test_custom(self):
        r = KeyResultRecord(
            objective_id="obj_abc",
            target_value=500.0,
            confidence=0.8,
        )
        assert r.objective_id == "obj_abc"
        assert r.target_value == 500.0
        assert r.confidence == 0.8


class TestCheckInRecord:
    def test_defaults(self):
        r = CheckInRecord()
        assert len(r.checkin_id) == 8
        assert r.kr_id == ""
        assert r.value == 0.0
        assert r.note == ""

    def test_custom(self):
        r = CheckInRecord(
            kr_id="kr_xyz",
            value=75.0,
            note="Good progress",
        )
        assert r.kr_id == "kr_xyz"
        assert r.value == 75.0


class TestReviewRecord:
    def test_defaults(self):
        r = ReviewRecord()
        assert len(r.review_id) == 8
        assert r.review_type == ReviewType.CHECK_IN
        assert r.period == ""
        assert r.score == 0.0

    def test_custom(self):
        r = ReviewRecord(
            review_type=ReviewType.QUARTERLY_REVIEW,
            period="Q1-2026",
            score=72.5,
        )
        assert r.review_type == ReviewType.QUARTERLY_REVIEW
        assert r.score == 72.5


# ── ObjectiveDefiner testleri ──


class TestCreateObjective:
    def test_basic(self):
        d = ObjectiveDefiner()
        r = d.create_objective("Grow Revenue 10x")
        assert r["created"] is True
        assert r["objective_id"].startswith("obj_")
        assert r["title"] == "Grow Revenue 10x"
        assert r["level"] == "company"

    def test_count(self):
        d = ObjectiveDefiner()
        d.create_objective("A")
        d.create_objective("B")
        assert d.objective_count == 2


class TestValidateSmart:
    def test_valid(self):
        d = ObjectiveDefiner()
        obj = d.create_objective(
            "Grow Revenue 10x", timeline_months=3,
        )
        r = d.validate_smart(obj["objective_id"])
        assert r["valid"] is True
        assert r["smart_score"] > 0

    def test_not_found(self):
        d = ObjectiveDefiner()
        r = d.validate_smart("nonexistent")
        assert r["valid"] is False
        assert r["smart_score"] == 0


class TestSetHierarchy:
    def test_basic(self):
        d = ObjectiveDefiner()
        obj = d.create_objective(
            "Team Goal", level="team",
        )
        r = d.set_hierarchy(
            obj["objective_id"], "parent_123",
        )
        assert r["hierarchy_set"] is True
        assert r["depth"] == 2

    def test_not_found(self):
        d = ObjectiveDefiner()
        r = d.set_hierarchy("nope", "parent")
        assert r["hierarchy_set"] is False


class TestAssignOwner:
    def test_basic(self):
        d = ObjectiveDefiner()
        obj = d.create_objective("Goal")
        r = d.assign_owner(
            obj["objective_id"], "alice",
        )
        assert r["assigned"] is True
        assert r["owner"] == "alice"


class TestSetTimeline:
    def test_quarterly(self):
        d = ObjectiveDefiner()
        obj = d.create_objective("Goal")
        r = d.set_timeline(
            obj["objective_id"], 3,
        )
        assert r["timeline_set"] is True
        assert r["period"] == "quarterly"

    def test_annual(self):
        d = ObjectiveDefiner()
        obj = d.create_objective("Goal")
        r = d.set_timeline(
            obj["objective_id"], 12,
        )
        assert r["period"] == "annual"

    def test_multi_year(self):
        d = ObjectiveDefiner()
        obj = d.create_objective("Goal")
        r = d.set_timeline(
            obj["objective_id"], 24,
        )
        assert r["period"] == "multi_year"


# ── KeyResultTracker testleri ──


class TestDefineKR:
    def test_basic(self):
        t = KeyResultTracker()
        r = t.define_kr("obj_1", "Revenue", 1000.0)
        assert r["defined"] is True
        assert r["kr_id"].startswith("kr_")
        assert r["target_value"] == 1000.0

    def test_count(self):
        t = KeyResultTracker()
        t.define_kr("o1", "A")
        t.define_kr("o1", "B")
        assert t.kr_count == 2


class TestTrackMetric:
    def test_basic(self):
        t = KeyResultTracker()
        kr = t.define_kr("obj_1", "Rev", 200.0)
        r = t.track_metric(kr["kr_id"], 100.0)
        assert r["tracked"] is True
        assert r["progress_pct"] == 50.0

    def test_capped_at_100(self):
        t = KeyResultTracker()
        kr = t.define_kr("obj_1", "Rev", 50.0)
        r = t.track_metric(kr["kr_id"], 100.0)
        assert r["progress_pct"] == 100.0


class TestCalculateProgress:
    def test_on_track(self):
        t = KeyResultTracker()
        kr = t.define_kr("o1", "A", 100.0)
        t.track_metric(kr["kr_id"], 75.0)
        r = t.calculate_progress(kr["kr_id"])
        assert r["calculated"] is True
        assert r["status"] == "on_track"

    def test_at_risk(self):
        t = KeyResultTracker()
        kr = t.define_kr("o1", "A", 100.0)
        t.track_metric(kr["kr_id"], 10.0)
        r = t.calculate_progress(kr["kr_id"])
        assert r["status"] == "at_risk"

    def test_completed(self):
        t = KeyResultTracker()
        kr = t.define_kr("o1", "A", 100.0)
        t.track_metric(kr["kr_id"], 100.0)
        r = t.calculate_progress(kr["kr_id"])
        assert r["status"] == "completed"


class TestManageTarget:
    def test_basic(self):
        t = KeyResultTracker()
        kr = t.define_kr("o1", "A", 100.0)
        r = t.manage_target(kr["kr_id"], 150.0)
        assert r["updated"] is True
        assert r["old_target"] == 100.0
        assert r["new_target"] == 150.0
        assert r["change_pct"] == 50.0


class TestScoreConfidence:
    def test_high(self):
        t = KeyResultTracker()
        kr = t.define_kr("o1", "A")
        r = t.score_confidence(kr["kr_id"], 0.9)
        assert r["scored"] is True
        assert r["confidence_level"] == "high"

    def test_low(self):
        t = KeyResultTracker()
        kr = t.define_kr("o1", "A")
        r = t.score_confidence(kr["kr_id"], 0.2)
        assert r["confidence_level"] == "low"


# ── OKRProgressVisualizer testleri ──


class TestGenerateProgressChart:
    def test_green(self):
        v = OKRProgressVisualizer()
        r = v.generate_progress_chart("obj_1", 80.0)
        assert r["generated"] is True
        assert r["color"] == "green"
        assert "█" in r["bar"]

    def test_red(self):
        v = OKRProgressVisualizer()
        r = v.generate_progress_chart("obj_1", 20.0)
        assert r["color"] == "red"

    def test_count(self):
        v = OKRProgressVisualizer()
        v.generate_progress_chart("o1", 50.0)
        v.generate_progress_chart("o2", 70.0)
        assert v.chart_count == 2


class TestVisualizeTrend:
    def test_improving(self):
        v = OKRProgressVisualizer()
        r = v.visualize_trend(
            "kr_1", [20.0, 40.0, 60.0],
        )
        assert r["visualized"] is True
        assert r["trend"] == "improving"

    def test_declining(self):
        v = OKRProgressVisualizer()
        r = v.visualize_trend(
            "kr_1", [80.0, 60.0, 40.0],
        )
        assert r["trend"] == "declining"

    def test_insufficient(self):
        v = OKRProgressVisualizer()
        r = v.visualize_trend("kr_1", [50.0])
        assert r["trend"] == "insufficient_data"


class TestCreateComparison:
    def test_basic(self):
        v = OKRProgressVisualizer()
        objs = [
            {"name": "A", "progress": 80},
            {"name": "B", "progress": 40},
        ]
        r = v.create_comparison(objs)
        assert r["compared"] is True
        assert r["leader"] == "A"
        assert r["laggard"] == "B"
        assert r["count"] == 2

    def test_empty(self):
        v = OKRProgressVisualizer()
        r = v.create_comparison()
        assert r["leader"] == ""
        assert r["count"] == 0


class TestBuildDashboard:
    def test_default(self):
        v = OKRProgressVisualizer()
        r = v.build_dashboard()
        assert r["built"] is True
        assert r["widget_count"] == 4
        assert r["layout"] == "grid"

    def test_scroll(self):
        v = OKRProgressVisualizer()
        r = v.build_dashboard(
            ["a", "b", "c", "d", "e"],
        )
        assert r["layout"] == "scroll"


class TestExportReport:
    def test_summary(self):
        v = OKRProgressVisualizer()
        r = v.export_report("summary")
        assert r["exported"] is True
        assert r["section_count"] == 2

    def test_detailed(self):
        v = OKRProgressVisualizer()
        r = v.export_report("detailed")
        assert r["section_count"] == 4


# ── AlignmentChecker testleri ──


class TestCheckVertical:
    def test_aligned(self):
        a = AlignmentChecker()
        r = a.check_vertical("c1", "p1", 60.0, 55.0)
        assert r["checked"] is True
        assert r["aligned"] is True
        assert r["alignment_type"] == "vertical"

    def test_misaligned(self):
        a = AlignmentChecker()
        r = a.check_vertical("c1", "p1", 80.0, 30.0)
        assert r["aligned"] is False

    def test_count(self):
        a = AlignmentChecker()
        a.check_vertical("c1", "p1", 50.0, 50.0)
        assert a.check_count == 1


class TestCheckHorizontal:
    def test_aligned(self):
        a = AlignmentChecker()
        r = a.check_horizontal(
            ["o1", "o2"], [60.0, 70.0],
        )
        assert r["checked"] is True
        assert r["aligned"] is True

    def test_misaligned(self):
        a = AlignmentChecker()
        r = a.check_horizontal(
            ["o1", "o2"], [10.0, 90.0],
        )
        assert r["aligned"] is False

    def test_empty(self):
        a = AlignmentChecker()
        r = a.check_horizontal()
        assert r["avg_progress"] == 0.0


class TestDetectGaps:
    def test_with_gaps(self):
        a = AlignmentChecker()
        objs = [
            {"name": "A", "progress": 10},
            {"name": "B", "progress": 80},
        ]
        r = a.detect_gaps(objs)
        assert r["detected"] is True
        assert r["gap_count"] == 1
        assert r["severity"] == "moderate"

    def test_critical(self):
        a = AlignmentChecker()
        objs = [
            {"name": "A", "progress": 10},
            {"name": "B", "progress": 20},
            {"name": "C", "progress": 5},
        ]
        r = a.detect_gaps(objs)
        assert r["severity"] == "critical"


class TestIdentifyConflicts:
    def test_conflict(self):
        a = AlignmentChecker()
        objs = [
            {"name": "A", "resource": "budget"},
            {"name": "B", "resource": "budget"},
        ]
        r = a.identify_conflicts(objs)
        assert r["identified"] is True
        assert r["has_conflicts"] is True
        assert r["conflict_count"] == 1

    def test_no_conflict(self):
        a = AlignmentChecker()
        objs = [
            {"name": "A", "resource": "budget"},
            {"name": "B", "resource": "team"},
        ]
        r = a.identify_conflicts(objs)
        assert r["has_conflicts"] is False


class TestRecommendAlignment:
    def test_healthy(self):
        a = AlignmentChecker()
        r = a.recommend_alignment(0, 0, 70.0)
        assert r["recommended"] is True
        assert r["health"] == "healthy"
        assert "maintain_course" in r["recommendations"]

    def test_critical(self):
        a = AlignmentChecker()
        r = a.recommend_alignment(3, 2, 30.0)
        assert r["health"] == "critical"


# ── CadenceManager testleri ──


class TestScheduleCheckin:
    def test_basic(self):
        c = CadenceManager()
        r = c.schedule_checkin("obj_1", "weekly")
        assert r["scheduled"] is True
        assert r["schedule_id"].startswith("sched_")
        assert r["frequency_days"] == 7

    def test_monthly(self):
        c = CadenceManager()
        r = c.schedule_checkin("obj_1", "monthly")
        assert r["frequency_days"] == 30

    def test_count(self):
        c = CadenceManager()
        c.schedule_checkin("o1")
        c.schedule_checkin("o2")
        assert c.schedule_count == 2


class TestManageReviewCycle:
    def test_quarterly(self):
        c = CadenceManager()
        r = c.manage_review_cycle("quarterly")
        assert r["managed"] is True
        assert r["total_cycles"] == 4
        assert r["cycle_duration_months"] == 3

    def test_annual(self):
        c = CadenceManager()
        r = c.manage_review_cycle("annual")
        assert r["total_cycles"] == 1


class TestSendReminder:
    def test_found(self):
        c = CadenceManager()
        s = c.schedule_checkin("obj_1")
        r = c.send_reminder(s["schedule_id"])
        assert r["reminded"] is True
        assert r["channel"] == "telegram"

    def test_not_found(self):
        c = CadenceManager()
        r = c.send_reminder("nonexistent")
        assert r["reminded"] is False


class TestPrepareMeeting:
    def test_checkin(self):
        c = CadenceManager()
        r = c.prepare_meeting(["o1"], "check_in")
        assert r["prepared"] is True
        assert r["agenda_item_count"] == 3

    def test_review(self):
        c = CadenceManager()
        r = c.prepare_meeting([], "review")
        assert r["agenda_item_count"] == 5


class TestCreateFollowup:
    def test_basic(self):
        c = CadenceManager()
        r = c.create_followup("mtg_1")
        assert r["created"] is True
        assert r["followup_id"].startswith("fu_")
        assert r["action_count"] == 2

    def test_custom_actions(self):
        c = CadenceManager()
        r = c.create_followup(
            "mtg_1", ["a", "b", "c"],
        )
        assert r["action_count"] == 3


# ── OKRScoreCalculator testleri ──


class TestCalculateScore:
    def test_basic(self):
        s = OKRScoreCalculator()
        krs = [
            {"current": 80, "target": 100},
            {"current": 60, "target": 100},
        ]
        r = s.calculate_score(krs)
        assert r["calculated"] is True
        assert r["score"] == 70.0
        assert r["grade"] == "strong"

    def test_empty(self):
        s = OKRScoreCalculator()
        r = s.calculate_score()
        assert r["score"] == 0.0
        assert r["grade"] == "failing"

    def test_count(self):
        s = OKRScoreCalculator()
        s.calculate_score(
            [{"current": 50, "target": 100}],
        )
        assert s.score_count == 1


class TestApplyWeights:
    def test_weighted(self):
        s = OKRScoreCalculator()
        r = s.apply_weights(
            [80.0, 60.0], [0.7, 0.3],
        )
        assert r["weighted"] is True
        assert r["weights_applied"] is True
        assert r["weighted_score"] == 74.0

    def test_unweighted(self):
        s = OKRScoreCalculator()
        r = s.apply_weights([80.0, 60.0])
        assert r["weights_applied"] is False
        assert r["weighted_score"] == 70.0


class TestAggregateScores:
    def test_basic(self):
        s = OKRScoreCalculator()
        r = s.aggregate_scores([80.0, 60.0, 40.0])
        assert r["aggregated"] is True
        assert r["overall_score"] == 60.0
        assert r["best"] == 80.0
        assert r["worst"] == 40.0
        assert r["spread"] == 40.0

    def test_empty(self):
        s = OKRScoreCalculator()
        r = s.aggregate_scores()
        assert r["overall_score"] == 0.0


class TestCompareHistorical:
    def test_improving(self):
        s = OKRScoreCalculator()
        r = s.compare_historical(
            75.0, [50.0, 55.0, 60.0],
        )
        assert r["compared"] is True
        assert r["trend"] == "improving"

    def test_declining(self):
        s = OKRScoreCalculator()
        r = s.compare_historical(40.0, [60.0, 65.0])
        assert r["trend"] == "declining"

    def test_stable(self):
        s = OKRScoreCalculator()
        r = s.compare_historical(50.0, [48.0, 52.0])
        assert r["trend"] == "stable"


class TestBenchmark:
    def test_above_top(self):
        s = OKRScoreCalculator()
        r = s.benchmark(85.0, 60.0, 80.0)
        assert r["benchmarked"] is True
        assert r["percentile"] == 90
        assert r["vs_industry"] == 25.0

    def test_below_avg(self):
        s = OKRScoreCalculator()
        r = s.benchmark(30.0, 60.0, 80.0)
        assert r["percentile"] == 20


# ── StrategicReviewer testleri ──


class TestQuarterlyReview:
    def test_basic(self):
        rv = StrategicReviewer()
        scores = [
            {"score": 80},
            {"score": 50},
            {"score": 30},
        ]
        r = rv.quarterly_review("Q1", 2026, scores)
        assert r["reviewed"] is True
        assert r["total_objectives"] == 3
        assert r["completed"] == 1
        assert r["at_risk"] == 1

    def test_count(self):
        rv = StrategicReviewer()
        rv.quarterly_review()
        assert rv.review_count == 1


class TestAnnualPlanning:
    def test_basic(self):
        rv = StrategicReviewer()
        r = rv.annual_planning(2026)
        assert r["planned"] is True
        assert r["focus_count"] == 3
        assert len(r["quarters"]) == 4


class TestCheckStrategyAlignment:
    def test_aligned(self):
        rv = StrategicReviewer()
        r = rv.check_strategy_alignment(
            "obj_1", ["growth", "efficiency"],
        )
        assert r["checked"] is True
        assert r["aligned"] is True
        assert r["alignment_score"] == 50

    def test_not_aligned(self):
        rv = StrategicReviewer()
        r = rv.check_strategy_alignment(
            "obj_1", ["growth"],
        )
        assert r["aligned"] is False
        assert r["alignment_score"] == 25


class TestDetectPivot:
    def test_needs_pivot(self):
        rv = StrategicReviewer()
        r = rv.detect_pivot(20.0, 70.0, 1)
        assert r["detected"] is True
        assert r["needs_pivot"] is True
        assert r["recommendation"] == "pivot_strategy"

    def test_exceeding(self):
        rv = StrategicReviewer()
        r = rv.detect_pivot(80.0, 70.0, 2)
        assert r["needs_pivot"] is False
        assert r["recommendation"] == "exceeding"

    def test_accelerate(self):
        rv = StrategicReviewer()
        r = rv.detect_pivot(40.0, 70.0, 3)
        assert r["recommendation"] == "accelerate"


class TestGenerateRecommendation:
    def test_low_score(self):
        rv = StrategicReviewer()
        r = rv.generate_recommendation(30.0, "declining", 4)
        assert r["recommended"] is True
        assert "review_and_reset_targets" in r["actions"]
        assert "investigate_root_causes" in r["actions"]
        assert r["urgency"] == "high"

    def test_high_score(self):
        rv = StrategicReviewer()
        r = rv.generate_recommendation(
            80.0, "improving", 0,
        )
        assert "raise_ambition" in r["actions"]
        assert r["urgency"] == "low"

    def test_stay_course(self):
        rv = StrategicReviewer()
        r = rv.generate_recommendation(
            60.0, "stable", 0,
        )
        assert "stay_the_course" in r["actions"]


# ── OKRCoach testleri ──


class TestSuggestBestPractices:
    def test_writing(self):
        c = OKRCoach()
        r = c.suggest_best_practices("writing")
        assert r["suggested"] is True
        assert "start_with_verbs" in r["practices"]
        assert r["practice_count"] == 4

    def test_general(self):
        c = OKRCoach()
        r = c.suggest_best_practices("general")
        assert "focus_on_outcomes" in r["practices"]

    def test_count(self):
        c = OKRCoach()
        c.suggest_best_practices()
        c.suggest_best_practices("tracking")
        assert c.session_count == 2


class TestAssistWriting:
    def test_good(self):
        c = OKRCoach()
        r = c.assist_writing(
            "Increase monthly revenue by 20%",
            "Reach $100k MRR by Q2",
        )
        assert r["assisted"] is True
        assert r["quality"] == "good"
        assert r["issue_count"] == 0

    def test_poor(self):
        c = OKRCoach()
        r = c.assist_writing("Short", "")
        assert r["quality"] == "poor"
        assert r["issue_count"] >= 2

    def test_not_measurable(self):
        c = OKRCoach()
        r = c.assist_writing(
            "Improve customer satisfaction",
            "make customers happier",
        )
        assert "kr_not_measurable" in r["issues"]


class TestSuggestImprovements:
    def test_low_score(self):
        c = OKRCoach()
        r = c.suggest_improvements(30.0, 3, 0.5)
        assert r["improved"] is True
        assert "lower_targets_or_increase_effort" in r["tips"]

    def test_too_many_krs(self):
        c = OKRCoach()
        r = c.suggest_improvements(50.0, 7, 0.5)
        assert "reduce_kr_count_for_focus" in r["tips"]

    def test_on_track(self):
        c = OKRCoach()
        r = c.suggest_improvements(60.0, 3, 0.6)
        assert "on_track_keep_going" in r["tips"]


class TestWarnPitfalls:
    def test_too_many_objectives(self):
        c = OKRCoach()
        r = c.warn_pitfalls(10, 3.0)
        assert r["warned"] is True
        assert "too_many_objectives" in r["warnings"]
        assert r["risk_level"] == "medium"

    def test_no_pitfalls(self):
        c = OKRCoach()
        r = c.warn_pitfalls(5, 3.0)
        assert "no_major_pitfalls" in r["warnings"]
        assert r["risk_level"] == "low"

    def test_binary_scoring(self):
        c = OKRCoach()
        r = c.warn_pitfalls(5, 3.0, "binary")
        assert "binary_scoring_loses_nuance" in r["warnings"]


class TestProvideTraining:
    def test_basics(self):
        c = OKRCoach()
        r = c.provide_training("okr_basics")
        assert r["training_ready"] is True
        assert r["module_count"] == 3
        assert r["duration_hours"] == 1.5

    def test_advanced(self):
        c = OKRCoach()
        r = c.provide_training("advanced_okrs")
        assert r["module_count"] == 4


# ── OKREngineOrchestrator testleri ──


class TestFullOKRCycle:
    def test_basic(self):
        o = OKREngineOrchestrator()
        r = o.full_okr_cycle(
            "Increase Revenue",
            "company",
            "ceo",
        )
        assert r["cycle_complete"] is True
        assert r["objective_id"].startswith("obj_")
        assert r["kr_count"] == 2
        assert r["smart_score"] > 0
        assert r["schedule_id"].startswith("sched_")

    def test_count(self):
        o = OKREngineOrchestrator()
        o.full_okr_cycle("Goal 1")
        o.full_okr_cycle("Goal 2")
        assert o.cycle_count == 2
        assert o.managed_count == 2


class TestCompanyWideReview:
    def test_basic(self):
        o = OKREngineOrchestrator()
        scores = [
            {"score": 80},
            {"score": 60},
            {"score": 40},
        ]
        r = o.company_wide_review(
            "Q1", 2026, scores,
        )
        assert r["review_complete"] is True
        assert r["total_objectives"] == 3
        assert isinstance(r["recommendations"], list)

    def test_empty(self):
        o = OKREngineOrchestrator()
        r = o.company_wide_review()
        assert r["review_complete"] is True
        assert r["total_objectives"] == 0


class TestOKRGetAnalytics:
    def test_initial(self):
        o = OKREngineOrchestrator()
        a = o.get_analytics()
        assert a["cycles_run"] == 0
        assert a["objectives_managed"] == 0
        assert a["objectives_defined"] == 0
        assert a["krs_tracked"] == 0

    def test_after_operations(self):
        o = OKREngineOrchestrator()
        o.full_okr_cycle("Test OKR Goal")
        a = o.get_analytics()
        assert a["cycles_run"] == 1
        assert a["objectives_managed"] == 1
        assert a["objectives_defined"] == 1
        assert a["krs_tracked"] == 2
        assert a["coaching_sessions"] >= 1
