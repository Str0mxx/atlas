"""ATLAS karar teorisi modulu.

Beklenen fayda, cok kriterli karar, belirsizlik altinda karar
ve risk-duyarli karar verme islemlerini saglar.
"""

import logging
from typing import Any

import numpy as np

from app.models.probability import (
    DecisionCriterion,
    DecisionResult,
    RiskAttitude,
    UtilityOutcome,
)

logger = logging.getLogger("atlas.autonomy.decision_theory")


class ExpectedUtility:
    """Beklenen fayda hesaplayicisi.

    Her aksiyonun beklenen faydasini hesaplayarak
    en yuksek faydali aksiyonu onerir.
    """

    def calculate(
        self,
        outcomes: list[UtilityOutcome],
    ) -> DecisionResult:
        """Beklenen fayda hesaplar ve en iyi aksiyonu secer.

        EU(action_i) = sum over states j: P(state_j) * payoff(action_i, state_j)

        Args:
            outcomes: Tum aksiyon-durum-olasilik-getiri birlesenleri.

        Returns:
            Karar sonucu.
        """
        # Aksiyonlara gore grupla
        action_utilities: dict[str, float] = {}
        for outcome in outcomes:
            if outcome.action not in action_utilities:
                action_utilities[outcome.action] = 0.0
            action_utilities[outcome.action] += (
                outcome.probability * outcome.payoff
            )

        if not action_utilities:
            return DecisionResult(
                recommended_action="",
                criterion_used="expected_utility",
            )

        best_action = max(
            action_utilities, key=lambda a: action_utilities[a],
        )

        return DecisionResult(
            recommended_action=best_action,
            criterion_used="expected_utility",
            expected_utility=action_utilities[best_action],
            all_scores=action_utilities,
        )

    def calculate_with_risk(
        self,
        outcomes: list[UtilityOutcome],
        risk_attitude: RiskAttitude = RiskAttitude.NEUTRAL,
        risk_parameter: float = 1.0,
    ) -> DecisionResult:
        """Risk tutumuna gore fayda hesaplar.

        CARA (sabit mutlak riskten kacinma) fayda fonksiyonu:
        - AVERSE:  U(x) = (1 - exp(-lambda * x)) / lambda
        - SEEKING: U(x) = (exp(lambda * x) - 1) / lambda
        - NEUTRAL: U(x) = x

        Args:
            outcomes: Aksiyon-durum birlesimleri.
            risk_attitude: Risk tutumu.
            risk_parameter: Risk parametresi (lambda).

        Returns:
            Risk-duyarli karar sonucu.
        """
        lam = max(risk_parameter, 1e-10)

        def utility_fn(payoff: float) -> float:
            if risk_attitude == RiskAttitude.AVERSE:
                return (1.0 - np.exp(-lam * payoff)) / lam
            if risk_attitude == RiskAttitude.SEEKING:
                return (np.exp(lam * payoff) - 1.0) / lam
            return payoff

        # Aksiyonlara gore grupla
        action_utilities: dict[str, float] = {}
        for outcome in outcomes:
            if outcome.action not in action_utilities:
                action_utilities[outcome.action] = 0.0
            action_utilities[outcome.action] += (
                outcome.probability * utility_fn(outcome.payoff)
            )

        if not action_utilities:
            return DecisionResult(
                recommended_action="",
                criterion_used=f"expected_utility_{risk_attitude.value}",
            )

        best_action = max(
            action_utilities, key=lambda a: action_utilities[a],
        )

        return DecisionResult(
            recommended_action=best_action,
            criterion_used=f"expected_utility_{risk_attitude.value}",
            expected_utility=action_utilities[best_action],
            all_scores=action_utilities,
            metadata={"risk_parameter": risk_parameter},
        )


