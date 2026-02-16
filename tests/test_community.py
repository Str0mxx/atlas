"""ATLAS Community & Audience Builder testleri."""

import pytest

from app.core.community import (
    AudienceSegmenter,
    CommunityContentPersonalizer,
    CommunityManager,
    CommunityOrchestrator,
    CommunityRetentionEngine,
    EngagementGamifier,
    GrowthTactician,
    MemberAnalyzer,
    ViralLoopDesigner,
)
from app.models.community_models import (
    CampaignRecord,
    EngagementLevel,
    GrowthChannel,
    MemberRecord,
    MemberStatus,
    RetentionStrategy,
    RewardRecord,
    RewardType,
    SegmentRecord,
    SegmentType,
)


# ── Model Testleri ──


class TestSegmentType:
    """SegmentType enum testleri."""

    def test_values(self) -> None:
        assert SegmentType.DEMOGRAPHIC == "demographic"
        assert SegmentType.BEHAVIORAL == "behavioral"
        assert SegmentType.INTEREST == "interest"
        assert SegmentType.VALUE == "value"
        assert SegmentType.DYNAMIC == "dynamic"

    def test_member_count(self) -> None:
        assert len(SegmentType) == 5


class TestMemberStatus:
    """MemberStatus enum testleri."""

    def test_values(self) -> None:
        assert MemberStatus.ACTIVE == "active"
        assert MemberStatus.INACTIVE == "inactive"
        assert MemberStatus.AT_RISK == "at_risk"
        assert MemberStatus.CHURNED == "churned"
        assert MemberStatus.NEW == "new"

    def test_member_count(self) -> None:
        assert len(MemberStatus) == 5


class TestEngagementLevel:
    """EngagementLevel enum testleri."""

    def test_values(self) -> None:
        assert EngagementLevel.LURKER == "lurker"
        assert EngagementLevel.CASUAL == "casual"
        assert EngagementLevel.ACTIVE == "active"
        assert EngagementLevel.POWER_USER == "power_user"
        assert EngagementLevel.CHAMPION == "champion"

    def test_member_count(self) -> None:
        assert len(EngagementLevel) == 5


class TestGrowthChannel:
    """GrowthChannel enum testleri."""

    def test_values(self) -> None:
        assert GrowthChannel.ORGANIC == "organic"
        assert GrowthChannel.REFERRAL == "referral"
        assert GrowthChannel.PAID == "paid"
        assert GrowthChannel.PARTNERSHIP == "partnership"

    def test_member_count(self) -> None:
        assert len(GrowthChannel) == 4


class TestRewardType:
    """RewardType enum testleri."""

    def test_values(self) -> None:
        assert RewardType.POINTS == "points"
        assert RewardType.BADGE == "badge"
        assert RewardType.LEVEL_UP == "level_up"
        assert RewardType.DISCOUNT == "discount"
        assert RewardType.ACCESS == "access"

    def test_member_count(self) -> None:
        assert len(RewardType) == 5


class TestRetentionStrategy:
    """RetentionStrategy enum testleri."""

    def test_values(self) -> None:
        assert RetentionStrategy.RE_ENGAGEMENT == "re_engagement"
        assert RetentionStrategy.WIN_BACK == "win_back"
        assert RetentionStrategy.LOYALTY == "loyalty"
        assert RetentionStrategy.PREVENTION == "prevention"

    def test_member_count(self) -> None:
        assert len(RetentionStrategy) == 4


class TestMemberRecord:
    """MemberRecord model testleri."""

    def test_defaults(self) -> None:
        r = MemberRecord()
        assert len(r.record_id) == 8
        assert r.name == ""
        assert r.segment == "general"
        assert r.engagement_level == "casual"
        assert r.points == 0

    def test_custom(self) -> None:
        r = MemberRecord(
            name="Ali", segment="tech",
            engagement_level="active", points=500,
        )
        assert r.name == "Ali"
        assert r.points == 500


class TestSegmentRecord:
    """SegmentRecord model testleri."""

    def test_defaults(self) -> None:
        r = SegmentRecord()
        assert len(r.record_id) == 8
        assert r.segment_type == "demographic"
        assert r.member_count == 0

    def test_custom(self) -> None:
        r = SegmentRecord(
            name="Tech Lovers",
            segment_type="interest",
            member_count=150,
        )
        assert r.name == "Tech Lovers"
        assert r.member_count == 150


