"""Olasiliksal karar verme veri modelleri testleri."""

import pytest
from pydantic import ValidationError

from app.models.probability import (
    ConfidenceInterval,
    ConditionalProbability,
    DecisionCriterion,
    DecisionResult,
    DistributionType,
    Evidence,
    PosteriorResult,
    PriorBelief,
    RiskAttitude,
    RiskQuantification,
    ScenarioAnalysis,
    SensitivityResult,
    SimulationConfig,
    SimulationResult,
    UtilityOutcome,
)


# === Enum Testleri ===


class TestDistributionType:
    """DistributionType enum testleri."""

    def test_values(self) -> None:
        """Tum dagilim tipleri mevcut olmalidir."""
        assert DistributionType.NORMAL == "normal"
        assert DistributionType.UNIFORM == "uniform"
        assert DistributionType.BETA == "beta"
        assert DistributionType.TRIANGULAR == "triangular"
        assert DistributionType.CUSTOM == "custom"

    def test_count(self) -> None:
        """5 adet dagilim tipi olmalidir."""
        assert len(DistributionType) == 5


class TestDecisionCriterion:
    """DecisionCriterion enum testleri."""

    def test_values(self) -> None:
        """Tum karar kriterleri mevcut olmalidir."""
        assert DecisionCriterion.MAXIMAX == "maximax"
        assert DecisionCriterion.MAXIMIN == "maximin"
        assert DecisionCriterion.HURWICZ == "hurwicz"
        assert DecisionCriterion.MINIMAX_REGRET == "minimax_regret"
        assert DecisionCriterion.EXPECTED_VALUE == "expected_value"

    def test_count(self) -> None:
        """5 adet karar kriteri olmalidir."""
        assert len(DecisionCriterion) == 5


class TestRiskAttitude:
    """RiskAttitude enum testleri."""

    def test_values(self) -> None:
        """Tum risk tutumlari mevcut olmalidir."""
        assert RiskAttitude.AVERSE == "averse"
        assert RiskAttitude.NEUTRAL == "neutral"
        assert RiskAttitude.SEEKING == "seeking"

    def test_count(self) -> None:
        """3 adet risk tutumu olmalidir."""
        assert len(RiskAttitude) == 3


# === Bayesian Model Testleri ===


class TestPriorBelief:
    """PriorBelief model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler dogru olmalidir."""
        pb = PriorBelief(
            variable="x", probabilities={"a": 0.5, "b": 0.5},
        )
        assert pb.variable == "x"
        assert pb.source == "prior"

    def test_custom(self) -> None:
        """Ozel degerler atanabilmelidir."""
        pb = PriorBelief(
            variable="weather",
            probabilities={"sunny": 0.7, "rainy": 0.3},
            source="expert",
        )
        assert pb.probabilities["sunny"] == 0.7
        assert pb.source == "expert"


class TestEvidence:
    """Evidence model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan confidence 1.0 olmalidir."""
        ev = Evidence(variable="x", observed_value="high")
        assert ev.confidence == 1.0
        assert ev.timestamp is not None

    def test_confidence_bounds(self) -> None:
        """Confidence 0-1 arasi olmalidir."""
        ev = Evidence(variable="x", observed_value="a", confidence=0.5)
        assert ev.confidence == 0.5
        with pytest.raises(ValidationError):
            Evidence(variable="x", observed_value="a", confidence=1.5)


class TestPosteriorResult:
    """PosteriorResult model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler dogru olmalidir."""
        pr = PosteriorResult(
            variable="x", prior={"a": 0.5}, posterior={"a": 0.8},
        )
        assert pr.evidence_used == []
        assert pr.log_likelihood == 0.0

    def test_evidence_used(self) -> None:
        """Kullanilan kanitlar kaydedilmelidir."""
        pr = PosteriorResult(
            variable="x",
            prior={"a": 0.5},
            posterior={"a": 0.8},
            evidence_used=["high", "low"],
        )
        assert len(pr.evidence_used) == 2


class TestConditionalProbability:
    """ConditionalProbability model testleri."""

    def test_table(self) -> None:
        """Tablo yapisi dogru olmalidir."""
        cpt = ConditionalProbability(
            child="alarm",
            parents=["fire"],
            table={
                "true": {"ring": 0.9, "silent": 0.1},
                "false": {"ring": 0.1, "silent": 0.9},
            },
        )
        assert cpt.child == "alarm"
        assert len(cpt.parents) == 1
        assert cpt.table["true"]["ring"] == 0.9


# === Belirsizlik Model Testleri ===


