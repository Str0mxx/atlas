"""ATLAS Referral & Word-of-Mouth Engine testleri."""

import pytest

from app.core.referral import (
    AmbassadorManager,
    IncentiveOptimizer,
    ReferralConversionTracker,
    ReferralFraudDetector,
    ReferralOrchestrator,
    ReferralProgramBuilder,
    ReferralRewardCalculator,
    TrackingLinkGenerator,
    ViralCoefficientCalculator,
)
from app.models.referral_models import (
    AmbassadorRecord,
    AmbassadorTier,
    FraudRecord,
    FraudRisk,
    IncentiveStrategy,
    LinkRecord,
    ReferralRecord,
    ReferralStatus,
    RewardType,
    ViralPhase,
)


# ── Model Testleri ──


class TestReferralStatus:
    """ReferralStatus enum testleri."""

    def test_values(self) -> None:
        assert ReferralStatus.PENDING == "pending"
        assert ReferralStatus.CLICKED == "clicked"
        assert ReferralStatus.SIGNED_UP == "signed_up"
        assert ReferralStatus.CONVERTED == "converted"
        assert ReferralStatus.REWARDED == "rewarded"
        assert ReferralStatus.REJECTED == "rejected"

    def test_member_count(self) -> None:
        assert len(ReferralStatus) == 6


class TestRewardType:
    """RewardType enum testleri."""

    def test_values(self) -> None:
        assert RewardType.CASH == "cash"
        assert RewardType.CREDIT == "credit"
        assert RewardType.DISCOUNT == "discount"
        assert RewardType.POINTS == "points"
        assert RewardType.GIFT == "gift"

    def test_member_count(self) -> None:
        assert len(RewardType) == 5


class TestAmbassadorTier:
    """AmbassadorTier enum testleri."""

    def test_values(self) -> None:
        assert AmbassadorTier.BRONZE == "bronze"
        assert AmbassadorTier.SILVER == "silver"
        assert AmbassadorTier.GOLD == "gold"
        assert AmbassadorTier.PLATINUM == "platinum"
        assert AmbassadorTier.DIAMOND == "diamond"

    def test_member_count(self) -> None:
        assert len(AmbassadorTier) == 5


class TestFraudRisk:
    """FraudRisk enum testleri."""

    def test_values(self) -> None:
        assert FraudRisk.CLEAN == "clean"
        assert FraudRisk.LOW == "low"
        assert FraudRisk.MEDIUM == "medium"
        assert FraudRisk.HIGH == "high"
        assert FraudRisk.BLOCKED == "blocked"

    def test_member_count(self) -> None:
        assert len(FraudRisk) == 5


class TestIncentiveStrategy:
    """IncentiveStrategy enum testleri."""

    def test_values(self) -> None:
        assert IncentiveStrategy.FIXED == "fixed"
        assert IncentiveStrategy.PERCENTAGE == "percentage"
        assert IncentiveStrategy.TIERED == "tiered"
        assert IncentiveStrategy.DYNAMIC == "dynamic"

    def test_member_count(self) -> None:
        assert len(IncentiveStrategy) == 4


class TestViralPhase:
    """ViralPhase enum testleri."""

    def test_values(self) -> None:
        assert ViralPhase.SEED == "seed"
        assert ViralPhase.GROWTH == "growth"
        assert ViralPhase.VIRAL == "viral"
        assert ViralPhase.PLATEAU == "plateau"

    def test_member_count(self) -> None:
        assert len(ViralPhase) == 4


class TestReferralRecord:
    """ReferralRecord model testleri."""

    def test_defaults(self) -> None:
        r = ReferralRecord()
        assert len(r.record_id) == 8
        assert r.status == "pending"
        assert r.reward_amount == 0.0

    def test_custom(self) -> None:
        r = ReferralRecord(
            referrer_id="u1", referred_id="u2",
            status="converted", reward_amount=25.0,
        )
        assert r.referrer_id == "u1"
        assert r.reward_amount == 25.0


