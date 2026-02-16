"""ATLAS Reputation & Brand Monitor testleri.

MentionTracker, BrandSentimentAggregator,
ReviewMonitor, CrisisDetector, ResponseSuggester,
BrandHealthScore, CompetitorBrandTracker,
InfluencerTracker, BrandMonOrchestrator testleri.
"""

import pytest

from app.core.brandmon.brand_health_score import (
    BrandHealthScore,
)
from app.core.brandmon.brandmon_orchestrator import (
    BrandMonOrchestrator,
)
from app.core.brandmon.competitor_brand_tracker import (
    CompetitorBrandTracker,
)
from app.core.brandmon.crisis_detector import (
    CrisisDetector,
)
from app.core.brandmon.influencer_tracker import (
    InfluencerTracker,
)
from app.core.brandmon.mention_tracker import (
    MentionTracker,
)
from app.core.brandmon.response_suggester import (
    ResponseSuggester,
)
from app.core.brandmon.review_monitor import (
    ReviewMonitor,
)
from app.core.brandmon.sentiment_aggregator import (
    BrandSentimentAggregator,
)
from app.models.brandmon_models import (
    BrandHealthRecord,
    CrisisLevel,
    CrisisRecord,
    HealthGrade,
    MentionRecord,
    MentionSource,
    ResponseTone,
    ReviewRecord,
    SentimentType,
    TrackingStatus,
)


# ── MentionTracker ─────────────────────────


class TestTrackSocialMedia:
    """track_social_media testleri."""

    def test_basic(self):
        m = MentionTracker()
        r = m.track_social_media(
            "brand1", platform="twitter",
        )
        assert r["tracked"] is True
        assert r["source"] == "social_media"
        assert m.mention_count == 1

    def test_with_content(self):
        m = MentionTracker()
        r = m.track_social_media(
            "b", content="great product",
            sentiment="positive", reach=5000,
        )
        assert r["tracked"] is True


class TestTrackNews:
    """track_news testleri."""

    def test_basic(self):
        m = MentionTracker()
        r = m.track_news(
            "brand1", outlet="CNN",
            headline="Breaking",
        )
        assert r["tracked"] is True
        assert r["source"] == "news"


class TestTrackForum:
    """track_forum testleri."""

    def test_basic(self):
        m = MentionTracker()
        r = m.track_forum(
            "brand1", forum="reddit",
            topic="discussion",
        )
        assert r["tracked"] is True
        assert r["source"] == "forum"


class TestTrackReviewSite:
    """track_review_site testleri."""

    def test_basic(self):
        m = MentionTracker()
        r = m.track_review_site(
            "brand1", site="trustpilot",
            rating=4.5,
        )
        assert r["tracked"] is True
        assert r["source"] == "review"


class TestGetRealtimeFeed:
    """get_realtime_feed testleri."""

    def test_empty(self):
        m = MentionTracker()
        r = m.get_realtime_feed("brand1")
        assert r["total"] == 0

    def test_with_data(self):
        m = MentionTracker()
        m.track_social_media("b", content="x")
        m.track_news("b", headline="y")
        r = m.get_realtime_feed("b")
        assert r["total"] == 2
        assert r["returned"] == 2


# ── BrandSentimentAggregator ──────────────


class TestAnalyzeSentiment:
    """analyze_sentiment testleri."""

    def test_positive(self):
        s = BrandSentimentAggregator()
        r = s.analyze_sentiment(
            "b", text="This is great and amazing",
        )
        assert r["analyzed"] is True
        assert r["sentiment"] == "positive"

    def test_negative(self):
        s = BrandSentimentAggregator()
        r = s.analyze_sentiment(
            "b", text="This is terrible and awful",
        )
        assert r["sentiment"] == "negative"

    def test_neutral(self):
        s = BrandSentimentAggregator()
        r = s.analyze_sentiment(
            "b", text="The product arrived today",
        )
        assert r["sentiment"] == "neutral"