class TestConfidenceInterval:
    """ConfidenceInterval model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan guven duzeyi 0.95 olmalidir."""
        ci = ConfidenceInterval(lower=1.0, upper=3.0, mean=2.0)
        assert ci.confidence_level == 0.95

    def test_custom(self) -> None:
        """Ozel degerler atanabilmelidir."""
        ci = ConfidenceInterval(
            lower=0.5, upper=1.5, confidence_level=0.99, mean=1.0,
        )
        assert ci.confidence_level == 0.99
        assert ci.lower < ci.upper


class TestRiskQuantification:
    """RiskQuantification model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler sifir olmalidir."""
        rq = RiskQuantification()
        assert rq.expected_loss == 0.0
        assert rq.var_95 == 0.0
        assert rq.probability_of_loss == 0.0

    def test_probability_bounds(self) -> None:
        """probability_of_loss 0-1 arasi olmalidir."""
        rq = RiskQuantification(probability_of_loss=0.8)
        assert rq.probability_of_loss == 0.8
        with pytest.raises(ValidationError):
            RiskQuantification(probability_of_loss=1.5)


class TestScenarioAnalysis:
    """ScenarioAnalysis model testleri."""

    def test_required_fields(self) -> None:
        """Zorunlu alanlar saglanmalidir."""
        sa = ScenarioAnalysis(
            worst_case=-100, best_case=200, expected_case=50,
        )
        assert sa.worst_case == -100
        assert sa.scenarios == {}

    def test_with_scenarios(self) -> None:
        """Senaryo detaylari eklenebilmelidir."""
        sa = ScenarioAnalysis(
            worst_case=-10, best_case=10, expected_case=0,
            scenarios={"a": -10, "b": 10},
            probabilities={"a": 0.5, "b": 0.5},
        )
        assert len(sa.scenarios) == 2


# === Karar Teorisi Model Testleri ===


class TestUtilityOutcome:
    """UtilityOutcome model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan payoff ve utility sifir olmalidir."""
        uo = UtilityOutcome(action="A", state="s1", probability=0.5)
        assert uo.payoff == 0.0
        assert uo.utility == 0.0

    def test_probability_bounds(self) -> None:
        """Probability 0-1 arasi olmalidir."""
        with pytest.raises(ValidationError):
            UtilityOutcome(action="A", state="s1", probability=1.5)


class TestDecisionResult:
    """DecisionResult model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler dogru olmalidir."""
        dr = DecisionResult(
            recommended_action="A", criterion_used="maximin",
        )
        assert dr.expected_utility == 0.0
        assert dr.all_scores == {}
        assert dr.metadata == {}

    def test_with_risk_assessment(self) -> None:
        """Risk degerlendirmesi eklenebilmelidir."""
        rq = RiskQuantification(expected_loss=-5.0)
        dr = DecisionResult(
            recommended_action="B",
            criterion_used="expected_utility",
            risk_assessment=rq,
        )
        assert dr.risk_assessment is not None
        assert dr.risk_assessment.expected_loss == -5.0


# === Monte Carlo Model Testleri ===


class TestSimulationConfig:
    """SimulationConfig model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan n_simulations 10000 olmalidir."""
        sc = SimulationConfig()
        assert sc.n_simulations == 10000
        assert sc.random_seed is None
        assert sc.variables == {}

    def test_min_simulations(self) -> None:
        """n_simulations minimum 100 olmalidir."""
        sc = SimulationConfig(n_simulations=100)
        assert sc.n_simulations == 100
        with pytest.raises(ValidationError):
            SimulationConfig(n_simulations=50)


class TestSimulationResult:
    """SimulationResult model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler dogru olmalidir."""
        sr = SimulationResult(mean=5.0, std=1.0)
        assert sr.n_simulations == 0
        assert sr.convergence_achieved is False
        assert sr.percentiles == {}

    def test_with_ci(self) -> None:
        """Guven araligi eklenebilmelidir."""
        ci = ConfidenceInterval(lower=4.0, upper=6.0, mean=5.0)
        sr = SimulationResult(
            mean=5.0, std=1.0, confidence_interval=ci,
        )
        assert sr.confidence_interval is not None


class TestSensitivityResult:
    """SensitivityResult model testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler dogru olmalidir."""
        sr = SensitivityResult(variable="x", base_value=10.0)
        assert sr.impact_scores == {}
        assert sr.tornado_data == []
        assert sr.correlation_coefficients == {}

    def test_with_data(self) -> None:
        """Etki skorlari ve korelasyonlar eklenebilmelidir."""
        sr = SensitivityResult(
            variable="price",
            base_value=100.0,
            impact_scores={"price": 0.8},
            correlation_coefficients={"price": -0.7},
        )
        assert sr.impact_scores["price"] == 0.8
