"""Karar teorisi modulu testleri."""

import pytest

from app.core.autonomy.decision_theory import (
    DecisionUnderUncertainty,
    ExpectedUtility,
    MultiCriteriaDecision,
    RiskAwareDecision,
)
from app.models.probability import (
    DecisionCriterion,
    RiskAttitude,
    UtilityOutcome,
)


def _make_outcomes(
    action_payoffs: dict[str, list[tuple[str, float, float]]],
) -> list[UtilityOutcome]:
    """Test icin UtilityOutcome listesi olusturur.

    Args:
        action_payoffs: {aksiyon: [(durum, olasilik, getiri), ...]}.

    Returns:
        UtilityOutcome listesi.
    """
    outcomes: list[UtilityOutcome] = []
    for action, entries in action_payoffs.items():
        for state, prob, payoff in entries:
            outcomes.append(UtilityOutcome(
                action=action, state=state,
                probability=prob, payoff=payoff,
            ))
    return outcomes


# === ExpectedUtility Testleri ===


class TestExpectedUtility:
    """Beklenen fayda testleri."""

    def test_simple_two_actions(self) -> None:
        """Basit iki aksiyonlu karar dogru sonuc vermelidir."""
        eu = ExpectedUtility()
        outcomes = _make_outcomes({
            "A": [("s1", 0.6, 10), ("s2", 0.4, -5)],
            "B": [("s1", 0.6, 3), ("s2", 0.4, 3)],
        })
        result = eu.calculate(outcomes)
        # EU(A) = 0.6*10 + 0.4*(-5) = 4.0
        # EU(B) = 0.6*3 + 0.4*3 = 3.0
        assert result.recommended_action == "A"
        assert result.expected_utility == pytest.approx(4.0)

    def test_single_action(self) -> None:
        """Tek aksiyon o aksiyonu donmelidir."""
        eu = ExpectedUtility()
        outcomes = _make_outcomes({
            "only": [("s1", 1.0, 5)],
        })
        result = eu.calculate(outcomes)
        assert result.recommended_action == "only"

    def test_empty_outcomes(self) -> None:
        """Bos sonuclar bos aksiyon donmelidir."""
        eu = ExpectedUtility()
        result = eu.calculate([])
        assert result.recommended_action == ""

    def test_all_scores_present(self) -> None:
        """Tum aksiyonlarin skorlari raporlanmalidir."""
        eu = ExpectedUtility()
        outcomes = _make_outcomes({
            "X": [("s1", 0.5, 10), ("s2", 0.5, 0)],
            "Y": [("s1", 0.5, 6), ("s2", 0.5, 6)],
        })
        result = eu.calculate(outcomes)
        assert "X" in result.all_scores
        assert "Y" in result.all_scores


class TestExpectedUtilityWithRisk:
    """Risk-duyarli beklenen fayda testleri."""

    def test_averse_prefers_stable(self) -> None:
        """Risk-kacinan karar kararlari tercih etmelidir."""
        eu = ExpectedUtility()
        outcomes = _make_outcomes({
            "risky": [("s1", 0.5, 20), ("s2", 0.5, -10)],
            "stable": [("s1", 0.5, 6), ("s2", 0.5, 4)],
        })
        result = eu.calculate_with_risk(
            outcomes, RiskAttitude.AVERSE, risk_parameter=0.5,
        )
        assert result.recommended_action == "stable"

    def test_neutral_same_as_basic(self) -> None:
        """Notral risk tutumu temel hesaplamayla ayni olmalidir."""
        eu = ExpectedUtility()
        outcomes = _make_outcomes({
            "A": [("s1", 0.6, 10), ("s2", 0.4, -5)],
            "B": [("s1", 0.6, 3), ("s2", 0.4, 3)],
        })
        basic = eu.calculate(outcomes)
        neutral = eu.calculate_with_risk(
            outcomes, RiskAttitude.NEUTRAL,
        )
        assert basic.recommended_action == neutral.recommended_action

    def test_seeking_prefers_risky(self) -> None:
        """Risk-arayan yuksek varyansli aksiyonu tercih etmelidir."""
        eu = ExpectedUtility()
        outcomes = _make_outcomes({
            "risky": [("s1", 0.5, 100), ("s2", 0.5, -20)],
            "stable": [("s1", 0.5, 30), ("s2", 0.5, 30)],
        })
        result = eu.calculate_with_risk(
            outcomes, RiskAttitude.SEEKING, risk_parameter=0.02,
        )
        assert result.recommended_action == "risky"

    def test_metadata_contains_param(self) -> None:
        """Metadata risk parametresini icermelidir."""
        eu = ExpectedUtility()
        outcomes = _make_outcomes({"A": [("s1", 1.0, 5)]})
        result = eu.calculate_with_risk(
            outcomes, RiskAttitude.AVERSE, risk_parameter=2.0,
        )
        assert result.metadata["risk_parameter"] == 2.0


