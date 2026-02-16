"""ATLAS Event & Conference Intelligence testleri."""

import pytest

from app.core.eventintel import (
    EventAgendaAnalyzer,
    EventDiscovery,
    EventIntelOrchestrator,
    EventROICalculator,
    EventRelevanceScorer,
    NetworkingPlanner,
    PostEventFollowUp,
    RegistrationAutomator,
    SpeakerTracker,
)
from app.models.eventintel_models import (
    ContactRecord,
    EventCategory,
    EventRecord,
    FollowUpStatus,
    NetworkingPriority,
    ROICategory,
    ROIRecord,
    RegistrationStatus,
    SpeakerRecord,
    SpeakerTier,
)


# ── Model Testleri ──


class TestEventCategory:
    """EventCategory enum testleri."""

    def test_values(self) -> None:
        assert EventCategory.CONFERENCE == "conference"
        assert EventCategory.SUMMIT == "summit"
        assert EventCategory.WORKSHOP == "workshop"
        assert EventCategory.MEETUP == "meetup"
        assert EventCategory.WEBINAR == "webinar"
        assert EventCategory.TRADE_SHOW == "trade_show"

    def test_member_count(self) -> None:
        assert len(EventCategory) == 6


class TestRegistrationStatus:
    """RegistrationStatus enum testleri."""

    def test_values(self) -> None:
        assert RegistrationStatus.PENDING == "pending"
        assert RegistrationStatus.CONFIRMED == "confirmed"
        assert RegistrationStatus.WAITLISTED == "waitlisted"
        assert RegistrationStatus.CANCELLED == "cancelled"
        assert RegistrationStatus.ATTENDED == "attended"

    def test_member_count(self) -> None:
        assert len(RegistrationStatus) == 5


class TestSpeakerTier:
    """SpeakerTier enum testleri."""

    def test_values(self) -> None:
        assert SpeakerTier.KEYNOTE == "keynote"
        assert SpeakerTier.FEATURED == "featured"
        assert SpeakerTier.REGULAR == "regular"
        assert SpeakerTier.PANELIST == "panelist"
        assert SpeakerTier.LIGHTNING == "lightning"

    def test_member_count(self) -> None:
        assert len(SpeakerTier) == 5


class TestFollowUpStatus:
    """FollowUpStatus enum testleri."""

    def test_values(self) -> None:
        assert FollowUpStatus.PENDING == "pending"
        assert FollowUpStatus.SENT == "sent"
        assert FollowUpStatus.RESPONDED == "responded"
        assert FollowUpStatus.MEETING_SET == "meeting_set"
        assert FollowUpStatus.CLOSED == "closed"

    def test_member_count(self) -> None:
        assert len(FollowUpStatus) == 5


class TestNetworkingPriority:
    """NetworkingPriority enum testleri."""

    def test_values(self) -> None:
        assert NetworkingPriority.CRITICAL == "critical"
        assert NetworkingPriority.HIGH == "high"
        assert NetworkingPriority.MEDIUM == "medium"
        assert NetworkingPriority.LOW == "low"

    def test_member_count(self) -> None:
        assert len(NetworkingPriority) == 4


class TestROICategory:
    """ROICategory enum testleri."""

    def test_values(self) -> None:
        assert ROICategory.EXCELLENT == "excellent"
        assert ROICategory.GOOD == "good"
        assert ROICategory.MODERATE == "moderate"
        assert ROICategory.POOR == "poor"

    def test_member_count(self) -> None:
        assert len(ROICategory) == 4


class TestEventRecord:
    """EventRecord model testleri."""

    def test_defaults(self) -> None:
        r = EventRecord()
        assert len(r.record_id) == 8
        assert r.name == ""
        assert r.category == "conference"
        assert r.relevance == 0.0

    def test_custom(self) -> None:
        r = EventRecord(
            name="Tech Summit", category="summit",
            location="Istanbul", relevance=0.85,
        )
        assert r.name == "Tech Summit"
        assert r.relevance == 0.85


