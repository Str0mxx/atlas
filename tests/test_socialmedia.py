"""ATLAS Social Media Intelligence & Automation testleri."""

import pytest

from app.core.socialmedia import (
    CommentManager,
    EngagementAnalyzer,
    SocialCampaignTracker,
    SocialContentScheduler,
    SocialInfluencerFinder,
    SocialListening,
    SocialMediaOrchestrator,
    SocialPlatformConnector,
    SocialTrendDetector,
)
from app.models.socialmedia_models import (
    CampaignRecord,
    CampaignStatus,
    EngagementRecord,
    EngagementType,
    MentionRecord,
    PostStatus,
    SentimentLevel,
    SocialPlatform,
    SocialPostRecord,
    TrendStrength,
)


# ── Model Testleri ──


class TestSocialPlatform:
    """SocialPlatform enum testleri."""

    def test_values(self) -> None:
        assert SocialPlatform.INSTAGRAM == "instagram"
        assert SocialPlatform.TWITTER == "twitter"
        assert SocialPlatform.FACEBOOK == "facebook"
        assert SocialPlatform.LINKEDIN == "linkedin"
        assert SocialPlatform.TIKTOK == "tiktok"
        assert SocialPlatform.YOUTUBE == "youtube"

    def test_member_count(self) -> None:
        assert len(SocialPlatform) == 6


class TestPostStatus:
    """PostStatus enum testleri."""

    def test_values(self) -> None:
        assert PostStatus.DRAFT == "draft"
        assert PostStatus.SCHEDULED == "scheduled"
        assert PostStatus.PUBLISHED == "published"
        assert PostStatus.FAILED == "failed"

    def test_member_count(self) -> None:
        assert len(PostStatus) == 4


class TestEngagementType:
    """EngagementType enum testleri."""

    def test_values(self) -> None:
        assert EngagementType.LIKE == "like"
        assert EngagementType.COMMENT == "comment"
        assert EngagementType.SHARE == "share"

    def test_member_count(self) -> None:
        assert len(EngagementType) == 5


class TestSentimentLevel:
    """SentimentLevel enum testleri."""

    def test_values(self) -> None:
        assert SentimentLevel.POSITIVE == "positive"
        assert SentimentLevel.NEUTRAL == "neutral"
        assert SentimentLevel.NEGATIVE == "negative"
        assert SentimentLevel.MIXED == "mixed"

    def test_member_count(self) -> None:
        assert len(SentimentLevel) == 4


class TestCampaignStatus:
    """CampaignStatus enum testleri."""

    def test_values(self) -> None:
        assert CampaignStatus.PLANNING == "planning"
        assert CampaignStatus.ACTIVE == "active"
        assert CampaignStatus.PAUSED == "paused"
        assert CampaignStatus.COMPLETED == "completed"

    def test_member_count(self) -> None:
        assert len(CampaignStatus) == 4


class TestTrendStrength:
    """TrendStrength enum testleri."""

    def test_values(self) -> None:
        assert TrendStrength.EMERGING == "emerging"
        assert TrendStrength.GROWING == "growing"
        assert TrendStrength.PEAK == "peak"
        assert TrendStrength.DECLINING == "declining"

    def test_member_count(self) -> None:
        assert len(TrendStrength) == 4


class TestSocialPostRecord:
    """SocialPostRecord model testleri."""

    def test_defaults(self) -> None:
        r = SocialPostRecord()
        assert r.platform == "instagram"
        assert r.content == ""
        assert r.status == "draft"
        assert r.engagement_count == 0
        assert r.record_id
        assert r.created_at

    def test_custom(self) -> None:
        r = SocialPostRecord(
            platform="twitter",
            content="Hello world",
            status="published",
            engagement_count=100,
        )
        assert r.platform == "twitter"
        assert r.content == "Hello world"
        assert r.engagement_count == 100


class TestEngagementRecord:
    """EngagementRecord model testleri."""

    def test_defaults(self) -> None:
        r = EngagementRecord()
        assert r.platform == "instagram"
        assert r.engagement_type == "like"
        assert r.count == 0

    def test_custom(self) -> None:
        r = EngagementRecord(
            post_id="p1",
            engagement_type="comment",
            count=50,
        )
        assert r.post_id == "p1"
        assert r.count == 50


