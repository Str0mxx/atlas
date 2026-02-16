"""ATLAS Etki Ölçer modülü.

Önce/sonra analizi, artış hesaplama,
istatistiksel anlamlılık, ROI ölçümü,
atfetme modellemesi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ImpactMeasurer:
    """Etki ölçer.

    Değişikliklerin etkisini ölçer.

    Attributes:
        _measurements: Ölçüm kayıtları.
        _baselines: Temel değerler.
    """

    def __init__(self) -> None:
        """Ölçeri başlatır."""
        self._measurements: list[
            dict[str, Any]
        ] = []
        self._baselines: dict[
            str, float
        ] = {}
        self._counter = 0
        self._stats = {
            "measurements_taken": 0,
            "significant_results": 0,
        }

        logger.info(
            "ImpactMeasurer baslatildi",
        )

    def set_baseline(
        self,
        metric: str,
        value: float,
    ) -> dict[str, Any]:
        """Temel değer belirler.

        Args:
            metric: Metrik adı.
            value: Değer.

        Returns:
            Temel bilgisi.
        """
        self._baselines[metric] = value

        return {
            "metric": metric,
            "baseline": value,
            "set": True,
        }

    def analyze_before_after(
        self,
        metric: str,
        before: float,
        after: float,
    ) -> dict[str, Any]:
        """Önce/sonra analizi yapar.

        Args:
            metric: Metrik.
            before: Önceki değer.
            after: Sonraki değer.

        Returns:
            Analiz bilgisi.
        """
        change = round(after - before, 2)
        change_pct = round(
            change / before * 100, 1,
        ) if before != 0 else 0.0

        direction = (
            "improved" if change > 0
            else "declined" if change < 0
            else "unchanged"
        )

        self._measurements.append({
            "metric": metric,
            "before": before,
            "after": after,
            "change": change,
            "timestamp": time.time(),
        })
        self._stats[
            "measurements_taken"
        ] += 1

        return {
            "metric": metric,
            "before": before,
            "after": after,
            "change": change,
            "change_pct": change_pct,
            "direction": direction,
            "analyzed": True,
        }

    def calculate_lift(
        self,
        control: float,
        treatment: float,
    ) -> dict[str, Any]:
        """Artış hesaplar.

        Args:
            control: Kontrol değeri.
            treatment: Uygulama değeri.

        Returns:
            Artış bilgisi.
        """
        if control == 0:
            return {
                "lift": 0.0,
                "calculated": False,
            }

        lift = round(
            (treatment - control)
            / control * 100,
            1,
        )
        absolute_lift = round(
            treatment - control, 2,
        )

        significance = (
            "high" if abs(lift) >= 10
            else "medium" if abs(lift) >= 5
            else "low"
        )

        return {
            "control": control,
            "treatment": treatment,
            "lift_pct": lift,
            "absolute_lift": absolute_lift,
            "significance": significance,
            "calculated": True,
        }

    def check_statistical_significance(
        self,
        sample_a: list[float]
        | None = None,
        sample_b: list[float]
        | None = None,
        confidence: float = 0.95,
    ) -> dict[str, Any]:
        """İstatistiksel anlamlılık kontrol.

        Args:
            sample_a: Örnek A.
            sample_b: Örnek B.
            confidence: Güven seviyesi.

        Returns:
            Anlamlılık bilgisi.
        """
        sample_a = sample_a or []
        sample_b = sample_b or []

        if (
            len(sample_a) < 2
            or len(sample_b) < 2
        ):
            return {
                "significant": False,
                "reason": "Insufficient data",
            }

        mean_a = sum(sample_a) / len(
            sample_a,
        )
        mean_b = sum(sample_b) / len(
            sample_b,
        )

        var_a = sum(
            (x - mean_a) ** 2
            for x in sample_a
        ) / len(sample_a)
        var_b = sum(
            (x - mean_b) ** 2
            for x in sample_b
        ) / len(sample_b)

        se = (
            var_a / len(sample_a)
            + var_b / len(sample_b)
        ) ** 0.5

        if se == 0:
            t_stat = 0.0
        else:
            t_stat = abs(
                mean_a - mean_b,
            ) / se

        # Basit eşik
        critical = (
            2.576 if confidence >= 0.99
            else 1.96 if confidence >= 0.95
            else 1.645
        )
        is_significant = t_stat >= critical

        if is_significant:
            self._stats[
                "significant_results"
            ] += 1

        return {
            "mean_a": round(mean_a, 2),
            "mean_b": round(mean_b, 2),
            "t_statistic": round(
                t_stat, 3,
            ),
            "critical_value": critical,
            "significant": is_significant,
            "confidence": confidence,
        }

    def measure_roi(
        self,
        cost: float,
        benefit: float,
    ) -> dict[str, Any]:
        """ROI ölçer.

        Args:
            cost: Maliyet.
            benefit: Fayda.

        Returns:
            ROI bilgisi.
        """
        if cost <= 0:
            return {
                "roi": 0.0,
                "calculated": False,
            }

        roi = round(
            (benefit - cost) / cost * 100,
            1,
        )
        net = round(benefit - cost, 2)
        profitable = benefit > cost

        level = (
            "excellent" if roi >= 200
            else "good" if roi >= 100
            else "acceptable" if roi >= 0
            else "negative"
        )

        return {
            "cost": cost,
            "benefit": benefit,
            "net": net,
            "roi_pct": roi,
            "level": level,
            "profitable": profitable,
            "calculated": True,
        }

    def model_attribution(
        self,
        total_impact: float,
        factors: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Atfetme modelleme yapar.

        Args:
            total_impact: Toplam etki.
            factors: Faktörler ve ağırlıkları.

        Returns:
            Atfetme bilgisi.
        """
        factors = factors or {}

        if not factors:
            return {
                "attributions": [],
                "modeled": False,
            }

        total_weight = sum(
            factors.values(),
        )
        attributions = []

        for factor, weight in (
            factors.items()
        ):
            share = (
                round(
                    weight / total_weight,
                    3,
                )
                if total_weight > 0
                else 0.0
            )
            attributed = round(
                total_impact * share, 2,
            )
            attributions.append({
                "factor": factor,
                "share": share,
                "attributed_impact": (
                    attributed
                ),
            })

        return {
            "total_impact": total_impact,
            "attributions": attributions,
            "factor_count": len(
                attributions,
            ),
            "modeled": True,
        }

    @property
    def measurement_count(self) -> int:
        """Ölçüm sayısı."""
        return self._stats[
            "measurements_taken"
        ]

    @property
    def significant_count(self) -> int:
        """Anlamlı sonuç sayısı."""
        return self._stats[
            "significant_results"
        ]