class TestSpeakerRecord:
    """SpeakerRecord model testleri."""

    def test_defaults(self) -> None:
        r = SpeakerRecord()
        assert r.tier == "regular"
        assert r.topics == []
        assert r.rating == 0.0

    def test_custom(self) -> None:
        r = SpeakerRecord(
            name="Dr. Smith", tier="keynote",
            topics=["AI", "ML"], rating=4.5,
        )
        assert r.name == "Dr. Smith"
        assert len(r.topics) == 2


class TestContactRecord:
    """ContactRecord model testleri."""

    def test_defaults(self) -> None:
        r = ContactRecord()
        assert r.followup_status == "pending"

    def test_custom(self) -> None:
        r = ContactRecord(
            name="Ali", event_id="e1",
            followup_status="sent",
        )
        assert r.name == "Ali"


class TestROIRecord:
    """ROIRecord model testleri."""

    def test_defaults(self) -> None:
        r = ROIRecord()
        assert r.total_cost == 0.0
        assert r.roi_pct == 0.0

    def test_custom(self) -> None:
        r = ROIRecord(
            event_id="e1", total_cost=1000.0,
            total_revenue=3000.0, roi_pct=200.0,
        )
        assert r.roi_pct == 200.0


# ── EventDiscovery Testleri ──


class TestSearchEvents:
    """search_events testleri."""

    def test_basic(self) -> None:
        d = EventDiscovery()
        r = d.search_events("AI Summit", "conference", "Istanbul")
        assert r["discovered"] is True
        assert r["category"] == "conference"

    def test_count(self) -> None:
        d = EventDiscovery()
        d.search_events("A")
        d.search_events("B")
        assert d.discovered_count == 2


class TestAggregateSources:
    """aggregate_sources testleri."""

    def test_basic(self) -> None:
        d = EventDiscovery()
        r = d.aggregate_sources(["eventbrite", "meetup", "luma"])
        assert r["aggregated"] is True
        assert r["source_count"] == 3

    def test_count(self) -> None:
        d = EventDiscovery()
        d.aggregate_sources(["a", "b"])
        assert d.source_count == 2


class TestFilterByCategory:
    """filter_by_category testleri."""

    def test_matches(self) -> None:
        d = EventDiscovery()
        d.search_events("A", "conference")
        d.search_events("B", "meetup")
        r = d.filter_by_category("conference")
        assert r["match_count"] == 1

    def test_no_matches(self) -> None:
        d = EventDiscovery()
        r = d.filter_by_category("summit")
        assert r["match_count"] == 0


class TestFilterByDate:
    """filter_by_date testleri."""

    def test_basic(self) -> None:
        d = EventDiscovery()
        r = d.filter_by_date("2025-01-01", "2025-12-31")
        assert r["filtered"] is True


class TestFilterByLocation:
    """filter_by_location testleri."""

    def test_matches(self) -> None:
        d = EventDiscovery()
        d.search_events("A", location="Istanbul")
        r = d.filter_by_location("Istanbul")
        assert r["match_count"] == 1


# ── EventRelevanceScorer Testleri ──


class TestScoreRelevance:
    """score_relevance testleri."""

    def test_must_attend(self) -> None:
        s = EventRelevanceScorer()
        r = s.score_relevance("e1", 0.9, 0.9, 0.9)
        assert r["level"] == "must_attend"

    def test_skip(self) -> None:
        s = EventRelevanceScorer()
        r = s.score_relevance("e1", 0.1, 0.1, 0.1)
        assert r["level"] == "skip"

    def test_count(self) -> None:
        s = EventRelevanceScorer()
        s.score_relevance("e1", 0.5, 0.5, 0.5)
        s.score_relevance("e2", 0.7, 0.7, 0.7)
        assert s.scored_count == 2


class TestMatchInterests:
    """match_interests testleri."""

    def test_full_match(self) -> None:
        s = EventRelevanceScorer()
        r = s.match_interests("e1", ["ai", "ml"], ["ai", "ml", "data"])
        assert r["match_score"] == 1.0

    def test_no_match(self) -> None:
        s = EventRelevanceScorer()
        r = s.match_interests("e1", ["ai"], ["cooking"])
        assert r["match_score"] == 0.0