class TestAmbassadorRecord:
    """AmbassadorRecord model testleri."""

    def test_defaults(self) -> None:
        r = AmbassadorRecord()
        assert r.tier == "bronze"
        assert r.total_referrals == 0

    def test_custom(self) -> None:
        r = AmbassadorRecord(
            name="Ali", tier="gold",
            total_referrals=25, total_earnings=500.0,
        )
        assert r.name == "Ali"
        assert r.total_earnings == 500.0


class TestLinkRecord:
    """LinkRecord model testleri."""

    def test_defaults(self) -> None:
        r = LinkRecord()
        assert r.clicks == 0
        assert r.conversions == 0

    def test_custom(self) -> None:
        r = LinkRecord(
            referrer_id="u1", url="https://x.com/ref/abc",
            clicks=100, conversions=10,
        )
        assert r.clicks == 100


class TestFraudRecord:
    """FraudRecord model testleri."""

    def test_defaults(self) -> None:
        r = FraudRecord()
        assert r.risk_level == "clean"

    def test_custom(self) -> None:
        r = FraudRecord(
            referral_id="r1", risk_level="high",
            reason="self-referral",
        )
        assert r.reason == "self-referral"


# ── ReferralProgramBuilder Testleri ──


class TestDesignProgram:
    """design_program testleri."""

    def test_basic(self) -> None:
        b = ReferralProgramBuilder()
        r = b.design_program("Friends Get $10", "credit", 10.0)
        assert r["designed"] is True
        assert r["reward_type"] == "credit"

    def test_count(self) -> None:
        b = ReferralProgramBuilder()
        b.design_program("A")
        b.design_program("B")
        assert b.program_count == 2


class TestSetRewardStructure:
    """set_reward_structure testleri."""

    def test_basic(self) -> None:
        b = ReferralProgramBuilder()
        p = b.design_program("Test")
        r = b.set_reward_structure(p["program_id"], 15.0, 10.0, True)
        assert r["configured"] is True
        assert r["double_sided"] is True


class TestAddRule:
    """add_rule testleri."""

    def test_basic(self) -> None:
        b = ReferralProgramBuilder()
        p = b.design_program("Test")
        r = b.add_rule(p["program_id"], "min_purchase", "value >= 50")
        assert r["added"] is True
        assert r["rule_count"] == 1


class TestConfigureTiers:
    """configure_tiers testleri."""

    def test_default(self) -> None:
        b = ReferralProgramBuilder()
        p = b.design_program("Test")
        r = b.configure_tiers(p["program_id"])
        assert r["configured"] is True
        assert r["tier_count"] == 4

    def test_custom(self) -> None:
        b = ReferralProgramBuilder()
        p = b.design_program("Test")
        r = b.configure_tiers(p["program_id"], [{"name": "basic"}])
        assert r["tier_count"] == 1


class TestCreateVariant:
    """create_variant testleri."""

    def test_basic(self) -> None:
        b = ReferralProgramBuilder()
        r = b.create_variant("p1", "higher_reward", {"amount": 20})
        assert r["created"] is True

    def test_count(self) -> None:
        b = ReferralProgramBuilder()
        b.create_variant("p1", "A")
        b.create_variant("p1", "B")
        assert b.variant_count == 2


# ── TrackingLinkGenerator Testleri ──


class TestGenerateLink:
    """generate_link testleri."""

    def test_basic(self) -> None:
        g = TrackingLinkGenerator()
        r = g.generate_link("user1", "summer")
        assert r["generated"] is True
        assert "ref/" in r["url"]

    def test_count(self) -> None:
        g = TrackingLinkGenerator()
        g.generate_link("u1")
        g.generate_link("u2")
        assert g.link_count == 2


class TestAddUtmParams:
    """add_utm_params testleri."""

    def test_basic(self) -> None:
        g = TrackingLinkGenerator()
        r = g.add_utm_params("https://app.com", "referral", "link", "summer")
        assert r["added"] is True
        assert "utm_source=referral" in r["full_url"]
        assert "utm_campaign=summer" in r["full_url"]


