"""ATLAS Scheduling & Calendar Intelligence testleri.

MeetingOptimizer, CalendarAvailabilityFinder,
CalendarTimezoneManager, CalendarConflictResolver,
PrepBriefGenerator, AgendaCreator,
MeetingFollowUpScheduler, CalendarAnalyzer,
CalendarIntelOrchestrator testleri.
"""

import pytest

from app.core.calendarintel.agenda_creator import (
    AgendaCreator,
)
from app.core.calendarintel.availability_finder import (
    CalendarAvailabilityFinder,
)
from app.core.calendarintel.calendar_analyzer import (
    CalendarAnalyzer,
)
from app.core.calendarintel.calendarintel_orchestrator import (
    CalendarIntelOrchestrator,
)
from app.core.calendarintel.conflict_resolver import (
    CalendarConflictResolver,
)
from app.core.calendarintel.meeting_followup_scheduler import (
    MeetingFollowUpScheduler,
)
from app.core.calendarintel.meeting_optimizer import (
    MeetingOptimizer,
)
from app.core.calendarintel.prep_brief_generator import (
    PrepBriefGenerator,
)
from app.core.calendarintel.timezone_manager import (
    CalendarTimezoneManager,
)
from app.models.calendarintel_models import (
    AgendaRecord,
    AnalysisPeriod,
    CalendarAnalysisRecord,
    ConflictRecord,
    ConflictSeverity,
    FollowUpStatus,
    MeetingPriority,
    MeetingRecord,
    MeetingType,
    SlotStatus,
)


# ── MeetingOptimizer ──────────────────────


class TestFindOptimalTime:
    """find_optimal_time testleri."""

    def test_basic(self):
        m = MeetingOptimizer()
        r = m.find_optimal_time(
            participants=["a", "b"],
            duration_minutes=60,
            preferred_hour=10,
        )
        assert r["found"] is True
        assert "10:00" in r[
            "suggested_start"
        ]

    def test_early_clamp(self):
        m = MeetingOptimizer()
        r = m.find_optimal_time(
            preferred_hour=7,
        )
        assert "09:00" in r[
            "suggested_start"
        ]

    def test_counter(self):
        m = MeetingOptimizer()
        m.find_optimal_time()
        m.find_optimal_time()
        assert m.optimization_count == 2


class TestOptimizeDuration:
    """optimize_duration testleri."""

    def test_standup(self):
        m = MeetingOptimizer()
        r = m.optimize_duration(
            meeting_type="standup",
        )
        assert r["optimized"] is True
        assert r["base_duration"] == 15

    def test_with_topics(self):
        m = MeetingOptimizer()
        r = m.optimize_duration(
            meeting_type="review",
            topics=["A", "B", "C"],
        )
        assert r["optimal_duration"] > 45

    def test_max_cap(self):
        m = MeetingOptimizer()
        r = m.optimize_duration(
            meeting_type="planning",
            participant_count=20,
            topics=["A"] * 20,
        )
        assert r["optimal_duration"] <= 120


class TestCheckAvailability:
    """check_availability testleri."""

    def test_work_hours(self):
        m = MeetingOptimizer()
        r = m.check_availability(
            participants=["a", "b"],
            hour=10,
        )
        assert r["checked"] is True
        assert r["all_available"] is True

    def test_outside_hours(self):
        m = MeetingOptimizer()
        r = m.check_availability(
            participants=["a"],
            hour=22,
        )
        assert r["all_available"] is False


class TestBookRoom:
    """book_room testleri."""

    def test_basic(self):
        m = MeetingOptimizer()
        r = m.book_room(
            room_name="Room A",
            hour=10,
        )
        assert r["booked"] is True
        assert m.booking_count == 1


class TestAddBufferTime:
    """add_buffer_time testleri."""

    def test_basic(self):
        m = MeetingOptimizer()
        meetings = [
            {"title": "A"},
            {"title": "B"},
            {"title": "C"},
        ]
        r = m.add_buffer_time(
            meetings, buffer_minutes=10,
        )
        assert r["adjusted"] is True
        assert r["total_buffer"] == 20
        assert r["meetings"][0][
            "buffer_before"
        ] == 0


# ── CalendarAvailabilityFinder ────────────


class TestFindFreeSlots:
    """find_free_slots testleri."""

    def test_basic(self):
        a = CalendarAvailabilityFinder()
        a.add_event("fatih", 9, 10)
        a.add_event("fatih", 14, 15)
        r = a.find_free_slots("fatih")
        assert r["found"] is True
        assert r["count"] >= 2

    def test_empty_calendar(self):
        a = CalendarAvailabilityFinder()
        r = a.find_free_slots("empty")
        assert r["found"] is True
        assert r["count"] == 1