class TestEstimateROI:
    """estimate_roi testleri."""

    def test_positive(self) -> None:
        s = EventRelevanceScorer()
        r = s.estimate_roi("e1", 500.0, 300.0, 10, 200.0)
        assert r["estimated"] is True
        assert r["estimated_roi"] > 0

    def test_zero_cost(self) -> None:
        s = EventRelevanceScorer()
        r = s.estimate_roi("e1", 0.0, 0.0, 5, 100.0)
        assert r["estimated_roi"] == 0.0


class TestRankPriority:
    """rank_priority testleri."""

    def test_basic(self) -> None:
        s = EventRelevanceScorer()
        events = [
            {"id": "e1", "score": 0.3},
            {"id": "e2", "score": 0.9},
            {"id": "e3", "score": 0.6},
        ]
        r = s.rank_priority(events)
        assert r["ranked"][0]["score"] == 0.9

    def test_count(self) -> None:
        s = EventRelevanceScorer()
        s.rank_priority([{"score": 1}])
        assert s.priority_count == 1


class TestPersonalizeScore:
    """personalize_score testleri."""

    def test_basic(self) -> None:
        s = EventRelevanceScorer()
        r = s.personalize_score("e1", 0.7, 3, 0.1)
        assert r["personalized"] is True
        assert r["final_score"] > 0.7

    def test_cap_at_one(self) -> None:
        s = EventRelevanceScorer()
        r = s.personalize_score("e1", 0.9, 10, 0.5)
        assert r["final_score"] <= 1.0


# ── RegistrationAutomator Testleri ──


class TestAutoRegister:
    """auto_register testleri."""

    def test_basic(self) -> None:
        ra = RegistrationAutomator()
        r = ra.auto_register("e1", "Fatih", "fatih@test.com")
        assert r["registered"] is True
        assert r["status"] == "confirmed"

    def test_count(self) -> None:
        ra = RegistrationAutomator()
        ra.auto_register("e1", "A")
        ra.auto_register("e2", "B")
        assert ra.registration_count == 2


class TestFillForm:
    """fill_form testleri."""

    def test_basic(self) -> None:
        ra = RegistrationAutomator()
        r = ra.fill_form("e1", {"name": "A", "email": "a@b.com"})
        assert r["filled"] is True
        assert r["fields_filled"] == 2


class TestHandlePayment:
    """handle_payment testleri."""

    def test_basic(self) -> None:
        ra = RegistrationAutomator()
        r = ra.handle_payment("e1", 500.0, "USD", "card")
        assert r["processed"] is True
        assert r["amount"] == 500.0


class TestTrackConfirmation:
    """track_confirmation testleri."""

    def test_basic(self) -> None:
        ra = RegistrationAutomator()
        reg = ra.auto_register("e1", "A")
        r = ra.track_confirmation(reg["registration_id"], "attended")
        assert r["tracked"] is True
        assert r["status"] == "attended"


class TestSyncCalendar:
    """sync_calendar testleri."""

    def test_basic(self) -> None:
        ra = RegistrationAutomator()
        r = ra.sync_calendar("e1", "google", "2025-06-15")
        assert r["synced"] is True

    def test_count(self) -> None:
        ra = RegistrationAutomator()
        ra.sync_calendar("e1")
        ra.sync_calendar("e2")
        assert ra.sync_count == 2


# ── EventAgendaAnalyzer Testleri ──


class TestAnalyzeSession:
    """analyze_session testleri."""

    def test_basic(self) -> None:
        a = EventAgendaAnalyzer()
        r = a.analyze_session("s1", "AI Workshop", "Dr. Smith", "10:00-11:00")
        assert r["analyzed"] is True
        assert r["speaker"] == "Dr. Smith"

    def test_count(self) -> None:
        a = EventAgendaAnalyzer()
        a.analyze_session("s1", "A")
        a.analyze_session("s2", "B")
        assert a.analyzed_count == 2