class TestCreateShortUrl:
    """create_short_url testleri."""

    def test_basic(self) -> None:
        g = TrackingLinkGenerator()
        r = g.create_short_url("https://app.com/very-long-url")
        assert r["created"] is True
        assert "ref.link" in r["short_url"]

    def test_custom_slug(self) -> None:
        g = TrackingLinkGenerator()
        r = g.create_short_url("https://app.com", "myref")
        assert r["slug"] == "myref"


class TestGenerateQrCode:
    """generate_qr_code testleri."""

    def test_basic(self) -> None:
        g = TrackingLinkGenerator()
        r = g.generate_qr_code("https://app.com/ref/abc", 512)
        assert r["generated"] is True
        assert r["size"] == 512

    def test_count(self) -> None:
        g = TrackingLinkGenerator()
        g.generate_qr_code("url1")
        g.generate_qr_code("url2")
        assert g.qr_count == 2


class TestCreateDeepLink:
    """create_deep_link testleri."""

    def test_universal(self) -> None:
        g = TrackingLinkGenerator()
        r = g.create_deep_link("u1", "signup", "universal")
        assert r["created"] is True
        assert "app.link" in r["deep_link"]

    def test_ios(self) -> None:
        g = TrackingLinkGenerator()
        r = g.create_deep_link("u1", "home", "ios")
        assert "app://" in r["deep_link"]


# ── ReferralRewardCalculator Testleri ──


class TestCalculateReward:
    """calculate_reward testleri."""

    def test_basic(self) -> None:
        c = ReferralRewardCalculator()
        r = c.calculate_reward("u1", 10.0, 2.0)
        assert r["calculated"] is True
        assert r["amount"] == 20.0

    def test_count(self) -> None:
        c = ReferralRewardCalculator()
        c.calculate_reward("u1", 10.0)
        c.calculate_reward("u2", 15.0)
        assert c.reward_count == 2
        assert c.total_paid == 25.0


class TestCalculateTiered:
    """calculate_tiered testleri."""

    def test_default_tiers(self) -> None:
        c = ReferralRewardCalculator()
        r = c.calculate_tiered("u1", 25)
        assert r["reward_rate"] == 20.0

    def test_low_count(self) -> None:
        c = ReferralRewardCalculator()
        r = c.calculate_tiered("u1", 2)
        assert r["reward_rate"] == 10.0


class TestApplyCap:
    """apply_cap testleri."""

    def test_within_limits(self) -> None:
        c = ReferralRewardCalculator()
        r = c.apply_cap("u1", 50.0, 100.0, 1000.0, 30.0, 200.0)
        assert r["approved"] == 50.0
        assert r["capped"] is False

    def test_exceeds_daily(self) -> None:
        c = ReferralRewardCalculator()
        r = c.apply_cap("u1", 50.0, 100.0, 1000.0, 80.0, 200.0)
        assert r["approved"] == 20.0
        assert r["capped"] is True


class TestConvertCurrency:
    """convert_currency testleri."""

    def test_basic(self) -> None:
        c = ReferralRewardCalculator()
        r = c.convert_currency(100.0, "USD", "TRY", 30.0)
        assert r["converted"] is True
        assert r["converted_amount"] == 3000.0


class TestEstimateTax:
    """estimate_tax testleri."""

    def test_basic(self) -> None:
        c = ReferralRewardCalculator()
        r = c.estimate_tax(100.0, 0.2)
        assert r["estimated"] is True
        assert r["tax_amount"] == 20.0
        assert r["net_amount"] == 80.0


# ── AmbassadorManager Testleri ──


class TestRecruit:
    """recruit testleri."""

    def test_basic(self) -> None:
        m = AmbassadorManager()
        r = m.recruit("Ali", "ali@test.com", "referral")
        assert r["recruited"] is True
        assert r["tier"] == "bronze"

    def test_count(self) -> None:
        m = AmbassadorManager()
        m.recruit("A")
        m.recruit("B")
        assert m.ambassador_count == 2


class TestTrackPerformance:
    """track_performance testleri."""

    def test_basic(self) -> None:
        m = AmbassadorManager()
        a = m.recruit("Ali")
        r = m.track_performance(a["ambassador_id"], 20, 8, 500.0)
        assert r["tracked"] is True
        assert r["conversion_rate"] == 0.4