class TestFindMultiPerson:
    """find_multi_person testleri."""

    def test_common_slot(self):
        a = CalendarAvailabilityFinder()
        a.add_event("a", 9, 11)
        a.add_event("b", 10, 12)
        r = a.find_multi_person(
            persons=["a", "b"],
            duration_hours=1,
        )
        assert r["found"] is True

    def test_no_overlap(self):
        a = CalendarAvailabilityFinder()
        # a busy 9-18, b busy 9-18
        for h in range(9, 18):
            a.add_event("a", h, h + 1)
        r = a.find_multi_person(
            persons=["a", "b"],
        )
        assert r["found"] is False


class TestMatchPreferences:
    """match_preferences testleri."""

    def test_basic(self):
        a = CalendarAvailabilityFinder()
        a.add_event("fatih", 9, 10)
        r = a.match_preferences(
            "fatih",
            preferred_hours=[10, 14],
        )
        assert r["matched"] is True

    def test_no_match(self):
        a = CalendarAvailabilityFinder()
        for h in range(9, 18):
            a.add_event("busy", h, h + 1)
        r = a.match_preferences(
            "busy",
            preferred_hours=[10],
        )
        assert r["matched"] is False


class TestRankSuggestions:
    """rank_suggestions testleri."""

    def test_basic(self):
        a = CalendarAvailabilityFinder()
        slots = [
            {"start_hour": 15},
            {"start_hour": 10},
            {"start_hour": 12},
        ]
        r = a.rank_suggestions(
            slots, preferred_hour=10,
        )
        assert r["ranked"] is True
        assert r["ranked_slots"][0][
            "start_hour"
        ] == 10


# ── CalendarTimezoneManager ───────────────


class TestConvertTimezone:
    """convert_timezone testleri."""

    def test_basic(self):
        t = CalendarTimezoneManager()
        r = t.convert_timezone(
            hour=10,
            from_tz="TR",
            to_tz="UTC",
        )
        assert r["converted"] is True
        assert r["converted_hour"] == 7

    def test_counter(self):
        t = CalendarTimezoneManager()
        t.convert_timezone(10, "UTC", "EST")
        assert t.conversion_count == 1


class TestHandleDst:
    """handle_dst testleri."""

    def test_no_dst(self):
        t = CalendarTimezoneManager()
        r = t.handle_dst(
            12, "CET", is_dst=False,
        )
        assert r["handled"] is True
        assert r["adjusted_hour"] == 13

    def test_with_dst(self):
        t = CalendarTimezoneManager()
        r = t.handle_dst(
            12, "CET", is_dst=True,
        )
        assert r["adjusted_hour"] == 14


class TestSetParticipantTimezone:
    """set_participant_timezone testleri."""

    def test_basic(self):
        t = CalendarTimezoneManager()
        r = t.set_participant_timezone(
            "fatih", "TR",
        )
        assert r["set"] is True


class TestFindBestTime:
    """find_best_time testleri."""

    def test_basic(self):
        t = CalendarTimezoneManager()
        t.set_participant_timezone(
            "fatih", "TR",
        )
        t.set_participant_timezone(
            "john", "EST",
        )
        r = t.find_best_time(
            participants=["fatih", "john"],
        )
        assert r["found"] is True
        assert r["best_hour_utc"] is not None

    def test_empty(self):
        t = CalendarTimezoneManager()
        r = t.find_best_time()
        assert r["found"] is False


class TestFormatDisplay:
    """format_display testleri."""

    def test_24h(self):
        t = CalendarTimezoneManager()
        r = t.format_display(
            14, "TR", format_24h=True,
        )
        assert r["formatted"] is True
        assert r["display"] == "14:00"

    def test_12h(self):
        t = CalendarTimezoneManager()
        r = t.format_display(
            14, "TR", format_24h=False,
        )
        assert "PM" in r["display"]

    def test_12h_morning(self):
        t = CalendarTimezoneManager()
        r = t.format_display(
            9, "UTC", format_24h=False,
        )
        assert "AM" in r["display"]


# ── CalendarConflictResolver ──────────────


