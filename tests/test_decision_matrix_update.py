"""Guncellenmis DecisionMatrix testleri.

Olasiliksal karar destegi, guven esigi, risk toleransi ve
geriye uyumluluk testleri.
"""

import pytest

from app.core.autonomy.probability import BayesianNetwork
from app.core.decision_matrix import (
    ActionType,
    Decision,
    DecisionMatrix,
    RiskLevel,
    UrgencyLevel,
)
from app.models.probability import Evidence, PriorBelief


class TestDecisionMatrixInit:
    """Yeni init parametreleri testleri."""

    def test_default_params(self) -> None:
        """Varsayilan parametreler dogru olmalidir."""
        dm = DecisionMatrix()
        assert dm.confidence_threshold == 0.6
        assert dm.risk_tolerance == 0.5
        assert dm._bayesian_net is None

    def test_custom_params(self) -> None:
        """Ozel parametreler atanabilmelidir."""
        dm = DecisionMatrix(
            confidence_threshold=0.8, risk_tolerance=0.3,
        )
        assert dm.confidence_threshold == 0.8
        assert dm.risk_tolerance == 0.3

    def test_backward_compat_no_args(self) -> None:
        """Parametresiz cagri hala calismmalidir."""
        dm = DecisionMatrix()
        assert len(dm.rules) == 9