class TestUpdateTier:
    """update_tier testleri."""

    def test_diamond(self) -> None:
        m = AmbassadorManager()
        r = m.update_tier("a1", 55)
        assert r["tier"] == "diamond"

    def test_bronze(self) -> None:
        m = AmbassadorManager()
        r = m.update_tier("a1", 3)
        assert r["tier"] == "bronze"


class TestSendCommunication:
    """send_communication testleri."""

    def test_basic(self) -> None:
        m = AmbassadorManager()
        r = m.send_communication("a1", "milestone", "email")
        assert r["sent"] is True


class TestGiveRecognition:
    """give_recognition testleri."""

    def test_basic(self) -> None:
        m = AmbassadorManager()
        r = m.give_recognition("a1", "badge", "Top performer")
        assert r["given"] is True

    def test_count(self) -> None:
        m = AmbassadorManager()
        m.give_recognition("a1", "badge")
        m.give_recognition("a2", "shoutout")
        assert m.recognition_count == 2


# ── ReferralConversionTracker Testleri ──


class TestTrackConversion:
    """track_conversion testleri."""

    def test_basic(self) -> None:
        t = ReferralConversionTracker()
        r = t.track_conversion("r1", "u1", "u2", 100.0)
        assert r["tracked"] is True
        assert r["value"] == 100.0

    def test_count(self) -> None:
        t = ReferralConversionTracker()
        t.track_conversion("r1", "u1", "u2")
        t.track_conversion("r2", "u3", "u4")
        assert t.conversion_count == 2


class TestAttributeConversion:
    """attribute_conversion testleri."""

    def test_last_click(self) -> None:
        t = ReferralConversionTracker()
        r = t.attribute_conversion("c1", "last_click", ["email", "social", "direct"])
        assert r["attributed_to"] == "direct"

    def test_first_click(self) -> None:
        t = ReferralConversionTracker()
        r = t.attribute_conversion("c1", "first_click", ["email", "social"])
        assert r["attributed_to"] == "email"


class TestAnalyzeFunnel:
    """analyze_funnel testleri."""

    def test_basic(self) -> None:
        t = ReferralConversionTracker()
        r = t.analyze_funnel({"clicked": 100, "signed_up": 50, "converted": 20})
        assert r["analyzed"] is True
        assert "signed_up" in r["drop_offs"]

    def test_count(self) -> None:
        t = ReferralConversionTracker()
        t.analyze_funnel({"a": 10, "b": 5})
        assert t.funnel_count == 1


class TestMeasureTimeToConvert:
    """measure_time_to_convert testleri."""

    def test_fast(self) -> None:
        t = ReferralConversionTracker()
        r = t.measure_time_to_convert("r1", 12.0)
        assert r["speed"] == "fast"

    def test_slow(self) -> None:
        t = ReferralConversionTracker()
        r = t.measure_time_to_convert("r1", 100.0)
        assert r["speed"] == "slow"


class TestScoreQuality:
    """score_quality testleri."""

    def test_grade_a(self) -> None:
        t = ReferralConversionTracker()
        r = t.score_quality("r1", 200.0, 90, 0.9)
        assert r["grade"] == "A"

    def test_grade_d(self) -> None:
        t = ReferralConversionTracker()
        r = t.score_quality("r1", 5.0, 2, 0.1)
        assert r["grade"] == "D"


# ── IncentiveOptimizer Testleri ──


class TestTestIncentive:
    """test_incentive testleri."""

    def test_basic(self) -> None:
        o = IncentiveOptimizer()
        r = o.test_incentive("Reward Amount", 10.0, 20.0, 200)
        assert r["tested"] is True
        assert r["winner"] in ("a", "b")

    def test_count(self) -> None:
        o = IncentiveOptimizer()
        o.test_incentive("T1", 5.0, 10.0)
        o.test_incentive("T2", 15.0, 25.0)
        assert o.test_count == 2