# === MultiCriteriaDecision Testleri ===


class TestMultiCriteriaDecision:
    """Cok kriterli karar testleri."""

    def test_equal_weights_beneficial(self) -> None:
        """Esit agirlik ve faydali kriterlerde en iyi secilmelidir."""
        mcd = MultiCriteriaDecision()
        result = mcd.evaluate(
            alternatives={
                "A": {"quality": 8, "speed": 6},
                "B": {"quality": 5, "speed": 9},
            },
            weights={"quality": 0.5, "speed": 0.5},
            beneficial_criteria=["quality", "speed"],
        )
        assert result.recommended_action in ("A", "B")
        assert result.criterion_used == "multi_criteria"

    def test_unequal_weights(self) -> None:
        """Agir kriteri yuksek olan alternatif secilmelidir."""
        mcd = MultiCriteriaDecision()
        result = mcd.evaluate(
            alternatives={
                "A": {"quality": 10, "cost": 5},
                "B": {"quality": 3, "cost": 1},
            },
            weights={"quality": 0.9, "cost": 0.1},
            beneficial_criteria=["quality"],
        )
        assert result.recommended_action == "A"

    def test_cost_criteria(self) -> None:
        """Maliyet kriterlerinde dusuk deger iyi olmalidir."""
        mcd = MultiCriteriaDecision()
        result = mcd.evaluate(
            alternatives={
                "cheap": {"cost": 10},
                "expensive": {"cost": 100},
            },
            weights={"cost": 1.0},
            beneficial_criteria=[],  # cost = dusuk iyi
        )
        assert result.recommended_action == "cheap"

    def test_single_criterion(self) -> None:
        """Tek kriter dogru calismmalidir."""
        mcd = MultiCriteriaDecision()
        result = mcd.evaluate(
            alternatives={"A": {"x": 10}, "B": {"x": 5}},
            weights={"x": 1.0},
            beneficial_criteria=["x"],
        )
        assert result.recommended_action == "A"

    def test_empty_alternatives(self) -> None:
        """Bos alternatifler bos aksiyon donmelidir."""
        mcd = MultiCriteriaDecision()
        result = mcd.evaluate(
            alternatives={}, weights={"x": 1.0},
        )
        assert result.recommended_action == ""


# === DecisionUnderUncertainty Testleri ===


class TestMaximax:
    """Maximax kriteri testleri."""

    def test_picks_optimistic(self) -> None:
        """En yuksek potansiyel aksiyonu secmelidir."""
        duu = DecisionUnderUncertainty()
        result = duu.evaluate(
            {"A": {"s1": 100, "s2": -50}, "B": {"s1": 20, "s2": 10}},
            criterion=DecisionCriterion.MAXIMAX,
        )
        assert result.recommended_action == "A"
        assert result.expected_utility == 100

    def test_all_scores(self) -> None:
        """Tum aksiyonlarin max degerleri raporlanmalidir."""
        duu = DecisionUnderUncertainty()
        result = duu.evaluate(
            {"X": {"s1": 5, "s2": 10}, "Y": {"s1": 8, "s2": 3}},
            criterion=DecisionCriterion.MAXIMAX,
        )
        assert result.all_scores["X"] == 10
        assert result.all_scores["Y"] == 8


class TestMaximin:
    """Maximin kriteri testleri."""

    def test_picks_conservative(self) -> None:
        """En guvenli aksiyonu secmelidir."""
        duu = DecisionUnderUncertainty()
        result = duu.evaluate(
            {"A": {"s1": 100, "s2": -50}, "B": {"s1": 20, "s2": 10}},
            criterion=DecisionCriterion.MAXIMIN,
        )
        assert result.recommended_action == "B"
        assert result.expected_utility == 10

    def test_all_scores(self) -> None:
        """Tum aksiyonlarin min degerleri raporlanmalidir."""
        duu = DecisionUnderUncertainty()
        result = duu.evaluate(
            {"X": {"s1": 5, "s2": -3}, "Y": {"s1": 2, "s2": 1}},
            criterion=DecisionCriterion.MAXIMIN,
        )
        assert result.all_scores["X"] == -3
        assert result.all_scores["Y"] == 1


