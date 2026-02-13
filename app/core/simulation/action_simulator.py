"""ATLAS Aksiyon Simulatoru modulu.

Aksiyon sonuclarini simule etme, yan etki tahmini,
kaynak tuketim tahmini, sure tahmini ve bagimlilik zinciri.
"""

import logging
import random
from typing import Any

from app.models.simulation import (
    ActionOutcome,
    OutcomeType,
    ResourceType,
    RiskLevel,
    SideEffect,
    WorldSnapshot,
)

logger = logging.getLogger(__name__)

# Aksiyon tipi -> temel basari olasiligi
_BASE_SUCCESS: dict[str, float] = {
    "deploy": 0.85,
    "restart": 0.95,
    "backup": 0.98,
    "migrate": 0.80,
    "delete": 0.90,
    "update": 0.88,
    "create": 0.92,
    "send": 0.95,
    "analyze": 0.97,
    "monitor": 0.99,
}

# Aksiyon tipi -> tahmini sure (saniye)
_BASE_DURATION: dict[str, float] = {
    "deploy": 300.0,
    "restart": 60.0,
    "backup": 180.0,
    "migrate": 600.0,
    "delete": 30.0,
    "update": 120.0,
    "create": 90.0,
    "send": 10.0,
    "analyze": 45.0,
    "monitor": 5.0,
}

# Aksiyon tipi -> kaynak tuketimi
_RESOURCE_COST: dict[str, dict[str, float]] = {
    "deploy": {"cpu": 0.3, "memory": 0.2, "disk": 0.1},
    "restart": {"cpu": 0.1, "memory": 0.05},
    "backup": {"disk": 0.3, "cpu": 0.1},
    "migrate": {"cpu": 0.4, "memory": 0.3, "disk": 0.2, "database": 0.5},
    "delete": {"cpu": 0.05},
    "update": {"cpu": 0.2, "memory": 0.1},
    "create": {"cpu": 0.15, "memory": 0.1, "disk": 0.05},
    "send": {"network": 0.05},
    "analyze": {"cpu": 0.2, "memory": 0.15},
    "monitor": {"cpu": 0.02, "network": 0.01},
}


