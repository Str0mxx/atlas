"""ATLAS Sure Tahmincisi modulu.

Gorev suresi tahmini, gecmis analizi,
guven araliklari, tampon hesaplama
ve gerceklerden ogrenme.
"""

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


class TimeEstimator:
    """Sure tahmincisi.

    Gorev surelerini tahmin eder ve
    gecmis verilerden ogrenir.

    Attributes:
        _estimates: Tahmin kayitlari.
        _actuals: Gercek sure kayitlari.
        _category_history: Kategori bazli gecmis.
    """

    def __init__(
        self,
        default_buffer: float = 0.2,
    ) -> None:
        """Sure tahmincisini baslatir.

        Args:
            default_buffer: Varsayilan tampon orani.
        """
        self._estimates: dict[str, dict[str, Any]] = {}
        self._actuals: dict[str, float] = {}
        self._category_history: dict[str, list[float]] = {}
        self._default_buffer = max(0.0, min(1.0, default_buffer))

        logger.info("TimeEstimator baslatildi")

    def estimate(
        self,
        task_id: str,
        category: str = "general",
        base_hours: float = 1.0,
    ) -> dict[str, Any]:
        """Sure tahmini yapar.

        Args:
            task_id: Gorev ID.
            category: Kategori.
            base_hours: Temel tahmin (saat).

        Returns:
            Tahmin sonucu.
        """
        history = self._category_history.get(category, [])

        # Gecmisten ogrenme: ortalama sapmayi hesapla
        if history:
            avg_actual = sum(history) / len(history)
            adjustment = avg_actual / base_hours if base_hours > 0 else 1.0
            adjusted = base_hours * min(3.0, max(0.5, adjustment))
        else:
            adjusted = base_hours

        buffer = adjusted * self._default_buffer
        confidence = min(1.0, len(history) / 10) if history else 0.3

        estimate = {
            "task_id": task_id,
            "category": category,
            "base_hours": base_hours,
            "adjusted_hours": round(adjusted, 2),
            "buffer_hours": round(buffer, 2),
            "total_hours": round(adjusted + buffer, 2),
            "confidence": round(confidence, 2),
            "low_estimate": round(adjusted * 0.8, 2),
            "high_estimate": round(
                (adjusted + buffer) * 1.2, 2,
            ),
        }
        self._estimates[task_id] = estimate
        return estimate

    def record_actual(
        self,
        task_id: str,
        actual_hours: float,
        category: str = "general",
    ) -> dict[str, Any]:
        """Gercek sureyi kaydeder.

        Args:
            task_id: Gorev ID.
            actual_hours: Gercek sure (saat).
            category: Kategori.

        Returns:
            Karsilastirma sonucu.
        """
        self._actuals[task_id] = actual_hours

        if category not in self._category_history:
            self._category_history[category] = []
        self._category_history[category].append(actual_hours)

        estimate = self._estimates.get(task_id)
        if estimate:
            variance = actual_hours - estimate["adjusted_hours"]
            accuracy = 1.0 - abs(variance) / max(
                1.0, estimate["adjusted_hours"],
            )
            return {
                "task_id": task_id,
                "estimated": estimate["adjusted_hours"],
                "actual": actual_hours,
                "variance": round(variance, 2),
                "accuracy": round(max(0.0, accuracy), 2),
            }

        return {
            "task_id": task_id,
            "estimated": None,
            "actual": actual_hours,
            "variance": None,
            "accuracy": None,
        }

    def get_confidence_interval(
        self,
        category: str,
    ) -> dict[str, Any]:
        """Guven araligi hesaplar.

        Args:
            category: Kategori.

        Returns:
            Guven araligi.
        """
        history = self._category_history.get(category, [])
        if len(history) < 2:
            return {
                "category": category,
                "mean": history[0] if history else 0.0,
                "std": 0.0,
                "lower": 0.0,
                "upper": 0.0,
                "samples": len(history),
            }

        mean = sum(history) / len(history)
        variance = sum(
            (x - mean) ** 2 for x in history
        ) / len(history)
        std = math.sqrt(variance)

        return {
            "category": category,
            "mean": round(mean, 2),
            "std": round(std, 2),
            "lower": round(mean - 2 * std, 2),
            "upper": round(mean + 2 * std, 2),
            "samples": len(history),
        }

    def get_accuracy_stats(self) -> dict[str, Any]:
        """Dogruluk istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        accuracies: list[float] = []
        for task_id, actual in self._actuals.items():
            est = self._estimates.get(task_id)
            if est:
                diff = abs(actual - est["adjusted_hours"])
                acc = 1.0 - diff / max(
                    1.0, est["adjusted_hours"],
                )
                accuracies.append(max(0.0, acc))

        if not accuracies:
            return {
                "avg_accuracy": 0.0,
                "total_estimates": len(self._estimates),
                "total_actuals": len(self._actuals),
            }

        return {
            "avg_accuracy": round(
                sum(accuracies) / len(accuracies), 2,
            ),
            "total_estimates": len(self._estimates),
            "total_actuals": len(self._actuals),
        }

    @property
    def estimate_count(self) -> int:
        """Tahmin sayisi."""
        return len(self._estimates)

    @property
    def actual_count(self) -> int:
        """Gercek kayit sayisi."""
        return len(self._actuals)

    @property
    def category_count(self) -> int:
        """Kategori sayisi."""
        return len(self._category_history)