class TestHurwicz:
    """Hurwicz kriteri testleri."""

    def test_alpha_zero_matches_maximin(self) -> None:
        """alpha=0 maximin ile ayni sonuc vermelidir."""
        duu = DecisionUnderUncertainty()
        payoffs = {"A": {"s1": 100, "s2": -50}, "B": {"s1": 20, "s2": 10}}
        hurwicz = duu.evaluate(payoffs, DecisionCriterion.HURWICZ, alpha=0.0)
        maximin = duu.evaluate(payoffs, DecisionCriterion.MAXIMIN)
        assert hurwicz.recommended_action == maximin.recommended_action

    def test_alpha_one_matches_maximax(self) -> None:
        """alpha=1 maximax ile ayni sonuc vermelidir."""
        duu = DecisionUnderUncertainty()
        payoffs = {"A": {"s1": 100, "s2": -50}, "B": {"s1": 20, "s2": 10}}
        hurwicz = duu.evaluate(payoffs, DecisionCriterion.HURWICZ, alpha=1.0)
        maximax = duu.evaluate(payoffs, DecisionCriterion.MAXIMAX)
        assert hurwicz.recommended_action == maximax.recommended_action

    def test_alpha_midpoint(self) -> None:
        """alpha=0.5 iki ucun ortasini vermmelidir."""
        duu = DecisionUnderUncertainty()
        result = duu.evaluate(
            {"A": {"s1": 100, "s2": 0}},
            DecisionCriterion.HURWICZ, alpha=0.5,
        )
        # 0.5*100 + 0.5*0 = 50
        assert result.expected_utility == pytest.approx(50.0)


class TestMinimaxRegret:
    """Minimax regret testleri."""

    def test_minimizes_regret(self) -> None:
        """Maximum pismanlik en dusuk olan aksiyon secilmelidir."""
        duu = DecisionUnderUncertainty()
        result = duu.evaluate(
            {
                "A": {"s1": 100, "s2": 0},
                "B": {"s1": 50, "s2": 40},
            },
            criterion=DecisionCriterion.MINIMAX_REGRET,
        )
        # s1: best=100, regret_A=0, regret_B=50
        # s2: best=40, regret_A=40, regret_B=0
        # max_regret: A=40, B=50 -> A wins
        assert result.recommended_action == "A"

    def test_dominant_action(self) -> None:
        """Baskin aksiyon sifir pismanlikla secilmelidir."""
        duu = DecisionUnderUncertainty()
        result = duu.evaluate(
            {
                "dominant": {"s1": 10, "s2": 10},
                "weak": {"s1": 5, "s2": 5},
            },
            criterion=DecisionCriterion.MINIMAX_REGRET,
        )
        assert result.recommended_action == "dominant"


class TestExpectedValue:
    """Laplace / Expected Value kriteri testleri."""

    def test_equal_probability(self) -> None:
        """Esit olasilik ortalama getiri ile secmelidir."""
        duu = DecisionUnderUncertainty()
        result = duu.evaluate(
            {
                "A": {"s1": 10, "s2": 0},
                "B": {"s1": 4, "s2": 8},
            },
            criterion=DecisionCriterion.EXPECTED_VALUE,
        )
        # avg(A) = 5, avg(B) = 6 -> B wins
        assert result.recommended_action == "B"
        assert result.expected_utility == pytest.approx(6.0)

    def test_empty_payoff(self) -> None:
        """Bos payoff matrisi bos aksiyon donmelidir."""
        duu = DecisionUnderUncertainty()
        result = duu.evaluate({}, DecisionCriterion.EXPECTED_VALUE)
        assert result.recommended_action == ""


# === RiskAwareDecision Testleri ===


class TestRiskAwareDecision:
    """Risk-duyarli karar testleri."""

    def test_low_confidence_uses_averse(self) -> None:
        """Dusuk guven muhafazakar tutum kullanmalidir."""
        rad = RiskAwareDecision(min_confidence=0.6)
        outcomes = _make_outcomes({
            "risky": [("s1", 0.5, 50), ("s2", 0.5, -30)],
            "safe": [("s1", 0.5, 8), ("s2", 0.5, 7)],
        })
        result = rad.evaluate(
            outcomes, RiskAttitude.SEEKING, confidence=0.3,
        )
        assert result.metadata["effective_attitude"] == "averse"

    def test_high_confidence_keeps_attitude(self) -> None:
        """Yuksek guven orijinal tutumu korumalidir."""
        rad = RiskAwareDecision(min_confidence=0.6)
        outcomes = _make_outcomes({
            "A": [("s1", 1.0, 10)],
        })
        result = rad.evaluate(
            outcomes, RiskAttitude.NEUTRAL, confidence=0.9,
        )
        assert result.metadata["effective_attitude"] == "neutral"

    def test_metadata_fields(self) -> None:
        """Metadata beklenen alanlari icermelidir."""
        rad = RiskAwareDecision()
        outcomes = _make_outcomes({"A": [("s1", 1.0, 5)]})
        result = rad.evaluate(outcomes, confidence=0.8)
        assert "original_confidence" in result.metadata
        assert "effective_attitude" in result.metadata
        assert "risk_parameter_used" in result.metadata

    def test_init_defaults(self) -> None:
        """Varsayilan degerler dogru olmalidir."""
        rad = RiskAwareDecision()
        assert rad.risk_tolerance == 0.5
        assert rad.min_confidence == 0.6

    def test_custom_init(self) -> None:
        """Ozel parametreler atanabilmelidir."""
        rad = RiskAwareDecision(
            risk_tolerance=0.8, min_confidence=0.3,
        )
        assert rad.risk_tolerance == 0.8
        assert rad.min_confidence == 0.3
