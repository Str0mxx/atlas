"""ATLAS People & Relationship Manager testleri.

ContactProfiler, PeopleInteractionLogger,
RelationshipScorer, PeopleFollowUpScheduler,
PeopleSentimentTracker, NetworkMapper,
BirthdayReminder, RelationshipAdvisor,
PeopleMgrOrchestrator testleri.
"""

import pytest

from app.core.peoplemgr.contact_profiler import (
    ContactProfiler,
)
from app.core.peoplemgr.interaction_logger import (
    PeopleInteractionLogger,
)
from app.core.peoplemgr.relationship_scorer import (
    RelationshipScorer,
)
from app.core.peoplemgr.followup_scheduler import (
    PeopleFollowUpScheduler,
)
from app.core.peoplemgr.sentiment_tracker import (
    PeopleSentimentTracker,
)
from app.core.peoplemgr.network_mapper import (
    NetworkMapper,
)
from app.core.peoplemgr.birthday_reminder import (
    BirthdayReminder,
)
from app.core.peoplemgr.relationship_advisor import (
    RelationshipAdvisor,
)
from app.core.peoplemgr.peoplemgr_orchestrator import (
    PeopleMgrOrchestrator,
)


# ─── ContactProfiler ────────────────────


class TestProfilerInit:
    """ContactProfiler başlatma."""

    def test_init(self):
        p = ContactProfiler()
        assert p.contact_count == 0

    def test_init_tags(self):
        p = ContactProfiler()
        assert p.tag_count == 0


class TestCreateProfile:
    """Profil oluşturma testleri."""

    def test_create_basic(self):
        p = ContactProfiler()
        r = p.create_profile("Alice")
        assert r["created"] is True
        assert r["name"] == "Alice"

    def test_create_with_details(self):
        p = ContactProfiler()
        r = p.create_profile(
            "Bob", email="bob@test.com",
            company="ACME",
            category="client",
            tags=["vip"],
        )
        assert r["category"] == "client"

    def test_create_increments(self):
        p = ContactProfiler()
        p.create_profile("A")
        p.create_profile("B")
        assert p.contact_count == 2

    def test_tags_indexed(self):
        p = ContactProfiler()
        p.create_profile(
            "A", tags=["vip", "tech"],
        )
        assert p.tag_count == 2


class TestAggregateData:
    """Veri toplama testleri."""

    def test_aggregate(self):
        p = ContactProfiler()
        r = p.create_profile("A")
        cid = r["contact_id"]
        a = p.aggregate_data(
            cid, {"role": "CTO"},
        )
        assert a["aggregated"] is True
        assert a["fields_added"] == 1

    def test_not_found(self):
        p = ContactProfiler()
        a = p.aggregate_data("x", {})
        assert a["aggregated"] is False


class TestEnrichProfile:
    """Zenginleştirme testleri."""

    def test_enrich(self):
        p = ContactProfiler()
        r = p.create_profile("A")
        cid = r["contact_id"]
        e = p.enrich_profile(
            cid, "linkedin",
            {"title": "CEO"},
        )
        assert e["enriched"] is True

    def test_not_found(self):
        p = ContactProfiler()
        e = p.enrich_profile("x", "src")
        assert e["enriched"] is False


class TestAddTags:
    """Etiketleme testleri."""

    def test_add_tags(self):
        p = ContactProfiler()
        r = p.create_profile("A")
        cid = r["contact_id"]
        t = p.add_tags(
            cid, ["vip", "priority"],
        )
        assert t["tags_added"] == 2

    def test_no_duplicate(self):
        p = ContactProfiler()
        r = p.create_profile(
            "A", tags=["vip"],
        )
        cid = r["contact_id"]
        t = p.add_tags(cid, ["vip"])
        assert t["tags_added"] == 0

    def test_not_found(self):
        p = ContactProfiler()
        t = p.add_tags("x", ["a"])
        assert t["tagged"] is False


class TestCategorize:
    """Kategorize testleri."""

    def test_categorize(self):
        p = ContactProfiler()
        r = p.create_profile("A")
        cid = r["contact_id"]
        c = p.categorize(cid, "client")
        assert c["categorized"] is True
        assert c["new_category"] == "client"

    def test_not_found(self):
        p = ContactProfiler()
        c = p.categorize("x", "client")
        assert c["categorized"] is False