class TestWeightSources:
    """weight_sources testleri."""

    def test_empty(self):
        s = BrandSentimentAggregator()
        r = s.weight_sources("b")
        assert r["weighted"] is False

    def test_with_data(self):
        s = BrandSentimentAggregator()
        s.analyze_sentiment(
            "b", text="great", source="news",
        )
        r = s.weight_sources("b")
        assert r["weighted"] is True
        assert r["weighted_score"] > 0


class TestCalculateTrend:
    """calculate_trend testleri."""

    def test_insufficient(self):
        s = BrandSentimentAggregator()
        s.analyze_sentiment("b", text="ok")
        r = s.calculate_trend("b", window=5)
        assert r["calculated"] is False

    def test_with_data(self):
        s = BrandSentimentAggregator()
        for _ in range(6):
            s.analyze_sentiment(
                "b", text="great amazing",
            )
        r = s.calculate_trend("b", window=3)
        assert r["calculated"] is True
        assert r["direction"] == "stable"


class TestCompareHistorical:
    """compare_historical testleri."""

    def test_empty(self):
        s = BrandSentimentAggregator()
        r = s.compare_historical("b")
        assert r["compared"] is False

    def test_with_data(self):
        s = BrandSentimentAggregator()
        s.analyze_sentiment(
            "b", text="great product",
        )
        r = s.compare_historical("b", 0.5)
        assert r["compared"] is True


class TestBreakdownByChannel:
    """breakdown_by_channel testleri."""

    def test_empty(self):
        s = BrandSentimentAggregator()
        r = s.breakdown_by_channel("b")
        assert r["channels"] == 0

    def test_with_data(self):
        s = BrandSentimentAggregator()
        s.analyze_sentiment(
            "b", text="good",
            source="social_media",
        )
        s.analyze_sentiment(
            "b", text="great",
            source="news",
        )
        r = s.breakdown_by_channel("b")
        assert r["channels"] == 2


# ── ReviewMonitor ──────────────────────────


class TestTrackReview:
    """track_review testleri."""

    def test_basic(self):
        m = ReviewMonitor()
        r = m.track_review(
            "b", platform="google",
            rating=4.5,
        )
        assert r["tracked"] is True
        assert m.review_count == 1


class TestAggregateRatings:
    """aggregate_ratings testleri."""

    def test_empty(self):
        m = ReviewMonitor()
        r = m.aggregate_ratings("b")
        assert r["aggregated"] is False

    def test_with_data(self):
        m = ReviewMonitor()
        m.track_review(
            "b", platform="google",
            rating=4.0,
        )
        m.track_review(
            "b", platform="yelp",
            rating=3.0,
        )
        r = m.aggregate_ratings("b")
        assert r["aggregated"] is True
        assert r["avg_rating"] == 3.5


class TestTrackResponse:
    """track_response testleri."""

    def test_basic(self):
        m = ReviewMonitor()
        r = m.track_response(
            "rev_1", response="Thank you",
            response_time_hours=2.0,
        )
        assert r["responded"] is True


class TestCompareCompetitorsReview:
    """compare_competitors testleri."""

    def test_basic(self):
        m = ReviewMonitor()
        m.track_review(
            "brand_a", rating=4.5,
        )
        m.track_review(
            "brand_b", rating=3.0,
        )
        r = m.compare_competitors(
            brands=["brand_a", "brand_b"],
        )
        assert r["brands_compared"] == 2
        assert r["ranking"][0] == "brand_a"


class TestAlertOnNegative:
    """alert_on_negative testleri."""

    def test_no_negative(self):
        m = ReviewMonitor()
        m.track_review("b", rating=4.5)
        r = m.alert_on_negative("b")
        assert r["alert"] is False

    def test_has_negative(self):
        m = ReviewMonitor()
        m.track_review("b", rating=1.0)
        r = m.alert_on_negative("b")
        assert r["alert"] is True
        assert r["negative_count"] == 1


# ── CrisisDetector ─────────────────────────


