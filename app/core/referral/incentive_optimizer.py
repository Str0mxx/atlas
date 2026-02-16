"""ATLAS Teşvik Optimizasyonu.

Teşvik testi, optimal ödüller, zamanlama,
segment hedefleme ve ROI maksimizasyonu.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class IncentiveOptimizer:
    """Teşvik optimizasyonu.

    Referans teşviklerini test eder,
    optimize eder ve ROI'yi maksimize eder.

    Attributes:
        _tests: Test kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Optimizasyonu başlatır."""
        self._tests: dict[str, dict] = {}
        self._stats = {
            "tests_run": 0,
            "optimizations_done": 0,
        }
        logger.info(
            "IncentiveOptimizer baslatildi",
        )

    @property
    def test_count(self) -> int:
        """Çalıştırılan test sayısı."""
        return self._stats["tests_run"]

    @property
    def optimization_count(self) -> int:
        """Yapılan optimizasyon sayısı."""
        return self._stats[
            "optimizations_done"
        ]

    def test_incentive(
        self,
        test_name: str,
        variant_a: float = 10.0,
        variant_b: float = 20.0,
        sample_size: int = 100,
    ) -> dict[str, Any]:
        """Teşvik testi yapar.

        Args:
            test_name: Test adı.
            variant_a: A varyant değeri.
            variant_b: B varyant değeri.
            sample_size: Örneklem boyutu.

        Returns:
            Test bilgisi.
        """
        tid = f"test_{len(self._tests)}"
        self._tests[tid] = {
            "name": test_name,
            "variant_a": variant_a,
            "variant_b": variant_b,
        }
        self._stats["tests_run"] += 1

        winner = (
            "a"
            if variant_a <= variant_b
            else "b"
        )

        return {
            "test_id": tid,
            "test_name": test_name,
            "winner": winner,
            "sample_size": sample_size,
            "tested": True,
        }

    def find_optimal_reward(
        self,
        min_reward: float = 5.0,
        max_reward: float = 50.0,
        conversion_rates: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Optimal ödül bulur.

        Args:
            min_reward: Minimum ödül.
            max_reward: Maksimum ödül.
            conversion_rates: Dönüşüm oranları.

        Returns:
            Optimal ödül bilgisi.
        """
        if conversion_rates is None:
            conversion_rates = []

        if conversion_rates:
            best_idx = conversion_rates.index(
                max(conversion_rates),
            )
            step = (
                (max_reward - min_reward)
                / max(
                    len(conversion_rates) - 1,
                    1,
                )
            )
            optimal = round(
                min_reward + best_idx * step,
                2,
            )
        else:
            optimal = round(
                (min_reward + max_reward) / 2,
                2,
            )

        self._stats[
            "optimizations_done"
        ] += 1

        return {
            "optimal_reward": optimal,
            "min_reward": min_reward,
            "max_reward": max_reward,
            "found": True,
        }

    def optimize_timing(
        self,
        event: str = "signup",
        delay_hours: list[int]
        | None = None,
    ) -> dict[str, Any]:
        """Zamanlama optimizasyonu yapar.

        Args:
            event: Tetikleyici olay.
            delay_hours: Gecikme seçenekleri.

        Returns:
            Zamanlama bilgisi.
        """
        if delay_hours is None:
            delay_hours = [0, 1, 24, 48]

        optimal = delay_hours[0]

        return {
            "event": event,
            "optimal_delay_hours": optimal,
            "options_tested": len(
                delay_hours,
            ),
            "optimized": True,
        }

    def target_segment(
        self,
        segment: str = "all",
        reward_amount: float = 10.0,
        expected_conv: float = 0.05,
    ) -> dict[str, Any]:
        """Segment hedefleme yapar.

        Args:
            segment: Hedef segment.
            reward_amount: Ödül miktarı.
            expected_conv: Beklenen dönüşüm.

        Returns:
            Hedefleme bilgisi.
        """
        cpa = (
            reward_amount / expected_conv
            if expected_conv > 0
            else 0.0
        )

        return {
            "segment": segment,
            "reward_amount": reward_amount,
            "expected_conversion": (
                expected_conv
            ),
            "cost_per_acquisition": round(
                cpa, 2,
            ),
            "targeted": True,
        }

    def maximize_roi(
        self,
        total_budget: float = 1000.0,
        reward_per_referral: float = 10.0,
        avg_customer_value: float = 100.0,
    ) -> dict[str, Any]:
        """ROI maksimize eder.

        Args:
            total_budget: Toplam bütçe.
            reward_per_referral: Referans ödülü.
            avg_customer_value: Ortalama müşteri
                değeri.

        Returns:
            ROI bilgisi.
        """
        max_referrals = int(
            total_budget / reward_per_referral,
        ) if reward_per_referral > 0 else 0

        expected_revenue = (
            max_referrals
            * avg_customer_value
        )
        roi = (
            (expected_revenue - total_budget)
            / total_budget
            * 100
            if total_budget > 0
            else 0.0
        )

        return {
            "total_budget": total_budget,
            "max_referrals": max_referrals,
            "expected_revenue": (
                expected_revenue
            ),
            "roi_pct": round(roi, 1),
            "maximized": True,
        }