class TestDecisionMatrixEvaluate:
    """evaluate testleri."""

    async def test_without_beliefs_unchanged(self) -> None:
        """Beliefs verilmediginde mevcut davranis korunmalidir."""
        dm = DecisionMatrix()
        decision = await dm.evaluate(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert decision.action == ActionType.IMMEDIATE
        assert decision.confidence == 0.90

    async def test_high_beliefs_preserves_action(self) -> None:
        """Yuksek guvenli beliefs aksiyonu korumalidir."""
        dm = DecisionMatrix(confidence_threshold=0.5)
        decision = await dm.evaluate(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            beliefs={"cpu": 0.95, "memory": 0.90},
        )
        assert decision.action == ActionType.IMMEDIATE

    async def test_low_beliefs_demotes_action(self) -> None:
        """Dusuk guvenli beliefs AUTO_FIX'i NOTIFY'a dusurmelidir."""
        dm = DecisionMatrix(confidence_threshold=0.8)
        decision = await dm.evaluate(
            RiskLevel.MEDIUM, UrgencyLevel.HIGH,
            beliefs={"cpu": 0.3, "memory": 0.2},
        )
        assert decision.action == ActionType.NOTIFY

    async def test_log_action_not_demoted(self) -> None:
        """LOG aksiyonu beliefs tarafindan dusurulmemelidir."""
        dm = DecisionMatrix(confidence_threshold=0.9)
        decision = await dm.evaluate(
            RiskLevel.LOW, UrgencyLevel.LOW,
            beliefs={"x": 0.1},
        )
        assert decision.action == ActionType.LOG

    async def test_context_still_works(self) -> None:
        """Context parametresi hala calismmalidir."""
        dm = DecisionMatrix()
        decision = await dm.evaluate(
            RiskLevel.LOW, UrgencyLevel.LOW,
            context={"detail": "test detail"},
        )
        assert "test detail" in decision.reason


class TestEvaluateProbabilistic:
    """evaluate_probabilistic testleri."""

    async def test_without_evidence_fallback(self) -> None:
        """Kanit yoksa standart evaluate gibi davranmalidir."""
        dm = DecisionMatrix()
        decision = await dm.evaluate_probabilistic(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
        )
        assert decision.action == ActionType.IMMEDIATE

    async def test_without_network_fallback(self) -> None:
        """Bayesci ag yoksa standart davranmalidir."""
        dm = DecisionMatrix()
        ev = Evidence(variable="x", observed_value="high")
        decision = await dm.evaluate_probabilistic(
            RiskLevel.MEDIUM, UrgencyLevel.MEDIUM,
            evidence=[ev],
        )
        assert decision.action == ActionType.NOTIFY

    async def test_with_network_and_evidence(self) -> None:
        """Bayesci ag ve kanit verildiginde olasiliksal karar verilmelidir."""
        dm = DecisionMatrix(confidence_threshold=0.7)
        bn = BayesianNetwork()
        bn.add_node("risk", ["high", "low"])
        bn.set_prior(PriorBelief(
            variable="risk",
            probabilities={"high": 0.5, "low": 0.5},
        ))
        dm.set_bayesian_network(bn)

        ev = Evidence(variable="risk", observed_value="high", confidence=0.9)
        decision = await dm.evaluate_probabilistic(
            RiskLevel.HIGH, UrgencyLevel.HIGH,
            evidence=[ev],
        )
        assert isinstance(decision, Decision)

    async def test_low_posterior_demotes(self) -> None:
        """Dusuk posterior AUTO_FIX'i NOTIFY'a dusurmelidir."""
        dm = DecisionMatrix(confidence_threshold=0.95)
        bn = BayesianNetwork()
        bn.add_node("status", ["ok", "fail"])
        bn.set_prior(PriorBelief(
            variable="status",
            probabilities={"ok": 0.5, "fail": 0.5},
        ))
        dm.set_bayesian_network(bn)

        ev = Evidence(variable="status", observed_value="ok", confidence=0.3)
        decision = await dm.evaluate_probabilistic(
            RiskLevel.HIGH, UrgencyLevel.MEDIUM,
            evidence=[ev],
        )
        # Dusuk confidence + yuksek threshold -> demote
        assert decision.action == ActionType.NOTIFY


class TestDecisionMatrixSetters:
    """Setter metod testleri."""

    def test_set_confidence_threshold(self) -> None:
        """Guven esigi guncellenmelidir."""
        dm = DecisionMatrix()
        dm.set_confidence_threshold(0.9)
        assert dm.confidence_threshold == 0.9

    def test_threshold_clamped(self) -> None:
        """Esik 0-1 arasina sinirlanmalidir."""
        dm = DecisionMatrix()
        dm.set_confidence_threshold(1.5)
        assert dm.confidence_threshold == 1.0
        dm.set_confidence_threshold(-0.5)
        assert dm.confidence_threshold == 0.0

    def test_set_risk_tolerance(self) -> None:
        """Risk toleransi guncellenmelidir."""
        dm = DecisionMatrix()
        dm.set_risk_tolerance(0.8)
        assert dm.risk_tolerance == 0.8

    def test_tolerance_clamped(self) -> None:
        """Tolerans 0-1 arasina sinirlanmalidir."""
        dm = DecisionMatrix()
        dm.set_risk_tolerance(2.0)
        assert dm.risk_tolerance == 1.0

    def test_set_bayesian_network(self) -> None:
        """Bayesci ag atanabilmelidir."""
        dm = DecisionMatrix()
        bn = BayesianNetwork()
        dm.set_bayesian_network(bn)
        assert dm._bayesian_net is bn


class TestDecisionMatrixRiskLevel:
    """_risk_level_to_float testleri."""

    def test_low(self) -> None:
        """LOW 0.2 olmalidir."""
        assert DecisionMatrix._risk_level_to_float(RiskLevel.LOW) == 0.2

    def test_medium(self) -> None:
        """MEDIUM 0.5 olmalidir."""
        assert DecisionMatrix._risk_level_to_float(RiskLevel.MEDIUM) == 0.5

    def test_high(self) -> None:
        """HIGH 0.9 olmalidir."""
        assert DecisionMatrix._risk_level_to_float(RiskLevel.HIGH) == 0.9


class TestDecisionMatrixBackwardCompat:
    """Geriye uyumluluk testleri."""

    def test_get_action_for_unchanged(self) -> None:
        """get_action_for mevcut davranisini korumalidir."""
        dm = DecisionMatrix()
        assert dm.get_action_for("low", "low") == ActionType.LOG
        assert dm.get_action_for("high", "high") == ActionType.IMMEDIATE

    async def test_evaluate_original_signature(self) -> None:
        """Orijinal evaluate(risk, urgency) calismmalidir."""
        dm = DecisionMatrix()
        decision = await dm.evaluate(RiskLevel.LOW, UrgencyLevel.LOW)
        assert decision.action == ActionType.LOG
        assert decision.confidence == 0.95

    async def test_evaluate_with_context(self) -> None:
        """evaluate(risk, urgency, context) calismmalidir."""
        dm = DecisionMatrix()
        decision = await dm.evaluate(
            RiskLevel.MEDIUM, UrgencyLevel.LOW,
            context={"detail": "test"},
        )
        assert decision.action == ActionType.NOTIFY