class TestDetectViral:
    """detect_viral testleri."""

    def test_not_viral(self):
        c = CrisisDetector()
        r = c.detect_viral(
            "b", mention_count=20,
            time_window_hours=1.0,
            normal_rate=10,
        )
        assert r["is_viral"] is False

    def test_viral(self):
        c = CrisisDetector()
        r = c.detect_viral(
            "b", mention_count=1000,
            time_window_hours=1.0,
            normal_rate=10,
        )
        assert r["is_viral"] is True


class TestDetectNegativeSpike:
    """detect_negative_spike testleri."""

    def test_no_spike(self):
        c = CrisisDetector()
        r = c.detect_negative_spike(
            "b", negative_count=2,
            total_count=100,
        )
        assert r["is_spike"] is False

    def test_spike(self):
        c = CrisisDetector()
        r = c.detect_negative_spike(
            "b", negative_count=80,
            total_count=100,
        )
        assert r["is_spike"] is True


class TestDetectInfluencerMention:
    """detect_influencer_mention testleri."""

    def test_not_risky(self):
        c = CrisisDetector()
        r = c.detect_influencer_mention(
            "b", influencer="user1",
            followers=50000,
            sentiment="positive",
        )
        assert r["is_significant"] is True
        assert r["is_risky"] is False

    def test_risky(self):
        c = CrisisDetector()
        r = c.detect_influencer_mention(
            "b", influencer="user1",
            followers=50000,
            sentiment="negative",
        )
        assert r["is_risky"] is True


class TestDetectMediaCoverage:
    """detect_media_coverage testleri."""

    def test_not_crisis(self):
        c = CrisisDetector()
        r = c.detect_media_coverage(
            "b", outlet_count=1,
        )
        assert r["is_crisis_risk"] is False

    def test_crisis_risk(self):
        c = CrisisDetector()
        r = c.detect_media_coverage(
            "b", outlet_count=5,
            sentiment="negative",
            tier="national",
        )
        assert r["is_crisis_risk"] is True


class TestIssueEarlyWarning:
    """issue_early_warning testleri."""

    def test_no_signals(self):
        c = CrisisDetector()
        r = c.issue_early_warning("b")
        assert r["warning"] is False

    def test_with_signals(self):
        c = CrisisDetector()
        c.detect_viral(
            "b", mention_count=1000,
            normal_rate=10,
        )
        c.detect_negative_spike(
            "b", negative_count=80,
            total_count=100,
        )
        r = c.issue_early_warning("b")
        assert r["warning"] is True
        assert r["level"] == "high"


# ── ResponseSuggester ──────────────────────


class TestAddTemplate:
    """add_template testleri."""

    def test_basic(self):
        r = ResponseSuggester()
        res = r.add_template(
            "apology",
            tone="empathetic",
            template="We are sorry...",
        )
        assert res["added"] is True
        assert r.template_count == 1


class TestSuggestResponse:
    """suggest_response testleri."""

    def test_negative(self):
        r = ResponseSuggester()
        r.add_template(
            "apology",
            tone="empathetic",
            template="We sincerely apologize.",
        )
        res = r.suggest_response(
            sentiment="negative",
        )
        assert res["suggested"] is True
        assert res["tone"] == "empathetic"

    def test_default(self):
        r = ResponseSuggester()
        res = r.suggest_response(
            context="shipping issue",
        )
        assert res["suggested"] is True
        assert "shipping" in res["response"]


class TestPersonalize:
    """personalize testleri."""

    def test_basic(self):
        r = ResponseSuggester()
        res = r.personalize(
            "We apologize.",
            customer_name="Ali",
            brand_name="FTRK",
        )
        assert "Ali" in res["personalized"]
        assert "FTRK" in res["personalized"]


class TestSetEscalationRule:
    """set_escalation_rule testleri."""

    def test_basic(self):
        r = ResponseSuggester()
        res = r.set_escalation_rule(
            "vip_customer",
            condition="vip",
            action="notify_manager",
        )
        assert res["set"] is True


class TestSubmitForApproval:
    """submit_for_approval testleri."""

    def test_basic(self):
        r = ResponseSuggester()
        res = r.submit_for_approval(
            "sug_1", approver="fatih",
        )
        assert res["submitted"] is True
        assert res["status"] == "pending"


