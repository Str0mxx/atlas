"""ATLAS Senaryo Uretici modulu.

Best/worst/most-likely senaryo uretimi,
edge case tespiti ve rastgele perturbasyonlar.
"""

import logging
import random
from typing import Any

from app.models.simulation import (
    ActionOutcome,
    Assumption,
    OutcomeType,
    Scenario,
    ScenarioType,
    SideEffect,
    RiskLevel,
)

logger = logging.getLogger(__name__)


class ScenarioGenerator:
    """Senaryo uretim sistemi.

    Bir aksiyon icin farkli senaryolar uretir
    ve olasi sonuclari modelleyerek karsilastirir.

    Attributes:
        _scenarios: Uretilen senaryolar.
        _rng: Random number generator.
    """

    def __init__(self, seed: int | None = None) -> None:
        """Senaryo ureticisini baslatir.

        Args:
            seed: Random seed.
        """
        self._scenarios: list[Scenario] = []
        self._rng = random.Random(seed)

        logger.info("ScenarioGenerator baslatildi")

    def generate_all(
        self,
        action_name: str,
        base_probability: float = 0.85,
        parameters: dict[str, Any] | None = None,
    ) -> list[Scenario]:
        """Tum senaryo tiplerini uretir.

        Args:
            action_name: Aksiyon adi.
            base_probability: Temel basari olasiligi.
            parameters: Aksiyon parametreleri.

        Returns:
            Scenario listesi.
        """
        scenarios = [
            self.generate_best_case(action_name, base_probability, parameters),
            self.generate_worst_case(action_name, base_probability, parameters),
            self.generate_most_likely(action_name, base_probability, parameters),
            self.generate_edge_case(action_name, parameters),
            self.generate_random(action_name, parameters),
        ]
        return scenarios

    def generate_best_case(
        self,
        action_name: str,
        base_probability: float = 0.85,
        parameters: dict[str, Any] | None = None,
    ) -> Scenario:
        """En iyi durum senaryosu uretir.

        Args:
            action_name: Aksiyon adi.
            base_probability: Temel olasilik.
            parameters: Parametreler.

        Returns:
            Scenario nesnesi.
        """
        prob = min(base_probability + 0.1, 0.99)

        outcome = ActionOutcome(
            action_name=action_name,
            outcome_type=OutcomeType.SUCCESS,
            success_probability=prob,
            estimated_duration_seconds=30.0,
        )

        scenario = Scenario(
            scenario_type=ScenarioType.BEST_CASE,
            name=f"En iyi durum: {action_name}",
            description="Tum kosullar ideal, hicbir sorun yok.",
            probability=round(prob * 0.3, 3),
            outcomes=[outcome],
            assumptions=[
                Assumption(description="Tum servisler saglikli", confidence=0.9),
                Assumption(description="Kaynaklar yeterli", confidence=0.95),
            ],
            impact_score=0.9,
            parameters=parameters or {},
        )

        self._scenarios.append(scenario)
        return scenario

    def generate_worst_case(
        self,
        action_name: str,
        base_probability: float = 0.85,
        parameters: dict[str, Any] | None = None,
    ) -> Scenario:
        """En kotu durum senaryosu uretir.

        Args:
            action_name: Aksiyon adi.
            base_probability: Temel olasilik.
            parameters: Parametreler.

        Returns:
            Scenario nesnesi.
        """
        prob = max(base_probability - 0.4, 0.05)

        outcome = ActionOutcome(
            action_name=action_name,
            outcome_type=OutcomeType.FAILURE,
            success_probability=prob,
            estimated_duration_seconds=600.0,
            side_effects=[
                SideEffect(
                    description="Tam hizmet kesintisi",
                    affected_entity="service",
                    severity=RiskLevel.CRITICAL,
                    probability=0.8,
                    reversible=False,
                ),
                SideEffect(
                    description="Veri tutarsizligi",
                    affected_entity="database",
                    severity=RiskLevel.HIGH,
                    probability=0.4,
                    reversible=True,
                ),
            ],
            error_message="Birden fazla bagimliliklta hata olustu",
        )

        scenario = Scenario(
            scenario_type=ScenarioType.WORST_CASE,
            name=f"En kotu durum: {action_name}",
            description="Birden fazla hata, zincirleme sorunlar.",
            probability=round((1.0 - prob) * 0.2, 3),
            outcomes=[outcome],
            assumptions=[
                Assumption(description="Birden fazla servis cokmus", confidence=0.3),
                Assumption(description="Kaynaklar yetersiz", confidence=0.4),
            ],
            impact_score=-0.8,
            parameters=parameters or {},
        )

        self._scenarios.append(scenario)
        return scenario

    def generate_most_likely(
        self,
        action_name: str,
        base_probability: float = 0.85,
        parameters: dict[str, Any] | None = None,
    ) -> Scenario:
        """En olasi senaryo uretir.

        Args:
            action_name: Aksiyon adi.
            base_probability: Temel olasilik.
            parameters: Parametreler.

        Returns:
            Scenario nesnesi.
        """
        if base_probability >= 0.7:
            outcome_type = OutcomeType.SUCCESS
        elif base_probability >= 0.5:
            outcome_type = OutcomeType.PARTIAL_SUCCESS
        else:
            outcome_type = OutcomeType.FAILURE

        outcome = ActionOutcome(
            action_name=action_name,
            outcome_type=outcome_type,
            success_probability=base_probability,
            estimated_duration_seconds=120.0,
            side_effects=[
                SideEffect(
                    description="Kisa sureli yavaslik",
                    affected_entity="performance",
                    severity=RiskLevel.LOW,
                    probability=0.4,
                    reversible=True,
                ),
            ],
        )

        scenario = Scenario(
            scenario_type=ScenarioType.MOST_LIKELY,
            name=f"En olasi durum: {action_name}",
            description="Normal kosullar, tipik sonuc.",
            probability=round(base_probability * 0.5 + 0.2, 3),
            outcomes=[outcome],
            assumptions=[
                Assumption(description="Servisler normal calisiyor", confidence=0.8),
            ],
            impact_score=0.3 if outcome_type == OutcomeType.SUCCESS else -0.2,
            parameters=parameters or {},
        )

        self._scenarios.append(scenario)
        return scenario

    def generate_edge_case(
        self,
        action_name: str,
        parameters: dict[str, Any] | None = None,
    ) -> Scenario:
        """Edge case senaryosu uretir.

        Args:
            action_name: Aksiyon adi.
            parameters: Parametreler.

        Returns:
            Scenario nesnesi.
        """
        edge_cases = [
            ("Timeout", "Islem zaman asimina ugradi", 0.1),
            ("Concurrent", "Esanli erisim catismasi", 0.08),
            ("Resource_exhaustion", "Kaynak tukenmesi", 0.05),
            ("Network_partition", "Ag bolunmesi", 0.03),
            ("Data_corruption", "Veri bozulmasi", 0.02),
        ]

        case = self._rng.choice(edge_cases)

        outcome = ActionOutcome(
            action_name=action_name,
            outcome_type=OutcomeType.FAILURE,
            success_probability=0.3,
            estimated_duration_seconds=300.0,
            error_message=case[1],
        )

        scenario = Scenario(
            scenario_type=ScenarioType.EDGE_CASE,
            name=f"Edge case ({case[0]}): {action_name}",
            description=case[1],
            probability=case[2],
            outcomes=[outcome],
            impact_score=-0.5,
            parameters=parameters or {},
        )

        self._scenarios.append(scenario)
        return scenario

    def generate_random(
        self,
        action_name: str,
        parameters: dict[str, Any] | None = None,
    ) -> Scenario:
        """Rastgele perturbasyonlu senaryo uretir.

        Args:
            action_name: Aksiyon adi.
            parameters: Parametreler.

        Returns:
            Scenario nesnesi.
        """
        prob = round(self._rng.uniform(0.3, 0.95), 3)
        impact = round(self._rng.uniform(-0.5, 0.8), 2)
        duration = round(self._rng.uniform(10.0, 500.0), 1)

        if prob >= 0.7:
            outcome_type = OutcomeType.SUCCESS
        elif prob >= 0.5:
            outcome_type = OutcomeType.PARTIAL_SUCCESS
        else:
            outcome_type = OutcomeType.FAILURE

        num_effects = self._rng.randint(0, 3)
        effects: list[SideEffect] = []
        for _ in range(num_effects):
            effects.append(SideEffect(
                description="Rastgele yan etki",
                severity=self._rng.choice(list(RiskLevel)),
                probability=round(self._rng.uniform(0.1, 0.8), 2),
            ))

        outcome = ActionOutcome(
            action_name=action_name,
            outcome_type=outcome_type,
            success_probability=prob,
            estimated_duration_seconds=duration,
            side_effects=effects,
        )

        scenario = Scenario(
            scenario_type=ScenarioType.RANDOM,
            name=f"Rastgele senaryo: {action_name}",
            description="Rastgele perturbasyonlarla uretildi.",
            probability=round(self._rng.uniform(0.05, 0.3), 3),
            outcomes=[outcome],
            impact_score=impact,
            parameters=parameters or {},
        )

        self._scenarios.append(scenario)
        return scenario

    def compare_scenarios(self, scenarios: list[Scenario]) -> dict[str, Any]:
        """Senaryolari karsilastirir.

        Args:
            scenarios: Senaryo listesi.

        Returns:
            Karsilastirma sozlugu.
        """
        if not scenarios:
            return {"count": 0, "best": None, "worst": None}

        sorted_by_impact = sorted(scenarios, key=lambda s: s.impact_score, reverse=True)

        avg_prob = sum(s.probability for s in scenarios) / len(scenarios)

        return {
            "count": len(scenarios),
            "best": sorted_by_impact[0].name,
            "worst": sorted_by_impact[-1].name,
            "average_probability": round(avg_prob, 3),
            "highest_impact": round(sorted_by_impact[0].impact_score, 2),
            "lowest_impact": round(sorted_by_impact[-1].impact_score, 2),
        }

    @property
    def scenario_count(self) -> int:
        """Senaryo sayisi."""
        return len(self._scenarios)