class TestTrackSpeakers:
    """track_speakers testleri."""

    def test_basic(self) -> None:
        a = EventAgendaAnalyzer()
        r = a.track_speakers("e1", ["Smith", "Jones", "Lee"])
        assert r["tracked"] is True
        assert r["speaker_count"] == 3


class TestExtractTopics:
    """extract_topics testleri."""

    def test_basic(self) -> None:
        a = EventAgendaAnalyzer()
        r = a.extract_topics("e1", ["Machine Learning Workshop", "Deep Learning Talk"])
        assert r["extracted"] is True
        assert r["topic_count"] > 0


class TestOptimizeSchedule:
    """optimize_schedule testleri."""

    def test_basic(self) -> None:
        a = EventAgendaAnalyzer()
        sessions = [{"id": f"s{i}"} for i in range(8)]
        r = a.optimize_schedule(sessions, 5)
        assert r["optimized"] is True
        assert r["selected_count"] == 5


class TestDetectConflicts:
    """detect_conflicts testleri."""

    def test_conflict(self) -> None:
        a = EventAgendaAnalyzer()
        sessions = [
            {"session_id": "s1", "time_slot": "10:00"},
            {"session_id": "s2", "time_slot": "10:00"},
            {"session_id": "s3", "time_slot": "11:00"},
        ]
        r = a.detect_conflicts(sessions)
        assert r["conflict_count"] == 1

    def test_no_conflict(self) -> None:
        a = EventAgendaAnalyzer()
        sessions = [
            {"session_id": "s1", "time_slot": "10:00"},
            {"session_id": "s2", "time_slot": "11:00"},
        ]
        r = a.detect_conflicts(sessions)
        assert r["conflict_count"] == 0

    def test_count(self) -> None:
        a = EventAgendaAnalyzer()
        a.detect_conflicts([
            {"session_id": "a", "time_slot": "9:00"},
            {"session_id": "b", "time_slot": "9:00"},
        ])
        assert a.conflict_count == 1


# ── NetworkingPlanner Testleri ──


class TestIdentifyTargets:
    """identify_targets testleri."""

    def test_basic(self) -> None:
        n = NetworkingPlanner()
        r = n.identify_targets("e1", {"role": "CTO", "company_size": "100+"})
        assert r["identified"] is True
        assert r["criteria_count"] == 2

    def test_count(self) -> None:
        n = NetworkingPlanner()
        n.identify_targets("e1")
        n.identify_targets("e2")
        assert n.target_count == 2


class TestScheduleMeeting:
    """schedule_meeting testleri."""

    def test_basic(self) -> None:
        n = NetworkingPlanner()
        r = n.schedule_meeting("t1", "14:00", "Lobby")
        assert r["scheduled"] is True

    def test_count(self) -> None:
        n = NetworkingPlanner()
        n.schedule_meeting("t1")
        n.schedule_meeting("t2")
        assert n.meeting_count == 2


class TestRequestIntro:
    """request_intro testleri."""

    def test_basic(self) -> None:
        n = NetworkingPlanner()
        r = n.request_intro("CEO Smith", "Ali", "Partnership")
        assert r["requested"] is True
        assert r["connector"] == "Ali"


class TestPlanFollowup:
    """plan_followup testleri."""

    def test_basic(self) -> None:
        n = NetworkingPlanner()
        r = n.plan_followup("Smith", "email", 2)
        assert r["planned"] is True
        assert r["days_after"] == 2


class TestTrackConnection:
    """track_connection testleri."""

    def test_basic(self) -> None:
        n = NetworkingPlanner()
        r = n.track_connection("Smith", "e1", "connected")
        assert r["tracked"] is True


# ── PostEventFollowUp Testleri ──


class TestCollectContact:
    """collect_contact testleri."""

    def test_basic(self) -> None:
        f = PostEventFollowUp()
        r = f.collect_contact("Ali", "ali@test.com", "e1", "Good talk")
        assert r["collected"] is True

    def test_count(self) -> None:
        f = PostEventFollowUp()
        f.collect_contact("A")
        f.collect_contact("B")
        assert f.contact_count == 2


