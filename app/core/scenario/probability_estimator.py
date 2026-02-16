"""ATLAS Senaryo Olasılık Tahmincisi.

Olasılık değerlendirme, uzman girişi,
tarihsel analiz, Bayesci güncelleme, güven aralığı.
"""

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


class ScenarioProbabilityEstimator:
    """Senaryo olasılık tahmincisi.

    Senaryo olasılıklarını tahmin eder,
    uzman görüşlerini entegre eder.

    Attributes:
        _estimates: Tahmin kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Tahmincisi başlatır."""
        self._estimates: dict[
            str, dict
        ] = {}
        self._stats = {
            "assessments_made": 0,
            "updates_applied": 0,
        }
        logger.info(
            "ScenarioProbabilityEstimator "
            "baslatildi",
        )

    @property
    def assessment_count(self) -> int:
        """Değerlendirme sayısı."""
        return self._stats[
            "assessments_made"
        ]

    @property
    def update_count(self) -> int:
        """Güncelleme sayısı."""
        return self._stats[
            "updates_applied"
        ]

    def assess_probability(
        self,
        scenario_id: str,
        base_probability: float = 0.5,
        factors: list[float] | None = None,
    ) -> dict[str, Any]:
        """Olasılık değerlendirir.

        Args:
            scenario_id: Senaryo kimliği.
            base_probability: Temel olasılık.
            factors: Düzeltme faktörleri.

        Returns:
            Değerlendirme bilgisi.
        """
        if factors is None:
            factors = []

        adjusted = base_probability
        for f in factors:
            adjusted *= f
        adjusted = round(
            min(max(adjusted, 0.0), 1.0),
            3,
        )

        self._estimates[scenario_id] = {
            "probability": adjusted,
        }
        self._stats[
            "assessments_made"
        ] += 1

        if adjusted >= 0.7:
            level = "high"
        elif adjusted >= 0.4:
            level = "medium"
        else:
            level = "low"

        return {
            "scenario_id": scenario_id,
            "probability": adjusted,
            "level": level,
            "assessed": True,
        }

    def integrate_expert(
        self,
        scenario_id: str,
        expert_estimates: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Uzman görüşü entegre eder.

        Args:
            scenario_id: Senaryo kimliği.
            expert_estimates: Uzman tahminleri.

        Returns:
            Entegrasyon bilgisi.
        """
        if expert_estimates is None:
            expert_estimates = []

        if not expert_estimates:
            return {
                "scenario_id": scenario_id,
                "consensus": 0.0,
                "spread": 0.0,
                "integrated": False,
            }

        consensus = round(
            sum(expert_estimates)
            / len(expert_estimates),
            3,
        )
        spread = round(
            max(expert_estimates)
            - min(expert_estimates),
            3,
        )

        self._stats[
            "assessments_made"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "consensus": consensus,
            "spread": spread,
            "expert_count": len(
                expert_estimates,
            ),
            "integrated": True,
        }

    def analyze_historical(
        self,
        scenario_id: str,
        past_occurrences: int = 0,
        total_opportunities: int = 1,
    ) -> dict[str, Any]:
        """Tarihsel analiz yapar.

        Args:
            scenario_id: Senaryo kimliği.
            past_occurrences: Geçmiş gerçekleşme.
            total_opportunities: Toplam fırsat.

        Returns:
            Analiz bilgisi.
        """
        if total_opportunities <= 0:
            total_opportunities = 1

        frequency = round(
            past_occurrences
            / total_opportunities,
            3,
        )

        self._stats[
            "assessments_made"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "frequency": frequency,
            "past_occurrences": (
                past_occurrences
            ),
            "total_opportunities": (
                total_opportunities
            ),
            "analyzed": True,
        }

    def bayesian_update(
        self,
        scenario_id: str,
        prior: float = 0.5,
        likelihood: float = 0.7,
        evidence: float = 0.5,
    ) -> dict[str, Any]:
        """Bayesci güncelleme yapar.

        P(H|E) = P(E|H) * P(H) / P(E)

        Args:
            scenario_id: Senaryo kimliği.
            prior: Öncül olasılık P(H).
            likelihood: Olabilirlik P(E|H).
            evidence: Kanıt olasılığı P(E).

        Returns:
            Güncelleme bilgisi.
        """
        if evidence <= 0:
            evidence = 0.001

        posterior = round(
            (likelihood * prior)
            / evidence,
            3,
        )
        posterior = min(
            max(posterior, 0.0), 1.0,
        )

        self._stats[
            "updates_applied"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "prior": prior,
            "likelihood": likelihood,
            "evidence": evidence,
            "posterior": posterior,
            "updated": True,
        }

    def confidence_interval(
        self,
        scenario_id: str,
        probability: float = 0.5,
        sample_size: int = 30,
        confidence_level: float = 0.95,
    ) -> dict[str, Any]:
        """Güven aralığı hesaplar.

        Args:
            scenario_id: Senaryo kimliği.
            probability: Olasılık tahmini.
            sample_size: Örneklem büyüklüğü.
            confidence_level: Güven seviyesi.

        Returns:
            Güven aralığı bilgisi.
        """
        z_scores = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
        }
        z = z_scores.get(
            confidence_level, 1.96,
        )

        if sample_size <= 0:
            sample_size = 1

        se = math.sqrt(
            probability
            * (1 - probability)
            / sample_size,
        )
        margin = round(z * se, 3)

        lower = round(
            max(probability - margin, 0.0),
            3,
        )
        upper = round(
            min(probability + margin, 1.0),
            3,
        )

        return {
            "scenario_id": scenario_id,
            "probability": probability,
            "lower": lower,
            "upper": upper,
            "margin": margin,
            "confidence_level": (
                confidence_level
            ),
            "calculated": True,
        }