class TestCampaignRecord:
    """CampaignRecord model testleri."""

    def test_defaults(self) -> None:
        r = CampaignRecord()
        assert r.name == ""
        assert r.status == "planning"
        assert r.budget == 0.0

    def test_custom(self) -> None:
        r = CampaignRecord(
            name="Summer Sale",
            budget=5000.0,
            status="active",
        )
        assert r.name == "Summer Sale"
        assert r.budget == 5000.0


class TestMentionRecord:
    """MentionRecord model testleri."""

    def test_defaults(self) -> None:
        r = MentionRecord()
        assert r.platform == "twitter"
        assert r.keyword == ""
        assert r.sentiment == "neutral"

    def test_custom(self) -> None:
        r = MentionRecord(
            keyword="atlas",
            sentiment="positive",
        )
        assert r.keyword == "atlas"
        assert r.sentiment == "positive"


# ── SocialPlatformConnector Testleri ──


class TestConnectPlatform:
    """connect_platform testleri."""

    def test_basic(self) -> None:
        c = SocialPlatformConnector()
        r = c.connect_platform("instagram", "key123")
        assert r["setup"] is True
        assert r["connected"] is True
        assert r["platform"] == "instagram"

    def test_no_key(self) -> None:
        c = SocialPlatformConnector()
        r = c.connect_platform("twitter")
        assert r["connected"] is False

    def test_count(self) -> None:
        c = SocialPlatformConnector()
        c.connect_platform("instagram", "k1")
        c.connect_platform("twitter", "k2")
        assert c.platform_count == 2


class TestMakeApiCall:
    """make_api_call testleri."""

    def test_success(self) -> None:
        c = SocialPlatformConnector()
        c.connect_platform("instagram", "key")
        r = c.make_api_call("instagram", "/posts")
        assert r["success"] is True
        assert r["status_code"] == 200

    def test_not_found(self) -> None:
        c = SocialPlatformConnector()
        r = c.make_api_call("missing", "/test")
        assert r["found"] is False

    def test_count(self) -> None:
        c = SocialPlatformConnector()
        c.connect_platform("ig", "k")
        c.make_api_call("ig", "/a")
        c.make_api_call("ig", "/b")
        assert c.api_call_count == 2


class TestCheckRateLimit:
    """check_rate_limit testleri."""

    def test_basic(self) -> None:
        c = SocialPlatformConnector()
        c.connect_platform("instagram", "k")
        r = c.check_rate_limit("instagram")
        assert r["checked"] is True
        assert r["remaining"] == 100

    def test_not_found(self) -> None:
        c = SocialPlatformConnector()
        r = c.check_rate_limit("missing")
        assert r["found"] is False


class TestHandleError:
    """handle_error testleri."""

    def test_retryable(self) -> None:
        c = SocialPlatformConnector()
        r = c.handle_error("ig", 429, "Rate limited")
        assert r["handled"] is True
        assert r["retry"] is True

    def test_not_retryable(self) -> None:
        c = SocialPlatformConnector()
        r = c.handle_error("ig", 404, "Not found")
        assert r["retry"] is False


class TestReconnect:
    """reconnect testleri."""

    def test_basic(self) -> None:
        c = SocialPlatformConnector()
        c.connect_platform("ig", "k")
        r = c.reconnect("ig")
        assert r["reconnected"] is True

    def test_not_found(self) -> None:
        c = SocialPlatformConnector()
        r = c.reconnect("missing")
        assert r["found"] is False


# ── SocialContentScheduler Testleri ──


class TestSchedulePost:
    """schedule_post testleri."""

    def test_basic(self) -> None:
        s = SocialContentScheduler()
        r = s.schedule_post("Test content", "instagram")
        assert r["scheduled"] is True
        assert r["status"] == "scheduled"

    def test_count(self) -> None:
        s = SocialContentScheduler()
        s.schedule_post("A")
        s.schedule_post("B")
        assert s.scheduled_count == 2