class TestAutomateFollowup:
    """automate_followup testleri."""

    def test_basic(self) -> None:
        f = PostEventFollowUp()
        r = f.automate_followup("c1", "thank_you", "email")
        assert r["sent"] is True

    def test_count(self) -> None:
        f = PostEventFollowUp()
        f.automate_followup("c1")
        f.automate_followup("c2")
        assert f.followup_count == 2


class TestOrganizeNotes:
    """organize_notes testleri."""

    def test_basic(self) -> None:
        f = PostEventFollowUp()
        r = f.organize_notes("e1", ["Note 1", "Note 2", "Note 3"])
        assert r["organized"] is True
        assert r["note_count"] == 3


class TestCreateActionItem:
    """create_action_item testleri."""

    def test_basic(self) -> None:
        f = PostEventFollowUp()
        r = f.create_action_item("Send proposal", "Fatih", 3, "high")
        assert r["created"] is True
        assert r["priority"] == "high"


class TestBuildRelationship:
    """build_relationship testleri."""

    def test_strong(self) -> None:
        f = PostEventFollowUp()
        r = f.build_relationship("c1", 10, 0.9)
        assert r["strength"] == "strong"

    def test_new(self) -> None:
        f = PostEventFollowUp()
        r = f.build_relationship("c1", 1, 0.5)
        assert r["strength"] == "new"


# ── SpeakerTracker Testleri ──


class TestAddSpeaker:
    """add_speaker testleri."""

    def test_basic(self) -> None:
        t = SpeakerTracker()
        r = t.add_speaker("Dr. Smith", ["AI", "ML"], "keynote")
        assert r["added"] is True
        assert r["tier"] == "keynote"

    def test_count(self) -> None:
        t = SpeakerTracker()
        t.add_speaker("A")
        t.add_speaker("B")
        assert t.tracked_count == 2


class TestFindByTopic:
    """find_by_topic testleri."""

    def test_match(self) -> None:
        t = SpeakerTracker()
        t.add_speaker("Smith", ["AI", "ML"])
        t.add_speaker("Jones", ["Data"])
        r = t.find_by_topic("AI")
        assert r["match_count"] == 1

    def test_no_match(self) -> None:
        t = SpeakerTracker()
        t.add_speaker("Smith", ["AI"])
        r = t.find_by_topic("cooking")
        assert r["match_count"] == 0


class TestCheckAvailability:
    """check_availability testleri."""

    def test_available(self) -> None:
        t = SpeakerTracker()
        s = t.add_speaker("Smith")
        r = t.check_availability(s["speaker_id"])
        assert r["available"] is True

    def test_not_found(self) -> None:
        t = SpeakerTracker()
        r = t.check_availability("nonexistent")
        assert r["found"] is False


class TestBookSpeaker:
    """book_speaker testleri."""

    def test_basic(self) -> None:
        t = SpeakerTracker()
        s = t.add_speaker("Smith")
        r = t.book_speaker(s["speaker_id"], "e1", "2025-06-15")
        assert r["booked"] is True

    def test_becomes_unavailable(self) -> None:
        t = SpeakerTracker()
        s = t.add_speaker("Smith")
        t.book_speaker(s["speaker_id"], "e1")
        r = t.check_availability(s["speaker_id"])
        assert r["available"] is False

    def test_count(self) -> None:
        t = SpeakerTracker()
        s = t.add_speaker("Smith")
        t.book_speaker(s["speaker_id"], "e1")
        assert t.booking_count == 1


class TestRateSpeaker:
    """rate_speaker testleri."""

    def test_basic(self) -> None:
        t = SpeakerTracker()
        s = t.add_speaker("Smith")
        r = t.rate_speaker(s["speaker_id"], 4.5, "Great talk")
        assert r["rated"] is True
        assert r["average_rating"] == 4.5

    def test_multiple_ratings(self) -> None:
        t = SpeakerTracker()
        s = t.add_speaker("Smith")
        t.rate_speaker(s["speaker_id"], 4.0)
        r = t.rate_speaker(s["speaker_id"], 5.0)
        assert r["average_rating"] == 4.5
        assert r["total_ratings"] == 2

    def test_not_found(self) -> None:
        t = SpeakerTracker()
        r = t.rate_speaker("nonexistent", 3.0)
        assert r["rated"] is False