class TestDetectConflicts:
    """detect_conflicts testleri."""

    def test_overlap(self):
        c = CalendarConflictResolver()
        c.add_event("e1", "A", 9, 11)
        c.add_event("e2", "B", 10, 12)
        r = c.detect_conflicts()
        assert r["detected"] is True
        assert r["count"] >= 1

    def test_no_conflict(self):
        c = CalendarConflictResolver()
        c.add_event("e1", "A", 9, 10)
        c.add_event("e2", "B", 10, 11)
        r = c.detect_conflicts()
        assert r["detected"] is False


class TestEvaluatePriority:
    """evaluate_priority testleri."""

    def test_basic(self):
        c = CalendarConflictResolver()
        c.add_event(
            "e1", "A", priority="high",
        )
        c.add_event(
            "e2", "B", priority="low",
        )
        r = c.evaluate_priority(
            "e1", "e2",
        )
        assert r["evaluated"] is True
        assert r["winner"] == "e1"

    def test_not_found(self):
        c = CalendarConflictResolver()
        r = c.evaluate_priority("x", "y")
        assert r["evaluated"] is False


class TestSuggestReschedule:
    """suggest_reschedule testleri."""

    def test_basic(self):
        c = CalendarConflictResolver()
        c.add_event("e1", "A", 9, 10)
        c.add_event("e2", "B", 9, 10)
        r = c.suggest_reschedule("e2")
        assert r["suggested"] is True
        assert r["count"] >= 1

    def test_not_found(self):
        c = CalendarConflictResolver()
        r = c.suggest_reschedule("none")
        assert r["suggested"] is False


class TestAutoResolve:
    """auto_resolve testleri."""

    def test_basic(self):
        c = CalendarConflictResolver()
        c.add_event(
            "e1", "A", 9, 11,
            priority="high",
        )
        c.add_event(
            "e2", "B", 10, 12,
            priority="low",
        )
        r = c.auto_resolve()
        assert r["auto_resolved"] is True
        assert c.resolved_count >= 1


class TestConflictNotify:
    """notify testleri."""

    def test_basic(self):
        c = CalendarConflictResolver()
        r = c.notify(
            "e1",
            message="Rescheduled",
            recipients=["a", "b"],
        )
        assert r["notified"] is True
        assert r["recipients_count"] == 2


# ── PrepBriefGenerator ────────────────────


class TestGenerateContext:
    """generate_context testleri."""

    def test_basic(self):
        p = PrepBriefGenerator()
        r = p.generate_context(
            "m1",
            title="Sprint Review",
        )
        assert r["generated"] is True
        assert r["title"] == "Sprint Review"


class TestGatherParticipantInfo:
    """gather_participant_info testleri."""

    def test_basic(self):
        p = PrepBriefGenerator()
        r = p.gather_participant_info([
            {"name": "Fatih", "role": "PM"},
            {"name": "Ali", "role": "Dev"},
        ])
        assert r["gathered"] is True
        assert r["count"] == 2


class TestGetPreviousMeetings:
    """get_previous_meetings testleri."""

    def test_basic(self):
        p = PrepBriefGenerator()
        p.add_meeting_to_history(
            "sprint",
            meeting_id="m1",
            summary="Good sprint",
        )
        r = p.get_previous_meetings(
            "sprint",
        )
        assert r["retrieved"] is True
        assert r["count"] == 1

    def test_empty(self):
        p = PrepBriefGenerator()
        r = p.get_previous_meetings("none")
        assert r["retrieved"] is False


class TestAttachDocuments:
    """attach_documents testleri."""

    def test_basic(self):
        p = PrepBriefGenerator()
        r = p.attach_documents(
            "m1",
            documents=["doc1.pdf", "doc2.pdf"],
        )
        assert r["attached"] is True
        assert r["count"] == 2


class TestListActionItems:
    """list_action_items testleri."""

    def test_basic(self):
        p = PrepBriefGenerator()
        r = p.list_action_items(
            "m1",
            items=[
                {"task": "Review PR"},
            ],
        )
        assert r["listed"] is True
        assert r["count"] == 1


class TestGenerateBrief:
    """generate_brief testleri."""

    def test_basic(self):
        p = PrepBriefGenerator()
        r = p.generate_brief(
            "m1",
            title="Sprint Review",
            participants=[
                {"name": "Fatih"},
            ],
        )
        assert r["generated"] is True
        assert p.brief_count == 1


# ── AgendaCreator ─────────────────────────