class TestGetBestTime:
    """get_best_time testleri."""

    def test_instagram(self) -> None:
        s = SocialContentScheduler()
        r = s.get_best_time("instagram")
        assert r["detected"] is True
        assert r["recommended"] == 9
        assert len(r["best_hours"]) == 3

    def test_unknown_platform(self) -> None:
        s = SocialContentScheduler()
        r = s.get_best_time("unknown")
        assert r["recommended"] == 9


class TestManageQueue:
    """manage_queue testleri."""

    def test_list(self) -> None:
        s = SocialContentScheduler()
        s.schedule_post("A")
        r = s.manage_queue("list")
        assert r["managed"] is True
        assert r["queue_size"] == 1

    def test_clear(self) -> None:
        s = SocialContentScheduler()
        s.schedule_post("A")
        s.schedule_post("B")
        r = s.manage_queue("clear")
        assert r["cleared"] == 2


class TestCrossPost:
    """cross_post testleri."""

    def test_basic(self) -> None:
        s = SocialContentScheduler()
        r = s.cross_post("Hello!", ["instagram", "twitter"])
        assert r["cross_posted"] is True
        assert r["posts_created"] == 2

    def test_default_platforms(self) -> None:
        s = SocialContentScheduler()
        r = s.cross_post("Test")
        assert r["posts_created"] == 2


class TestSaveDraft:
    """save_draft testleri."""

    def test_basic(self) -> None:
        s = SocialContentScheduler()
        r = s.save_draft("d1", "Draft content", "twitter")
        assert r["saved"] is True
        assert r["draft_id"] == "d1"


# ── EngagementAnalyzer Testleri ──


class TestTrackMetrics:
    """track_metrics testleri."""

    def test_basic(self) -> None:
        e = EngagementAnalyzer()
        r = e.track_metrics(
            "p1", "instagram",
            likes=100, comments=20, shares=10,
            impressions=5000,
        )
        assert r["tracked"] is True
        assert r["total_engagements"] == 130
        assert r["engagement_rate"] == 2.6

    def test_zero_impressions(self) -> None:
        e = EngagementAnalyzer()
        r = e.track_metrics("p2", likes=10)
        assert r["engagement_rate"] == 0.0

    def test_count(self) -> None:
        e = EngagementAnalyzer()
        e.track_metrics("p1")
        e.track_metrics("p2")
        assert e.tracked_count == 2


class TestCalculateEngagementRate:
    """calculate_engagement_rate testleri."""

    def test_excellent(self) -> None:
        e = EngagementAnalyzer()
        r = e.calculate_engagement_rate(500, 5000)
        assert r["calculated"] is True
        assert r["rate"] == 10.0
        assert r["quality"] == "excellent"

    def test_good(self) -> None:
        e = EngagementAnalyzer()
        r = e.calculate_engagement_rate(350, 10000)
        assert r["quality"] == "good"

    def test_average(self) -> None:
        e = EngagementAnalyzer()
        r = e.calculate_engagement_rate(150, 10000)
        assert r["quality"] == "average"

    def test_low(self) -> None:
        e = EngagementAnalyzer()
        r = e.calculate_engagement_rate(5, 10000)
        assert r["quality"] == "low"

    def test_zero_followers(self) -> None:
        e = EngagementAnalyzer()
        r = e.calculate_engagement_rate(100, 0)
        assert r["rate"] == 0.0


class TestAnalyzeAudience:
    """analyze_audience testleri."""

    def test_mega(self) -> None:
        e = EngagementAnalyzer()
        r = e.analyze_audience("instagram", 2000000)
        assert r["audience_size"] == "mega"

    def test_macro(self) -> None:
        e = EngagementAnalyzer()
        r = e.analyze_audience("instagram", 500000)
        assert r["audience_size"] == "macro"

    def test_mid(self) -> None:
        e = EngagementAnalyzer()
        r = e.analyze_audience("instagram", 50000)
        assert r["audience_size"] == "mid"

    def test_micro(self) -> None:
        e = EngagementAnalyzer()
        r = e.analyze_audience("instagram", 5000)
        assert r["audience_size"] == "micro"

    def test_nano(self) -> None:
        e = EngagementAnalyzer()
        r = e.analyze_audience("instagram", 500)
        assert r["audience_size"] == "nano"

    def test_count(self) -> None:
        e = EngagementAnalyzer()
        e.analyze_audience("ig", 100)
        assert e.analysis_count == 1