# ── BrandHealthScore ───────────────────────


class TestCalculateHealth:
    """calculate_health testleri."""

    def test_excellent(self):
        h = BrandHealthScore()
        r = h.calculate_health(
            "b", sentiment_score=90,
            review_score=90,
            mention_volume=80,
            crisis_score=100,
        )
        assert r["grade"] == "excellent"
        assert h.score_count == 1

    def test_poor(self):
        h = BrandHealthScore()
        r = h.calculate_health(
            "b", sentiment_score=35,
            review_score=35,
            mention_volume=30,
            crisis_score=30,
        )
        assert r["grade"] == "poor"


class TestGetComponentScores:
    """get_component_scores testleri."""

    def test_not_found(self):
        h = BrandHealthScore()
        r = h.get_component_scores("b")
        assert r["found"] is False

    def test_found(self):
        h = BrandHealthScore()
        h.calculate_health("b")
        r = h.get_component_scores("b")
        assert r["found"] is True
        assert "sentiment" in r["components"]


class TestTrackTrend:
    """track_trend testleri."""

    def test_insufficient(self):
        h = BrandHealthScore()
        h.calculate_health("b")
        r = h.track_trend("b")
        assert r["tracked"] is False

    def test_improving(self):
        h = BrandHealthScore()
        h.calculate_health(
            "b", sentiment_score=50,
        )
        h.calculate_health(
            "b", sentiment_score=80,
        )
        r = h.track_trend("b")
        assert r["tracked"] is True
        assert r["direction"] == "improving"


class TestCompareBenchmark:
    """compare_benchmark testleri."""

    def test_not_found(self):
        h = BrandHealthScore()
        r = h.compare_benchmark("b")
        assert r["compared"] is False

    def test_above(self):
        h = BrandHealthScore()
        h.calculate_health(
            "b", sentiment_score=90,
            review_score=90,
            crisis_score=90,
        )
        r = h.compare_benchmark(
            "b", industry_avg=50.0,
        )
        assert r["compared"] is True
        assert r["position"] == "above_average"


class TestSuggestImprovements:
    """suggest_improvements testleri."""

    def test_not_found(self):
        h = BrandHealthScore()
        r = h.suggest_improvements("b")
        assert r["suggested"] is False

    def test_with_low_scores(self):
        h = BrandHealthScore()
        h.calculate_health(
            "b", sentiment_score=30,
            review_score=80,
            mention_volume=20,
            crisis_score=90,
        )
        r = h.suggest_improvements("b")
        assert r["suggested"] is True
        assert r["suggestion_count"] >= 1


# ── CompetitorBrandTracker ─────────────────


class TestMonitorCompetitor:
    """monitor_competitor testleri."""

    def test_basic(self):
        c = CompetitorBrandTracker()
        r = c.monitor_competitor(
            "rival", mentions=50,
        )
        assert r["monitored"] is True
        assert c.competitor_count == 1


class TestCalculateShareOfVoice:
    """calculate_share_of_voice testleri."""

    def test_empty(self):
        c = CompetitorBrandTracker()
        r = c.calculate_share_of_voice(
            "b", brand_mentions=0,
        )
        assert r["calculated"] is False

    def test_with_data(self):
        c = CompetitorBrandTracker()
        c.monitor_competitor(
            "rival", mentions=50,
        )
        r = c.calculate_share_of_voice(
            "b", brand_mentions=100,
        )
        assert r["calculated"] is True
        assert r["sov"] > 0


class TestCompareSentiment:
    """compare_sentiment testleri."""

    def test_basic(self):
        c = CompetitorBrandTracker()
        c.monitor_competitor(
            "rival", sentiment_score=0.4,
        )
        r = c.compare_sentiment(
            "b", brand_score=0.7,
        )
        assert r["compared"] is True


