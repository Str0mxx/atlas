"""ATLAS adaptif ogrenme modulu.

Online ogrenme, konsept drift algilama ve strateji degistirme.
"""

import logging
import math
from typing import Any

import numpy as np
from scipy import stats

from app.models.learning import AdaptationState, DriftDetection, DriftType

logger = logging.getLogger("atlas.learning.adaptation")


class AdaptiveAgent:
    """Adaptif strateji yonetimi.

    Konsept drift algilama ve dinamik strateji secimi ile
    degiflen kosullara uyum saglar.

    Attributes:
        strategies: Strateji listesi.
        window_size: Kayan pencere boyutu.
        drift_threshold: Drift algilama esigi (p-value).
    """

    def __init__(
        self,
        strategies: list[str],
        window_size: int = 50,
        drift_threshold: float = 0.05,
    ) -> None:
        """AdaptiveAgent'i baslatir.

        Args:
            strategies: Kullanilabilir strateji adlari.
            window_size: Drift algilama pencere boyutu.
            drift_threshold: Drift icin p-value esigi.
        """
        if not strategies:
            raise ValueError("En az bir strateji gereklidir")

        self.strategies = list(strategies)
        self.window_size = window_size
        self.drift_threshold = drift_threshold

        self._current_strategy = strategies[0]
        self._performance: dict[str, list[float]] = {s: [] for s in strategies}
        self._switch_count = 0
        self._drift_history: list[DriftDetection] = []

        # UCB icin sayaclar
        self._strategy_counts: dict[str, int] = {s: 0 for s in strategies}
        self._total_count = 0

        logger.info(
            "AdaptiveAgent olusturuldu (%d strateji, pencere=%d)",
            len(strategies), window_size,
        )

    def record_outcome(self, strategy: str, reward: float) -> None:
        """Strateji sonucunu kaydeder.

        Args:
            strategy: Kullanilan strateji.
            reward: Alinan odul.
        """
        if strategy not in self._performance:
            self._performance[strategy] = []
        self._performance[strategy].append(reward)
        self._strategy_counts[strategy] = self._strategy_counts.get(strategy, 0) + 1
        self._total_count += 1

    def detect_drift(self, strategy: str | None = None) -> DriftDetection:
        """Konsept drift algilar.

        Kayan pencere ortalamasi ile referans ortalamasi arasinda
        istatistiksel fark olup olmadigini kontrol eder.

        Args:
            strategy: Kontrol edilecek strateji (None ise mevcut).

        Returns:
            Drift algilama sonucu.
        """
        s = strategy or self._current_strategy
        history = self._performance.get(s, [])

        if len(history) < self.window_size * 2:
            return DriftDetection(
                detected=False,
                window_mean=float(np.mean(history)) if history else 0.0,
                reference_mean=float(np.mean(history)) if history else 0.0,
                p_value=1.0,
            )

        # Referans pencere (ilk yari) vs guncel pencere (son window_size)
        reference = history[:-self.window_size]
        window = history[-self.window_size:]

        ref_mean = float(np.mean(reference))
        win_mean = float(np.mean(window))

        # Welch's t-test
        t_stat, p_value = stats.ttest_ind(reference, window, equal_var=False)
        p_value = float(p_value)

        detected = p_value < self.drift_threshold
        drift_type = None

        if detected:
            diff_ratio = abs(win_mean - ref_mean) / (abs(ref_mean) + 1e-10)
            if diff_ratio > 0.5:
                drift_type = DriftType.SUDDEN
            elif diff_ratio > 0.2:
                drift_type = DriftType.GRADUAL
            else:
                drift_type = DriftType.INCREMENTAL

        result = DriftDetection(
            detected=detected,
            drift_type=drift_type,
            confidence=1.0 - p_value,
            window_mean=win_mean,
            reference_mean=ref_mean,
            p_value=p_value,
        )

        if detected:
            self._drift_history.append(result)
            logger.warning(
                "Drift algilandi: strateji=%s, tip=%s, p=%.4f",
                s, drift_type, p_value,
            )

        return result

    def select_strategy(self) -> str:
        """En iyi stratejiyi secer.

        Ortalama odul + UCB kesfif bonusu ile secim yapar.

        Returns:
            Secilen strateji adi.
        """
        if self._total_count == 0:
            return self.strategies[0]

        best_strategy = self.strategies[0]
        best_score = float("-inf")

        for s in self.strategies:
            history = self._performance.get(s, [])
            count = self._strategy_counts.get(s, 0)

            if count == 0:
                return s  # Denenmemis strateji

            avg = float(np.mean(history)) if history else 0.0

            # UCB kesfif bonusu
            bonus = math.sqrt(2 * math.log(self._total_count) / count)
            score = avg + bonus

            if score > best_score:
                best_score = score
                best_strategy = s

        return best_strategy

    def switch_strategy(self, new_strategy: str) -> None:
        """Strateji degistirir.

        Args:
            new_strategy: Yeni strateji.
        """
        if new_strategy not in self.strategies:
            logger.warning("Bilinmeyen strateji: %s", new_strategy)
            return

        if new_strategy != self._current_strategy:
            old = self._current_strategy
            self._current_strategy = new_strategy
            self._switch_count += 1
            logger.info("Strateji degistirildi: %s -> %s", old, new_strategy)

    def adapt(self) -> str:
        """Adaptasyon dongusunu calistirir.

        1. Drift kontrol
        2. Strateji sec
        3. Gerekirse degistir

        Returns:
            Mevcut/yeni strateji.
        """
        # Drift kontrol
        drift = self.detect_drift()
        if drift.detected:
            logger.info("Drift algilandi, strateji yeniden seciliyor")

        # En iyi stratejiyi sec
        best = self.select_strategy()

        # Gerekirse degistir
        if best != self._current_strategy:
            if drift.detected or self._should_switch(best):
                self.switch_strategy(best)

        return self._current_strategy

    def _should_switch(self, candidate: str) -> bool:
        """Strateji degifltirmenin gerekip gerekmmedigini degerlendirir.

        Args:
            candidate: Aday strateji.

        Returns:
            True ise degistirmeli.
        """
        current_history = self._performance.get(self._current_strategy, [])
        candidate_history = self._performance.get(candidate, [])

        if not current_history or not candidate_history:
            return True

        # Son penceredeki ortalamalar
        n = min(self.window_size, len(current_history), len(candidate_history))
        current_avg = float(np.mean(current_history[-n:]))
        candidate_avg = float(np.mean(candidate_history[-n:]))

        # Aday belirgin sekilde daha iyiyse degistir
        return candidate_avg > current_avg * 1.1

    def get_state(self) -> AdaptationState:
        """Adaptasyon durumunu dondurur."""
        strategy_scores: dict[str, float] = {}
        for s in self.strategies:
            history = self._performance.get(s, [])
            strategy_scores[s] = float(np.mean(history)) if history else 0.0

        all_rewards: list[float] = []
        for rewards in self._performance.values():
            all_rewards.extend(rewards)

        return AdaptationState(
            current_strategy=self._current_strategy,
            strategies=strategy_scores,
            switch_count=self._switch_count,
            performance_history=all_rewards[-100:],
            drift_detections=self._drift_history[-10:],
        )