class MultiCriteriaDecision:
    """Cok kriterli karar analizi (MCDA).

    Birden fazla kriteri agirliklandirarak karar verir.
    Min-max normalize edilmis puanlama matrisi kullanir.
    """

    def evaluate(
        self,
        alternatives: dict[str, dict[str, float]],
        weights: dict[str, float],
        beneficial_criteria: list[str] | None = None,
    ) -> DecisionResult:
        """Alternatifleri cok kriterli olarak degerlendirir.

        Args:
            alternatives: {alternatif_adi: {kriter: deger}}.
            weights: {kriter: agirlik}.
            beneficial_criteria: Yuksek degeri iyi olan kriterler
                                 (belirtilmeyen maliyet sayilir).

        Returns:
            Karar sonucu.
        """
        if not alternatives or not weights:
            return DecisionResult(
                recommended_action="",
                criterion_used="multi_criteria",
            )

        beneficial = set(beneficial_criteria or [])
        criteria = list(weights.keys())

        # Agirliklar normalize
        total_weight = sum(weights.values())
        norm_weights = {
            k: v / total_weight for k, v in weights.items()
        }

        # Her kriter icin min/max bul
        min_vals: dict[str, float] = {}
        max_vals: dict[str, float] = {}
        for criterion in criteria:
            vals = [
                alt.get(criterion, 0.0) for alt in alternatives.values()
            ]
            min_vals[criterion] = min(vals)
            max_vals[criterion] = max(vals)

        # Min-max normalizasyon ve agirlikli toplam
        scores: dict[str, float] = {}
        for alt_name, alt_values in alternatives.items():
            score = 0.0
            for criterion in criteria:
                val = alt_values.get(criterion, 0.0)
                range_val = max_vals[criterion] - min_vals[criterion]

                if range_val > 0:
                    if criterion in beneficial:
                        # Yuksek = iyi
                        norm_val = (
                            (val - min_vals[criterion]) / range_val
                        )
                    else:
                        # Dusuk = iyi (maliyet)
                        norm_val = (
                            (max_vals[criterion] - val) / range_val
                        )
                else:
                    norm_val = 1.0  # Tum degerler esit

                score += norm_weights[criterion] * norm_val
            scores[alt_name] = score

        best = max(scores, key=lambda a: scores[a])

        return DecisionResult(
            recommended_action=best,
            criterion_used="multi_criteria",
            expected_utility=scores[best],
            all_scores=scores,
        )