class TestCampaignRecord:
    """CampaignRecord model testleri."""

    def test_defaults(self) -> None:
        r = CampaignRecord()
        assert r.campaign_type == "retention"
        assert r.status == "draft"

    def test_custom(self) -> None:
        r = CampaignRecord(
            name="Re-engage Q1",
            campaign_type="win_back",
            status="active",
        )
        assert r.name == "Re-engage Q1"


class TestRewardRecord:
    """RewardRecord model testleri."""

    def test_defaults(self) -> None:
        r = RewardRecord()
        assert r.reward_type == "points"
        assert r.value == 0

    def test_custom(self) -> None:
        r = RewardRecord(
            member_id="m1",
            reward_type="badge",
            value=100,
        )
        assert r.member_id == "m1"
        assert r.value == 100


# ── AudienceSegmenter Testleri ──


class TestSegmentDemographic:
    """segment_demographic testleri."""

    def test_young(self) -> None:
        s = AudienceSegmenter()
        r = s.segment_demographic("m1", age=15)
        assert r["segmented"] is True
        assert r["group"] == "young"

    def test_adult(self) -> None:
        s = AudienceSegmenter()
        r = s.segment_demographic("m1", age=25, gender="M", location="Istanbul")
        assert r["group"] == "adult"
        assert r["location"] == "Istanbul"

    def test_senior(self) -> None:
        s = AudienceSegmenter()
        r = s.segment_demographic("m1", age=60)
        assert r["group"] == "senior"

    def test_count(self) -> None:
        s = AudienceSegmenter()
        s.segment_demographic("m1", age=30)
        s.segment_demographic("m2", age=40)
        assert s.segment_count == 2
        assert s.segmented_count == 2


class TestSegmentBehavioral:
    """segment_behavioral testleri."""

    def test_power_user(self) -> None:
        s = AudienceSegmenter()
        r = s.segment_behavioral("m1", 10, 10, 10.0)
        assert r["behavior"] == "power_user"

    def test_lurker(self) -> None:
        s = AudienceSegmenter()
        r = s.segment_behavioral("m1", 0, 0, 0.0)
        assert r["behavior"] == "lurker"


class TestClusterInterests:
    """cluster_interests testleri."""

    def test_technology(self) -> None:
        s = AudienceSegmenter()
        r = s.cluster_interests("m1", ["ai", "software"])
        assert "technology" in r["clusters"]

    def test_general(self) -> None:
        s = AudienceSegmenter()
        r = s.cluster_interests("m1", ["cooking"])
        assert "general" in r["clusters"]

    def test_empty(self) -> None:
        s = AudienceSegmenter()
        r = s.cluster_interests("m1")
        assert r["interest_count"] == 0


class TestSegmentByValue:
    """segment_by_value testleri."""

    def test_platinum(self) -> None:
        s = AudienceSegmenter()
        r = s.segment_by_value("m1", 5000.0, 10)
        assert r["tier"] == "platinum"

    def test_bronze(self) -> None:
        s = AudienceSegmenter()
        r = s.segment_by_value("m1", 100.0, 0)
        assert r["tier"] == "bronze"


class TestCreateDynamicGroup:
    """create_dynamic_group testleri."""

    def test_basic(self) -> None:
        s = AudienceSegmenter()
        r = s.create_dynamic_group("VIPs", {"min_points": 1000})
        assert r["created"] is True
        assert r["criteria_count"] == 1

    def test_count(self) -> None:
        s = AudienceSegmenter()
        s.create_dynamic_group("A")
        s.create_dynamic_group("B")
        assert s.segment_count == 2


# ── GrowthTactician Testleri ──


class TestCreateStrategy:
    """create_strategy testleri."""

    def test_basic(self) -> None:
        g = GrowthTactician()
        r = g.create_strategy("Content Growth", "organic", 0.2)
        assert r["created"] is True
        assert r["channel"] == "organic"

    def test_count(self) -> None:
        g = GrowthTactician()
        g.create_strategy("A")
        g.create_strategy("B")
        assert g.strategy_count == 2