class TestProfilerQuery:
    """Sorgu testleri."""

    def test_get_contact(self):
        p = ContactProfiler()
        r = p.create_profile("A")
        c = p.get_contact(
            r["contact_id"],
        )
        assert c is not None

    def test_get_none(self):
        p = ContactProfiler()
        assert p.get_contact("x") is None

    def test_search_category(self):
        p = ContactProfiler()
        p.create_profile(
            "A", category="client",
        )
        p.create_profile(
            "B", category="supplier",
        )
        r = p.search_contacts(
            category="client",
        )
        assert len(r) == 1

    def test_search_tag(self):
        p = ContactProfiler()
        p.create_profile(
            "A", tags=["vip"],
        )
        p.create_profile("B")
        r = p.search_contacts(tag="vip")
        assert len(r) == 1


# ─── PeopleInteractionLogger ────────────


class TestLoggerInit:
    """Logger başlatma."""

    def test_init(self):
        lg = PeopleInteractionLogger()
        assert lg.interaction_count == 0

    def test_init_channels(self):
        lg = PeopleInteractionLogger()
        assert lg.channel_count == 0


class TestLogInteraction:
    """Etkileşim kayıt testleri."""

    def test_log(self):
        lg = PeopleInteractionLogger()
        r = lg.log_interaction(
            "c1", channel="email",
        )
        assert r["logged"] is True

    def test_log_with_content(self):
        lg = PeopleInteractionLogger()
        r = lg.log_interaction(
            "c1", content="Hello",
            sentiment="positive",
        )
        assert r["channel"] == "other"

    def test_increments(self):
        lg = PeopleInteractionLogger()
        lg.log_interaction("c1")
        lg.log_interaction("c1")
        assert lg.interaction_count == 2

    def test_channels_tracked(self):
        lg = PeopleInteractionLogger()
        lg.log_interaction(
            "c1", channel="email",
        )
        lg.log_interaction(
            "c1", channel="phone",
        )
        assert lg.channel_count == 2


class TestChannelStats:
    """Kanal istatistikleri testleri."""

    def test_stats(self):
        lg = PeopleInteractionLogger()
        lg.log_interaction(
            "c1", channel="email",
        )
        lg.log_interaction(
            "c1", channel="email",
        )
        lg.log_interaction(
            "c1", channel="phone",
        )
        s = lg.get_channel_stats("c1")
        assert (
            s["primary_channel"] == "email"
        )

    def test_empty(self):
        lg = PeopleInteractionLogger()
        s = lg.get_channel_stats("c1")
        assert s["total_interactions"] == 0


class TestContentLog:
    """İçerik log testleri."""

    def test_get_log(self):
        lg = PeopleInteractionLogger()
        lg.log_interaction(
            "c1", content="Hi",
        )
        lg.log_interaction(
            "c1", content="Bye",
        )
        logs = lg.get_content_log("c1")
        assert len(logs) == 2


class TestTimeline:
    """Zaman çizelgesi testleri."""

    def test_timeline(self):
        lg = PeopleInteractionLogger()
        lg.log_interaction("c1")
        lg.log_interaction("c1")
        t = lg.get_timeline("c1")
        assert len(t) == 2

    def test_last_interaction(self):
        lg = PeopleInteractionLogger()
        lg.log_interaction("c1")
        last = lg.get_last_interaction("c1")
        assert last is not None

    def test_last_none(self):
        lg = PeopleInteractionLogger()
        assert (
            lg.get_last_interaction("x")
            is None
        )


# ─── RelationshipScorer ─────────────────


class TestScorerInit:
    """Scorer başlatma."""

    def test_init(self):
        s = RelationshipScorer()
        assert s.scored_count == 0


class TestCalculateStrength:
    """İlişki gücü testleri."""

    def test_strong(self):
        s = RelationshipScorer()
        r = s.calculate_strength(
            "c1",
            interaction_count=10,
            recency_days=3,
            sentiment_avg=0.9,
            response_rate=0.9,
        )
        assert r["strength"] == "strong"

    def test_weak(self):
        s = RelationshipScorer()
        r = s.calculate_strength(
            "c1",
            interaction_count=1,
            recency_days=120,
            sentiment_avg=0.3,
        )
        assert r["strength"] in (
            "weak", "dormant",
        )

    def test_breakdown(self):
        s = RelationshipScorer()
        r = s.calculate_strength(
            "c1",
            interaction_count=5,
        )
        assert "interaction" in (
            r["breakdown"]
        )