class TestGetContentPerformance:
    """get_content_performance testleri."""

    def test_basic(self) -> None:
        e = EngagementAnalyzer()
        e.track_metrics("p1", "instagram", impressions=1000, likes=50)
        e.track_metrics("p2", "instagram", impressions=1000, likes=100)
        r = e.get_content_performance("instagram")
        assert r["retrieved"] is True
        assert r["total_tracked"] == 2


class TestBenchmark:
    """benchmark testleri."""

    def test_above_average(self) -> None:
        e = EngagementAnalyzer()
        r = e.benchmark("instagram", 5.0)
        assert r["benchmarked"] is True
        assert r["status"] == "above_average"
        assert r["industry_average"] == 3.5

    def test_below_average(self) -> None:
        e = EngagementAnalyzer()
        r = e.benchmark("instagram", 2.0)
        assert r["status"] == "below_average"


# ── SocialTrendDetector Testleri ──


class TestDetectTrending:
    """detect_trending testleri."""

    def test_basic(self) -> None:
        t = SocialTrendDetector()
        r = t.detect_trending("twitter", "TR")
        assert r["detected"] is True
        assert r["strength"] == "growing"

    def test_count(self) -> None:
        t = SocialTrendDetector()
        t.detect_trending("twitter")
        t.detect_trending("instagram")
        assert t.trend_count == 2


class TestAnalyzeHashtag:
    """analyze_hashtag testleri."""

    def test_basic(self) -> None:
        t = SocialTrendDetector()
        r = t.analyze_hashtag("#fashion", "instagram")
        assert r["analyzed"] is True
        assert r["hashtag"] == "fashion"

    def test_high_competition(self) -> None:
        t = SocialTrendDetector()
        r = t.analyze_hashtag("#longhashtagnamehere")
        assert r["competition"] == "high"

    def test_count(self) -> None:
        t = SocialTrendDetector()
        t.analyze_hashtag("#a")
        t.analyze_hashtag("#b")
        assert t.hashtag_count == 2


class TestDetectViral:
    """detect_viral testleri."""

    def test_viral(self) -> None:
        t = SocialTrendDetector()
        r = t.detect_viral("p1", 10.0, 5.0)
        assert r["detected"] is True
        assert r["is_viral"] is True

    def test_not_viral(self) -> None:
        t = SocialTrendDetector()
        r = t.detect_viral("p1", 2.0, 5.0)
        assert r["is_viral"] is False


class TestDetectEarlyTrend:
    """detect_early_trend testleri."""

    def test_emerging(self) -> None:
        t = SocialTrendDetector()
        r = t.detect_early_trend("AI", 500, 24)
        assert r["detected"] is True
        assert r["is_emerging"] is True

    def test_not_emerging(self) -> None:
        t = SocialTrendDetector()
        r = t.detect_early_trend("old", 10, 24)
        assert r["is_emerging"] is False


class TestCreateOpportunityAlert:
    """create_opportunity_alert testleri."""

    def test_basic(self) -> None:
        t = SocialTrendDetector()
        r = t.create_opportunity_alert("t1", 0.9, "High relevance trend")
        assert r["alert_created"] is True
        assert r["relevance"] == 0.9


# ── SocialInfluencerFinder Testleri ──


class TestDiscoverInfluencers:
    """discover_influencers testleri."""

    def test_basic(self) -> None:
        f = SocialInfluencerFinder()
        r = f.discover_influencers("beauty", "instagram", 10000)
        assert r["discovered"] is True
        assert r["niche"] == "beauty"

    def test_count(self) -> None:
        f = SocialInfluencerFinder()
        f.discover_influencers("beauty")
        f.discover_influencers("tech")
        assert f.found_count == 2


