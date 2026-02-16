"""ATLAS Autonomous Negotiation Engine testleri."""

import pytest

from app.models.negotiation_models import (
    ConcessionRecord,
    ConcessionType,
    DealOutcome,
    DealScore,
    NegotiationPhase,
    NegotiationRecord,
    NegotiationStrategy,
    OfferRecord,
    OfferStatus,
    PartyRole,
)


# ==================== Model Testleri ====================


class TestNegotiationPhase:
    """NegotiationPhase enum testleri."""

    def test_values(self):
        assert NegotiationPhase.PLANNING == "planning"
        assert NegotiationPhase.OPENING == "opening"
        assert NegotiationPhase.BARGAINING == "bargaining"
        assert NegotiationPhase.CLOSING == "closing"
        assert NegotiationPhase.SETTLED == "settled"
        assert NegotiationPhase.FAILED == "failed"

    def test_member_count(self):
        assert len(NegotiationPhase) == 6


class TestOfferStatus:
    """OfferStatus enum testleri."""

    def test_values(self):
        assert OfferStatus.DRAFT == "draft"
        assert OfferStatus.SENT == "sent"
        assert OfferStatus.RECEIVED == "received"
        assert OfferStatus.ACCEPTED == "accepted"
        assert OfferStatus.REJECTED == "rejected"
        assert OfferStatus.COUNTERED == "countered"

    def test_member_count(self):
        assert len(OfferStatus) == 6


class TestConcessionType:
    """ConcessionType enum testleri."""

    def test_values(self):
        assert ConcessionType.PRICE == "price"
        assert ConcessionType.TERMS == "terms"
        assert ConcessionType.TIMELINE == "timeline"
        assert ConcessionType.SCOPE == "scope"
        assert ConcessionType.WARRANTY == "warranty"
        assert ConcessionType.VOLUME == "volume"

    def test_member_count(self):
        assert len(ConcessionType) == 6


class TestNegotiationStrategy:
    """NegotiationStrategy enum testleri."""

    def test_values(self):
        assert NegotiationStrategy.COMPETITIVE == "competitive"
        assert NegotiationStrategy.COLLABORATIVE == "collaborative"
        assert NegotiationStrategy.COMPROMISING == "compromising"
        assert NegotiationStrategy.ACCOMMODATING == "accommodating"
        assert NegotiationStrategy.AVOIDING == "avoiding"

    def test_member_count(self):
        assert len(NegotiationStrategy) == 5


class TestDealOutcome:
    """DealOutcome enum testleri."""

    def test_values(self):
        assert DealOutcome.WON == "won"
        assert DealOutcome.LOST == "lost"
        assert DealOutcome.DRAW == "draw"
        assert DealOutcome.PENDING == "pending"
        assert DealOutcome.CANCELLED == "cancelled"

    def test_member_count(self):
        assert len(DealOutcome) == 5


class TestPartyRole:
    """PartyRole enum testleri."""

    def test_values(self):
        assert PartyRole.BUYER == "buyer"
        assert PartyRole.SELLER == "seller"
        assert PartyRole.MEDIATOR == "mediator"
        assert PartyRole.PARTNER == "partner"

    def test_member_count(self):
        assert len(PartyRole) == 4


class TestNegotiationRecord:
    """NegotiationRecord model testleri."""

    def test_defaults(self):
        r = NegotiationRecord()
        assert r.negotiation_id
        assert r.parties == []
        assert r.phase == NegotiationPhase.PLANNING
        assert r.strategy == NegotiationStrategy.COLLABORATIVE
        assert r.outcome == DealOutcome.PENDING

    def test_custom(self):
        r = NegotiationRecord(
            parties=["A", "B"],
            phase=NegotiationPhase.BARGAINING,
            strategy=NegotiationStrategy.COMPETITIVE,
        )
        assert r.parties == ["A", "B"]
        assert r.phase == NegotiationPhase.BARGAINING

    def test_unique_ids(self):
        r1 = NegotiationRecord()
        r2 = NegotiationRecord()
        assert r1.negotiation_id != r2.negotiation_id


class TestOfferRecord:
    """OfferRecord model testleri."""

    def test_defaults(self):
        r = OfferRecord()
        assert r.offer_id
        assert r.amount == 0.0
        assert r.status == OfferStatus.DRAFT

    def test_custom(self):
        r = OfferRecord(
            amount=5000.0,
            status=OfferStatus.SENT,
            negotiation_id="neg_1",
        )
        assert r.amount == 5000.0
        assert r.negotiation_id == "neg_1"


