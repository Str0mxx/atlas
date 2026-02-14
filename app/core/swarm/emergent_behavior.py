"""ATLAS Ortaya Cikan Davranis modulu.

Oruntu tespiti, kendinden organizasyon,
adaptif davranis, kolektif zeka ve sinerji tespiti.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EmergentBehavior:
    """Ortaya cikan davranis sistemi.

    Suru uyelerinin bireysel davranislarindan
    ortaya cikan kolektif kaliplari tespit eder.

    Attributes:
        _agent_actions: Agent aksiyon gecmisi.
        _patterns: Tespit edilen oruntuler.
        _synergies: Tespit edilen sinerjiler.
        _behaviors: Kolektif davranislar.
    """

    def __init__(self) -> None:
        """Ortaya cikan davranis sistemini baslatir."""
        self._agent_actions: dict[str, list[str]] = {}
        self._patterns: list[dict[str, Any]] = []
        self._synergies: list[dict[str, Any]] = []
        self._behaviors: dict[str, dict[str, Any]] = {}

        logger.info("EmergentBehavior baslatildi")

    def record_action(
        self,
        agent_id: str,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Aksiyon kaydeder.

        Args:
            agent_id: Agent ID.
            action: Aksiyon adi.
            context: Baglam bilgisi.
        """
        if agent_id not in self._agent_actions:
            self._agent_actions[agent_id] = []
        self._agent_actions[agent_id].append(action)

        # Son 100 aksiyon tut
        if len(self._agent_actions[agent_id]) > 100:
            self._agent_actions[agent_id] = self._agent_actions[agent_id][-100:]

    def detect_patterns(self) -> list[dict[str, Any]]:
        """Oruntuleri tespit eder.

        Returns:
            Oruntu listesi.
        """
        new_patterns: list[dict[str, Any]] = []

        # Agent'lar arasi ortak aksiyon kaliplari
        if len(self._agent_actions) < 2:
            return new_patterns

        # Tum agent'larin son aksiyonlari
        action_freq: dict[str, int] = {}
        for actions in self._agent_actions.values():
            for action in actions[-10:]:
                action_freq[action] = action_freq.get(action, 0) + 1

        # Birden fazla agent'in yaptigi aksiyonlar
        total_agents = len(self._agent_actions)
        for action, count in action_freq.items():
            if count >= total_agents * 0.5 and count >= 2:
                pattern = {
                    "type": "convergent_behavior",
                    "action": action,
                    "agent_count": count,
                    "ratio": round(count / total_agents, 2),
                }
                new_patterns.append(pattern)

        # Sira kaliplari tespit et
        sequences = self._find_common_sequences()
        for seq in sequences:
            pattern = {
                "type": "sequence_pattern",
                "sequence": seq["sequence"],
                "agent_count": seq["count"],
            }
            new_patterns.append(pattern)

        self._patterns.extend(new_patterns)
        return new_patterns

    def detect_synergy(
        self,
        agent_pairs: list[tuple[str, str]],
        outcomes: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Sinerji tespit eder.

        Args:
            agent_pairs: Agent ciftleri.
            outcomes: Sonuc puanlari.

        Returns:
            Sinerji listesi.
        """
        new_synergies: list[dict[str, Any]] = []

        for a1, a2 in agent_pairs:
            pair_key = f"{a1}+{a2}"
            solo_a1 = outcomes.get(a1, 0.0)
            solo_a2 = outcomes.get(a2, 0.0)
            combined = outcomes.get(pair_key, 0.0)

            expected = solo_a1 + solo_a2
            if expected > 0 and combined > expected:
                synergy = {
                    "agents": [a1, a2],
                    "solo_sum": round(expected, 3),
                    "combined": round(combined, 3),
                    "synergy_ratio": round(combined / expected, 3),
                }
                new_synergies.append(synergy)

        self._synergies.extend(new_synergies)
        return new_synergies

    def register_behavior(
        self,
        name: str,
        description: str = "",
        trigger_conditions: dict[str, Any] | None = None,
    ) -> None:
        """Kolektif davranis kaydeder.

        Args:
            name: Davranis adi.
            description: Aciklama.
            trigger_conditions: Tetikleme kosullari.
        """
        self._behaviors[name] = {
            "description": description,
            "trigger_conditions": trigger_conditions or {},
            "active": True,
            "trigger_count": 0,
        }

    def check_behavior_trigger(
        self,
        name: str,
        current_state: dict[str, Any],
    ) -> bool:
        """Davranis tetiklenme kontrol eder.

        Args:
            name: Davranis adi.
            current_state: Mevcut durum.

        Returns:
            Tetiklendiyse True.
        """
        behavior = self._behaviors.get(name)
        if not behavior or not behavior["active"]:
            return False

        conditions = behavior["trigger_conditions"]
        if not conditions:
            return False

        # Her kosula bak
        for key, expected in conditions.items():
            actual = current_state.get(key)
            if actual is None:
                return False
            if isinstance(expected, (int, float)):
                if actual < expected:
                    return False
            elif actual != expected:
                return False

        behavior["trigger_count"] += 1
        return True

    def get_self_organization_score(self) -> float:
        """Kendinden organizasyon puanini hesaplar.

        Returns:
            Organizasyon puani (0-1).
        """
        if not self._agent_actions:
            return 0.0

        # Oruntu sayisi ve cesitliligi
        pattern_score = min(1.0, len(self._patterns) / 10.0)

        # Sinerji skoru
        synergy_score = min(1.0, len(self._synergies) / 5.0)

        # Agent cesitliligi
        unique_actions: set[str] = set()
        for actions in self._agent_actions.values():
            unique_actions.update(actions)
        diversity_score = min(1.0, len(unique_actions) / 20.0)

        return round(
            (pattern_score + synergy_score + diversity_score) / 3.0, 3,
        )

    def get_collective_intelligence_score(
        self,
        individual_scores: dict[str, float],
        collective_score: float,
    ) -> float:
        """Kolektif zeka puanini hesaplar.

        Args:
            individual_scores: Bireysel puanlar.
            collective_score: Kolektif puan.

        Returns:
            CI skoru (>1 sinerjik, <1 olumsuz).
        """
        if not individual_scores:
            return 0.0

        avg_individual = sum(individual_scores.values()) / len(individual_scores)
        if avg_individual == 0:
            return 0.0

        return round(collective_score / avg_individual, 3)

    def get_patterns(self) -> list[dict[str, Any]]:
        """Tespit edilen oruntuler.

        Returns:
            Oruntu listesi.
        """
        return list(self._patterns)

    def get_synergies(self) -> list[dict[str, Any]]:
        """Tespit edilen sinerjiler.

        Returns:
            Sinerji listesi.
        """
        return list(self._synergies)

    def _find_common_sequences(
        self, min_length: int = 2,
    ) -> list[dict[str, Any]]:
        """Ortak aksiyon serilerini bulur."""
        sequences: list[dict[str, Any]] = []

        if len(self._agent_actions) < 2:
            return sequences

        # Her agent'in son aksiyonlarindan bigram'lar cikar
        bigram_agents: dict[str, list[str]] = {}
        for agent_id, actions in self._agent_actions.items():
            recent = actions[-10:]
            for i in range(len(recent) - 1):
                bigram = f"{recent[i]}->{recent[i + 1]}"
                if bigram not in bigram_agents:
                    bigram_agents[bigram] = []
                if agent_id not in bigram_agents[bigram]:
                    bigram_agents[bigram].append(agent_id)

        # Birden fazla agent'ta gorulenleri raporla
        for bigram, agents in bigram_agents.items():
            if len(agents) >= 2:
                sequences.append({
                    "sequence": bigram,
                    "count": len(agents),
                })

        return sequences

    @property
    def tracked_agents(self) -> int:
        """Takip edilen agent sayisi."""
        return len(self._agent_actions)

    @property
    def pattern_count(self) -> int:
        """Tespit edilen oruntu sayisi."""
        return len(self._patterns)

    @property
    def behavior_count(self) -> int:
        """Kayitli davranis sayisi."""
        return len(self._behaviors)
