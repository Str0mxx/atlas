"""ATLAS Deger Tahmincisi modulu.

Beklenen fayda hesaplama, maliyet tahmini,
ROI projeksiyonu, risk ayarli deger ve
zaman degeri degerlendirmesi.
"""

import logging
import math
from typing import Any

from app.models.goal_pursuit import ValueEstimate

logger = logging.getLogger(__name__)


class ValueEstimator:
    """Deger tahmincisi.

    Hedeflerin beklenen degerini, maliyetini
    ve yatirim getirisini hesaplar.

    Attributes:
        _estimates: Deger tahminleri.
        _discount_rate: Iskonto orani.
        _risk_factors: Risk faktorleri.
        _benchmarks: Karsilastirma degerleri.
    """

    def __init__(
        self,
        discount_rate: float = 0.05,
    ) -> None:
        """Deger tahmincisini baslatir.

        Args:
            discount_rate: Yillik iskonto orani.
        """
        self._estimates: dict[str, ValueEstimate] = {}
        self._discount_rate = discount_rate
        self._risk_factors: dict[str, float] = {}
        self._benchmarks: dict[str, dict[str, float]] = {}
        self._history: list[dict[str, Any]] = []

        logger.info(
            "ValueEstimator baslatildi (discount=%.2f)",
            discount_rate,
        )

    def estimate_benefit(
        self,
        goal_id: str,
        revenue_impact: float = 0.0,
        cost_saving: float = 0.0,
        efficiency_gain: float = 0.0,
        strategic_value: float = 0.0,
    ) -> float:
        """Beklenen faydayi hesaplar.

        Args:
            goal_id: Hedef ID.
            revenue_impact: Gelir etkisi.
            cost_saving: Maliyet tasarrufu.
            efficiency_gain: Verimlilik kazanimi.
            strategic_value: Stratejik deger.

        Returns:
            Toplam beklenen fayda.
        """
        total = revenue_impact + cost_saving + efficiency_gain + strategic_value

        estimate = self._get_or_create(goal_id)
        estimate.expected_benefit = total
        estimate.factors["revenue_impact"] = revenue_impact
        estimate.factors["cost_saving"] = cost_saving
        estimate.factors["efficiency_gain"] = efficiency_gain
        estimate.factors["strategic_value"] = strategic_value

        return total

    def estimate_cost(
        self,
        goal_id: str,
        direct_cost: float = 0.0,
        opportunity_cost: float = 0.0,
        resource_cost: float = 0.0,
        risk_cost: float = 0.0,
    ) -> float:
        """Maliyet tahmini yapar.

        Args:
            goal_id: Hedef ID.
            direct_cost: Dogrudan maliyet.
            opportunity_cost: Firsat maliyeti.
            resource_cost: Kaynak maliyeti.
            risk_cost: Risk maliyeti.

        Returns:
            Toplam tahmini maliyet.
        """
        total = direct_cost + opportunity_cost + resource_cost + risk_cost

        estimate = self._get_or_create(goal_id)
        estimate.estimated_cost = total
        estimate.factors["direct_cost"] = direct_cost
        estimate.factors["opportunity_cost"] = opportunity_cost
        estimate.factors["resource_cost"] = resource_cost
        estimate.factors["risk_cost"] = risk_cost

        return total

    def calculate_roi(self, goal_id: str) -> float:
        """ROI projeksiyonu hesaplar.

        Args:
            goal_id: Hedef ID.

        Returns:
            ROI orani.
        """
        estimate = self._estimates.get(goal_id)
        if not estimate or estimate.estimated_cost == 0:
            return 0.0

        roi = (
            (estimate.expected_benefit - estimate.estimated_cost)
            / estimate.estimated_cost
        )
        estimate.roi_projection = round(roi, 4)
        return estimate.roi_projection

    def calculate_risk_adjusted_value(
        self,
        goal_id: str,
        success_probability: float = 0.5,
    ) -> float:
        """Risk ayarli degeri hesaplar.

        Args:
            goal_id: Hedef ID.
            success_probability: Basari olasiligi (0-1).

        Returns:
            Risk ayarli deger.
        """
        estimate = self._estimates.get(goal_id)
        if not estimate:
            return 0.0

        prob = max(0.0, min(1.0, success_probability))
        risk_adjusted = (
            estimate.expected_benefit * prob
            - estimate.estimated_cost * (1 - prob)
        )
        estimate.risk_adjusted_value = round(risk_adjusted, 2)
        estimate.confidence = prob

        return estimate.risk_adjusted_value

    def calculate_time_value(
        self,
        goal_id: str,
        time_horizon_days: int = 30,
    ) -> float:
        """Zaman degerini hesaplar (NPV).

        Args:
            goal_id: Hedef ID.
            time_horizon_days: Zaman ufku (gun).

        Returns:
            Net bugunku deger.
        """
        estimate = self._estimates.get(goal_id)
        if not estimate:
            return 0.0

        estimate.time_horizon_days = time_horizon_days
        years = time_horizon_days / 365.0

        # NPV hesaplama
        if years > 0 and self._discount_rate > 0:
            discount_factor = 1 / math.pow(1 + self._discount_rate, years)
        else:
            discount_factor = 1.0

        npv = estimate.expected_benefit * discount_factor - estimate.estimated_cost
        return round(npv, 2)

    def compare_goals(
        self,
        goal_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Hedefleri degerlerine gore karsilastirir.

        Args:
            goal_ids: Hedef ID listesi.

        Returns:
            Sirali karsilastirma listesi.
        """
        comparisons = []
        for gid in goal_ids:
            estimate = self._estimates.get(gid)
            if estimate:
                comparisons.append({
                    "goal_id": gid,
                    "benefit": estimate.expected_benefit,
                    "cost": estimate.estimated_cost,
                    "roi": estimate.roi_projection,
                    "risk_adjusted": estimate.risk_adjusted_value,
                    "confidence": estimate.confidence,
                })

        return sorted(
            comparisons,
            key=lambda c: c["risk_adjusted"],
            reverse=True,
        )

    def set_risk_factor(
        self,
        factor_name: str,
        weight: float,
    ) -> None:
        """Risk faktoru ayarlar.

        Args:
            factor_name: Faktor adi.
            weight: Agirlik (0-1).
        """
        self._risk_factors[factor_name] = max(0.0, min(1.0, weight))

    def set_benchmark(
        self,
        category: str,
        benchmarks: dict[str, float],
    ) -> None:
        """Karsilastirma degerleri ayarlar.

        Args:
            category: Kategori.
            benchmarks: Degerler.
        """
        self._benchmarks[category] = benchmarks

    def get_estimate(self, goal_id: str) -> ValueEstimate | None:
        """Deger tahminini getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            ValueEstimate veya None.
        """
        return self._estimates.get(goal_id)

    def remove_estimate(self, goal_id: str) -> bool:
        """Deger tahminini kaldirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Basarili ise True.
        """
        if goal_id in self._estimates:
            del self._estimates[goal_id]
            return True
        return False

    def _get_or_create(self, goal_id: str) -> ValueEstimate:
        """Var olan veya yeni tahmin getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            ValueEstimate nesnesi.
        """
        if goal_id not in self._estimates:
            self._estimates[goal_id] = ValueEstimate(goal_id=goal_id)
        return self._estimates[goal_id]

    @property
    def total_estimates(self) -> int:
        """Toplam tahmin sayisi."""
        return len(self._estimates)

    @property
    def discount_rate(self) -> float:
        """Iskonto orani."""
        return self._discount_rate