class TestAutoCreateAgenda:
    """auto_create testleri."""

    def test_basic(self):
        a = AgendaCreator()
        r = a.auto_create(
            "m1",
            meeting_type="review",
            duration_minutes=45,
        )
        assert r["created"] is True
        assert len(r["topics"]) > 0
        assert a.agenda_count == 1

    def test_custom_topics(self):
        a = AgendaCreator()
        r = a.auto_create(
            "m1",
            topics=["A", "B"],
            duration_minutes=30,
        )
        assert len(r["topics"]) == 2


class TestAllocateTime:
    """allocate_time testleri."""

    def test_basic(self):
        a = AgendaCreator()
        r = a.allocate_time(
            topics=["A", "B", "C"],
            total_minutes=60,
        )
        assert r["allocated"] is True
        total = sum(
            t["minutes"]
            for t in r["allocation"]
        )
        assert total == 60


class TestPrioritizeTopics:
    """prioritize_topics testleri."""

    def test_basic(self):
        a = AgendaCreator()
        topics = [
            {"name": "A", "priority": "low"},
            {"name": "B", "priority": "critical"},
        ]
        r = a.prioritize_topics(topics)
        assert r["prioritized"] is True
        assert r["topics"][0][
            "priority"
        ] == "critical"


class TestAddParticipantInput:
    """add_participant_input testleri."""

    def test_basic(self):
        a = AgendaCreator()
        a.auto_create("m1")
        r = a.add_participant_input(
            "m1",
            participant="Fatih",
            topic="Budget",
        )
        assert r["added"] is True


class TestUseTemplate:
    """use_template testleri."""

    def test_standup(self):
        a = AgendaCreator()
        r = a.use_template(
            "m1",
            template_name="standup",
        )
        assert r["created"] is True

    def test_not_found(self):
        a = AgendaCreator()
        r = a.use_template(
            "m1",
            template_name="nonexistent",
        )
        assert r["used"] is False


# ── MeetingFollowUpScheduler ─────────────


class TestScheduleFollowup:
    """schedule_followup testleri."""

    def test_basic(self):
        f = MeetingFollowUpScheduler()
        r = f.schedule_followup(
            "m1",
            followup_days=7,
            title="Follow-up",
        )
        assert r["scheduled"] is True
        assert f.followup_count == 1


class TestTrackActions:
    """track_actions testleri."""

    def test_basic(self):
        f = MeetingFollowUpScheduler()
        actions = [
            {"task": "A", "status": "done"},
            {"task": "B", "status": "pending"},
        ]
        r = f.track_actions(
            "m1", actions=actions,
        )
        assert r["tracked"] is True
        assert r["pending"] == 1
        assert r["completed"] == 1


class TestSetReminder:
    """set_reminder testleri."""

    def test_basic(self):
        f = MeetingFollowUpScheduler()
        r = f.set_reminder(
            "m1",
            remind_in_days=1,
        )
        assert r["set"] is True


class TestCreateRecurring:
    """create_recurring testleri."""

    def test_basic(self):
        f = MeetingFollowUpScheduler()
        r = f.create_recurring(
            "daily_standup",
            frequency="daily",
            duration_minutes=15,
        )
        assert r["created"] is True
        assert f.recurring_count == 1


class TestManageSeries:
    """manage_series testleri."""

    def test_pause(self):
        f = MeetingFollowUpScheduler()
        f.create_recurring("standup")
        r = f.manage_series(
            "standup", action="pause",
        )
        assert r["managed"] is True
        assert r["active"] is False

    def test_not_found(self):
        f = MeetingFollowUpScheduler()
        r = f.manage_series("none")
        assert r["found"] is False


# ── CalendarAnalyzer ──────────────────────


class TestAnalyzeTimeAllocation:
    """analyze_time_allocation testleri."""

    def test_basic(self):
        a = CalendarAnalyzer()
        a.add_event("A", 9, 10)
        a.add_event("B", 14, 16)
        r = a.analyze_time_allocation(
            work_hours=8,
        )
        assert r["analyzed"] is True
        assert r["total_meeting_hours"] == 3
        assert a.analysis_count == 1


class TestCalculateMeetingLoad:
    """calculate_meeting_load testleri."""

    def test_optimal(self):
        a = CalendarAnalyzer()
        a.add_event("A", 9, 10)
        r = a.calculate_meeting_load(
            work_hours=8,
        )
        assert r["calculated"] is True
        assert r["status"] == "optimal"

    def test_overloaded(self):
        a = CalendarAnalyzer()
        for h in range(9, 15):
            a.add_event(f"M{h}", h, h + 1)
        r = a.calculate_meeting_load(
            max_meeting_pct=50.0,
            work_hours=8,
        )
        assert r["status"] == "overloaded"