class TestOptimizeChannel:
    """optimize_channel testleri."""

    def test_scale_up(self) -> None:
        g = GrowthTactician()
        r = g.optimize_channel("organic", 1.0, 0.8)
        assert r["recommendation"] == "scale_up"

    def test_reconsider(self) -> None:
        g = GrowthTactician()
        r = g.optimize_channel("paid", 100.0, 0.01)
        assert r["recommendation"] == "reconsider"


class TestSuggestAcquisition:
    """suggest_acquisition testleri."""

    def test_high_budget(self) -> None:
        g = GrowthTactician()
        r = g.suggest_acquisition("devs", 2000.0)
        assert "paid_ads" in r["tactics"]
        assert "influencer" in r["tactics"]

    def test_low_budget(self) -> None:
        g = GrowthTactician()
        r = g.suggest_acquisition("devs", 100.0)
        assert "paid_ads" not in r["tactics"]
        assert "seo" in r["tactics"]


class TestOptimizeConversion:
    """optimize_conversion testleri."""

    def test_basic(self) -> None:
        g = GrowthTactician()
        r = g.optimize_conversion("awareness", 0.05, 1000)
        assert r["optimized"] is True
        assert r["potential_converts"] > 0


class TestSuggestExperiment:
    """suggest_experiment testleri."""

    def test_basic(self) -> None:
        g = GrowthTactician()
        r = g.suggest_experiment("CTA color matters", "click_rate")
        assert r["suggested"] is True
        assert r["metric"] == "click_rate"

    def test_count(self) -> None:
        g = GrowthTactician()
        g.suggest_experiment("H1")
        g.suggest_experiment("H2")
        assert g.experiment_count == 2


# ── CommunityManager Testleri ──


class TestManagePlatform:
    """manage_platform testleri."""

    def test_basic(self) -> None:
        m = CommunityManager()
        r = m.manage_platform("Discord", "chat")
        assert r["managed"] is True
        assert r["platform_type"] == "chat"

    def test_count(self) -> None:
        m = CommunityManager()
        m.manage_platform("Discord")
        m.manage_platform("Slack")
        assert m.platform_count == 2


class TestModerateMember:
    """moderate_member testleri."""

    def test_basic(self) -> None:
        m = CommunityManager()
        r = m.moderate_member("m1", "warn", "spam")
        assert r["moderated"] is True
        assert r["action"] == "warn"

    def test_count(self) -> None:
        m = CommunityManager()
        m.moderate_member("m1", "warn")
        m.moderate_member("m2", "ban")
        assert m.moderated_count == 2


class TestCurateContent:
    """curate_content testleri."""

    def test_basic(self) -> None:
        m = CommunityManager()
        r = m.curate_content("c1", "tutorial", True)
        assert r["curated"] is True
        assert r["featured"] is True


class TestCoordinateEvent:
    """coordinate_event testleri."""

    def test_basic(self) -> None:
        m = CommunityManager()
        r = m.coordinate_event("Hackathon", "workshop", 200)
        assert r["coordinated"] is True
        assert r["capacity"] == 200

    def test_count(self) -> None:
        m = CommunityManager()
        m.coordinate_event("E1")
        m.coordinate_event("E2")
        assert m.event_count == 2


class TestRunEngagementProgram:
    """run_engagement_program testleri."""

    def test_basic(self) -> None:
        m = CommunityManager()
        r = m.run_engagement_program("Welcome Week", "new_members", 7)
        assert r["started"] is True
        assert r["duration_days"] == 7


# ── MemberAnalyzer Testleri ──


class TestCreateProfile:
    """create_profile testleri."""

    def test_basic(self) -> None:
        a = MemberAnalyzer()
        r = a.create_profile("m1", "2025-01-01", ["ai", "tech"])
        assert r["profiled"] is True
        assert r["interest_count"] == 2

    def test_count(self) -> None:
        a = MemberAnalyzer()
        a.create_profile("m1")
        a.create_profile("m2")
        assert a.profile_count == 2


class TestAnalyzeActivity:
    """analyze_activity testleri."""

    def test_champion(self) -> None:
        a = MemberAnalyzer()
        r = a.analyze_activity("m1", 50, 40, 20)
        assert r["activity_level"] == "champion"

    def test_lurker(self) -> None:
        a = MemberAnalyzer()
        r = a.analyze_activity("m1", 1, 1, 1)
        assert r["activity_level"] == "lurker"