class DecisionUnderUncertainty:
    """Belirsizlik altinda karar verme sinifi.

    Olasiliklar bilinmediginde klasik karar kriterlerini uygular:
    maximax, maximin, hurwicz, minimax regret, expected value (Laplace).
    """

    def evaluate(
        self,
        payoff_matrix: dict[str, dict[str, float]],
        criterion: DecisionCriterion = DecisionCriterion.HURWICZ,
        alpha: float = 0.5,
    ) -> DecisionResult:
        """Belirsizlik altinda karar verir.

        Args:
            payoff_matrix: {aksiyon: {durum: getiri}}.
            criterion: Karar kriteri.
            alpha: Hurwicz iyimserlik katsayisi (0=kotumser, 1=iyimser).

        Returns:
            Karar sonucu.
        """
        if not payoff_matrix:
            return DecisionResult(
                recommended_action="",
                criterion_used=criterion.value,
            )

        dispatch = {
            DecisionCriterion.MAXIMAX: lambda: self._maximax(payoff_matrix),
            DecisionCriterion.MAXIMIN: lambda: self._maximin(payoff_matrix),
            DecisionCriterion.HURWICZ: lambda: self._hurwicz(
                payoff_matrix, alpha,
            ),
            DecisionCriterion.MINIMAX_REGRET: lambda: self._minimax_regret(
                payoff_matrix,
            ),
            DecisionCriterion.EXPECTED_VALUE: lambda: self._expected_value(
                payoff_matrix,
            ),
        }

        action, score = dispatch[criterion]()

        # Tum aksiyonlarin skorlarini hesapla
        all_scores: dict[str, float] = {}
        for act, state_payoffs in payoff_matrix.items():
            vals = list(state_payoffs.values())
            if criterion == DecisionCriterion.MAXIMAX:
                all_scores[act] = max(vals)
            elif criterion == DecisionCriterion.MAXIMIN:
                all_scores[act] = min(vals)
            elif criterion == DecisionCriterion.HURWICZ:
                all_scores[act] = alpha * max(vals) + (
                    1 - alpha
                ) * min(vals)
            elif criterion == DecisionCriterion.EXPECTED_VALUE:
                all_scores[act] = sum(vals) / len(vals) if vals else 0.0
            else:
                all_scores[act] = 0.0

        # Minimax regret icin ayri hesapla
        if criterion == DecisionCriterion.MINIMAX_REGRET:
            all_scores = self._regret_scores(payoff_matrix)

        return DecisionResult(
            recommended_action=action,
            criterion_used=criterion.value,
            expected_utility=score,
            all_scores=all_scores,
            metadata={"alpha": alpha} if criterion == DecisionCriterion.HURWICZ else {},
        )

    def _maximax(
        self, payoff_matrix: dict[str, dict[str, float]],
    ) -> tuple[str, float]:
        """Maximax: en iyimser — max_a(max_s(payoff))."""
        best_action = ""
        best_score = float("-inf")
        for action, payoffs in payoff_matrix.items():
            max_payoff = max(payoffs.values())
            if max_payoff > best_score:
                best_score = max_payoff
                best_action = action
        return best_action, best_score

    def _maximin(
        self, payoff_matrix: dict[str, dict[str, float]],
    ) -> tuple[str, float]:
        """Maximin: en kotumser — max_a(min_s(payoff))."""
        best_action = ""
        best_score = float("-inf")
        for action, payoffs in payoff_matrix.items():
            min_payoff = min(payoffs.values())
            if min_payoff > best_score:
                best_score = min_payoff
                best_action = action
        return best_action, best_score

    def _hurwicz(
        self,
        payoff_matrix: dict[str, dict[str, float]],
        alpha: float,
    ) -> tuple[str, float]:
        """Hurwicz: alpha * max + (1-alpha) * min."""
        best_action = ""
        best_score = float("-inf")
        for action, payoffs in payoff_matrix.items():
            vals = list(payoffs.values())
            score = alpha * max(vals) + (1 - alpha) * min(vals)
            if score > best_score:
                best_score = score
                best_action = action
        return best_action, best_score

    def _minimax_regret(
        self, payoff_matrix: dict[str, dict[str, float]],
    ) -> tuple[str, float]:
        """Minimax regret: min_a(max_s(regret))."""
        regret_scores = self._regret_scores(payoff_matrix)
        # En dusuk maximum regret
        best_action = min(
            regret_scores, key=lambda a: regret_scores[a],
        )
        return best_action, regret_scores[best_action]

    def _regret_scores(
        self, payoff_matrix: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        """Her aksiyon icin max regret hesaplar."""
        actions = list(payoff_matrix.keys())
        all_states: set[str] = set()
        for payoffs in payoff_matrix.values():
            all_states.update(payoffs.keys())

        # Her durum icin en iyi getiri
        best_per_state: dict[str, float] = {}
        for state in all_states:
            best_per_state[state] = max(
                payoff_matrix[a].get(state, 0.0) for a in actions
            )

        # Her aksiyon icin max regret
        max_regrets: dict[str, float] = {}
        for action in actions:
            regrets = [
                best_per_state[s] - payoff_matrix[action].get(s, 0.0)
                for s in all_states
            ]
            max_regrets[action] = max(regrets) if regrets else 0.0

        return max_regrets

    def _expected_value(
        self, payoff_matrix: dict[str, dict[str, float]],
    ) -> tuple[str, float]:
        """Laplace kriteri: esit olasilik varsayimi — max_a(mean_s(payoff))."""
        best_action = ""
        best_score = float("-inf")
        for action, payoffs in payoff_matrix.items():
            vals = list(payoffs.values())
            avg = sum(vals) / len(vals) if vals else 0.0
            if avg > best_score:
                best_score = avg
                best_action = action
        return best_action, best_score


class RiskAwareDecision:
    """Risk-duyarli karar birlestiricisi.

    Guven seviyesine gore karar stratejisini ayarlar:
    dusuk guven → muhafazakar, yuksek guven → iyimser.

    Attributes:
        risk_tolerance: Risk toleransi (0-1).
        min_confidence: Minimum guven esigi.
    """

    def __init__(
        self,
        risk_tolerance: float = 0.5,
        min_confidence: float = 0.6,
    ) -> None:
        """RiskAwareDecision'i baslatir.

        Args:
            risk_tolerance: Risk toleransi (0-1).
            min_confidence: Minimum guven esigi.
        """
        self.risk_tolerance = risk_tolerance
        self.min_confidence = min_confidence
        self._eu = ExpectedUtility()
        logger.info(
            "RiskAwareDecision olusturuldu "
            "(risk_tol=%.2f, min_conf=%.2f)",
            risk_tolerance, min_confidence,
        )

    def evaluate(
        self,
        outcomes: list[UtilityOutcome],
        risk_attitude: RiskAttitude = RiskAttitude.NEUTRAL,
        confidence: float = 1.0,
    ) -> DecisionResult:
        """Risk-duyarli karar verir.

        Dusuk guven'de muhafazakar (risk_averse),
        yuksek guven'de verilen risk_attitude ile karar verir.

        Args:
            outcomes: Aksiyon-sonuc birlesimleri.
            risk_attitude: Risk tutumu.
            confidence: Mevcut guven duzeyi.

        Returns:
            Risk-duyarli karar.
        """
        # Guven yetersizse muhafazakar ol
        if confidence < self.min_confidence:
            effective_attitude = RiskAttitude.AVERSE
            risk_param = 2.0  # Daha guclu riskten kacinma
        else:
            effective_attitude = risk_attitude
            # Guven ile risk parametresini ayarla
            risk_param = 1.0 + (1.0 - confidence) * (
                1.0 - self.risk_tolerance
            )

        result = self._eu.calculate_with_risk(
            outcomes,
            risk_attitude=effective_attitude,
            risk_parameter=risk_param,
        )

        result.metadata["original_confidence"] = confidence
        result.metadata["effective_attitude"] = effective_attitude.value
        result.metadata["risk_parameter_used"] = risk_param

        return result
