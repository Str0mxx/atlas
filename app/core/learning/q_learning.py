"""ATLAS Q-Learning modulu.

Q-tablosu, Double Q-Learning ve opsiyonel fonksiyon yaklasimi
ile deger tabanli ogrenme.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from app.core.learning.policy import EpsilonGreedyPolicy, Policy
from app.models.learning import LearningConfig, LearningMetrics

logger = logging.getLogger("atlas.learning.q_learning")


def _try_import_torch() -> bool:
    """PyTorch kullanilabilirligini kontrol eder."""
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


class QLearner:
    """Q-Learning agent'i.

    Q-tablosu veya fonksiyon yaklasimi ile deger ogrenme.
    Double Q-Learning ve opsiyonel PyTorch destegi.

    Attributes:
        config: Ogrenme yapilandirmasi.
        policy: Aksiyon secim politikasi.
    """

    def __init__(
        self,
        config: LearningConfig | None = None,
        policy: Policy | None = None,
    ) -> None:
        """QLearner'i baslatir.

        Args:
            config: Ogrenme yapilandirmasi.
            policy: Aksiyon secim politikasi.
        """
        self.config = config or LearningConfig()
        self.policy = policy or EpsilonGreedyPolicy()

        # Q-tablosu
        self._q1: dict[str, dict[str, float]] = {}
        self._q2: dict[str, dict[str, float]] = {}  # Double Q icin

        # Fonksiyon yaklasimi
        self._use_torch = self.config.use_torch and _try_import_torch()
        self._weights: np.ndarray | None = None
        self._feature_size = 0

        # Metrikler
        self._total_episodes = 0
        self._total_reward = 0.0
        self._reward_history: list[float] = []

        self._rng = np.random.default_rng()

        logger.info(
            "QLearner olusturuldu (gamma=%.2f, alpha=%.2f, double_q=%s, torch=%s)",
            self.config.gamma, self.config.alpha,
            self.config.double_q, self._use_torch,
        )

    def get_q_value(self, state: dict[str, Any], action: str) -> float:
        """Q-degerini dondurur.

        Args:
            state: Durum.
            action: Aksiyon.

        Returns:
            Q(s, a) degeri.
        """
        if self._use_torch or self._weights is not None:
            return self._get_q_approx(state, action)

        key = self._state_to_key(state)
        if self.config.double_q:
            q1 = self._q1.get(key, {}).get(action, 0.0)
            q2 = self._q2.get(key, {}).get(action, 0.0)
            return (q1 + q2) / 2.0
        return self._q1.get(key, {}).get(action, 0.0)

    def update(
        self,
        state: dict[str, Any],
        action: str,
        reward: float,
        next_state: dict[str, Any],
        done: bool,
    ) -> float:
        """Q-degerini gunceller.

        Args:
            state: Mevcut durum.
            action: Alinan aksiyon.
            reward: Alinan odul.
            next_state: Sonraki durum.
            done: Episode bitti mi.

        Returns:
            TD-hata degeri.
        """
        self._total_episodes += 1
        self._total_reward += reward
        self._reward_history.append(reward)

        if self._use_torch or self._weights is not None:
            return self._update_approx(state, action, reward, next_state, done)

        if self.config.double_q:
            return self._update_double_q(state, action, reward, next_state, done)

        return self._update_single_q(state, action, reward, next_state, done)

    def _update_single_q(
        self,
        state: dict[str, Any],
        action: str,
        reward: float,
        next_state: dict[str, Any],
        done: bool,
    ) -> float:
        """Tek Q-tablosu guncellemesi."""
        key = self._state_to_key(state)
        next_key = self._state_to_key(next_state)

        if key not in self._q1:
            self._q1[key] = {}
        if next_key not in self._q1:
            self._q1[next_key] = {}

        current_q = self._q1[key].get(action, 0.0)

        if done:
            target = reward
        else:
            next_values = self._q1[next_key]
            max_next = max(next_values.values()) if next_values else 0.0
            target = reward + self.config.gamma * max_next

        td_error = target - current_q
        self._q1[key][action] = current_q + self.config.alpha * td_error
        return td_error

    def _update_double_q(
        self,
        state: dict[str, Any],
        action: str,
        reward: float,
        next_state: dict[str, Any],
        done: bool,
    ) -> float:
        """Double Q-Learning guncellemesi."""
        key = self._state_to_key(state)
        next_key = self._state_to_key(next_state)

        # Tablolari baslat
        for q in (self._q1, self._q2):
            if key not in q:
                q[key] = {}
            if next_key not in q:
                q[next_key] = {}

        # Rastgele Q1 veya Q2 guncelle
        if self._rng.random() < 0.5:
            update_q, eval_q = self._q1, self._q2
        else:
            update_q, eval_q = self._q2, self._q1

        current_q = update_q[key].get(action, 0.0)

        if done:
            target = reward
        else:
            # update_q'dan en iyi aksiyonu sec, eval_q'dan degerlend
            next_actions = update_q[next_key]
            if next_actions:
                best_action = max(next_actions, key=next_actions.get)
                max_next = eval_q[next_key].get(best_action, 0.0)
            else:
                max_next = 0.0
            target = reward + self.config.gamma * max_next

        td_error = target - current_q
        update_q[key][action] = current_q + self.config.alpha * td_error
        return td_error

    def _get_q_approx(self, state: dict[str, Any], action: str) -> float:
        """Fonksiyon yaklasimi ile Q-degeri."""
        features = self._extract_features(state, action)
        if self._weights is None or len(self._weights) != len(features):
            self._weights = np.zeros(len(features))
            self._feature_size = len(features)
        return float(np.dot(self._weights, features))

    def _update_approx(
        self,
        state: dict[str, Any],
        action: str,
        reward: float,
        next_state: dict[str, Any],
        done: bool,
    ) -> float:
        """Fonksiyon yaklasimi guncellemesi (lineer)."""
        features = self._extract_features(state, action)
        if self._weights is None or len(self._weights) != len(features):
            self._weights = np.zeros(len(features))
            self._feature_size = len(features)

        current_q = float(np.dot(self._weights, features))

        if done:
            target = reward
        else:
            # Tum aksiyonlar icin Q-degerlerini hesapla
            max_next = 0.0
            for a in self._get_known_actions(next_state):
                next_features = self._extract_features(next_state, a)
                if len(next_features) == len(self._weights):
                    q_val = float(np.dot(self._weights, next_features))
                    max_next = max(max_next, q_val)
            target = reward + self.config.gamma * max_next

        td_error = target - current_q
        self._weights += self.config.alpha * td_error * features
        return td_error

    def _extract_features(self, state: dict[str, Any], action: str) -> np.ndarray:
        """Durumdan ozellik vektoru cikarir.

        Args:
            state: Durum sozlugu.
            action: Aksiyon.

        Returns:
            Ozellik vektoru.
        """
        features = []
        for value in sorted(state.items()):
            v = value[1]
            if isinstance(v, (int, float)):
                features.append(float(v))
            elif isinstance(v, bool):
                features.append(1.0 if v else 0.0)
            else:
                features.append(hash(str(v)) % 100 / 100.0)

        # Aksiyon kodlamasi
        features.append(hash(action) % 100 / 100.0)
        # Bias
        features.append(1.0)

        return np.array(features, dtype=np.float64)

    def _get_known_actions(self, state: dict[str, Any]) -> list[str]:
        """Bilinen aksiyonlari dondurur."""
        key = self._state_to_key(state)
        actions = set()
        if key in self._q1:
            actions.update(self._q1[key].keys())
        if self.config.double_q and key in self._q2:
            actions.update(self._q2[key].keys())
        return list(actions) if actions else ["default"]

    def get_best_action(
        self,
        state: dict[str, Any],
        available_actions: list[str],
    ) -> str:
        """En iyi aksiyonu dondurur.

        Args:
            state: Mevcut durum.
            available_actions: Mevcut aksiyonlar.

        Returns:
            En yuksek Q-degerli aksiyon.
        """
        if not available_actions:
            return ""

        q_values = {a: self.get_q_value(state, a) for a in available_actions}
        return max(q_values, key=q_values.get)

    def get_metrics(self) -> LearningMetrics:
        """Ogrenme metriklerini dondurur."""
        n = self._total_episodes
        avg = self._total_reward / n if n > 0 else 0.0

        # Q-tablosu boyutu
        q_size = sum(len(v) for v in self._q1.values())
        if self.config.double_q:
            q_size += sum(len(v) for v in self._q2.values())

        # Yakinsaklik orani (son 100 episode'un std'si)
        recent = self._reward_history[-100:] if self._reward_history else []
        conv = 1.0 / (1.0 + float(np.std(recent))) if len(recent) > 1 else 0.0

        epsilon = getattr(self.policy.config, "epsilon", 0.0)

        return LearningMetrics(
            total_episodes=n,
            avg_reward=avg,
            epsilon_current=epsilon,
            q_table_size=q_size,
            convergence_rate=conv,
        )

    def decay_learning_rate(self) -> None:
        """Ogrenme oranini azaltir."""
        self.config.alpha = max(0.001, self.config.alpha * self.config.alpha_decay)

    def save(self, path: str) -> None:
        """Q-tablosunu dosyaya kaydeder.

        Args:
            path: Dosya yolu.
        """
        data = {
            "q1": self._q1,
            "q2": self._q2 if self.config.double_q else {},
            "config": self.config.model_dump(),
            "metrics": {
                "total_episodes": self._total_episodes,
                "total_reward": self._total_reward,
            },
        }
        Path(path).write_text(json.dumps(data, indent=2))
        logger.info("Q-tablosu kaydedildi: %s", path)

    def load(self, path: str) -> None:
        """Q-tablosunu dosyadan yukler.

        Args:
            path: Dosya yolu.
        """
        data = json.loads(Path(path).read_text())
        self._q1 = data.get("q1", {})
        self._q2 = data.get("q2", {})
        metrics = data.get("metrics", {})
        self._total_episodes = metrics.get("total_episodes", 0)
        self._total_reward = metrics.get("total_reward", 0.0)
        logger.info("Q-tablosu yuklendi: %s", path)

    @staticmethod
    def _state_to_key(state: dict[str, Any]) -> str:
        """Durumu hash anahtarina donusturur.

        Args:
            state: Durum sozlugu.

        Returns:
            Deterministik hash anahtari.
        """
        serialized = json.dumps(state, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()[:16]