class TestScoreContribution:
    """score_contribution testleri."""

    def test_top(self) -> None:
        a = MemberAnalyzer()
        r = a.score_contribution("m1", 0.9, 0.9, 0.9)
        assert r["rank"] == "top_contributor"

    def test_newcomer(self) -> None:
        a = MemberAnalyzer()
        r = a.score_contribution("m1", 0.1, 0.1, 0.1)
        assert r["rank"] == "newcomer"


class TestMapInfluence:
    """map_influence testleri."""

    def test_influencer(self) -> None:
        a = MemberAnalyzer()
        r = a.map_influence("m1", 200, 100, 50)
        assert r["tier"] == "influencer"

    def test_member(self) -> None:
        a = MemberAnalyzer()
        r = a.map_influence("m1", 5, 2, 1)
        assert r["tier"] == "member"


class TestPredictChurn:
    """predict_churn testleri."""

    def test_high_risk(self) -> None:
        a = MemberAnalyzer()
        r = a.predict_churn("m1", 80, 0.1, 0.2)
        assert r["status"] == "high_risk"

    def test_low_risk(self) -> None:
        a = MemberAnalyzer()
        r = a.predict_churn("m1", 5, 0.9, 0.9)
        assert r["status"] == "low_risk"

    def test_count(self) -> None:
        a = MemberAnalyzer()
        a.predict_churn("m1")
        a.predict_churn("m2")
        assert a.churn_count == 2


# ── CommunityContentPersonalizer Testleri ──


class TestPersonalizeContent:
    """personalize_content testleri."""

    def test_basic(self) -> None:
        p = CommunityContentPersonalizer()
        r = p.personalize_content("m1", ["a", "b", "c"], "tech")
        assert r["personalized"] is True
        assert r["count"] == 3

    def test_count(self) -> None:
        p = CommunityContentPersonalizer()
        p.personalize_content("m1", ["a"])
        p.personalize_content("m2", ["b"])
        assert p.personalized_count == 2


class TestRecommend:
    """recommend testleri."""

    def test_basic(self) -> None:
        p = CommunityContentPersonalizer()
        r = p.recommend("m1", "tech", 3)
        assert r["recommended"] is True
        assert r["limit"] == 3


class TestLearnPreference:
    """learn_preference testleri."""

    def test_basic(self) -> None:
        p = CommunityContentPersonalizer()
        r = p.learn_preference("m1", "c1", "like", 0.9)
        assert r["learned"] is True

    def test_accumulate(self) -> None:
        p = CommunityContentPersonalizer()
        p.learn_preference("m1", "c1", "view")
        p.learn_preference("m1", "c2", "like")
        assert len(p._preferences["m1"]["actions"]) == 2


class TestRunAbTest:
    """run_ab_test testleri."""

    def test_basic(self) -> None:
        p = CommunityContentPersonalizer()
        r = p.run_ab_test("Header Test", "Bold", "Subtle", 200)
        assert r["tested"] is True
        assert r["winner"] in ("a", "b")

    def test_count(self) -> None:
        p = CommunityContentPersonalizer()
        p.run_ab_test("T1", "A", "B")
        p.run_ab_test("T2", "C", "D")
        assert p.test_count == 2


class TestOptimizeEngagement:
    """optimize_engagement testleri."""

    def test_low_ctr(self) -> None:
        p = CommunityContentPersonalizer()
        r = p.optimize_engagement("m1", 0.01, "article")
        assert "improve_headline" in r["suggestions"]

    def test_moderate_ctr(self) -> None:
        p = CommunityContentPersonalizer()
        r = p.optimize_engagement("m1", 0.03, "video")
        assert "improve_headline" not in r["suggestions"]
        assert "add_visuals" in r["suggestions"]


# ── CommunityRetentionEngine Testleri ──


class TestCreateRetentionStrategy:
    """create_retention_strategy testleri."""

    def test_high_risk(self) -> None:
        e = CommunityRetentionEngine()
        r = e.create_retention_strategy("vip", "high")
        assert r["created"] is True
        assert "personal_outreach" in r["actions"]

    def test_low_risk(self) -> None:
        e = CommunityRetentionEngine()
        r = e.create_retention_strategy("all", "low")
        assert "regular_newsletter" in r["actions"]


