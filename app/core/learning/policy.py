"""ATLAS politika modulu.

Epsilon-greedy, UCB, Softmax ve Gradient politika stratejileri.
"""

import logging
import math
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from app.models.learning import PolicyConfig, PolicyType

logger = logging.getLogger("atlas.learning.policy")


class Policy(ABC):
    """Soyut politika sinifi.

    Aksiyon secimi icin strateji arayuzu tanimlar.

    Attributes:
        config: Politika yapilandirmasi.
    """

    def __init__(self, config: PolicyConfig | None = None) -> None:
        """Policy'yi baslatir.

        Args:
            config: Politika yapilandirmasi.
        """
        self.config = config or PolicyConfig()

    @abstractmethod
    def select_action(
        self,
        state: dict[str, Any],
        q_values: dict[str, float],
        available_actions: list[str],
    ) -> str:
        """Aksiyon secer.

        Args:
            state: Mevcut durum.
            q_values: Aksiyon Q-degerleri.
            available_actions: Mevcut aksiyonlar.

        Returns:
            Secilen aksiyon.
        """

    @abstractmethod
    def update(self, reward: float) -> None:
        """Politikayi gunceller.

        Args:
            reward: Alinan odul.
        """

    def get_config(self) -> PolicyConfig:
        """Politika yapilandirmasini dondurur."""
        return self.config


class EpsilonGreedyPolicy(Policy):
    """Epsilon-greedy politikasi.

    epsilon olasilikla rastgele, (1-epsilon) olasilikla en iyi aksiyon.
    """

    def __init__(self, config: PolicyConfig | None = None) -> None:
        """EpsilonGreedyPolicy'yi baslatir."""
        cfg = config or PolicyConfig(policy_type=PolicyType.EPSILON_GREEDY)
        super().__init__(cfg)
        self._rng = np.random.default_rng()

    def select_action(
        self,
        state: dict[str, Any],
        q_values: dict[str, float],
        available_actions: list[str],
    ) -> str:
        """Epsilon-greedy aksiyon secimi."""
        if not available_actions:
            return ""

        if self._rng.random() < self.config.epsilon:
            return str(self._rng.choice(available_actions))

        # En yuksek Q-degerli aksiyonu sec
        best_action = available_actions[0]
        best_value = q_values.get(best_action, 0.0)
        for action in available_actions[1:]:
            v = q_values.get(action, 0.0)
            if v > best_value:
                best_value = v
                best_action = action
        return best_action

    def update(self, reward: float) -> None:
        """Epsilon decay uygular."""
        self.config.epsilon = max(
            self.config.epsilon_min,
            self.config.epsilon * self.config.epsilon_decay,
        )


class UCBPolicy(Policy):
    """Upper Confidence Bound (UCB1) politikasi.

    UCB(a) = Q(a) + c * sqrt(ln(N) / N(a))
    """

    def __init__(self, config: PolicyConfig | None = None) -> None:
        """UCBPolicy'yi baslatir."""
        cfg = config or PolicyConfig(policy_type=PolicyType.UCB)
        super().__init__(cfg)
        self._action_counts: dict[str, int] = {}
        self._total_count = 0

    def select_action(
        self,
        state: dict[str, Any],
        q_values: dict[str, float],
        available_actions: list[str],
    ) -> str:
        """UCB1 aksiyon secimi."""
        if not available_actions:
            return ""

        self._total_count += 1

        # Denenmemis aksiyonu sec
        for action in available_actions:
            if self._action_counts.get(action, 0) == 0:
                self._action_counts[action] = 1
                return action

        # UCB skorlarini hesapla
        best_action = available_actions[0]
        best_score = float("-inf")

        for action in available_actions:
            q = q_values.get(action, 0.0)
            n_a = self._action_counts.get(action, 1)
            ucb = q + self.config.ucb_c * math.sqrt(
                math.log(self._total_count) / n_a,
            )
            if ucb > best_score:
                best_score = ucb
                best_action = action

        self._action_counts[best_action] = self._action_counts.get(best_action, 0) + 1
        return best_action

    def update(self, reward: float) -> None:
        """UCB guncelleme (sayac zaten select_action'da artiyor)."""


