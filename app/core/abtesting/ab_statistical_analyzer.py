"""ATLAS İstatistiksel Analizci modülü.

Anlamlılık testi, güven aralığı,
güç analizi, Bayesci analiz,
ardışık test.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class ABStatisticalAnalyzer:
    """İstatistiksel analizci.

    A/B test sonuçlarını analiz eder.

    Attributes:
        _analyses: Analiz kayıtları.
    """

    def __init__(self) -> None:
        """Analizciyi başlatır."""
        self._analyses: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "tests_performed": 0,
            "significant_results": 0,
        }

        logger.info(
            "ABStatisticalAnalyzer "
            "baslatildi",
        )

    def test_significance(
        self,
        control_conversions: int,
        control_total: int,
        treatment_conversions: int,
        treatment_total: int,
        confidence: float = 0.95,
    ) -> dict[str, Any]:
        """Anlamlılık testi yapar.

        Args:
            control_conversions: Kontrol dönüşüm.
            control_total: Kontrol toplam.
            treatment_conversions: Tedavi dönüşüm.
            treatment_total: Tedavi toplam.
            confidence: Güven düzeyi.

        Returns:
            Test bilgisi.
        """
        p_c = (
            control_conversions
            / max(control_total, 1)
        )
        p_t = (
            treatment_conversions
            / max(treatment_total, 1)
        )

        p_pool = (
            (
                control_conversions
                + treatment_conversions
            )
            / max(
                control_total
                + treatment_total,
                1,
            )
        )

        se = math.sqrt(
            p_pool * (1 - p_pool)
            * (
                1 / max(control_total, 1)
                + 1
                / max(treatment_total, 1)
            ),
        )

        z = (
            abs(p_t - p_c)
            / max(se, 0.0001)
        )

        z_critical = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
        }.get(confidence, 1.96)

        significant = z > z_critical
        p_value = max(
            0.001,
            round(
                2 * (1 - min(
                    0.5
                    + 0.5
                    * math.erf(
                        z / math.sqrt(2),
                    ),
                    0.9999,
                )),
                4,
            ),
        )

        if significant:
            self._stats[
                "significant_results"
            ] += 1

        self._stats[
            "tests_performed"
        ] += 1

        lift = round(
            (p_t - p_c)
            / max(p_c, 0.0001)
            * 100,
            2,
        )

        return {
            "control_rate": round(p_c, 4),
            "treatment_rate": round(
                p_t, 4,
            ),
            "z_score": round(z, 4),
            "p_value": p_value,
            "significant": significant,
            "lift_pct": lift,
            "confidence": confidence,
            "tested": True,
        }

    def confidence_interval(
        self,
        conversions: int,
        total: int,
        confidence: float = 0.95,
    ) -> dict[str, Any]:
        """Güven aralığı hesaplar.

        Args:
            conversions: Dönüşüm.
            total: Toplam.
            confidence: Güven düzeyi.

        Returns:
            Hesaplama bilgisi.
        """
        p = conversions / max(total, 1)

        z = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
        }.get(confidence, 1.96)

        se = math.sqrt(
            p * (1 - p)
            / max(total, 1),
        )
        margin = z * se

        return {
            "rate": round(p, 4),
            "lower": round(
                max(p - margin, 0), 4,
            ),
            "upper": round(
                min(p + margin, 1), 4,
            ),
            "margin": round(margin, 4),
            "confidence": confidence,
            "calculated": True,
        }

    def power_analysis(
        self,
        effect_size: float = 0.05,
        sample_size: int = 1000,
        alpha: float = 0.05,
    ) -> dict[str, Any]:
        """Güç analizi yapar.

        Args:
            effect_size: Etki boyutu.
            sample_size: Örneklem boyutu.
            alpha: Alfa değeri.

        Returns:
            Analiz bilgisi.
        """
        se = math.sqrt(
            2 * 0.5 * 0.5
            / max(sample_size, 1),
        )
        z_alpha = {
            0.01: 2.576,
            0.05: 1.96,
            0.10: 1.645,
        }.get(alpha, 1.96)

        z_beta = (
            effect_size
            / max(se, 0.0001)
            - z_alpha
        )

        power = min(
            0.5
            + 0.5
            * math.erf(
                z_beta / math.sqrt(2),
            ),
            0.999,
        )
        power = max(power, 0.01)

        return {
            "power": round(power, 3),
            "effect_size": effect_size,
            "sample_size": sample_size,
            "alpha": alpha,
            "adequate": power >= 0.80,
            "analyzed": True,
        }

    def bayesian_analysis(
        self,
        control_conversions: int,
        control_total: int,
        treatment_conversions: int,
        treatment_total: int,
        prior_alpha: float = 1.0,
        prior_beta: float = 1.0,
    ) -> dict[str, Any]:
        """Bayesci analiz yapar.

        Args:
            control_conversions: Kontrol dönüşüm.
            control_total: Kontrol toplam.
            treatment_conversions: Tedavi dönüşüm.
            treatment_total: Tedavi toplam.
            prior_alpha: Önsel alfa.
            prior_beta: Önsel beta.

        Returns:
            Analiz bilgisi.
        """
        a_c = (
            prior_alpha
            + control_conversions
        )
        b_c = (
            prior_beta
            + control_total
            - control_conversions
        )
        a_t = (
            prior_alpha
            + treatment_conversions
        )
        b_t = (
            prior_beta
            + treatment_total
            - treatment_conversions
        )

        mean_c = a_c / (a_c + b_c)
        mean_t = a_t / (a_t + b_t)

        prob_t_better = (
            0.5
            + 0.5
            * math.erf(
                (mean_t - mean_c)
                / max(
                    math.sqrt(
                        mean_c
                        * (1 - mean_c)
                        / max(
                            control_total,
                            1,
                        )
                        + mean_t
                        * (1 - mean_t)
                        / max(
                            treatment_total,
                            1,
                        ),
                    ),
                    0.0001,
                )
                / math.sqrt(2),
            )
        )

        return {
            "control_mean": round(
                mean_c, 4,
            ),
            "treatment_mean": round(
                mean_t, 4,
            ),
            "prob_treatment_better": round(
                prob_t_better, 4,
            ),
            "analyzed": True,
        }

    def sequential_test(
        self,
        observations: list[
            dict[str, Any]
        ],
        spending_func: str = "obrien_fleming",
        max_looks: int = 5,
    ) -> dict[str, Any]:
        """Ardışık test yapar.

        Args:
            observations: Gözlemler.
            spending_func: Harcama fonksiyonu.
            max_looks: Maks bakış.

        Returns:
            Test bilgisi.
        """
        current_look = min(
            len(observations), max_looks,
        )

        boundaries = {
            "obrien_fleming": [
                4.56, 3.23, 2.63,
                2.28, 2.04,
            ],
            "pocock": [
                2.41, 2.41, 2.41,
                2.41, 2.41,
            ],
        }
        bounds = boundaries.get(
            spending_func,
            boundaries["obrien_fleming"],
        )

        boundary = (
            bounds[current_look - 1]
            if current_look <= len(bounds)
            else bounds[-1]
        )

        if observations:
            last = observations[-1]
            z_score = last.get(
                "z_score", 0,
            )
        else:
            z_score = 0

        should_stop = (
            abs(z_score) > boundary
        )

        return {
            "current_look": current_look,
            "boundary": boundary,
            "z_score": z_score,
            "should_stop": should_stop,
            "spending_func": spending_func,
            "tested": True,
        }

    @property
    def test_count(self) -> int:
        """Test sayısı."""
        return self._stats[
            "tests_performed"
        ]

    @property
    def significant_count(self) -> int:
        """Anlamlı sonuç sayısı."""
        return self._stats[
            "significant_results"
        ]