class TestLaunchReEngagement:
    """launch_re_engagement testleri."""

    def test_basic(self) -> None:
        e = CommunityRetentionEngine()
        r = e.launch_re_engagement("Q1 Campaign", ["m1", "m2"], "email")
        assert r["launched"] is True
        assert r["target_count"] == 2

    def test_count(self) -> None:
        e = CommunityRetentionEngine()
        e.launch_re_engagement("C1")
        e.launch_re_engagement("C2")
        assert e.campaign_count == 2


class TestRunWinBack:
    """run_win_back testleri."""

    def test_basic(self) -> None:
        e = CommunityRetentionEngine()
        r = e.run_win_back("m1", "discount", 20.0)
        assert r["win_back"] is True
        assert r["offer_value"] == 20.0

    def test_count(self) -> None:
        e = CommunityRetentionEngine()
        e.run_win_back("m1")
        e.run_win_back("m2")
        assert e.retained_count == 2


class TestManageLoyaltyProgram:
    """manage_loyalty_program testleri."""

    def test_default_tiers(self) -> None:
        e = CommunityRetentionEngine()
        r = e.manage_loyalty_program("VIP Club")
        assert r["managed"] is True
        assert r["tier_count"] == 4

    def test_custom_tiers(self) -> None:
        e = CommunityRetentionEngine()
        r = e.manage_loyalty_program("Elite", ["basic", "pro"], 2.0)
        assert r["tier_count"] == 2
        assert r["reward_multiplier"] == 2.0


class TestPreventChurn:
    """prevent_churn testleri."""

    def test_high_risk_auto(self) -> None:
        e = CommunityRetentionEngine()
        r = e.prevent_churn("m1", 0.75)
        assert r["action"] == "personal_call"
        assert r["prevented"] is True

    def test_very_high_risk(self) -> None:
        e = CommunityRetentionEngine()
        r = e.prevent_churn("m1", 0.9)
        assert r["prevented"] is False


# ── ViralLoopDesigner Testleri ──


class TestDesignReferral:
    """design_referral testleri."""

    def test_basic(self) -> None:
        v = ViralLoopDesigner()
        r = v.design_referral("Friend Invite", "points", 200)
        assert r["designed"] is True
        assert r["reward_value"] == 200

    def test_count(self) -> None:
        v = ViralLoopDesigner()
        v.design_referral("A")
        v.design_referral("B")
        assert v.loop_count == 2


class TestCreateSharingIncentive:
    """create_sharing_incentive testleri."""

    def test_basic(self) -> None:
        v = ViralLoopDesigner()
        r = v.create_sharing_incentive("share", 50, 5)
        assert r["created"] is True
        assert r["daily_max_points"] == 250


class TestAnalyzeNetworkEffects:
    """analyze_network_effects testleri."""

    def test_strong(self) -> None:
        v = ViralLoopDesigner()
        r = v.analyze_network_effects(100, 60, 5.0)
        assert r["effect_strength"] == "strong"

    def test_weak(self) -> None:
        v = ViralLoopDesigner()
        r = v.analyze_network_effects(100, 10, 1.0)
        assert r["effect_strength"] == "weak"

    def test_zero_users(self) -> None:
        v = ViralLoopDesigner()
        r = v.analyze_network_effects(0, 0, 0.0)
        assert r["activation_rate"] == 0.0


class TestCalculateViralCoefficient:
    """calculate_viral_coefficient testleri."""

    def test_viral(self) -> None:
        v = ViralLoopDesigner()
        r = v.calculate_viral_coefficient(5.0, 0.3)
        assert r["is_viral"] is True
        assert r["k_factor"] == 1.5

    def test_not_viral(self) -> None:
        v = ViralLoopDesigner()
        r = v.calculate_viral_coefficient(2.0, 0.2)
        assert r["is_viral"] is False
        assert r["k_factor"] == 0.4