class TestDetectPatterns:
    """detect_patterns testleri."""

    def test_basic(self):
        a = CalendarAnalyzer()
        a.add_event("A", 10, 11, day="Mon")
        a.add_event("B", 10, 11, day="Mon")
        a.add_event("C", 14, 15, day="Tue")
        r = a.detect_patterns()
        assert r["detected"] is True
        assert r["busiest_hour"] == 10
        assert r["busiest_day"] == "Mon"


class TestGetRecommendations:
    """get_recommendations testleri."""

    def test_overloaded(self):
        a = CalendarAnalyzer()
        for h in range(9, 15):
            a.add_event(f"M{h}", h, h + 1)
        r = a.get_recommendations(
            max_meeting_pct=50.0,
            work_hours=8,
        )
        assert r["generated"] is True
        assert r["count"] >= 1

    def test_balanced(self):
        a = CalendarAnalyzer()
        a.add_event("A", 10, 11)
        r = a.get_recommendations(
            work_hours=8,
        )
        assert r["generated"] is True


class TestTrackTrend:
    """track_trend testleri."""

    def test_basic(self):
        a = CalendarAnalyzer()
        a.add_event("A", 9, 10)
        r = a.track_trend("weekly")
        assert r["tracked"] is True
        assert r["trend"] == "stable"


# ── CalendarIntelOrchestrator ─────────────


class TestScheduleOptimizePrepare:
    """schedule_optimize_prepare testleri."""

    def test_basic(self):
        o = CalendarIntelOrchestrator()
        r = o.schedule_optimize_prepare(
            meeting_id="m1",
            title="Sprint Review",
            participants=["a", "b"],
            duration_minutes=60,
            preferred_hour=10,
        )
        assert r["pipeline_complete"] is True
        assert r["agenda_created"] is True
        assert r["brief_generated"] is True
        assert r["followup_scheduled"] is True

    def test_counter(self):
        o = CalendarIntelOrchestrator()
        o.schedule_optimize_prepare("m1")
        o.schedule_optimize_prepare("m2")
        assert o.pipeline_count == 2
        assert o.meeting_count == 2


class TestSmartSchedule:
    """smart_schedule testleri."""

    def test_basic(self):
        o = CalendarIntelOrchestrator()
        r = o.smart_schedule(
            title="Standup",
            participants=["a", "b"],
            duration_minutes=15,
        )
        assert r["scheduled"] is True


class TestCalendarIntelAnalytics:
    """get_analytics testleri."""

    def test_basic(self):
        o = CalendarIntelOrchestrator()
        o.schedule_optimize_prepare(
            "m1", title="Test",
        )
        r = o.get_analytics()
        assert r["pipelines_run"] >= 1
        assert r["optimizations"] >= 1
        assert r["agendas_created"] >= 1


# ── Models ────────────────────────────────


class TestCalendarintelModels:
    """Model testleri."""

    def test_meeting_type(self):
        assert (
            MeetingType.STANDUP == "standup"
        )
        assert (
            MeetingType.REVIEW == "review"
        )

    def test_meeting_priority(self):
        assert (
            MeetingPriority.CRITICAL
            == "critical"
        )
        assert (
            MeetingPriority.LOW == "low"
        )

    def test_conflict_severity(self):
        assert (
            ConflictSeverity.HARD == "hard"
        )
        assert (
            ConflictSeverity.SOFT == "soft"
        )

    def test_slot_status(self):
        assert SlotStatus.FREE == "free"
        assert SlotStatus.BUSY == "busy"

    def test_followup_status(self):
        assert (
            FollowUpStatus.PENDING
            == "pending"
        )
        assert (
            FollowUpStatus.COMPLETED
            == "completed"
        )

    def test_analysis_period(self):
        assert (
            AnalysisPeriod.DAILY == "daily"
        )
        assert (
            AnalysisPeriod.WEEKLY
            == "weekly"
        )

    def test_meeting_record(self):
        r = MeetingRecord(
            title="Sprint",
        )
        assert r.title == "Sprint"
        assert r.meeting_id

    def test_conflict_record(self):
        r = ConflictRecord(
            severity="hard",
        )
        assert r.severity == "hard"

    def test_agenda_record(self):
        r = AgendaRecord(
            topics=["A", "B"],
        )
        assert len(r.topics) == 2

    def test_analysis_record(self):
        r = CalendarAnalysisRecord(
            meeting_hours=5.0,
        )
        assert r.meeting_hours == 5.0