class TestEngagementLevel:
    """Bağlılık seviyesi testleri."""

    def test_engaged(self):
        s = RelationshipScorer()
        s.calculate_strength(
            "c1",
            interaction_count=10,
            recency_days=5,
            sentiment_avg=0.8,
            response_rate=0.8,
        )
        e = s.get_engagement_level("c1")
        assert e["engagement"] in (
            "highly_engaged", "engaged",
        )

    def test_unknown(self):
        s = RelationshipScorer()
        e = s.get_engagement_level("x")
        assert e["engagement"] == "unknown"


class TestRecencyWeight:
    """Güncellik ağırlığı testleri."""

    def test_recent(self):
        s = RelationshipScorer()
        r = s.apply_recency_weight(
            "c1", days_since=5,
        )
        assert r["weight"] >= 0.8

    def test_old(self):
        s = RelationshipScorer()
        r = s.apply_recency_weight(
            "c1", days_since=100,
        )
        assert r["weight"] < 0.5


class TestTrustScore:
    """Güven puanlama testleri."""

    def test_high_trust(self):
        s = RelationshipScorer()
        r = s.score_trust(
            "c1",
            reliability=0.9,
            consistency=0.9,
            transparency=0.9,
        )
        assert r["trust_level"] == "high"

    def test_low_trust(self):
        s = RelationshipScorer()
        r = s.score_trust(
            "c1",
            reliability=0.2,
            consistency=0.2,
            transparency=0.2,
        )
        assert r["trust_level"] == "low"


class TestScorerTrend:
    """Trend analiz testleri."""

    def test_insufficient(self):
        s = RelationshipScorer()
        r = s.analyze_trend("c1")
        assert r["trend"] == (
            "insufficient_data"
        )

    def test_improving(self):
        s = RelationshipScorer()
        s.calculate_strength(
            "c1",
            interaction_count=2,
            recency_days=30,
        )
        s.calculate_strength(
            "c1",
            interaction_count=10,
            recency_days=3,
            sentiment_avg=0.9,
            response_rate=0.9,
        )
        r = s.analyze_trend("c1")
        assert r["trend"] == "improving"


# ─── PeopleFollowUpScheduler ────────────


class TestFollowUpInit:
    """FollowUp başlatma."""

    def test_init(self):
        f = PeopleFollowUpScheduler()
        assert f.followup_count == 0

    def test_init_pending(self):
        f = PeopleFollowUpScheduler()
        assert f.pending_count == 0


class TestScheduleFollowup:
    """Zamanlama testleri."""

    def test_schedule(self):
        f = PeopleFollowUpScheduler()
        r = f.schedule_followup(
            "c1", "Call back",
        )
        assert r["scheduled"] is True

    def test_with_priority(self):
        f = PeopleFollowUpScheduler()
        r = f.schedule_followup(
            "c1", "Urgent call",
            priority="urgent",
        )
        assert r["priority"] == "urgent"

    def test_increments(self):
        f = PeopleFollowUpScheduler()
        f.schedule_followup("c1", "A")
        f.schedule_followup("c2", "B")
        assert f.followup_count == 2
        assert f.pending_count == 2


class TestOptimalTime:
    """Optimal zaman testleri."""

    def test_weekday(self):
        f = PeopleFollowUpScheduler()
        r = f.find_optimal_time("c1")
        assert r["optimal"] is True

    def test_weekend(self):
        f = PeopleFollowUpScheduler()
        r = f.find_optimal_time(
            "c1", preferred_day="weekend",
        )
        assert r["optimal"] is True


class TestReminder:
    """Hatırlatma testleri."""

    def test_create_reminder(self):
        f = PeopleFollowUpScheduler()
        r = f.schedule_followup(
            "c1", "Call",
        )
        fid = r["followup_id"]
        rem = f.create_reminder(fid)
        assert rem["reminded"] is True

    def test_not_found(self):
        f = PeopleFollowUpScheduler()
        rem = f.create_reminder("x")
        assert rem["reminded"] is False