class TestConcessionRecord:
    """ConcessionRecord model testleri."""

    def test_defaults(self):
        r = ConcessionRecord()
        assert r.concession_id
        assert r.concession_type == ConcessionType.PRICE
        assert r.original_value == 0.0

    def test_custom(self):
        r = ConcessionRecord(
            concession_type=ConcessionType.TERMS,
            original_value=100.0,
            conceded_value=90.0,
            party="vendor",
        )
        assert r.concession_type == ConcessionType.TERMS
        assert r.party == "vendor"


class TestDealScore:
    """DealScore model testleri."""

    def test_defaults(self):
        r = DealScore()
        assert r.score_id
        assert r.overall_score == 0.0
        assert r.recommendation == "evaluate"

    def test_custom(self):
        r = DealScore(
            overall_score=85.0,
            risk_score=20.0,
            recommendation="accept",
        )
        assert r.overall_score == 85.0


# ==================== Strategy Planner Testleri ====================


class TestStrategyPlannerInit:
    """NegotiationStrategyPlanner init testleri."""

    def test_default_init(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        assert sp.strategy_count == 0
        assert sp.goal_count == 0

    def test_custom_strategy(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner(default_strategy="competitive")
        assert sp._default_strategy == "competitive"


class TestStrategyPlannerSelect:
    """Strategy selection testleri."""

    def test_select_collaborative(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        result = sp.select_strategy(relationship="long_term")
        assert result["strategy"] == "collaborative"
        assert result["created"] is True
        assert len(result["tactics"]) > 0

    def test_select_competitive(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        result = sp.select_strategy(power_balance="strong")
        assert result["strategy"] == "competitive"

    def test_select_compromising(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        result = sp.select_strategy(importance="low")
        assert result["strategy"] == "compromising"

    def test_select_default(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        result = sp.select_strategy()
        assert result["strategy"] == "collaborative"


class TestStrategyPlannerBATNA:
    """BATNA testleri."""

    def test_calculate_batna(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        alts = [
            {"name": "alt_1", "value": 100},
            {"name": "alt_2", "value": 150},
        ]
        result = sp.calculate_batna("neg_1", alts)
        assert result["batna_value"] == 150
        assert result["best_alternative"] == "alt_2"
        assert result["calculated"] is True

    def test_batna_no_alternatives(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        result = sp.calculate_batna("neg_1", [], current_best=80)
        assert result["batna_value"] == 80
        assert result["best_alternative"] == "no_alternative"

    def test_get_batna(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        sp.calculate_batna("neg_1", [{"name": "a", "value": 50}])
        assert sp.get_batna("neg_1") is not None
        assert sp.get_batna("unknown") is None


class TestStrategyPlannerGoals:
    """Goal setting testleri."""

    def test_set_goals(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        result = sp.set_goals("neg_1", target=1000, minimum=800)
        assert result["target"] == 1000
        assert result["minimum"] == 800
        assert result["optimistic"] == 1200.0
        assert result["set"] is True

    def test_set_goals_custom_optimistic(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        result = sp.set_goals("neg_1", target=1000, minimum=800, optimistic=1500)
        assert result["optimistic"] == 1500

    def test_assess_risk(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        result = sp.assess_risk("neg_1", factors={"power_balance": "weak", "time_pressure": True})
        assert result["risk_score"] > 0
        assert result["risk_level"] in ("low", "medium", "high")
        assert "weak_position" in result["risks"]

    def test_assess_risk_no_batna(self):
        from app.core.negotiation.negotiation_strategy_planner import (
            NegotiationStrategyPlanner,
        )
        sp = NegotiationStrategyPlanner()
        result = sp.assess_risk("neg_1")
        assert "no_batna" in result["risks"]


# ==================== Offer Generator Testleri ====================


class TestOfferGeneratorInit:
    """OfferGenerator init testleri."""

    def test_default_init(self):
        from app.core.negotiation.offer_generator import OfferGenerator
        og = OfferGenerator()
        assert og.offer_count == 0
        assert og.bundle_count == 0


class TestOfferGeneratorGenerate:
    """Offer generation testleri."""

    def test_generate_initial_offer(self):
        from app.core.negotiation.offer_generator import OfferGenerator
        og = OfferGenerator()
        result = og.generate_initial_offer(target_value=1000)
        assert result["amount"] > 1000
        assert result["generated"] is True
        assert result["currency"] == "TRY"

    def test_competitive_offer(self):
        from app.core.negotiation.offer_generator import OfferGenerator
        og = OfferGenerator()
        result = og.generate_initial_offer(target_value=1000, strategy="competitive")
        assert result["amount"] > 1150

    def test_accommodating_offer(self):
        from app.core.negotiation.offer_generator import OfferGenerator
        og = OfferGenerator()
        result = og.generate_initial_offer(target_value=1000, strategy="accommodating")
        assert result["amount"] < 1000

    def test_create_bundle(self):
        from app.core.negotiation.offer_generator import OfferGenerator
        og = OfferGenerator()
        items = [
            {"name": "A", "value": 100},
            {"name": "B", "value": 200},
        ]
        result = og.create_bundle(items, discount_rate=0.1)
        assert result["total_value"] == 300.0
        assert result["discount"] == 30.0
        assert result["bundle_price"] == 270.0
        assert result["item_count"] == 2

    def test_structure_terms(self):
        from app.core.negotiation.offer_generator import OfferGenerator
        og = OfferGenerator()
        og.generate_initial_offer(target_value=1000)
        result = og.structure_terms("offer_1", payment_terms="net_60", warranty="1_year")
        assert result["payment_terms"] == "net_60"
        assert result["structured"] is True

    def test_format_presentation(self):
        from app.core.negotiation.offer_generator import OfferGenerator
        og = OfferGenerator()
        og.generate_initial_offer(target_value=1000)
        result = og.format_presentation("offer_1", format_type="formal")
        assert result["formatted"] is True
        assert "executive_summary" in result["sections"]

    def test_format_not_found(self):
        from app.core.negotiation.offer_generator import OfferGenerator
        og = OfferGenerator()
        result = og.format_presentation("unknown")
        assert result["found"] is False

    def test_get_offer(self):
        from app.core.negotiation.offer_generator import OfferGenerator
        og = OfferGenerator()
        og.generate_initial_offer(target_value=500)
        assert og.get_offer("offer_1") is not None
        assert og.get_offer("unknown") is None


# ==================== Counter Offer Analyzer Testleri ====================


class TestCounterOfferAnalyzerInit:
    """CounterOfferAnalyzer init testleri."""

    def test_default_init(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        assert coa.analysis_count == 0
        assert coa.gap_count == 0


class TestCounterOfferAnalyzerParse:
    """Offer parsing testleri."""

    def test_parse_offer(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        result = coa.parse_offer(amount=5000, party="vendor")
        assert result["amount"] == 5000
        assert result["parsed"] is True

    def test_assess_value_excellent(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        result = coa.assess_value(
            offer_amount=1000, our_target=900, our_minimum=800
        )
        assert result["quality"] == "excellent"
        assert result["acceptable"] is True

    def test_assess_value_poor(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        result = coa.assess_value(
            offer_amount=500, our_target=1000, our_minimum=800
        )
        assert result["quality"] == "poor"
        assert result["acceptable"] is False

    def test_assess_value_market(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        result = coa.assess_value(
            offer_amount=1000, our_target=1000, our_minimum=800, market_rate=900
        )
        assert result["market_compare"] == "above_market"


class TestCounterOfferAnalyzerGap:
    """Gap analysis testleri."""

    def test_analyze_gap_close(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        result = coa.analyze_gap(our_position=1000, their_position=950)
        assert result["gap"] == 50
        assert result["closable"] is True
        assert result["difficulty"] == "easy"

    def test_analyze_gap_far(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        result = coa.analyze_gap(our_position=1000, their_position=500)
        assert result["closable"] is False
        assert result["difficulty"] == "very_hard"

    def test_detect_intent_increasing(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        history = [
            {"amount": 800},
            {"amount": 850},
            {"amount": 900},
        ]
        result = coa.detect_intent(history)
        assert result["intent"] == "increasing"
        assert result["detected"] is True

    def test_detect_intent_empty(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        result = coa.detect_intent([])
        assert result["intent"] == "unknown"
        assert result["detected"] is False

    def test_recommend_accept(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        result = coa.recommend_response(
            offer_amount=1100, our_target=1000, our_minimum=800
        )
        assert result["action"] == "accept"

    def test_recommend_counter(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        result = coa.recommend_response(
            offer_amount=850, our_target=1000, our_minimum=800
        )
        assert result["action"] == "counter"

    def test_recommend_reject(self):
        from app.core.negotiation.counter_offer_analyzer import CounterOfferAnalyzer
        coa = CounterOfferAnalyzer()
        result = coa.recommend_response(
            offer_amount=500, our_target=1000, our_minimum=800, gap_percent=50
        )
        assert result["action"] == "reject"


# ==================== Concession Tracker Testleri ====================


class TestConcessionTrackerInit:
    """ConcessionTracker init testleri."""

    def test_default_init(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        assert ct.concession_count == 0
        assert ct.red_line_count == 0


class TestConcessionTrackerRecord:
    """Concession recording testleri."""

    def test_record_concession(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        result = ct.record_concession(
            party="vendor", original=1000, conceded=950
        )
        assert result["magnitude"] == 50
        assert result["percent"] == 5.0
        assert result["recorded"] is True

    def test_multiple_concessions(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        ct.record_concession(party="A", original=100, conceded=90)
        ct.record_concession(party="B", original=200, conceded=180)
        assert ct.concession_count == 2


class TestConcessionTrackerAnalysis:
    """Pattern analysis testleri."""

    def test_analyze_pattern_empty(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        result = ct.analyze_pattern()
        assert result["pattern"] == "none"
        assert result["analyzed"] is False

    def test_analyze_pattern_with_data(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        ct.record_concession(party="A", original=100, conceded=90)
        ct.record_concession(party="A", original=90, conceded=87)
        result = ct.analyze_pattern(party="A")
        assert result["analyzed"] is True
        assert result["count"] == 2

    def test_remaining_room(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        result = ct.get_remaining_room(current_position=900, minimum=800)
        assert result["remaining"] == 100
        assert result["urgency"] in ("critical", "tight", "moderate", "comfortable")

    def test_remaining_room_tight(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        result = ct.get_remaining_room(current_position=805, minimum=800)
        assert result["urgency"] == "critical"

    def test_track_reciprocity_empty(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        result = ct.track_reciprocity()
        assert result["balanced"] is True

    def test_track_reciprocity_balanced(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        ct.record_concession(party="A", original=100, conceded=90)
        ct.record_concession(party="B", original=200, conceded=188)
        result = ct.track_reciprocity()
        assert "A" in result["parties"]
        assert "B" in result["parties"]


class TestConcessionTrackerRedLines:
    """Red line testleri."""

    def test_set_red_line(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        result = ct.set_red_line("price", 500.0)
        assert result["set"] is True
        assert ct.red_line_count == 1

    def test_check_red_line_ok(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        ct.set_red_line("price", 500.0)
        result = ct.check_red_line("price", 600.0)
        assert result["violated"] is False
        assert result["has_red_line"] is True

    def test_check_red_line_violated(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        ct.set_red_line("price", 500.0)
        result = ct.check_red_line("price", 400.0)
        assert result["violated"] is True

    def test_check_red_line_missing(self):
        from app.core.negotiation.concession_tracker import ConcessionTracker
        ct = ConcessionTracker()
        result = ct.check_red_line("price", 600.0)
        assert result["has_red_line"] is False


# ==================== Win-Win Optimizer Testleri ====================


class TestWinWinOptimizerInit:
    """WinWinOptimizer init testleri."""

    def test_default_init(self):
        from app.core.negotiation.win_win_optimizer import WinWinOptimizer
        ww = WinWinOptimizer()
        assert ww.solution_count == 0
        assert ww.tradeoff_count == 0


class TestWinWinOptimizerValue:
    """Value creation testleri."""

    def test_create_value(self):
        from app.core.negotiation.win_win_optimizer import WinWinOptimizer
        ww = WinWinOptimizer()
        result = ww.create_value(
            our_strengths=["tech", "speed"],
            their_needs=["tech", "quality"],
        )
        assert result["matches"] == ["tech"]
        assert result["synergies"] >= 1
        assert result["created"] is True

    def test_create_value_no_match(self):
        from app.core.negotiation.win_win_optimizer import WinWinOptimizer
        ww = WinWinOptimizer()
        result = ww.create_value(
            our_strengths=["a"],
            their_needs=["b"],
        )
        assert result["matches"] == []
        assert result["potential"] == "low"


class TestWinWinOptimizerAlign:
    """Interest alignment testleri."""

    def test_align_interests(self):
        from app.core.negotiation.win_win_optimizer import WinWinOptimizer
        ww = WinWinOptimizer()
        result = ww.align_interests(
            party_a="us", interests_a=["growth", "quality", "speed"],
            party_b="them", interests_b=["quality", "cost", "speed"],
        )
        assert "quality" in result["common"]
        assert "speed" in result["common"]
        assert result["alignment_percent"] > 0

    def test_analyze_tradeoff(self):
        from app.core.negotiation.win_win_optimizer import WinWinOptimizer
        ww = WinWinOptimizer()
        result = ww.analyze_tradeoff(
            dimension_a="price", value_a_gives=10, value_a_gets=20,
            dimension_b="timeline", value_b_gives=15, value_b_gets=25,
        )
        assert result["net_a"] == 10
        assert result["net_b"] == 10
        assert result["win_win"] is True

    def test_tradeoff_not_win_win(self):
        from app.core.negotiation.win_win_optimizer import WinWinOptimizer
        ww = WinWinOptimizer()
        result = ww.analyze_tradeoff(
            dimension_a="price", value_a_gives=30, value_a_gets=10,
            dimension_b="scope", value_b_gives=5, value_b_gets=20,
        )
        assert result["win_win"] is False


class TestWinWinOptimizerPareto:
    """Pareto optimization testleri."""

    def test_find_pareto_optimal(self):
        from app.core.negotiation.win_win_optimizer import WinWinOptimizer
        ww = WinWinOptimizer()
        options = [
            {"value_a": 10, "value_b": 20},
            {"value_a": 15, "value_b": 15},
            {"value_a": 5, "value_b": 10},
        ]
        result = ww.find_pareto_optimal(options)
        assert result["count"] >= 1
        assert result["count"] <= 3

    def test_pareto_empty(self):
        from app.core.negotiation.win_win_optimizer import WinWinOptimizer
        ww = WinWinOptimizer()
        result = ww.find_pareto_optimal([])
        assert result["count"] == 0

    def test_generate_creative_solution(self):
        from app.core.negotiation.win_win_optimizer import WinWinOptimizer
        ww = WinWinOptimizer()
        result = ww.generate_creative_solution(
            deadlock_issue="pricing",
            party_a_priority="quality",
            party_b_priority="cost",
        )
        assert result["count"] >= 3
        assert result["generated"] is True


# ==================== Deal Scorer Testleri ====================


class TestDealScorerInit:
    """DealScorer init testleri."""

    def test_default_init(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        assert ds.score_count == 0
        assert ds.recommendation_count == 0


class TestDealScorerEvaluate:
    """Deal evaluation testleri."""

    def test_evaluate_deal(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.evaluate_deal(
            deal_value=1000, target_value=1000
        )
        assert result["overall"] > 0
        assert result["value_score"] > 0
        assert ds.score_count == 1

    def test_evaluate_with_risks(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.evaluate_deal(
            deal_value=900, target_value=1000,
            risk_factors=["market_volatility", "credit_risk"]
        )
        assert result["risk_score"] < 80

    def test_score_risk(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.score_risk(
            factors=["market", "credit"],
            severity={"market": 0.8, "credit": 0.5}
        )
        assert result["total_risk"] > 0
        assert result["level"] in ("low", "medium", "high")

    def test_score_risk_empty(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.score_risk(factors=[])
        assert result["total_risk"] == 0
        assert result["level"] == "low"


class TestDealScorerAssess:
    """Value assessment testleri."""

    def test_assess_value_above_market(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.assess_value(deal_value=1100, market_value=1000)
        assert result["vs_market_percent"] == 10.0
        assert result["rating"] == "excellent"

    def test_assess_value_below_market(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.assess_value(deal_value=800, market_value=1000)
        assert result["rating"] == "poor"

    def test_assess_value_with_cost(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.assess_value(deal_value=1000, market_value=900, cost=600)
        assert result["margin"] == 40.0

    def test_compare_alternatives(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        current = {"score": 80, "value": 1000}
        alts = [
            {"name": "alt1", "score": 70, "value": 900},
            {"name": "alt2", "score": 90, "value": 1100},
        ]
        result = ds.compare_alternatives(current, alts)
        assert result["current_is_best"] is False
        assert result["best_alternative"] == "alt2"


class TestDealScorerRecommend:
    """Recommendation testleri."""

    def test_recommend_strong_accept(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.recommend(overall_score=85)
        assert result["recommendation"] == "strong_accept"

    def test_recommend_accept(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.recommend(overall_score=65)
        assert result["recommendation"] == "accept"

    def test_recommend_reject(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.recommend(overall_score=40)
        assert result["recommendation"] == "reject"

    def test_recommend_below_batna(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.recommend(
            overall_score=70, batna_value=1000, deal_value=800
        )
        assert result["recommendation"] == "reject"
        assert "below_batna" in result["reasons"]

    def test_set_criteria_weight(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.set_criteria_weight("value", 0.5)
        assert result["set"] is True
        assert result["new_weight"] == 0.5

    def test_set_unknown_criterion(self):
        from app.core.negotiation.deal_scorer import DealScorer
        ds = DealScorer()
        result = ds.set_criteria_weight("unknown", 0.5)
        assert result["set"] is False


# ==================== Negotiation Memory Testleri ====================


class TestNegotiationMemoryInit:
    """NegotiationMemory init testleri."""

    def test_default_init(self):
        from app.core.negotiation.negotiation_memory import NegotiationMemory
        nm = NegotiationMemory()
        assert nm.negotiation_count == 0
        assert nm.profile_count == 0
        assert nm.practice_count == 0


class TestNegotiationMemoryStore:
    """Storage testleri."""

    def test_store_negotiation(self):
        from app.core.negotiation.negotiation_memory import NegotiationMemory
        nm = NegotiationMemory()
        result = nm.store_negotiation(
            negotiation_id="neg_1",
            parties=["A", "B"],
            outcome="won",
        )
        assert result["stored"] is True
        assert nm.negotiation_count == 1

    def test_get_negotiation(self):
        from app.core.negotiation.negotiation_memory import NegotiationMemory
        nm = NegotiationMemory()
        nm.store_negotiation("neg_1", ["A", "B"])
        assert nm.get_negotiation("neg_1") is not None
        assert nm.get_negotiation("unknown") is None


class TestNegotiationMemoryProfiles:
    """Profile testleri."""

    def test_create_profile(self):
        from app.core.negotiation.negotiation_memory import NegotiationMemory
        nm = NegotiationMemory()
        result = nm.create_party_profile("Vendor A", style="competitive")
        assert result["created"] is True
        assert nm.profile_count == 1

    def test_update_profile(self):
        from app.core.negotiation.negotiation_memory import NegotiationMemory
        nm = NegotiationMemory()
        nm.create_party_profile("Vendor A")
        result = nm.update_party_profile("Vendor A", concession_avg=5.0)
        assert result["updated"] is True
        assert result["negotiations"] == 1

    def test_update_profile_not_found(self):
        from app.core.negotiation.negotiation_memory import NegotiationMemory
        nm = NegotiationMemory()
        result = nm.update_party_profile("Unknown")
        assert result["updated"] is False

    def test_get_party_profile(self):
        from app.core.negotiation.negotiation_memory import NegotiationMemory
        nm = NegotiationMemory()
        nm.create_party_profile("V", style="collaborative")
        profile = nm.get_party_profile("V")
        assert profile is not None
        assert profile["style"] == "collaborative"


class TestNegotiationMemoryOutcomes:
    """Outcome tracking testleri."""

    def test_get_past_outcomes(self):
        from app.core.negotiation.negotiation_memory import NegotiationMemory
        nm = NegotiationMemory()
        nm.store_negotiation("n1", ["A"], outcome="won", strategy="collaborative")
        nm.store_negotiation("n2", ["A"], outcome="lost", strategy="competitive")
        result = nm.get_past_outcomes()
        assert result["total"] == 2
        assert result["won"] == 1

    def test_filter_by_party(self):
        from app.core.negotiation.negotiation_memory import NegotiationMemory
        nm = NegotiationMemory()
        nm.store_negotiation("n1", ["A", "B"], outcome="won")
        nm.store_negotiation("n2", ["C", "D"], outcome="lost")
        result = nm.get_past_outcomes(party="A")
        assert result["total"] == 1

    def test_learn_pattern(self):
        from app.core.negotiation.negotiation_memory import NegotiationMemory
        nm = NegotiationMemory()
        result = nm.learn_pattern("anchoring", "High anchor leads to better outcomes", success_rate=75.0)
        assert result["learned"] is True

    def test_add_best_practice(self):
        from app.core.negotiation.negotiation_memory import NegotiationMemory
        nm = NegotiationMemory()
        result = nm.add_best_practice("Always prepare BATNA", "Calculate alternatives before negotiation")
        assert result["added"] is True
        assert nm.practice_count == 1


# ==================== Communication Manager Testleri ====================


class TestCommunicationManagerInit:
    """NegotiationCommunicationManager init testleri."""

    def test_default_init(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        assert cm.message_count == 0
        assert cm.response_count == 0


class TestCommunicationManagerCraft:
    """Message crafting testleri."""

    def test_craft_professional(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        result = cm.craft_message("We propose a partnership", tone="professional")
        assert result["crafted"] is True
        assert result["tone"] == "professional"

    def test_craft_firm(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        result = cm.craft_message("our position is final", tone="firm")
        assert "clearly state" in result["content"]

    def test_adjust_tone(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        cm.craft_message("test", tone="firm")
        result = cm.adjust_tone("msg_1", "friendly")
        assert result["adjusted"] is True
        assert result["new_tone"] == "friendly"

    def test_adjust_tone_not_found(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        result = cm.adjust_tone("unknown", "friendly")
        assert result["adjusted"] is False


class TestCommunicationManagerTiming:
    """Timing optimization testleri."""

    def test_optimize_timing(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        result = cm.optimize_timing("vendor", message_type="offer")
        assert result["optimized"] is True
        assert result["timing"]["best_day"] == "Tuesday"

    def test_timing_counter(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        result = cm.optimize_timing("vendor", message_type="counter")
        assert result["delay_strategy"] == "wait_24h"

    def test_select_channel_formal(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        result = cm.select_channel("vendor", formality="formal")
        assert result["recommended"] == "email"

    def test_select_channel_preferred(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        cm.set_channel_preference("vendor", "video_call")
        result = cm.select_channel("vendor")
        assert result["recommended"] == "video_call"


class TestCommunicationManagerResponse:
    """Response handling testleri."""

    def test_handle_positive(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        result = cm.handle_response("Sounds good", from_party="vendor", sentiment="positive")
        assert result["suggested_action"] == "proceed"
        assert result["handled"] is True

    def test_handle_negative(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        result = cm.handle_response("Not acceptable", from_party="vendor", sentiment="negative")
        assert result["suggested_action"] == "reassess_approach"
        assert result["priority"] == "high"

    def test_handle_urgent(self):
        from app.core.negotiation.communication_manager import NegotiationCommunicationManager
        cm = NegotiationCommunicationManager()
        result = cm.handle_response("Urgent!", from_party="vendor", sentiment="urgent")
        assert result["priority"] == "critical"


# ==================== Orchestrator Testleri ====================


class TestOrchestratorInit:
    """NegotiationOrchestrator init testleri."""

    def test_default_init(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator()
        assert no.active_count == 0
        assert no.completed_count == 0

    def test_custom_init(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator(currency="USD", min_acceptable_score=70.0)
        assert no._currency == "USD"


class TestOrchestratorNegotiation:
    """Negotiation lifecycle testleri."""

    def test_start_negotiation(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator()
        result = no.start_negotiation(
            parties=["us", "vendor"],
            target_value=10000,
            minimum_value=8000,
        )
        assert result["started"] is True
        assert result["initial_offer"] > 0
        assert result["phase"] == "opening"
        assert no.active_count == 1

    def test_process_counter_offer(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator()
        no.start_negotiation(
            parties=["us", "vendor"],
            target_value=10000,
            minimum_value=8000,
        )
        result = no.process_counter_offer(
            negotiation_id="neg_1",
            counter_amount=9000,
            counter_party="vendor",
        )
        assert result["counter_amount"] == 9000
        assert result["recommended_action"] in ("accept", "counter", "reject")
        assert result["round"] == 1

    def test_process_counter_not_found(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator()
        result = no.process_counter_offer("unknown", 5000)
        assert result["found"] is False

    def test_close_deal(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator()
        no.start_negotiation(
            parties=["us", "vendor"],
            target_value=10000,
            minimum_value=8000,
        )
        result = no.close_deal("neg_1", final_value=9500, outcome="won")
        assert result["closed"] is True
        assert result["final_value"] == 9500
        assert no.active_count == 0
        assert no.completed_count == 1

    def test_close_deal_not_found(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator()
        result = no.close_deal("unknown", 5000)
        assert result["found"] is False


class TestOrchestratorStatus:
    """Status and analytics testleri."""

    def test_get_status_active(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator()
        no.start_negotiation(
            parties=["us", "vendor"],
            target_value=5000,
            minimum_value=4000,
        )
        result = no.get_negotiation_status("neg_1")
        assert result["active"] is True
        assert result["phase"] == "opening"

    def test_get_status_completed(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator()
        no.start_negotiation(["us", "v"], 5000, 4000)
        no.close_deal("neg_1", 4500, "won")
        result = no.get_negotiation_status("neg_1")
        assert result["active"] is False

    def test_get_status_not_found(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator()
        result = no.get_negotiation_status("unknown")
        assert result["found"] is False

    def test_get_analytics(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator()
        no.start_negotiation(["us", "v"], 5000, 4000)
        analytics = no.get_analytics()
        assert analytics["negotiations_started"] == 1
        assert analytics["offers_generated"] >= 1
        assert analytics["strategies_used"] >= 1


class TestOrchestratorIntegration:
    """Full pipeline integration testleri."""

    def test_full_negotiation_pipeline(self):
        from app.core.negotiation.negotiation_orchestrator import NegotiationOrchestrator
        no = NegotiationOrchestrator()

        # Başlat
        start = no.start_negotiation(
            parties=["us", "supplier"],
            target_value=50000,
            minimum_value=40000,
            context="annual_contract",
            relationship="long_term",
        )
        assert start["started"] is True
        assert start["strategy"] == "collaborative"

        # Karşı teklif al
        counter1 = no.process_counter_offer(
            "neg_1", counter_amount=42000, counter_party="supplier"
        )
        assert counter1["round"] == 1

        # İkinci tur
        counter2 = no.process_counter_offer(
            "neg_1", counter_amount=45000, counter_party="supplier"
        )
        assert counter2["round"] == 2

        # Kapat
        close = no.close_deal("neg_1", final_value=46000, outcome="won")
        assert close["closed"] is True
        assert close["rounds"] == 2

        # Analitik
        analytics = no.get_analytics()
        assert analytics["negotiations_completed"] == 1
        assert analytics["deals_closed"] == 1


# ==================== Config Testleri ====================


class TestNegotiationConfig:
    """Negotiation config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.negotiation_enabled is True
        assert s.auto_respond is False
        assert s.min_acceptable_score == 60.0
        assert s.max_rounds == 10
        assert s.require_approval is True


# ==================== Import Testleri ====================


class TestNegotiationImports:
    """Import testleri."""

    def test_import_all(self):
        from app.core.negotiation import (
            ConcessionTracker,
            CounterOfferAnalyzer,
            DealScorer,
            NegotiationCommunicationManager,
            NegotiationMemory,
            NegotiationOrchestrator,
            NegotiationStrategyPlanner,
            OfferGenerator,
            WinWinOptimizer,
        )
        assert ConcessionTracker is not None
        assert CounterOfferAnalyzer is not None
        assert DealScorer is not None
        assert NegotiationCommunicationManager is not None
        assert NegotiationMemory is not None
        assert NegotiationOrchestrator is not None
        assert NegotiationStrategyPlanner is not None
        assert OfferGenerator is not None
        assert WinWinOptimizer is not None

    def test_import_models(self):
        from app.models.negotiation_models import (
            ConcessionRecord,
            ConcessionType,
            DealOutcome,
            DealScore,
            NegotiationPhase,
            NegotiationRecord,
            NegotiationStrategy,
            OfferRecord,
            OfferStatus,
            PartyRole,
        )
        assert NegotiationPhase is not None
        assert OfferStatus is not None
        assert ConcessionType is not None
        assert NegotiationStrategy is not None
        assert DealOutcome is not None
        assert PartyRole is not None
        assert NegotiationRecord is not None
        assert OfferRecord is not None
        assert ConcessionRecord is not None
        assert DealScore is not None