class TestScoreRelevance:
    """score_relevance testleri."""

    def test_premium(self) -> None:
        f = SocialInfluencerFinder()
        r = f.score_relevance("i1", 0.9, 0.9, 0.9)
        assert r["scored"] is True
        assert r["tier"] == "premium"

    def test_high(self) -> None:
        f = SocialInfluencerFinder()
        r = f.score_relevance("i1", 0.7, 0.7, 0.5)
        assert r["tier"] == "high"

    def test_medium(self) -> None:
        f = SocialInfluencerFinder()
        r = f.score_relevance("i1", 0.5, 0.4, 0.3)
        assert r["tier"] == "medium"

    def test_low(self) -> None:
        f = SocialInfluencerFinder()
        r = f.score_relevance("i1", 0.1, 0.1, 0.1)
        assert r["tier"] == "low"


class TestInfluencerEngagement:
    """analyze_engagement testleri."""

    def test_authentic(self) -> None:
        f = SocialInfluencerFinder()
        r = f.analyze_engagement("i1", 10000, 300, 50)
        assert r["analyzed"] is True
        assert r["authentic"] is True
        assert r["engagement_rate"] == 3.5

    def test_not_authentic_too_high(self) -> None:
        f = SocialInfluencerFinder()
        r = f.analyze_engagement("i1", 100, 30, 5)
        assert r["authentic"] is False

    def test_zero_followers(self) -> None:
        f = SocialInfluencerFinder()
        r = f.analyze_engagement("i1", 0, 10, 5)
        assert r["engagement_rate"] == 0.0


class TestTrackOutreach:
    """track_outreach testleri."""

    def test_basic(self) -> None:
        f = SocialInfluencerFinder()
        r = f.track_outreach("i1", "sent", "Hello!")
        assert r["tracked"] is True
        assert r["status"] == "sent"

    def test_count(self) -> None:
        f = SocialInfluencerFinder()
        f.track_outreach("i1")
        f.track_outreach("i2")
        assert f.outreach_count == 2


class TestEstimateROI:
    """estimate_roi testleri."""

    def test_basic(self) -> None:
        f = SocialInfluencerFinder()
        r = f.estimate_roi("i1", 1000.0, 50000, 0.02)
        assert r["estimated"] is True
        assert r["estimated_conversions"] == 1000

    def test_zero_cost(self) -> None:
        f = SocialInfluencerFinder()
        r = f.estimate_roi("i1", 0.0, 1000)
        assert r["roi_percent"] == 0.0


# ── CommentManager Testleri ──


class TestMonitorComments:
    """monitor_comments testleri."""

    def test_basic(self) -> None:
        m = CommentManager()
        r = m.monitor_comments("p1", "instagram")
        assert r["monitoring"] is True
        assert r["post_id"] == "p1"

    def test_count(self) -> None:
        m = CommentManager()
        m.monitor_comments("p1")
        m.monitor_comments("p2")
        assert m.monitored_count == 2


class TestAutoRespond:
    """auto_respond testleri."""

    def test_basic(self) -> None:
        m = CommentManager()
        r = m.auto_respond("c1", "thanks", "Thank you!")
        assert r["auto_responded"] is True
        assert r["response"] == "Thank you!"

    def test_default_response(self) -> None:
        m = CommentManager()
        r = m.auto_respond("c1")
        assert "alindi" in r["response"]

    def test_count(self) -> None:
        m = CommentManager()
        m.auto_respond("c1")
        m.auto_respond("c2")
        assert m.auto_response_count == 2


class TestFilterSentiment:
    """filter_sentiment testleri."""

    def test_positive(self) -> None:
        m = CommentManager()
        r = m.filter_sentiment("This is great and amazing")
        assert r["filtered"] is True
        assert r["sentiment"] == "positive"

    def test_negative(self) -> None:
        m = CommentManager()
        r = m.filter_sentiment("This is terrible and awful")
        assert r["sentiment"] == "negative"

    def test_neutral(self) -> None:
        m = CommentManager()
        r = m.filter_sentiment("Hello there")
        assert r["sentiment"] == "neutral"

    def test_needs_review(self) -> None:
        m = CommentManager()
        r = m.filter_sentiment("terrible product", threshold=0.6)
        assert r["needs_review"] is True