class TestFindOptimalReward:
    """find_optimal_reward testleri."""

    def test_with_data(self) -> None:
        o = IncentiveOptimizer()
        r = o.find_optimal_reward(5.0, 50.0, [0.02, 0.05, 0.08, 0.06])
        assert r["found"] is True
        assert r["optimal_reward"] > 5.0

    def test_no_data(self) -> None:
        o = IncentiveOptimizer()
        r = o.find_optimal_reward(10.0, 30.0)
        assert r["optimal_reward"] == 20.0


class TestOptimizeTiming:
    """optimize_timing testleri."""

    def test_basic(self) -> None:
        o = IncentiveOptimizer()
        r = o.optimize_timing("signup", [0, 1, 24])
        assert r["optimized"] is True


class TestTargetSegment:
    """target_segment testleri."""

    def test_basic(self) -> None:
        o = IncentiveOptimizer()
        r = o.target_segment("power_users", 15.0, 0.1)
        assert r["targeted"] is True
        assert r["cost_per_acquisition"] == 150.0


class TestMaximizeRoi:
    """maximize_roi testleri."""

    def test_basic(self) -> None:
        o = IncentiveOptimizer()
        r = o.maximize_roi(1000.0, 10.0, 100.0)
        assert r["maximized"] is True
        assert r["max_referrals"] == 100
        assert r["roi_pct"] == 900.0


# ── ViralCoefficientCalculator Testleri ──


class TestCalculateKFactor:
    """calculate_k_factor testleri."""

    def test_viral(self) -> None:
        v = ViralCoefficientCalculator()
        r = v.calculate_k_factor(5.0, 0.4)
        assert r["is_viral"] is True
        assert r["phase"] == "viral"

    def test_seed(self) -> None:
        v = ViralCoefficientCalculator()
        r = v.calculate_k_factor(3.0, 0.2)
        assert r["is_viral"] is False
        assert r["phase"] == "seed"

    def test_count(self) -> None:
        v = ViralCoefficientCalculator()
        v.calculate_k_factor(1.0, 0.5)
        v.calculate_k_factor(2.0, 0.3)
        assert v.calculation_count == 2


class TestModelGrowth:
    """model_growth testleri."""

    def test_basic(self) -> None:
        v = ViralCoefficientCalculator()
        r = v.model_growth(100, 0.5, 4)
        assert r["modeled"] is True
        assert r["final_users"] > 100
        assert len(r["timeline"]) == 5


class TestMeasureCycleTime:
    """measure_cycle_time testleri."""

    def test_fast(self) -> None:
        v = ViralCoefficientCalculator()
        r = v.measure_cycle_time(6.0, 12.0)
        assert r["speed"] == "fast"

    def test_slow(self) -> None:
        v = ViralCoefficientCalculator()
        r = v.measure_cycle_time(48.0, 48.0)
        assert r["speed"] == "slow"


class TestProjectGrowth:
    """project_growth testleri."""

    def test_reachable(self) -> None:
        v = ViralCoefficientCalculator()
        r = v.project_growth(100, 1.5, 7, 10000)
        assert r["reachable"] is True
        assert r["days_needed"] > 0

    def test_unreachable(self) -> None:
        v = ViralCoefficientCalculator()
        r = v.project_growth(0, 0.0, 7, 10000)
        assert r["reachable"] is False

    def test_count(self) -> None:
        v = ViralCoefficientCalculator()
        v.project_growth(100, 0.5, 7, 500)
        assert v.projection_count == 1


class TestBenchmark:
    """benchmark testleri."""

    def test_exceptional(self) -> None:
        v = ViralCoefficientCalculator()
        r = v.benchmark(1.0, "saas")
        assert r["rating"] == "exceptional"

    def test_below_average(self) -> None:
        v = ViralCoefficientCalculator()
        r = v.benchmark(0.1, "saas")
        assert r["rating"] == "below_average"


# ── ReferralFraudDetector Testleri ──