class TestDetectCampaign:
    """detect_campaign testleri."""

    def test_no_campaign(self):
        c = CompetitorBrandTracker()
        r = c.detect_campaign(
            "rival", mention_spike=10,
            normal_rate=10,
        )
        assert r["is_campaign"] is False

    def test_campaign(self):
        c = CompetitorBrandTracker()
        r = c.detect_campaign(
            "rival", mention_spike=100,
            normal_rate=10,
        )
        assert r["is_campaign"] is True
        assert c.campaign_count == 1


class TestAnalyzePositioning:
    """analyze_positioning testleri."""

    def test_no_competitors(self):
        c = CompetitorBrandTracker()
        r = c.analyze_positioning("b")
        assert r["analyzed"] is False

    def test_leader(self):
        c = CompetitorBrandTracker()
        c.monitor_competitor(
            "r1", sentiment_score=0.5,
        )
        c.monitor_competitor(
            "r2", sentiment_score=0.4,
        )
        r = c.analyze_positioning(
            "b", brand_score=80.0,
        )
        assert r["analyzed"] is True
        assert r["position"] == "leader"


# ── InfluencerTracker ──────────────────────


class TestIdentifyInfluencer:
    """identify_influencer testleri."""

    def test_micro(self):
        t = InfluencerTracker()
        r = t.identify_influencer(
            "user1", followers=15000,
            engagement_rate=0.05,
        )
        assert r["identified"] is True
        assert r["tier"] == "micro"

    def test_mega(self):
        t = InfluencerTracker()
        r = t.identify_influencer(
            "celeb", followers=2000000,
        )
        assert r["tier"] == "mega"


class TestAnalyzeReach:
    """analyze_reach testleri."""

    def test_not_found(self):
        t = InfluencerTracker()
        r = t.analyze_reach("unknown")
        assert r["analyzed"] is False

    def test_found(self):
        t = InfluencerTracker()
        t.identify_influencer(
            "user1", followers=50000,
            engagement_rate=0.04,
        )
        r = t.analyze_reach("user1")
        assert r["analyzed"] is True
        assert r["estimated_reach"] == 2000


class TestTrackInfluencerSentiment:
    """track_sentiment testleri."""

    def test_basic(self):
        t = InfluencerTracker()
        r = t.track_sentiment(
            "user1", brand="b",
            sentiment="positive",
        )
        assert r["tracked"] is True


class TestMonitorEngagement:
    """monitor_engagement testleri."""

    def test_empty(self):
        t = InfluencerTracker()
        r = t.monitor_engagement("user1")
        assert r["monitored"] is False

    def test_with_data(self):
        t = InfluencerTracker()
        t.track_sentiment(
            "u", brand="b",
            sentiment="positive",
        )
        t.track_sentiment(
            "u", brand="b",
            sentiment="negative",
        )
        r = t.monitor_engagement("u")
        assert r["monitored"] is True
        assert r["positive_pct"] == 50.0


class TestDetectOpportunity:
    """detect_opportunity testleri."""

    def test_no_match(self):
        t = InfluencerTracker()
        t.identify_influencer(
            "u", followers=100,
            engagement_rate=0.01,
        )
        r = t.detect_opportunity("b")
        assert r["detected"] is False

    def test_found(self):
        t = InfluencerTracker()
        t.identify_influencer(
            "u", followers=50000,
            engagement_rate=0.05,
        )
        t.track_sentiment(
            "u", brand="b",
            sentiment="positive",
        )
        r = t.detect_opportunity("b")
        assert r["detected"] is True
        assert r["count"] == 1


# ── BrandMonOrchestrator ──────────────────


class TestRunBrandMonitoring:
    """run_brand_monitoring testleri."""

    def test_empty(self):
        o = BrandMonOrchestrator()
        r = o.run_brand_monitoring("b")
        assert r["pipeline_complete"] is True
        assert o.pipeline_count == 1

    def test_with_mentions(self):
        o = BrandMonOrchestrator()
        r = o.run_brand_monitoring(
            "b",
            mentions=[
                {
                    "source": "social_media",
                    "content": "great brand",
                    "sentiment": "positive",
                },
                {
                    "source": "news",
                    "content": "coverage",
                    "sentiment": "neutral",
                },
            ],
        )
        assert r["mentions_processed"] == 2

    def test_crisis_alert(self):
        o = BrandMonOrchestrator()
        mentions = [
            {
                "source": "social_media",
                "content": "terrible",
                "sentiment": "negative",
            }
            for _ in range(5)
        ]
        r = o.run_brand_monitoring(
            "b", mentions=mentions,
        )
        assert r["crisis_alert"] is True