class TestModerate:
    """moderate testleri."""

    def test_approve(self) -> None:
        m = CommentManager()
        r = m.moderate("c1", "approve")
        assert r["moderated"] is True
        assert r["action"] == "approve"

    def test_reject(self) -> None:
        m = CommentManager()
        r = m.moderate("c1", "reject", "spam")
        assert r["action"] == "reject"


class TestEscalate:
    """escalate testleri."""

    def test_basic(self) -> None:
        m = CommentManager()
        r = m.escalate("c1", "high", "Urgent complaint")
        assert r["escalated"] is True
        assert r["severity"] == "high"


# ── SocialListening Testleri ──


class TestTrackBrandMention:
    """track_brand_mention testleri."""

    def test_basic(self) -> None:
        l = SocialListening()
        r = l.track_brand_mention("ATLAS", "twitter", "Great product!", "positive")
        assert r["tracked"] is True
        assert r["brand"] == "ATLAS"
        assert r["sentiment"] == "positive"

    def test_count(self) -> None:
        l = SocialListening()
        l.track_brand_mention("A", "twitter")
        l.track_brand_mention("A", "instagram")
        assert l.mention_count == 2


class TestTrackKeyword:
    """track_keyword testleri."""

    def test_basic(self) -> None:
        l = SocialListening()
        r = l.track_keyword("AI", ["twitter", "linkedin"])
        assert r["tracking"] is True
        assert len(r["platforms"]) == 2

    def test_default_platforms(self) -> None:
        l = SocialListening()
        r = l.track_keyword("tech")
        assert len(r["platforms"]) == 2


class TestMonitorCompetitor:
    """monitor_competitor testleri."""

    def test_basic(self) -> None:
        l = SocialListening()
        r = l.monitor_competitor("CompetitorX", ["twitter"])
        assert r["monitoring"] is True

    def test_default_platforms(self) -> None:
        l = SocialListening()
        r = l.monitor_competitor("CompetitorY")
        assert r["platforms"] == ["twitter"]


class TestAnalyzeSentimentListening:
    """analyze_sentiment testleri."""

    def test_positive(self) -> None:
        l = SocialListening()
        r = l.analyze_sentiment("This is great and wonderful")
        assert r["analyzed"] is True
        assert r["sentiment"] == "positive"
        assert r["score"] == 0.8

    def test_negative(self) -> None:
        l = SocialListening()
        r = l.analyze_sentiment("This is terrible and horrible")
        assert r["sentiment"] == "negative"
        assert r["score"] == 0.2

    def test_neutral(self) -> None:
        l = SocialListening()
        r = l.analyze_sentiment("Hello world")
        assert r["sentiment"] == "neutral"


class TestGenerateAlert:
    """generate_alert testleri."""

    def test_basic(self) -> None:
        l = SocialListening()
        r = l.generate_alert("mention", "warning", "Negative spike")
        assert r["generated"] is True
        assert r["severity"] == "warning"

    def test_count(self) -> None:
        l = SocialListening()
        l.generate_alert("mention")
        l.generate_alert("trend")
        assert l.alert_count == 2


# ── SocialCampaignTracker Testleri ──


class TestCreateCampaign:
    """create_campaign testleri."""

    def test_basic(self) -> None:
        t = SocialCampaignTracker()
        r = t.create_campaign("c1", "Summer Sale", "instagram", 5000.0)
        assert r["created"] is True
        assert r["name"] == "Summer Sale"
        assert r["budget"] == 5000.0

    def test_count(self) -> None:
        t = SocialCampaignTracker()
        t.create_campaign("c1", "A")
        t.create_campaign("c2", "B")
        assert t.campaign_count == 2


class TestTrackPerformance:
    """track_performance testleri."""

    def test_basic(self) -> None:
        t = SocialCampaignTracker()
        t.create_campaign("c1", "Test")
        r = t.track_performance("c1", 10000, 500, 25)
        assert r["tracked"] is True
        assert r["ctr"] == 5.0
        assert r["cvr"] == 5.0

    def test_not_found(self) -> None:
        t = SocialCampaignTracker()
        r = t.track_performance("missing")
        assert r["found"] is False

    def test_cumulative(self) -> None:
        t = SocialCampaignTracker()
        t.create_campaign("c1", "Test")
        t.track_performance("c1", 1000, 50, 5)
        r = t.track_performance("c1", 1000, 50, 5)
        assert r["total_impressions"] == 2000
        assert r["total_clicks"] == 100