class TestModelGrowth:
    """model_growth testleri."""

    def test_basic(self) -> None:
        v = ViralLoopDesigner()
        r = v.model_growth(100, 0.5, 7, 3)
        assert r["modeled"] is True
        assert r["final_users"] > 100
        assert len(r["projections"]) == 4

    def test_count(self) -> None:
        v = ViralLoopDesigner()
        v.model_growth()
        assert v.referral_count == 1


# ── EngagementGamifier Testleri ──


class TestAwardPoints:
    """award_points testleri."""

    def test_basic(self) -> None:
        g = EngagementGamifier()
        r = g.award_points("m1", 150, "contribution")
        assert r["awarded"] is True
        assert r["total_points"] == 150
        assert r["level"] == 2

    def test_accumulate(self) -> None:
        g = EngagementGamifier()
        g.award_points("m1", 50)
        r = g.award_points("m1", 60)
        assert r["total_points"] == 110

    def test_total_points(self) -> None:
        g = EngagementGamifier()
        g.award_points("m1", 100)
        g.award_points("m2", 200)
        assert g.total_points == 300


class TestAwardBadge:
    """award_badge testleri."""

    def test_basic(self) -> None:
        g = EngagementGamifier()
        r = g.award_badge("m1", "First Post", "achievement")
        assert r["awarded"] is True
        assert r["total_badges"] == 1

    def test_count(self) -> None:
        g = EngagementGamifier()
        g.award_badge("m1", "A")
        g.award_badge("m2", "B")
        assert g.badge_count == 2


class TestGetLeaderboard:
    """get_leaderboard testleri."""

    def test_basic(self) -> None:
        g = EngagementGamifier()
        g.award_points("m1", 300)
        g.award_points("m2", 500)
        r = g.get_leaderboard(10)
        assert r["retrieved"] is True
        assert r["entries"][0]["member_id"] == "m2"

    def test_empty(self) -> None:
        g = EngagementGamifier()
        r = g.get_leaderboard()
        assert r["total_members"] == 0


class TestCreateChallenge:
    """create_challenge testleri."""

    def test_basic(self) -> None:
        g = EngagementGamifier()
        r = g.create_challenge("Post 5 times", "post", 5, 100)
        assert r["created"] is True
        assert r["reward_points"] == 100

    def test_count(self) -> None:
        g = EngagementGamifier()
        g.create_challenge("C1", "post", 1)
        g.create_challenge("C2", "comment", 3)
        assert g.challenge_count == 2


class TestClaimReward:
    """claim_reward testleri."""

    def test_affordable(self) -> None:
        g = EngagementGamifier()
        g.award_points("m1", 500)
        r = g.claim_reward("m1", "discount", 200)
        assert r["claimed"] is True
        assert r["remaining_points"] == 300

    def test_not_affordable(self) -> None:
        g = EngagementGamifier()
        g.award_points("m1", 50)
        r = g.claim_reward("m1", "discount", 200)
        assert r["claimed"] is False


# ── CommunityOrchestrator Testleri ──


class TestOnboardMember:
    """onboard_member testleri."""

    def test_basic(self) -> None:
        o = CommunityOrchestrator()
        r = o.onboard_member("Ali", 28, ["ai", "tech"])
        assert r["onboarded"] is True
        assert r["welcome_points"] == 50

    def test_count(self) -> None:
        o = CommunityOrchestrator()
        o.onboard_member("A", 20)
        o.onboard_member("B", 30)
        assert o.onboarded_count == 2
        assert o.pipeline_count == 2


class TestEngageMember:
    """engage_member testleri."""

    def test_basic(self) -> None:
        o = CommunityOrchestrator()
        r = o.engage_member("m1", ["content1", "content2"])
        assert r["engaged"] is True
        assert r["points_earned"] == 10


class TestCommunityGetAnalytics:
    """get_analytics testleri."""

    def test_basic(self) -> None:
        o = CommunityOrchestrator()
        a = o.get_analytics()
        assert "pipelines_run" in a
        assert "total_points" in a

    def test_after_operations(self) -> None:
        o = CommunityOrchestrator()
        o.onboard_member("Ali", 25)
        o.engage_member("m_0", ["c1"])
        a = o.get_analytics()
        assert a["pipelines_run"] == 2
        assert a["members_onboarded"] == 1
        assert a["total_points"] > 0