class TestPrioritize:
    """Önceliklendirme testleri."""

    def test_prioritize(self):
        f = PeopleFollowUpScheduler()
        f.schedule_followup(
            "c1", "A", priority="low",
        )
        f.schedule_followup(
            "c2", "B", priority="urgent",
        )
        p = f.prioritize()
        assert p[0]["priority"] == "urgent"


class TestAutoSchedule:
    """Otomatik zamanlama testleri."""

    def test_auto(self):
        f = PeopleFollowUpScheduler()
        r = f.auto_schedule(
            "c1",
            relationship_score=80,
        )
        assert r["scheduled"] is True

    def test_overdue(self):
        f = PeopleFollowUpScheduler()
        r = f.auto_schedule(
            "c1",
            relationship_score=80,
            last_contact_days=30,
        )
        assert r["overdue"] is True


class TestCompleteFollowup:
    """Tamamlama testleri."""

    def test_complete(self):
        f = PeopleFollowUpScheduler()
        r = f.schedule_followup(
            "c1", "Call",
        )
        c = f.complete_followup(
            r["followup_id"],
        )
        assert c["completed"] is True
        assert f.pending_count == 0

    def test_not_found(self):
        f = PeopleFollowUpScheduler()
        c = f.complete_followup("x")
        assert c["completed"] is False


# ─── PeopleSentimentTracker ──────────────


class TestSentimentInit:
    """Sentiment başlatma."""

    def test_init(self):
        s = PeopleSentimentTracker()
        assert s.analyzed_count == 0

    def test_init_alerts(self):
        s = PeopleSentimentTracker()
        assert s.alert_count == 0


class TestAnalyzeSentiment:
    """Duygu analizi testleri."""

    def test_positive(self):
        s = PeopleSentimentTracker()
        r = s.analyze_sentiment(
            "c1", score=0.8,
        )
        assert r["level"] == "very_positive"

    def test_negative(self):
        s = PeopleSentimentTracker()
        r = s.analyze_sentiment(
            "c1", score=0.1,
        )
        assert r["level"] == "very_negative"
        assert r["alert"] is not None

    def test_neutral(self):
        s = PeopleSentimentTracker()
        r = s.analyze_sentiment(
            "c1", score=0.5,
        )
        assert r["level"] == "neutral"


class TestTrackMood:
    """Ruh hali testleri."""

    def test_mood(self):
        s = PeopleSentimentTracker()
        s.analyze_sentiment("c1", score=0.8)
        s.analyze_sentiment("c1", score=0.7)
        m = s.track_mood("c1")
        assert m["mood"] == "positive"

    def test_unknown(self):
        s = PeopleSentimentTracker()
        m = s.track_mood("x")
        assert m["mood"] == "unknown"


class TestDetectSentimentTrend:
    """Duygu trend testleri."""

    def test_improving(self):
        s = PeopleSentimentTracker()
        s.analyze_sentiment("c1", score=0.3)
        s.analyze_sentiment("c1", score=0.4)
        s.analyze_sentiment("c1", score=0.7)
        s.analyze_sentiment("c1", score=0.8)
        r = s.detect_trend("c1")
        assert r["trend"] == "improving"

    def test_insufficient(self):
        s = PeopleSentimentTracker()
        r = s.detect_trend("c1")
        assert r["trend"] == (
            "insufficient_data"
        )


class TestAlertNegative:
    """Negatif uyarı testleri."""

    def test_alert(self):
        s = PeopleSentimentTracker()
        s.analyze_sentiment("c1", score=0.1)
        r = s.alert_on_negative("c1")
        assert r["alert"] is True

    def test_no_alert(self):
        s = PeopleSentimentTracker()
        s.analyze_sentiment("c1", score=0.8)
        r = s.alert_on_negative("c1")
        assert r["alert"] is False

    def test_empty(self):
        s = PeopleSentimentTracker()
        r = s.alert_on_negative("x")
        assert r["alert"] is False


class TestSentimentHistorical:
    """Geçmiş görünüm testleri."""

    def test_historical(self):
        s = PeopleSentimentTracker()
        s.analyze_sentiment("c1", score=0.5)
        s.analyze_sentiment("c1", score=0.7)
        h = s.get_historical("c1")
        assert len(h) == 2


# ─── NetworkMapper ───────────────────────


