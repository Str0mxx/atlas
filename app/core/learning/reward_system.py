"""ATLAS odul sistemi modulu.

Coklu hedefli odul hesaplama, odul sekillendirme ve
icselfif merak motivasyonu.
"""

import logging
import math
from typing import Any

from app.agents.base_agent import TaskResult
from app.models.learning import RewardConfig, RewardSignal

logger = logging.getLogger("atlas.learning.reward_system")


class RewardFunction:
    """Coklu hedefli odul fonksiyonu.

    TaskResult'tan odul sinyali uretir. Odul sekillendirme
    ve merak tabanli icselfif motivasyon destekler.

    Attributes:
        config: Odul yapilandirmasi.
    """

    def __init__(self, config: RewardConfig | None = None) -> None:
        """RewardFunction'i baslatir.

        Args:
            config: Odul yapilandirmasi (None ise varsayilan).
        """
        self.config = config or RewardConfig()
        self._episode_count = 0
        self._total_reward = 0.0
        logger.info("RewardFunction olusturuldu")

    def calculate(
        self,
        task_result: TaskResult,
        context: dict[str, Any] | None = None,
    ) -> RewardSignal:
        """TaskResult'tan odul sinyali hesaplar.

        Args:
            task_result: Gorev sonucu.
            context: Ek baglamsal bilgi.

        Returns:
            Odul sinyali.
        """
        ctx = context or {}
        components: dict[str, float] = {}

        # Basari odulu / basarisizlik cezasi
        base_reward = (
            self.config.success_reward if task_result.success
            else self.config.failure_penalty
        )
        components["base"] = base_reward

        # Verimlilik bilefleni
        if "efficiency" in self.config.objectives:
            efficiency_score = ctx.get("efficiency", 0.5)
            components["efficiency"] = float(efficiency_score)

        # Kesfif bilefleni
        if "exploration" in self.config.objectives:
            exploration_score = ctx.get("exploration", 0.0)
            components["exploration"] = float(exploration_score)

        # Basari orani bilefleni
        if "success_rate" in self.config.objectives:
            components["success_rate"] = 1.0 if task_result.success else 0.0

        # Agirlikli toplam
        total = 0.0
        for key, weight in self.config.objectives.items():
            if key in components:
                total += weight * components[key]
            elif key == "success_rate":
                total += weight * base_reward

        # Base odulu agirliksiz ekle (hedef tabanli degil)
        if "base" not in self.config.objectives:
            total += base_reward

        self._episode_count += 1
        self._total_reward += total

        return RewardSignal(
            value=total,
            components=components,
            shaped_value=total,
            intrinsic_bonus=0.0,
        )

    def shape_reward(
        self,
        current_reward: float,
        current_state: dict[str, Any],
        next_state: dict[str, Any],
        gamma: float | None = None,
    ) -> float:
        """Potansiyel tabanli odul sekillendirme.

        F = gamma * phi(s') - phi(s)
        Toplam odul = r + F

        Args:
            current_reward: Mevcut odul.
            current_state: Mevcut durum.
            next_state: Sonraki durum.
            gamma: Iskonto faktoru (None ise config'den).

        Returns:
            Sekillenmis odul.
        """
        g = gamma if gamma is not None else self.config.shaping_gamma
        phi_current = self._state_potential(current_state)
        phi_next = self._state_potential(next_state)
        shaping = g * phi_next - phi_current
        return current_reward + shaping

    def intrinsic_motivation(
        self,
        state: dict[str, Any],
        visit_counts: dict[str, int],
    ) -> float:
        """Merak tabanli icselfif motivasyon.

        bonus = beta / sqrt(count + 1)

        Args:
            state: Mevcut durum.
            visit_counts: Durum ziyaret sayilari.

        Returns:
            Merak bonusu.
        """
        state_key = str(sorted(state.items()))
        count = visit_counts.get(state_key, 0)
        bonus = self.config.curiosity_weight / math.sqrt(count + 1)
        return bonus

    def _state_potential(self, state: dict[str, Any]) -> float:
        """Durum potansiyel fonksiyonu.

        Durumdaki sayisal degerlerin toplamini dondurur.

        Args:
            state: Durum sozlugu.

        Returns:
            Potansiyel degeri.
        """
        total = 0.0
        for value in state.values():
            if isinstance(value, (int, float)):
                total += float(value)
        return total

    def update_objectives(self, objectives: dict[str, float]) -> None:
        """Hedef agirliklarini gunceller.

        Args:
            objectives: Yeni hedef agirliklari.
        """
        self.config.objectives.update(objectives)
        logger.info("Odul hedefleri guncellendi: %s", objectives)

    def get_stats(self) -> dict[str, Any]:
        """Odul istatistiklerini dondurur."""
        avg = self._total_reward / self._episode_count if self._episode_count > 0 else 0.0
        return {
            "episode_count": self._episode_count,
            "total_reward": self._total_reward,
            "avg_reward": avg,
        }
