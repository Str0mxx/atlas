"""ATLAS Ne Olur Analizi modulu.

Parametre varyasyonu, hassasiyet analizi,
esik degeri tespiti, devrilme noktasi ve optimizasyon onerileri.
"""

import logging
from typing import Any

from app.models.simulation import (
    SensitivityLevel,
    WhatIfResult,
)

logger = logging.getLogger(__name__)


class WhatIfEngine:
    """Ne olur analiz sistemi.

    Parametre degisikliklerinin sonuclara etkisini
    analiz eder ve optimizasyon onerileri sunar.

    Attributes:
        _results: Analiz sonuclari.
        _thresholds: Tespit edilen esikler.
    """

    def __init__(self) -> None:
        """Ne olur motorunu baslatir."""
        self._results: list[WhatIfResult] = []
        self._thresholds: dict[str, float] = {}

        logger.info("WhatIfEngine baslatildi")

    def analyze_parameter(
        self,
        parameter: str,
        original_value: float,
        varied_value: float,
        outcome_function: Any | None = None,
    ) -> WhatIfResult:
        """Parametre degisikligini analiz eder.

        Args:
            parameter: Parametre adi.
            original_value: Orijinal deger.
            varied_value: Degistirilmis deger.
            outcome_function: Sonuc hesaplama fonksiyonu.

        Returns:
            WhatIfResult nesnesi.
        """
        if outcome_function and callable(outcome_function):
            original_outcome = outcome_function(original_value)
            varied_outcome = outcome_function(varied_value)
            outcome_change = varied_outcome - original_outcome
        else:
            # Varsayilan: dogrusal etki
            if original_value != 0:
                pct_change = (varied_value - original_value) / abs(original_value)
            else:
                pct_change = varied_value
            outcome_change = pct_change

        sensitivity = self._classify_sensitivity(
            original_value, varied_value, outcome_change
        )

        threshold = self._detect_threshold(parameter, original_value, varied_value, outcome_change)
        tipping = abs(outcome_change) > 0.5

        recommendation = self._generate_recommendation(
            parameter, outcome_change, sensitivity, tipping
        )

        result = WhatIfResult(
            parameter=parameter,
            original_value=original_value,
            varied_value=varied_value,
            outcome_change=round(outcome_change, 4),
            sensitivity=sensitivity,
            threshold=threshold,
            tipping_point=tipping,
            recommendation=recommendation,
        )

        self._results.append(result)
        return result

    def sensitivity_analysis(
        self,
        parameter: str,
        base_value: float,
        variations: list[float] | None = None,
        outcome_function: Any | None = None,
    ) -> list[WhatIfResult]:
        """Hassasiyet analizi yapar.

        Args:
            parameter: Parametre adi.
            base_value: Temel deger.
            variations: Varyasyon listesi (yuzde).
            outcome_function: Sonuc fonksiyonu.

        Returns:
            WhatIfResult listesi.
        """
        if variations is None:
            variations = [-0.5, -0.25, -0.1, 0.1, 0.25, 0.5]

        results: list[WhatIfResult] = []
        for pct in variations:
            varied = base_value * (1.0 + pct)
            result = self.analyze_parameter(
                parameter, base_value, varied, outcome_function
            )
            results.append(result)

        return results

    def find_threshold(
        self,
        parameter: str,
        base_value: float,
        target_outcome: float,
        outcome_function: Any,
        tolerance: float = 0.01,
        max_iterations: int = 50,
    ) -> float | None:
        """Esik deger bulur.

        Args:
            parameter: Parametre adi.
            base_value: Temel deger.
            target_outcome: Hedef sonuc.
            outcome_function: Sonuc fonksiyonu.
            tolerance: Tolerans.
            max_iterations: Maks iterasyon.

        Returns:
            Esik degeri veya None.
        """
        low = base_value * 0.01
        high = base_value * 10.0

        for _ in range(max_iterations):
            mid = (low + high) / 2
            result = outcome_function(mid)

            if abs(result - target_outcome) < tolerance:
                self._thresholds[parameter] = mid
                return round(mid, 4)

            if result < target_outcome:
                low = mid
            else:
                high = mid

        return None

    def detect_tipping_points(
        self,
        parameter: str,
        base_value: float,
        outcome_function: Any,
        steps: int = 20,
    ) -> list[dict[str, Any]]:
        """Devrilme noktalarini tespit eder.

        Args:
            parameter: Parametre adi.
            base_value: Temel deger.
            outcome_function: Sonuc fonksiyonu.
            steps: Adim sayisi.

        Returns:
            Devrilme noktasi listesi.
        """
        tipping_points: list[dict[str, Any]] = []
        step_size = base_value / steps if base_value != 0 else 0.1

        prev_value = base_value
        prev_outcome = outcome_function(base_value)

        for i in range(1, steps + 1):
            current_value = base_value + step_size * i
            current_outcome = outcome_function(current_value)

            if prev_outcome != 0:
                rate_of_change = abs(
                    (current_outcome - prev_outcome) / abs(prev_outcome)
                )
            else:
                rate_of_change = abs(current_outcome)

            if rate_of_change > 0.3:
                tipping_points.append({
                    "parameter": parameter,
                    "value": round(current_value, 4),
                    "outcome_before": round(prev_outcome, 4),
                    "outcome_after": round(current_outcome, 4),
                    "rate_of_change": round(rate_of_change, 4),
                })

            prev_value = current_value
            prev_outcome = current_outcome

        return tipping_points

    def optimize(
        self,
        parameters: dict[str, float],
        outcome_function: Any,
        direction: str = "maximize",
        step_size: float = 0.1,
        max_iterations: int = 100,
    ) -> dict[str, Any]:
        """Basit gradient-free optimizasyon yapar.

        Args:
            parameters: Parametre -> deger haritasi.
            outcome_function: Sonuc fonksiyonu.
            direction: maximize veya minimize.
            step_size: Adim boyutu.
            max_iterations: Maks iterasyon.

        Returns:
            Optimizasyon sonucu.
        """
        current = dict(parameters)
        current_outcome = outcome_function(current)
        best = dict(current)
        best_outcome = current_outcome

        for _ in range(max_iterations):
            improved = False
            for param in current:
                for delta in [step_size, -step_size]:
                    trial = dict(current)
                    trial[param] = trial[param] * (1.0 + delta)
                    trial_outcome = outcome_function(trial)

                    if direction == "maximize" and trial_outcome > best_outcome:
                        best = dict(trial)
                        best_outcome = trial_outcome
                        improved = True
                    elif direction == "minimize" and trial_outcome < best_outcome:
                        best = dict(trial)
                        best_outcome = trial_outcome
                        improved = True

            current = dict(best)
            if not improved:
                break

        return {
            "original_parameters": parameters,
            "optimized_parameters": {k: round(v, 4) for k, v in best.items()},
            "original_outcome": round(outcome_function(parameters), 4),
            "optimized_outcome": round(best_outcome, 4),
            "improvement": round(best_outcome - outcome_function(parameters), 4),
            "direction": direction,
        }

    def get_summary(self) -> dict[str, Any]:
        """Analiz ozetini getirir.

        Returns:
            Ozet sozlugu.
        """
        if not self._results:
            return {"total_analyses": 0}

        tipping_count = sum(1 for r in self._results if r.tipping_point)
        high_sens = sum(
            1 for r in self._results
            if r.sensitivity in (SensitivityLevel.HIGH_SENSITIVITY, SensitivityLevel.CRITICAL_SENSITIVITY)
        )

        parameters = set(r.parameter for r in self._results)

        return {
            "total_analyses": len(self._results),
            "unique_parameters": len(parameters),
            "tipping_points_found": tipping_count,
            "high_sensitivity_count": high_sens,
            "thresholds_detected": len(self._thresholds),
        }

    def _classify_sensitivity(
        self, original: float, varied: float, outcome_change: float
    ) -> SensitivityLevel:
        """Hassasiyet seviyesini siniflandirir."""
        if original != 0:
            input_change = abs((varied - original) / abs(original))
        else:
            input_change = abs(varied)

        if input_change == 0:
            return SensitivityLevel.INSENSITIVE

        elasticity = abs(outcome_change) / max(input_change, 0.001)

        if elasticity < 0.1:
            return SensitivityLevel.INSENSITIVE
        if elasticity < 0.5:
            return SensitivityLevel.LOW_SENSITIVITY
        if elasticity < 1.0:
            return SensitivityLevel.MODERATE
        if elasticity < 2.0:
            return SensitivityLevel.HIGH_SENSITIVITY
        return SensitivityLevel.CRITICAL_SENSITIVITY

    def _detect_threshold(
        self,
        parameter: str,
        original: float,
        varied: float,
        outcome_change: float,
    ) -> float | None:
        """Esik deger tespit eder."""
        if abs(outcome_change) > 0.3:
            threshold = (original + varied) / 2
            self._thresholds[parameter] = threshold
            return threshold
        return None

    def _generate_recommendation(
        self,
        parameter: str,
        outcome_change: float,
        sensitivity: SensitivityLevel,
        tipping: bool,
    ) -> str:
        """Optimizasyon onerisi uretir."""
        if tipping:
            return f"DIKKAT: {parameter} devrilme noktasina yakin, dikkatli ayarla"

        if sensitivity == SensitivityLevel.CRITICAL_SENSITIVITY:
            return f"KRITIK: {parameter} cok hassas, kucuk degisiklikler yapın"

        if sensitivity == SensitivityLevel.HIGH_SENSITIVITY:
            return f"{parameter} hassas parametre, yakin izleme gerekli"

        if outcome_change > 0:
            return f"{parameter} artisi olumlu etki yapar"
        if outcome_change < 0:
            return f"{parameter} artisi olumsuz etki yapar, dikkat"

        return f"{parameter} degisikligi minimal etki yapar"

    @property
    def result_count(self) -> int:
        """Sonuc sayisi."""
        return len(self._results)

    @property
    def threshold_count(self) -> int:
        """Tespit edilen esik sayisi."""
        return len(self._thresholds)