class TestNetworkInit:
    """Network başlatma."""

    def test_init(self):
        n = NetworkMapper()
        assert n.node_count == 0

    def test_init_edges(self):
        n = NetworkMapper()
        assert n.edge_count == 0


class TestAddNode:
    """Düğüm ekleme testleri."""

    def test_add(self):
        n = NetworkMapper()
        r = n.add_node("c1", name="Alice")
        assert r["added"] is True

    def test_increments(self):
        n = NetworkMapper()
        n.add_node("c1")
        n.add_node("c2")
        assert n.node_count == 2


class TestMapConnection:
    """Bağlantı haritalama testleri."""

    def test_map(self):
        n = NetworkMapper()
        n.add_node("c1")
        n.add_node("c2")
        r = n.map_connection("c1", "c2")
        assert r["mapped"] is True

    def test_increments(self):
        n = NetworkMapper()
        n.add_node("c1")
        n.add_node("c2")
        n.add_node("c3")
        n.map_connection("c1", "c2")
        n.map_connection("c1", "c3")
        assert n.edge_count == 2


class TestScoreInfluence:
    """Etki puanlama testleri."""

    def test_score(self):
        n = NetworkMapper()
        n.add_node(
            "c1", influence=0.7,
        )
        n.add_node("c2")
        n.map_connection("c1", "c2")
        r = n.score_influence("c1")
        assert r["scored"] is True
        assert r["influence_score"] > 0

    def test_not_found(self):
        n = NetworkMapper()
        r = n.score_influence("x")
        assert r["scored"] is False


class TestDetectCommunities:
    """Topluluk tespiti testleri."""

    def test_single_community(self):
        n = NetworkMapper()
        n.add_node("c1")
        n.add_node("c2")
        n.map_connection("c1", "c2")
        r = n.detect_communities()
        assert r["count"] == 1

    def test_two_communities(self):
        n = NetworkMapper()
        n.add_node("c1")
        n.add_node("c2")
        n.add_node("c3")
        n.add_node("c4")
        n.map_connection("c1", "c2")
        n.map_connection("c3", "c4")
        r = n.detect_communities()
        assert r["count"] == 2

    def test_empty(self):
        n = NetworkMapper()
        r = n.detect_communities()
        assert r["count"] == 0


class TestFindPath:
    """Yol bulma testleri."""

    def test_direct(self):
        n = NetworkMapper()
        n.add_node("c1")
        n.add_node("c2")
        n.map_connection("c1", "c2")
        r = n.find_path("c1", "c2")
        assert r["found"] is True
        assert r["length"] == 1

    def test_indirect(self):
        n = NetworkMapper()
        n.add_node("c1")
        n.add_node("c2")
        n.add_node("c3")
        n.map_connection("c1", "c2")
        n.map_connection("c2", "c3")
        r = n.find_path("c1", "c3")
        assert r["found"] is True
        assert r["length"] == 2

    def test_no_path(self):
        n = NetworkMapper()
        n.add_node("c1")
        n.add_node("c2")
        r = n.find_path("c1", "c2")
        assert r["found"] is False


class TestVisualizationData:
    """Görselleştirme testleri."""

    def test_data(self):
        n = NetworkMapper()
        n.add_node("c1", name="Alice")
        n.add_node("c2", name="Bob")
        n.map_connection("c1", "c2")
        v = n.get_visualization_data()
        assert v["node_count"] == 2
        assert v["edge_count"] == 1


# ─── BirthdayReminder ───────────────────


class TestBirthdayInit:
    """Birthday başlatma."""

    def test_init(self):
        b = BirthdayReminder()
        assert b.tracked_count == 0

    def test_init_celebrations(self):
        b = BirthdayReminder()
        assert b.celebration_count == 0


class TestTrackBirthday:
    """Doğum günü takip testleri."""

    def test_track(self):
        b = BirthdayReminder()
        r = b.track_birthday(
            "c1", "Alice", 6, 15,
        )
        assert r["tracked"] is True
        assert r["date"] == "06-15"

    def test_increments(self):
        b = BirthdayReminder()
        b.track_birthday(
            "c1", "Alice", 6, 15,
        )
        b.track_birthday(
            "c2", "Bob", 3, 20,
        )
        assert b.tracked_count == 2