# ── EventROICalculator Testleri ──


class TestTrackCosts:
    """track_costs testleri."""

    def test_basic(self) -> None:
        c = EventROICalculator()
        r = c.track_costs("e1", 500.0, 300.0, 200.0, 50.0)
        assert r["tracked"] is True
        assert r["total_cost"] == 1050.0


class TestAttributeLeads:
    """attribute_leads testleri."""

    def test_basic(self) -> None:
        c = EventROICalculator()
        r = c.attribute_leads("e1", 20, 8)
        assert r["attributed"] is True
        assert r["qualification_rate"] == 0.4

    def test_zero_leads(self) -> None:
        c = EventROICalculator()
        r = c.attribute_leads("e1", 0, 0)
        assert r["qualification_rate"] == 0.0


class TestTrackRevenueImpact:
    """track_revenue_impact testleri."""

    def test_basic(self) -> None:
        c = EventROICalculator()
        r = c.track_revenue_impact("e1", 5000.0, 15000.0)
        assert r["tracked"] is True
        assert r["total_impact"] == 20000.0


class TestCalculateROI:
    """calculate_roi testleri."""

    def test_excellent(self) -> None:
        c = EventROICalculator()
        c.track_costs("e1", 500.0, 200.0)
        c.track_revenue_impact("e1", 3000.0, 0.0)
        r = c.calculate_roi("e1")
        assert r["calculated"] is True
        assert r["category"] == "excellent"

    def test_poor(self) -> None:
        c = EventROICalculator()
        c.track_costs("e1", 1000.0, 500.0)
        r = c.calculate_roi("e1")
        assert r["category"] == "poor"

    def test_not_found(self) -> None:
        c = EventROICalculator()
        r = c.calculate_roi("nonexistent")
        assert r["found"] is False

    def test_count(self) -> None:
        c = EventROICalculator()
        c.track_costs("e1", 100.0)
        c.calculate_roi("e1")
        assert c.calculated_count == 1


class TestCompareEvents:
    """compare_events testleri."""

    def test_basic(self) -> None:
        c = EventROICalculator()
        c.track_costs("e1", 500.0)
        c.track_revenue_impact("e1", 2000.0)
        c.track_costs("e2", 300.0)
        c.track_revenue_impact("e2", 3000.0)
        r = c.compare_events(["e1", "e2"])
        assert r["compared"] is True
        assert r["best_event"] == "e2"

    def test_count(self) -> None:
        c = EventROICalculator()
        c.compare_events([])
        assert c.comparison_count == 1


# ── EventIntelOrchestrator Testleri ──


class TestDiscoverAndRegister:
    """discover_and_register testleri."""

    def test_basic(self) -> None:
        o = EventIntelOrchestrator()
        r = o.discover_and_register("AI Summit", "conference", "Fatih")
        assert r["pipeline_complete"] is True
        assert "registration_id" in r

    def test_count(self) -> None:
        o = EventIntelOrchestrator()
        o.discover_and_register("A")
        o.discover_and_register("B")
        assert o.pipeline_count == 2
        assert o.managed_count == 2


class TestPostEventProcess:
    """post_event_process testleri."""

    def test_basic(self) -> None:
        o = EventIntelOrchestrator()
        r = o.post_event_process("e1", ["Ali", "Veli", "Ayse"])
        assert r["processed"] is True
        assert r["contacts_collected"] == 3


class TestEventIntelGetAnalytics:
    """get_analytics testleri."""

    def test_basic(self) -> None:
        o = EventIntelOrchestrator()
        a = o.get_analytics()
        assert "pipelines_run" in a
        assert "rois_calculated" in a

    def test_after_operations(self) -> None:
        o = EventIntelOrchestrator()
        o.discover_and_register("AI Summit", "conference", "Fatih")
        o.post_event_process("e1", ["Ali"])
        a = o.get_analytics()
        assert a["pipelines_run"] == 2
        assert a["events_discovered"] == 1
        assert a["contacts_collected"] == 1