class SoftmaxPolicy(Policy):
    """Boltzmann (Softmax) politikasi.

    P(a) = exp(Q(a)/tau) / sum(exp(Q(a')/tau))
    """

    def __init__(self, config: PolicyConfig | None = None) -> None:
        """SoftmaxPolicy'yi baslatir."""
        cfg = config or PolicyConfig(policy_type=PolicyType.SOFTMAX)
        super().__init__(cfg)
        self._rng = np.random.default_rng()

    def select_action(
        self,
        state: dict[str, Any],
        q_values: dict[str, float],
        available_actions: list[str],
    ) -> str:
        """Boltzmann dagilimi ile aksiyon secimi."""
        if not available_actions:
            return ""

        values = np.array([q_values.get(a, 0.0) for a in available_actions])
        probs = self._softmax(values, self.config.temperature)
        idx = self._rng.choice(len(available_actions), p=probs)
        return available_actions[idx]

    def _softmax(self, values: np.ndarray, temperature: float) -> np.ndarray:
        """Softmax olasilik hesaplar."""
        scaled = values / temperature
        # Numerik kararlilk icin max cikar
        scaled = scaled - np.max(scaled)
        exp_vals = np.exp(scaled)
        return exp_vals / np.sum(exp_vals)

    def update(self, reward: float) -> None:
        """Softmax guncelleme (sicaklik sabittir)."""


class GradientPolicy(Policy):
    """Politika gradyani politikasi.

    Tercih vektoru uzerinden softmax ile aksiyon secimi.
    Baseline olarak ortalama odul kullanilir.
    """

    def __init__(self, config: PolicyConfig | None = None) -> None:
        """GradientPolicy'yi baslatir."""
        cfg = config or PolicyConfig(policy_type=PolicyType.GRADIENT)
        super().__init__(cfg)
        self._preferences: dict[str, float] = {}
        self._avg_reward = 0.0
        self._step_count = 0
        self._last_action: str | None = None
        self._last_probs: dict[str, float] = {}
        self._rng = np.random.default_rng()

    def select_action(
        self,
        state: dict[str, Any],
        q_values: dict[str, float],
        available_actions: list[str],
    ) -> str:
        """Gradyan tabanli aksiyon secimi."""
        if not available_actions:
            return ""

        # Tercihleri baslat
        for a in available_actions:
            if a not in self._preferences:
                self._preferences[a] = 0.0

        prefs = np.array([self._preferences.get(a, 0.0) for a in available_actions])
        probs = self._softmax_probs(prefs)

        # Olasiliklari kaydet (update icin)
        self._last_probs = {
            a: float(p) for a, p in zip(available_actions, probs)
        }

        idx = self._rng.choice(len(available_actions), p=probs)
        self._last_action = available_actions[idx]
        return self._last_action

    def update(self, reward: float) -> None:
        """Politika gradyani guncelleme.

        H(a) += alpha * (R - R_avg) * (1(a=At) - pi(a))
        """
        self._step_count += 1
        self._avg_reward += (reward - self._avg_reward) / self._step_count

        if self._last_action is None:
            return

        advantage = reward - self._avg_reward
        lr = self.config.learning_rate

        for action, prob in self._last_probs.items():
            if action == self._last_action:
                self._preferences[action] += lr * advantage * (1 - prob)
            else:
                self._preferences[action] -= lr * advantage * prob

    def _softmax_probs(self, preferences: np.ndarray) -> np.ndarray:
        """Tercihlerden softmax olasilik hesaplar."""
        shifted = preferences - np.max(preferences)
        exp_vals = np.exp(shifted)
        return exp_vals / np.sum(exp_vals)