class TestDetectSelfReferral:
    """detect_self_referral testleri."""

    def test_self(self) -> None:
        d = ReferralFraudDetector()
        r = d.detect_self_referral("u1", "u1")
        assert r["is_self_referral"] is True
        assert r["risk"] == "high"

    def test_same_ip(self) -> None:
        d = ReferralFraudDetector()
        r = d.detect_self_referral("u1", "u2", "1.2.3.4", "1.2.3.4")
        assert r["same_ip"] is True
        assert r["risk"] == "high"

    def test_clean(self) -> None:
        d = ReferralFraudDetector()
        r = d.detect_self_referral("u1", "u2", "1.1.1.1", "2.2.2.2")
        assert r["risk"] == "clean"


class TestDetectFakeAccount:
    """detect_fake_account testleri."""

    def test_high_risk(self) -> None:
        d = ReferralFraudDetector()
        r = d.detect_fake_account("a1", 0, False, False)
        assert r["risk"] == "high"

    def test_clean(self) -> None:
        d = ReferralFraudDetector()
        r = d.detect_fake_account("a1", 720, True, True)
        assert r["risk"] == "clean"


class TestAnalyzePattern:
    """analyze_pattern testleri."""

    def test_suspicious(self) -> None:
        d = ReferralFraudDetector()
        r = d.analyze_pattern("u1", [0.01, 0.02, 0.03])
        assert r["suspicious"] is True

    def test_normal(self) -> None:
        d = ReferralFraudDetector()
        r = d.analyze_pattern("u1", [2.0, 3.0, 5.0])
        assert r["suspicious"] is False


class TestCheckVelocity:
    """check_velocity testleri."""

    def test_violation(self) -> None:
        d = ReferralFraudDetector()
        r = d.check_velocity("u1", 10, 30, 5, 20)
        assert r["violation"] is True

    def test_within_limits(self) -> None:
        d = ReferralFraudDetector()
        r = d.check_velocity("u1", 2, 10, 5, 20)
        assert r["violation"] is False

    def test_count(self) -> None:
        d = ReferralFraudDetector()
        d.detect_self_referral("u1", "u1")
        d.check_velocity("u1", 10, 30)
        assert d.check_count == 2


class TestBlacklist:
    """blacklist testleri."""

    def test_basic(self) -> None:
        d = ReferralFraudDetector()
        r = d.blacklist("u1", "self-referral")
        assert r["blacklisted"] is True
        assert r["blacklist_size"] == 1

    def test_multiple(self) -> None:
        d = ReferralFraudDetector()
        d.blacklist("u1")
        d.blacklist("u2")
        r = d.blacklist("u3")
        assert r["blacklist_size"] == 3


# ── ReferralOrchestrator Testleri ──


class TestCreateAndShare:
    """create_and_share testleri."""

    def test_basic(self) -> None:
        o = ReferralOrchestrator()
        r = o.create_and_share("user1", "summer_promo")
        assert r["pipeline_complete"] is True
        assert "link_url" in r

    def test_count(self) -> None:
        o = ReferralOrchestrator()
        o.create_and_share("u1")
        o.create_and_share("u2")
        assert o.pipeline_count == 2


class TestProcessReferral:
    """process_referral testleri."""

    def test_valid(self) -> None:
        o = ReferralOrchestrator()
        r = o.process_referral("u1", "u2", 50.0)
        assert r["processed"] is True
        assert r["fraud_detected"] is False
        assert r["reward_amount"] == 10.0

    def test_self_referral(self) -> None:
        o = ReferralOrchestrator()
        r = o.process_referral("u1", "u1")
        assert r["processed"] is False
        assert r["fraud_detected"] is True


class TestReferralGetAnalytics:
    """get_analytics testleri."""

    def test_basic(self) -> None:
        o = ReferralOrchestrator()
        a = o.get_analytics()
        assert "pipelines_run" in a
        assert "fraud_checks" in a

    def test_after_operations(self) -> None:
        o = ReferralOrchestrator()
        o.create_and_share("u1")
        o.process_referral("u1", "u2", 100.0)
        a = o.get_analytics()
        assert a["pipelines_run"] == 2
        assert a["programs_created"] == 1
        assert a["links_generated"] == 1
        assert a["rewards_calculated"] == 1
        assert a["fraud_checks"] == 1
