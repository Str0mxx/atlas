"""ATLAS A/B Deney Tasarımcısı modülü.

Hipotez tanımlama, varyant oluşturma,
örneklem boyutu, süre hesaplama,
başarı metrikleri.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class ABExperimentDesigner:
    """A/B deney tasarımcısı.

    Deneyleri tasarlar ve yapılandırır.

    Attributes:
        _experiments: Deney kayıtları.
        _hypotheses: Hipotez kayıtları.
    """

    def __init__(self) -> None:
        """Tasarımcıyı başlatır."""
        self._experiments: dict[
            str, dict[str, Any]
        ] = {}
        self._hypotheses: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "experiments_designed": 0,
            "hypotheses_defined": 0,
        }

        logger.info(
            "ABExperimentDesigner "
            "baslatildi",
        )

    def define_hypothesis(
        self,
        experiment_id: str,
        null_hypothesis: str = "",
        alt_hypothesis: str = "",
        metric: str = "conversion",
        expected_lift: float = 0.05,
    ) -> dict[str, Any]:
        """Hipotez tanımlar.

        Args:
            experiment_id: Deney kimliği.
            null_hypothesis: Boş hipotez.
            alt_hypothesis: Alternatif hipotez.
            metric: Başarı metriği.
            expected_lift: Beklenen artış.

        Returns:
            Tanımlama bilgisi.
        """
        self._hypotheses[
            experiment_id
        ] = {
            "experiment_id": experiment_id,
            "null_hypothesis": (
                null_hypothesis
                or "No difference"
            ),
            "alt_hypothesis": (
                alt_hypothesis
                or "Treatment is better"
            ),
            "metric": metric,
            "expected_lift": expected_lift,
            "timestamp": time.time(),
        }

        self._stats[
            "hypotheses_defined"
        ] += 1

        return {
            "experiment_id": experiment_id,
            "metric": metric,
            "expected_lift": expected_lift,
            "defined": True,
        }

    def create_variants(
        self,
        experiment_id: str,
        variant_count: int = 2,
        names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Varyantlar oluşturur.

        Args:
            experiment_id: Deney kimliği.
            variant_count: Varyant sayısı.
            names: Varyant adları.

        Returns:
            Oluşturma bilgisi.
        """
        names = names or []
        variants = []

        for i in range(variant_count):
            name = (
                names[i]
                if i < len(names)
                else (
                    "control"
                    if i == 0
                    else f"treatment_{i}"
                )
            )
            vtype = (
                "control"
                if i == 0
                else "treatment"
            )
            pct = round(
                100.0 / variant_count, 1,
            )

            variants.append({
                "name": name,
                "type": vtype,
                "traffic_pct": pct,
            })

        if experiment_id not in (
            self._experiments
        ):
            self._experiments[
                experiment_id
            ] = {}

        self._experiments[
            experiment_id
        ]["variants"] = variants

        return {
            "experiment_id": experiment_id,
            "variants": variants,
            "count": variant_count,
            "created": True,
        }

    def calculate_sample_size(
        self,
        baseline_rate: float = 0.10,
        min_detectable_effect: float = 0.02,
        confidence: float = 0.95,
        power: float = 0.80,
    ) -> dict[str, Any]:
        """Örneklem boyutu hesaplar.

        Args:
            baseline_rate: Taban oranı.
            min_detectable_effect: MDE.
            confidence: Güven düzeyi.
            power: İstatistiksel güç.

        Returns:
            Hesaplama bilgisi.
        """
        z_alpha = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
        }.get(confidence, 1.96)

        z_beta = {
            0.80: 0.842,
            0.90: 1.282,
            0.95: 1.645,
        }.get(power, 0.842)

        p1 = baseline_rate
        p2 = baseline_rate + (
            min_detectable_effect
        )
        p_bar = (p1 + p2) / 2

        numerator = (
            z_alpha
            * math.sqrt(
                2 * p_bar * (1 - p_bar),
            )
            + z_beta
            * math.sqrt(
                p1 * (1 - p1)
                + p2 * (1 - p2),
            )
        ) ** 2
        denominator = (
            (p2 - p1) ** 2
        )

        n = math.ceil(
            numerator
            / max(denominator, 0.0001),
        )

        return {
            "sample_size_per_variant": n,
            "total_sample_size": n * 2,
            "baseline_rate": baseline_rate,
            "mde": min_detectable_effect,
            "confidence": confidence,
            "power": power,
            "calculated": True,
        }

    def calculate_duration(
        self,
        sample_size: int = 1000,
        daily_traffic: int = 100,
        variant_count: int = 2,
    ) -> dict[str, Any]:
        """Süre hesaplar.

        Args:
            sample_size: Örneklem boyutu.
            daily_traffic: Günlük trafik.
            variant_count: Varyant sayısı.

        Returns:
            Hesaplama bilgisi.
        """
        total_needed = (
            sample_size * variant_count
        )
        days = math.ceil(
            total_needed
            / max(daily_traffic, 1),
        )

        return {
            "duration_days": days,
            "total_needed": total_needed,
            "daily_traffic": daily_traffic,
            "calculated": True,
        }

    def define_success_metrics(
        self,
        experiment_id: str,
        primary_metric: str = "conversion",
        secondary_metrics: list[str]
        | None = None,
        guardrails: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Başarı metrikleri tanımlar.

        Args:
            experiment_id: Deney kimliği.
            primary_metric: Birincil metrik.
            secondary_metrics: İkincil metrikler.
            guardrails: Koruma metrikleri.

        Returns:
            Tanımlama bilgisi.
        """
        secondary_metrics = (
            secondary_metrics or []
        )
        guardrails = guardrails or []

        if experiment_id not in (
            self._experiments
        ):
            self._experiments[
                experiment_id
            ] = {}

        self._experiments[
            experiment_id
        ]["metrics"] = {
            "primary": primary_metric,
            "secondary": secondary_metrics,
            "guardrails": guardrails,
        }

        self._stats[
            "experiments_designed"
        ] += 1

        return {
            "experiment_id": experiment_id,
            "primary": primary_metric,
            "secondary_count": len(
                secondary_metrics,
            ),
            "guardrail_count": len(
                guardrails,
            ),
            "defined": True,
        }

    @property
    def experiment_count(self) -> int:
        """Deney sayısı."""
        return self._stats[
            "experiments_designed"
        ]

    @property
    def hypothesis_count(self) -> int:
        """Hipotez sayısı."""
        return self._stats[
            "hypotheses_defined"
        ]