class TestCheckUpcoming:
    """Yaklaşan kontrol testleri."""

    def test_upcoming(self):
        b = BirthdayReminder()
        b.track_birthday(
            "c1", "Alice", 6, 20,
        )
        r = b.check_upcoming(6, 15, 7)
        assert len(r) == 1
        assert r[0]["name"] == "Alice"

    def test_none_upcoming(self):
        b = BirthdayReminder()
        b.track_birthday(
            "c1", "Alice", 12, 25,
        )
        r = b.check_upcoming(6, 15, 7)
        assert len(r) == 0


class TestSuggestGift:
    """Hediye önerisi testleri."""

    def test_client(self):
        b = BirthdayReminder()
        r = b.suggest_gift(
            "c1", budget=150,
            relationship="client",
        )
        assert r["count"] == 3

    def test_colleague(self):
        b = BirthdayReminder()
        r = b.suggest_gift(
            "c1",
            relationship="colleague",
        )
        assert r["count"] == 3


class TestMessageTemplate:
    """Mesaj şablonu testleri."""

    def test_professional(self):
        b = BirthdayReminder()
        b.track_birthday(
            "c1", "Alice", 6, 15,
        )
        r = b.get_message_template("c1")
        assert "Alice" in r["message"]

    def test_friendly(self):
        b = BirthdayReminder()
        b.track_birthday(
            "c1", "Bob", 3, 20,
        )
        r = b.get_message_template(
            "c1", tone="friendly",
        )
        assert "Happy Birthday" in (
            r["message"]
        )


class TestRecordCelebration:
    """Kutlama kaydı testleri."""

    def test_record(self):
        b = BirthdayReminder()
        r = b.record_celebration(
            "c1", action="sent_message",
            message_sent=True,
        )
        assert r["recorded"] is True
        assert b.celebration_count == 1


class TestGetBirthday:
    """Doğum günü sorgulama."""

    def test_get(self):
        b = BirthdayReminder()
        b.track_birthday(
            "c1", "Alice", 6, 15,
        )
        bd = b.get_birthday("c1")
        assert bd is not None

    def test_get_none(self):
        b = BirthdayReminder()
        assert b.get_birthday("x") is None


# ─── RelationshipAdvisor ─────────────────


class TestAdvisorInit:
    """Advisor başlatma."""

    def test_init(self):
        a = RelationshipAdvisor()
        assert a.health_check_count == 0

    def test_init_suggestions(self):
        a = RelationshipAdvisor()
        assert a.suggestion_count == 0


class TestAssessHealth:
    """Sağlık değerlendirme testleri."""

    def test_healthy(self):
        a = RelationshipAdvisor()
        r = a.assess_health(
            "c1", score=100,
            last_contact_days=5,
            sentiment_avg=1.0,
            interaction_count=15,
        )
        assert r["status"] == "healthy"

    def test_at_risk(self):
        a = RelationshipAdvisor()
        r = a.assess_health(
            "c1", score=20,
            last_contact_days=100,
            sentiment_avg=0.3,
        )
        assert r["status"] == "at_risk"


class TestSuggestActions:
    """Aksiyon önerisi testleri."""

    def test_at_risk(self):
        a = RelationshipAdvisor()
        r = a.suggest_actions(
            "c1",
            health_status="at_risk",
        )
        assert r["count"] >= 4

    def test_healthy(self):
        a = RelationshipAdvisor()
        r = a.suggest_actions(
            "c1",
            health_status="healthy",
        )
        assert r["count"] >= 3

    def test_client(self):
        a = RelationshipAdvisor()
        r = a.suggest_actions(
            "c1",
            relationship_type="client",
        )
        assert r["suggested"] is True


class TestReengageTips:
    """Yeniden bağlanma testleri."""

    def test_long_dormant(self):
        a = RelationshipAdvisor()
        r = a.reengage_tips(
            "c1", dormant_days=200,
        )
        assert r["urgency"] == "high"

    def test_medium_dormant(self):
        a = RelationshipAdvisor()
        r = a.reengage_tips(
            "c1", dormant_days=100,
        )
        assert r["urgency"] == "medium"

    def test_negative_last(self):
        a = RelationshipAdvisor()
        r = a.reengage_tips(
            "c1", dormant_days=100,
            last_sentiment="negative",
        )
        assert "Acknowledge" in (
            r["tips"][0]
        )