class TestTrackAnalyzeAlertRespond:
    """track_analyze_alert_respond testleri."""

    def test_positive(self):
        o = BrandMonOrchestrator()
        r = o.track_analyze_alert_respond(
            "b", content="love this product",
        )
        assert r["processed"] is True
        assert r["needs_response"] is False

    def test_negative(self):
        o = BrandMonOrchestrator()
        r = o.track_analyze_alert_respond(
            "b",
            content="terrible awful service",
        )
        assert r["needs_response"] is True
        assert r["response_suggested"] is True


class TestGetBrandAnalytics:
    """get_analytics testleri."""

    def test_initial(self):
        o = BrandMonOrchestrator()
        r = o.get_analytics()
        assert r["pipelines_run"] == 0
        assert r["mentions"] == 0

    def test_after_pipeline(self):
        o = BrandMonOrchestrator()
        o.run_brand_monitoring("b")
        r = o.get_analytics()
        assert r["pipelines_run"] == 1


# ── Models ─────────────────────────────────


class TestMentionSource:
    """MentionSource testleri."""

    def test_values(self):
        assert (
            MentionSource.SOCIAL_MEDIA
            == "social_media"
        )
        assert MentionSource.NEWS == "news"
        assert MentionSource.FORUM == "forum"
        assert MentionSource.REVIEW == "review"


class TestSentimentType:
    """SentimentType testleri."""

    def test_values(self):
        assert (
            SentimentType.POSITIVE == "positive"
        )
        assert (
            SentimentType.NEGATIVE == "negative"
        )
        assert SentimentType.MIXED == "mixed"


class TestCrisisLevel:
    """CrisisLevel testleri."""

    def test_values(self):
        assert (
            CrisisLevel.CRITICAL == "critical"
        )
        assert CrisisLevel.LOW == "low"


class TestResponseTone:
    """ResponseTone testleri."""

    def test_values(self):
        assert (
            ResponseTone.APOLOGETIC
            == "apologetic"
        )
        assert (
            ResponseTone.EMPATHETIC
            == "empathetic"
        )


class TestHealthGrade:
    """HealthGrade testleri."""

    def test_values(self):
        assert (
            HealthGrade.EXCELLENT == "excellent"
        )
        assert HealthGrade.POOR == "poor"


class TestTrackingStatus:
    """TrackingStatus testleri."""

    def test_values(self):
        assert (
            TrackingStatus.ACTIVE == "active"
        )
        assert (
            TrackingStatus.ARCHIVED
            == "archived"
        )


class TestMentionRecordModel:
    """MentionRecord testleri."""

    def test_defaults(self):
        r = MentionRecord()
        assert r.mention_id
        assert r.source == "social_media"

    def test_custom(self):
        r = MentionRecord(
            source="news",
            sentiment="positive",
        )
        assert r.source == "news"


class TestReviewRecordModel:
    """ReviewRecord testleri."""

    def test_defaults(self):
        r = ReviewRecord()
        assert r.review_id
        assert r.rating == 0.0


class TestCrisisRecordModel:
    """CrisisRecord testleri."""

    def test_defaults(self):
        r = CrisisRecord()
        assert r.crisis_id
        assert r.level == "low"


class TestBrandHealthRecordModel:
    """BrandHealthRecord testleri."""

    def test_defaults(self):
        r = BrandHealthRecord()
        assert r.record_id
        assert r.grade == "fair"

    def test_custom(self):
        r = BrandHealthRecord(
            brand="FTRK",
            score=85.0,
            grade="excellent",
        )
        assert r.brand == "FTRK"
        assert r.score == 85.0