class TestRunABTest:
    """run_ab_test testleri."""

    def test_basic(self) -> None:
        t = SocialCampaignTracker()
        t.create_campaign("c1", "Test")
        r = t.run_ab_test("t1", "c1", "Variant A", "Variant B")
        assert r["started"] is True
        assert r["status"] == "running"

    def test_count(self) -> None:
        t = SocialCampaignTracker()
        t.create_campaign("c1", "T")
        t.run_ab_test("t1", "c1")
        t.run_ab_test("t2", "c1")
        assert t.ab_test_count == 2


class TestTrackBudget:
    """track_budget testleri."""

    def test_basic(self) -> None:
        t = SocialCampaignTracker()
        t.create_campaign("c1", "Test", budget=1000.0)
        r = t.track_budget("c1", 300.0)
        assert r["tracked"] is True
        assert r["spent"] == 300.0
        assert r["remaining"] == 700.0
        assert r["over_budget"] is False

    def test_over_budget(self) -> None:
        t = SocialCampaignTracker()
        t.create_campaign("c1", "Test", budget=100.0)
        t.track_budget("c1", 80.0)
        r = t.track_budget("c1", 50.0)
        assert r["over_budget"] is True

    def test_not_found(self) -> None:
        t = SocialCampaignTracker()
        r = t.track_budget("missing")
        assert r["found"] is False


class TestCalculateROI:
    """calculate_roi testleri."""

    def test_profitable(self) -> None:
        t = SocialCampaignTracker()
        t.create_campaign("c1", "Test", budget=1000.0)
        t.track_budget("c1", 500.0)
        r = t.calculate_roi("c1", 1500.0)
        assert r["calculated"] is True
        assert r["roi_percent"] == 200.0
        assert r["profitable"] is True

    def test_not_profitable(self) -> None:
        t = SocialCampaignTracker()
        t.create_campaign("c1", "Test", budget=1000.0)
        t.track_budget("c1", 500.0)
        r = t.calculate_roi("c1", 300.0)
        assert r["profitable"] is False

    def test_not_found(self) -> None:
        t = SocialCampaignTracker()
        r = t.calculate_roi("missing")
        assert r["found"] is False


# ── SocialMediaOrchestrator Testleri ──


class TestPublishContent:
    """publish_content testleri."""

    def test_basic(self) -> None:
        o = SocialMediaOrchestrator()
        r = o.publish_content("Hello world!", "instagram")
        assert r["pipeline_complete"] is True
        assert r["platform"] == "instagram"
        assert "post_id" in r

    def test_with_sentiment(self) -> None:
        o = SocialMediaOrchestrator()
        r = o.publish_content("Great news for everyone!")
        assert r["sentiment"] in ("positive", "neutral", "negative")

    def test_count(self) -> None:
        o = SocialMediaOrchestrator()
        o.publish_content("A")
        o.publish_content("B")
        assert o.pipeline_count == 2


class TestManagePlatform:
    """manage_platform testleri."""

    def test_basic(self) -> None:
        o = SocialMediaOrchestrator()
        r = o.manage_platform("instagram", "key123")
        assert r["managed"] is True
        assert r["connected"] is True

    def test_count(self) -> None:
        o = SocialMediaOrchestrator()
        o.manage_platform("instagram")
        o.manage_platform("twitter")
        assert o.platform_managed_count == 2


class TestOrchestratorGetAnalytics:
    """get_analytics testleri."""

    def test_basic(self) -> None:
        o = SocialMediaOrchestrator()
        a = o.get_analytics()
        assert "pipelines_run" in a
        assert "platforms_connected" in a
        assert "posts_scheduled" in a
        assert "trends_detected" in a
        assert "influencers_found" in a
        assert "campaigns_created" in a

    def test_after_operations(self) -> None:
        o = SocialMediaOrchestrator()
        o.publish_content("Test")
        o.manage_platform("instagram")
        a = o.get_analytics()
        assert a["pipelines_run"] == 1
        assert a["platforms_managed"] == 1