class TestResolveConflict:
    """Çatışma çözümü testleri."""

    def test_communication(self):
        a = RelationshipAdvisor()
        r = a.resolve_conflict(
            "c1",
            conflict_type="communication",
        )
        assert r["count"] >= 3

    def test_trust(self):
        a = RelationshipAdvisor()
        r = a.resolve_conflict(
            "c1",
            conflict_type="trust",
        )
        assert r["count"] >= 3

    def test_high_severity(self):
        a = RelationshipAdvisor()
        r = a.resolve_conflict(
            "c1", severity="high",
        )
        assert "Escalate" in (
            r["strategies"][0]
        )


class TestGrowthOpportunities:
    """Büyüme fırsatları testleri."""

    def test_client(self):
        a = RelationshipAdvisor()
        r = a.find_growth_opportunities(
            "c1",
            relationship_type="client",
            current_score=70,
        )
        assert r["count"] >= 3

    def test_low_score(self):
        a = RelationshipAdvisor()
        r = a.find_growth_opportunities(
            "c1", current_score=30,
        )
        assert "trust" in (
            r["opportunities"][0].lower()
        )


# ─── PeopleMgrOrchestrator ──────────────


class TestOrchestratorInit:
    """Orchestrator başlatma."""

    def test_init(self):
        o = PeopleMgrOrchestrator()
        assert o.contact_count == 0

    def test_init_cycles(self):
        o = PeopleMgrOrchestrator()
        assert o.cycle_count == 0

    def test_has_components(self):
        o = PeopleMgrOrchestrator()
        assert o.profiler is not None
        assert o.interactions is not None
        assert o.scorer is not None
        assert o.followups is not None
        assert o.sentiment is not None
        assert o.network is not None
        assert o.birthdays is not None
        assert o.advisor is not None


class TestOnboardContact:
    """Kişi onboard testleri."""

    def test_onboard(self):
        o = PeopleMgrOrchestrator()
        r = o.onboard_contact("Alice")
        assert r["onboarded"] is True

    def test_with_details(self):
        o = PeopleMgrOrchestrator()
        r = o.onboard_contact(
            "Bob",
            email="bob@test.com",
            category="client",
            tags=["vip"],
        )
        assert r["category"] == "client"

    def test_increments(self):
        o = PeopleMgrOrchestrator()
        o.onboard_contact("A")
        o.onboard_contact("B")
        assert o.contact_count == 2


class TestRelationshipCycle:
    """İlişki döngüsü testleri."""

    def test_cycle(self):
        o = PeopleMgrOrchestrator()
        r = o.onboard_contact("Alice")
        cid = r["contact_id"]
        c = o.run_relationship_cycle(
            cid,
            interaction_count=5,
            last_contact_days=10,
            sentiment_score=0.7,
        )
        assert c["cycle_complete"] is True

    def test_at_risk_followup(self):
        o = PeopleMgrOrchestrator()
        r = o.onboard_contact("Alice")
        cid = r["contact_id"]
        c = o.run_relationship_cycle(
            cid,
            interaction_count=0,
            last_contact_days=120,
            sentiment_score=0.2,
        )
        assert (
            c["followup_scheduled"] is True
        )

    def test_increments(self):
        o = PeopleMgrOrchestrator()
        r = o.onboard_contact("A")
        o.run_relationship_cycle(
            r["contact_id"],
        )
        assert o.cycle_count == 1


class TestNetworkIntelligence:
    """Ağ zekası testleri."""

    def test_intelligence(self):
        o = PeopleMgrOrchestrator()
        o.onboard_contact("A")
        o.onboard_contact("B")
        r = o.get_network_intelligence()
        assert r["total_contacts"] == 2
        assert r["network_nodes"] == 2


class TestOrchestratorAnalytics:
    """Analitik testleri."""

    def test_analytics(self):
        o = PeopleMgrOrchestrator()
        o.onboard_contact("Alice")
        a = o.get_analytics()
        assert a["contacts_managed"] == 1
        assert a["total_contacts"] == 1

    def test_analytics_empty(self):
        o = PeopleMgrOrchestrator()
        a = o.get_analytics()
        assert a["contacts_managed"] == 0