class ActionSimulator:
    """Aksiyon simulasyon sistemi.

    Aksiyonlarin olasi sonuclarini, yan etkilerini
    ve kaynak gereksinimlerini simule eder.

    Attributes:
        _simulations: Simulasyon gecmisi.
        _seed: Random seed.
    """

    def __init__(self, seed: int | None = None) -> None:
        """Aksiyon simulatorunu baslatir.

        Args:
            seed: Random seed (tekrarlanabilirlik icin).
        """
        self._simulations: list[ActionOutcome] = []
        self._rng = random.Random(seed)

        logger.info("ActionSimulator baslatildi")

    def simulate(
        self,
        action_name: str,
        parameters: dict[str, Any] | None = None,
        world_state: WorldSnapshot | None = None,
        dependencies: list[str] | None = None,
    ) -> ActionOutcome:
        """Aksiyon sonucunu simule eder.

        Args:
            action_name: Aksiyon adi.
            parameters: Aksiyon parametreleri.
            world_state: Dunya durumu.
            dependencies: Bagimliliklar.

        Returns:
            ActionOutcome nesnesi.
        """
        action_type = self._detect_action_type(action_name)

        # Basari olasiligi
        base_prob = _BASE_SUCCESS.get(action_type, 0.85)
        adjusted_prob = self._adjust_probability(base_prob, world_state, parameters)

        # Sonuc tipi
        outcome_type = self._determine_outcome(adjusted_prob)

        # Yan etkiler
        side_effects = self._predict_side_effects(action_type, world_state)

        # Kaynak tuketimi
        resource_cost = self._estimate_resources(action_type, parameters)

        # Sure tahmini
        duration = self._estimate_duration(action_type, parameters)

        outcome = ActionOutcome(
            action_name=action_name,
            outcome_type=outcome_type,
            success_probability=round(adjusted_prob, 3),
            side_effects=side_effects,
            resource_cost=resource_cost,
            estimated_duration_seconds=duration,
            dependencies=dependencies or [],
        )

        self._simulations.append(outcome)
        return outcome

    def simulate_chain(
        self, actions: list[str], world_state: WorldSnapshot | None = None
    ) -> list[ActionOutcome]:
        """Aksiyon zincirini simule eder.

        Args:
            actions: Aksiyon listesi (sirali).
            world_state: Dunya durumu.

        Returns:
            ActionOutcome listesi.
        """
        results: list[ActionOutcome] = []
        cumulative_prob = 1.0

        for i, action in enumerate(actions):
            deps = [actions[j] for j in range(i)]
            outcome = self.simulate(action, world_state=world_state, dependencies=deps)

            # Zincir etkisi: onceki basarisizlik sonrakini etkiler
            cumulative_prob *= outcome.success_probability
            outcome.success_probability = round(cumulative_prob, 3)

            if cumulative_prob < 0.5:
                outcome.outcome_type = OutcomeType.FAILURE

            results.append(outcome)

        return results

    def estimate_total_duration(self, actions: list[str]) -> float:
        """Toplam sure tahmin eder.

        Args:
            actions: Aksiyon listesi.

        Returns:
            Toplam saniye.
        """
        total = 0.0
        for action in actions:
            action_type = self._detect_action_type(action)
            total += _BASE_DURATION.get(action_type, 60.0)
        return total

    def get_resource_requirements(
        self, action_name: str
    ) -> dict[str, float]:
        """Kaynak gereksinimlerini getirir.

        Args:
            action_name: Aksiyon adi.

        Returns:
            Kaynak -> kullanim sozlugu.
        """
        action_type = self._detect_action_type(action_name)
        return dict(_RESOURCE_COST.get(action_type, {"cpu": 0.1}))

    def _detect_action_type(self, action_name: str) -> str:
        """Aksiyon tipini tespit eder."""
        lower = action_name.lower()
        for action_type in _BASE_SUCCESS:
            if action_type in lower:
                return action_type
        return "update"

    def _adjust_probability(
        self,
        base: float,
        world_state: WorldSnapshot | None,
        parameters: dict[str, Any] | None,
    ) -> float:
        """Olasiligi ayarlar."""
        prob = base

        if world_state:
            # Kaynak durumu etkisi
            for resource in world_state.resources:
                if resource.current_usage > 0.9:
                    prob -= 0.1
                elif resource.current_usage > 0.7:
                    prob -= 0.05

            # Karsilanmayan kisitlamalar
            unsatisfied = sum(1 for c in world_state.constraints if not c.is_satisfied)
            prob -= unsatisfied * 0.05

        if parameters:
            # Force parametresi risk artirir
            if parameters.get("force"):
                prob -= 0.05
            # Dry_run her zaman basarili
            if parameters.get("dry_run"):
                prob = 1.0

        return max(0.0, min(1.0, prob))

    def _determine_outcome(self, probability: float) -> OutcomeType:
        """Sonuc tipini belirler."""
        if probability >= 0.9:
            return OutcomeType.SUCCESS
        if probability >= 0.7:
            return OutcomeType.PARTIAL_SUCCESS
        if probability >= 0.5:
            return OutcomeType.UNKNOWN
        return OutcomeType.FAILURE

    def _predict_side_effects(
        self, action_type: str, world_state: WorldSnapshot | None
    ) -> list[SideEffect]:
        """Yan etkileri tahmin eder."""
        effects: list[SideEffect] = []

        if action_type in ("deploy", "restart"):
            effects.append(SideEffect(
                description="Gecici hizmet kesintisi",
                affected_entity="service",
                severity=RiskLevel.MEDIUM,
                probability=0.7,
                reversible=True,
            ))

        if action_type == "migrate":
            effects.append(SideEffect(
                description="Veritabani gecici erisilemez",
                affected_entity="database",
                severity=RiskLevel.HIGH,
                probability=0.6,
                reversible=True,
            ))
            effects.append(SideEffect(
                description="Veri kaybi riski",
                affected_entity="data",
                severity=RiskLevel.CRITICAL,
                probability=0.05,
                reversible=False,
            ))

        if action_type == "delete":
            effects.append(SideEffect(
                description="Kalici veri silme",
                affected_entity="data",
                severity=RiskLevel.HIGH,
                probability=0.9,
                reversible=False,
            ))

        if action_type == "update":
            effects.append(SideEffect(
                description="Uyumsuzluk riski",
                affected_entity="dependencies",
                severity=RiskLevel.LOW,
                probability=0.2,
                reversible=True,
            ))

        return effects

    def _estimate_resources(
        self, action_type: str, parameters: dict[str, Any] | None
    ) -> dict[str, float]:
        """Kaynak tuketimini tahmin eder."""
        base_cost = dict(_RESOURCE_COST.get(action_type, {"cpu": 0.1}))

        if parameters:
            # Buyuk veri seti ek maliyet
            size = parameters.get("data_size", 0)
            if size > 1000:
                multiplier = 1.0 + (size / 10000)
                base_cost = {k: min(v * multiplier, 1.0) for k, v in base_cost.items()}

        return base_cost

    def _estimate_duration(
        self, action_type: str, parameters: dict[str, Any] | None
    ) -> float:
        """Sure tahmin eder."""
        base = _BASE_DURATION.get(action_type, 60.0)

        if parameters:
            size = parameters.get("data_size", 0)
            if size > 1000:
                base *= 1.0 + (size / 5000)

        return round(base, 1)

    @property
    def simulation_count(self) -> int:
        """Simulasyon sayisi."""
        return len(self._simulations)
